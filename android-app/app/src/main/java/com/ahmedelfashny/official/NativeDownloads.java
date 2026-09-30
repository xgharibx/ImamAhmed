package com.ahmedelfashny.official;

import android.app.Activity;
import android.content.Intent;
import android.content.ClipData;
import android.net.Uri;
import android.os.Bundle;
import android.util.Base64;
import android.webkit.CookieManager;
import android.webkit.URLUtil;
import android.widget.Toast;

import androidx.webkit.JavaScriptReplyProxy;
import androidx.webkit.WebViewFeature;
import androidx.core.content.FileProvider;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

final class NativeDownloads {
    static final int SAVE_REQUEST = 43;
    private final Activity activity;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private File pending;
    private FileOutputStream stream;
    private long received;
    private long expected;
    private String filename;
    private boolean choosing;
    private String mime = "application/pdf";
    private String operation = "save";
    private boolean stateSaved;
    private volatile boolean closed;
    private volatile HttpURLConnection activeConnection;

    NativeDownloads(Activity activity, Bundle state) {
        this.activity = activity;
        if (state != null && state.containsKey("pendingDownload")) {
            try {
                File restored = new File(state.getString("pendingDownload", ""));
                if (restored.getCanonicalPath().startsWith(activity.getCacheDir().getCanonicalPath() + File.separator)
                        && restored.isFile() && restored.length() <= DownloadPolicy.MAX_BYTES) {
                    pending = restored;
                    mime = state.getString("downloadMime", "application/pdf");
                    filename = DownloadPolicy.filename(state.getString("downloadName"), mime);
                    choosing = true;
                }
            } catch (Exception ignored) { /* A removed cache file is reported when the picker returns. */ }
        }
        File shared = new File(activity.getCacheDir(), "shared");
        File[] oldShares = shared.listFiles();
        if (oldShares != null) for (File file : oldShares) {
            if (file.lastModified() < System.currentTimeMillis() - 86400000L) file.delete();
        }
    }

    void saveState(Bundle state) {
        if (choosing && pending != null) {
            state.putString("pendingDownload", pending.getAbsolutePath());
            state.putString("downloadName", filename);
            state.putString("downloadMime", mime);
            stateSaved = true;
        }
    }

    void message(String raw, JavaScriptReplyProxy reply) {
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) return;
        int id = -1;
        boolean touchedTransfer = false;
        try {
            if (closed) throw new IllegalStateException("Activity closed");
            if (raw == null || raw.length() > 70000) throw new IllegalArgumentException("Invalid message");
            JSONObject message = new JSONObject(raw);
            id = message.getInt("id");
            switch (message.getString("type")) {
                case "start":
                    if (pending != null || choosing) throw new IllegalStateException("A download is already active");
                    expected = message.getLong("size");
                    if (expected <= 0 || expected > DownloadPolicy.MAX_BYTES) throw new IllegalArgumentException("Invalid PDF size");
                    mime = message.optString("mime", "application/pdf");
                    operation = message.optString("operation", "save");
                    if (!DownloadPolicy.supportedMime(mime) || !(operation.equals("save") || operation.equals("share"))) throw new IllegalArgumentException("Unsupported file");
                    filename = DownloadPolicy.filename(message.optString("name"), mime);
                    File directory = operation.equals("share") ? new File(activity.getCacheDir(), "shared") : activity.getCacheDir();
                    if (!directory.exists() && !directory.mkdirs()) throw new IllegalStateException("No cache directory");
                    touchedTransfer = true;
                    pending = File.createTempFile("download-", "-" + filename, directory);
                    stream = new FileOutputStream(pending);
                    received = 0;
                    break;
                case "chunk":
                    if (stream == null) throw new IllegalStateException("No active download");
                    touchedTransfer = true;
                    byte[] bytes = Base64.decode(message.getString("data"), Base64.NO_WRAP);
                    if (bytes.length > 49152 || received + bytes.length > expected) throw new IllegalArgumentException("Invalid chunk");
                    if (received == 0 && !DownloadPolicy.validHeader(bytes, mime)) {
                        throw new IllegalArgumentException("Invalid file header");
                    }
                    stream.write(bytes);
                    received += bytes.length;
                    break;
                case "finish":
                    touchedTransfer = stream != null;
                    if (stream == null || received != expected) throw new IllegalArgumentException("Incomplete PDF");
                    stream.close(); stream = null;
                    if (operation.equals("share")) {
                        Uri fileUri = FileProvider.getUriForFile(activity, BuildConfig.APPLICATION_ID + ".files", pending);
                        Intent fileShare = new Intent(Intent.ACTION_SEND).setType(mime)
                                .putExtra(Intent.EXTRA_STREAM, fileUri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        fileShare.setClipData(ClipData.newRawUri(filename, fileUri));
                        activity.startActivity(Intent.createChooser(fileShare, activity.getString(R.string.share)));
                        pending = null;
                    } else chooseDestination();
                    break;
                case "cancel":
                    if (!choosing) cleanup();
                    break;
                case "share":
                    String url = message.optString("url");
                    if (!url.isEmpty() && !DownloadPolicy.isOwnedHttps(url)) throw new IllegalArgumentException("Invalid share URL");
                    Intent share = new Intent(Intent.ACTION_SEND).setType("text/plain");
                    share.putExtra(Intent.EXTRA_SUBJECT, message.optString("title"));
                    share.putExtra(Intent.EXTRA_TEXT, message.optString("text") + (url.isEmpty() ? "" : "\n" + url));
                    activity.startActivity(Intent.createChooser(share, activity.getString(R.string.share)));
                    break;
                default: throw new IllegalArgumentException("Unknown operation");
            }
            reply.postMessage(new JSONObject().put("id", id).put("ok", true).toString());
        } catch (Exception error) {
            if (touchedTransfer && !choosing) cleanup();
            try { reply.postMessage(new JSONObject().put("id", id).put("ok", false).put("error", error.getMessage()).toString()); }
            catch (Exception ignored) { /* A navigation may have removed the calling frame. */ }
        }
    }

