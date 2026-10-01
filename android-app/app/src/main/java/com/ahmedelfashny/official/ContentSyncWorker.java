package com.ahmedelfashny.official;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import java.io.File;
import java.io.FilterInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.TimeUnit;

public final class ContentSyncWorker extends Worker {
    private static OfflineContentStore repository;

    public ContentSyncWorker(@NonNull Context context, @NonNull WorkerParameters parameters) { super(context, parameters); }

    static synchronized OfflineContentStore store(Context context) throws IOException {
        if (repository == null) {
            Context app = context.getApplicationContext();
            repository = new OfflineContentStore(new File(app.getFilesDir(), "offline-content"), new OfflineContentStore.SeedSource() {
                public byte[] manifest() throws IOException { return OfflineContentStore.readLimited(app.getAssets().open("offline/manifest.json"), ContentManifest.MAX_MANIFEST); }
                public InputStream open(String hash) throws IOException { return app.getAssets().open("offline/objects/" + hash); }
            });
        }
        return repository;
    }

    static void enqueue(Context context) {
        Constraints connected = new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build();
        WorkManager manager = WorkManager.getInstance(context);
        manager.enqueueUniqueWork("content-check", ExistingWorkPolicy.KEEP,
                new OneTimeWorkRequest.Builder(ContentSyncWorker.class).setConstraints(connected)
                        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS).build());
        manager.enqueueUniquePeriodicWork("content-maintenance", ExistingPeriodicWorkPolicy.KEEP,
                new PeriodicWorkRequest.Builder(ContentSyncWorker.class, 6, TimeUnit.HOURS).setConstraints(connected)
                        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS).build());
    }

    @NonNull @Override public Result doWork() {
        SharedPreferences preferences = getApplicationContext().getSharedPreferences("content-sync", Context.MODE_PRIVATE);
        HttpURLConnection manifestConnection = null;
        try {
            OfflineContentStore content = store(getApplicationContext());
            manifestConnection = connect("data/app-content-manifest.json", preferences.getString("etag", null));
            int status = manifestConnection.getResponseCode();
            if (status == HttpURLConnection.HTTP_NOT_MODIFIED) return Result.success();
            if (status != HttpURLConnection.HTTP_OK) throw new IOException("Manifest HTTP " + status);
            byte[] manifest = OfflineContentStore.readLimited(manifestConnection.getInputStream(), ContentManifest.MAX_MANIFEST);
            boolean changed = content.synchronize(manifest, path -> {
                if (isStopped()) throw new IOException("Sync interrupted");
                HttpURLConnection connection = connect(path, null);
                if (connection.getResponseCode() != HttpURLConnection.HTTP_OK) { connection.disconnect(); throw new IOException("Resource unavailable"); }
                return new FilterInputStream(connection.getInputStream()) {
                    @Override public int read(byte[] buffer, int offset, int length) throws IOException {
                        if (isStopped()) throw new IOException("Sync interrupted");
                        return super.read(buffer, offset, length);
                    }
                    @Override public void close() throws IOException { try { super.close(); } finally { connection.disconnect(); } }
                };
            });
            preferences.edit().putString("etag", manifestConnection.getHeaderField("ETag")).apply();
            android.util.Log.i("ContentSync", changed ? "Activated " + content.snapshot().revision : "Content unchanged");
            return Result.success();
        } catch (IOException | RuntimeException error) {
            android.util.Log.w("ContentSync", "Keeping last complete offline content", error);
            return getRunAttemptCount() < 5 ? Result.retry() : Result.failure();
        } finally { if (manifestConnection != null) manifestConnection.disconnect(); }
    }

    private static HttpURLConnection connect(String path, String etag) throws IOException {
        if (!path.equals("data/app-content-manifest.json") && !ContentManifest.safePath(path)) throw new IOException("Unsafe download path");
        URL url = new URL(BuildConfig.LIVE_SITE_URL + new android.net.Uri.Builder().path(path).build().toString());
        for (int redirects = 0; redirects < 5; redirects++) {
            if (!DownloadPolicy.isOwnedHttps(url.toString())) throw new IOException("Untrusted content redirect");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(15000); connection.setReadTimeout(20000);
            connection.setInstanceFollowRedirects(false); connection.setUseCaches(false);
            connection.setRequestProperty("Cache-Control", "no-cache");
            if (etag != null) connection.setRequestProperty("If-None-Match", etag);
            int status = connection.getResponseCode();
            if (status >= 300 && status <= 399 && status != HttpURLConnection.HTTP_NOT_MODIFIED) {
                String location = connection.getHeaderField("Location"); connection.disconnect();
                if (location == null) throw new IOException("Invalid redirect");
                url = new URL(url, location);
            } else return connection;
        }
        throw new IOException("Too many content redirects");
    }
}