    void download(String url, String disposition, String userAgent) {
        if (!DownloadPolicy.isOwnedHttps(url) || pending != null || choosing) {
            Toast.makeText(activity, R.string.download_failed, Toast.LENGTH_LONG).show();
            return;
        }
        filename = DownloadPolicy.pdfFilename(URLUtil.guessFileName(url, disposition, "application/pdf"));
        mime = "application/pdf";
        String cookies = CookieManager.getInstance().getCookie(url);
        choosing = true;
        worker.execute(() -> {
            File file = null;
            try {
                file = File.createTempFile("pdf-", ".pdf", activity.getCacheDir());
                String current = url;
                HttpURLConnection connection = null;
                for (int redirect = 0; redirect < 6; redirect++) {
                    if (!DownloadPolicy.isOwnedHttps(current)) throw new IllegalArgumentException("Untrusted redirect");
                    connection = (HttpURLConnection) new URL(current).openConnection();
                    activeConnection = connection;
                    if (closed) throw new IllegalStateException("Activity closed");
                    connection.setInstanceFollowRedirects(false);
                    connection.setConnectTimeout(20000); connection.setReadTimeout(30000);
                    connection.setRequestProperty("User-Agent", userAgent);
                    if (cookies != null) connection.setRequestProperty("Cookie", cookies);
                    int status = connection.getResponseCode();
                    if (status >= 300 && status < 400) {
                        String location = connection.getHeaderField("Location");
                        String next = location == null ? "" : new URL(new URL(current), location).toString();
                        connection.disconnect(); connection = null; current = next;
                    } else {
                        if (status != 200) { connection.disconnect(); throw new IllegalArgumentException("HTTP " + status); }
                        break;
                    }
                }
                if (connection == null) throw new IllegalArgumentException("Too many redirects");
                try (InputStream input = connection.getInputStream(); OutputStream output = new FileOutputStream(file)) {
                    byte[] header = new byte[5];
                    int length = 0;
                    while (length < 5) { int read = input.read(header, length, 5 - length); if (read < 0) break; length += read; }
                    if (length != 5 || !new String(header, StandardCharsets.US_ASCII).equals("%PDF-")) throw new IllegalArgumentException("Not a PDF");
                    output.write(header); copy(input, output, DownloadPolicy.MAX_BYTES - 5);
                } finally { connection.disconnect(); }
                File ready = file;
                activity.runOnUiThread(() -> {
                    if (closed || activity.isFinishing() || activity.isDestroyed()) { ready.delete(); return; }
                    pending = ready; choosing = false; chooseDestination();
                });
            } catch (Exception error) {
                if (file != null) file.delete();
                activity.runOnUiThread(() -> { choosing = false; if (!closed) Toast.makeText(activity, R.string.download_failed, Toast.LENGTH_LONG).show(); });
            } finally {
                if (activeConnection != null) { activeConnection.disconnect(); activeConnection = null; }
            }
        });
    }

    private void chooseDestination() {
        if (closed || activity.isDestroyed() || activity.isFinishing()) { cleanup(); return; }
        choosing = true;
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType(mime).putExtra(Intent.EXTRA_TITLE, filename);
        try { activity.startActivityForResult(intent, SAVE_REQUEST); }
        catch (Exception error) { choosing = false; cleanup(); Toast.makeText(activity, R.string.download_failed, Toast.LENGTH_LONG).show(); }
    }

    void result(int resultCode, Intent data) {
        choosing = false;
        if (resultCode != Activity.RESULT_OK || data == null || data.getData() == null) { cleanup(); return; }
        if (pending == null) { Toast.makeText(activity, R.string.download_failed, Toast.LENGTH_LONG).show(); return; }
        Uri destination = data.getData();
        File file = pending; pending = null;
        worker.execute(() -> {
            boolean success = false;
            try (InputStream input = new FileInputStream(file); OutputStream output = activity.getContentResolver().openOutputStream(destination, "w")) {
                if (output == null) throw new IllegalArgumentException("No destination");
                copy(input, output, DownloadPolicy.MAX_BYTES); success = true;
            } catch (Exception ignored) { /* Report below, without exposing the user's document URI. */ }
            finally { file.delete(); }
            boolean saved = success;
            activity.runOnUiThread(() -> { if (!closed) Toast.makeText(activity, saved ? R.string.download_saved : R.string.download_failed, Toast.LENGTH_LONG).show(); });
        });
    }

    private static void copy(InputStream input, OutputStream output, long limit) throws Exception {
        byte[] buffer = new byte[32768]; long total = 0; int count;
        while ((count = input.read(buffer)) != -1) {
            total += count;
            if (total > limit) throw new IllegalArgumentException("PDF too large");
            output.write(buffer, 0, count);
        }
    }

    private void cleanup() {
        if (stream != null) { try { stream.close(); } catch (Exception ignored) {} stream = null; }
        if (pending != null) { pending.delete(); pending = null; }
    }

    void close() {
        closed = true;
        HttpURLConnection connection = activeConnection;
        if (connection != null) connection.disconnect();
        if (!(choosing && stateSaved && pending != null)) cleanup();
        worker.shutdownNow();
    }
}
