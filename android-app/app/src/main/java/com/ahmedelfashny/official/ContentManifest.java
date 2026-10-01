package com.ahmedelfashny.official;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Collections;
import java.util.Map;
import java.util.TreeMap;

final class ContentManifest {
    static final int MAX_MANIFEST = 5 * 1024 * 1024;
    static final int MAX_FILE = 32 * 1024 * 1024;
    static final long MAX_TOTAL = 384L * 1024 * 1024;
    private static final String[] CDN_PREFIXES = {
            "https://fonts.googleapis.com/css", "https://fonts.gstatic.com/s/",
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/",
            "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/",
            "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/",
            "https://cdnjs.cloudflare.com/ajax/libs/jspdf/", "https://unpkg.com/aos@2.3.1/dist/",
            "https://i.ytimg.com/vi/", "https://img.youtube.com/vi/"
    };
    final String revision;
    final Map<String, Resource> resources;
    final byte[] encoded;

    static final class Resource {
        final String key, path, sha256, mime;
        final int size;
        Resource(String key, String path, String hash, int size, String mime) {
            this.key = key; this.path = path; this.sha256 = hash; this.size = size; this.mime = mime;
        }
    }

    private ContentManifest(String revision, Map<String, Resource> resources, byte[] encoded) {
        this.revision = revision;
        this.resources = Collections.unmodifiableMap(resources);
        this.encoded = encoded.clone();
    }

    static ContentManifest parse(byte[] encoded) throws IOException {
        if (encoded.length == 0 || encoded.length > MAX_MANIFEST) throw new IOException("Manifest size rejected");
        try {
            JSONObject json = new JSONObject(new String(encoded, StandardCharsets.UTF_8));
            if (json.getInt("schema") != 1) throw new IOException("Unsupported content schema");
            String revision = json.getString("revision");
            JSONArray entries = json.getJSONArray("resources");
            if (entries.length() == 0 || entries.length() > 10000) throw new IOException("Invalid resource count");
            Map<String, Resource> resources = new TreeMap<>();
            long total = 0;
            for (int i = 0; i < entries.length(); i++) {
                JSONObject entry = entries.getJSONObject(i);
                String key = entry.getString("key"), path = entry.getString("path");
                String hash = entry.getString("sha256"), mime = entry.getString("mime");
                long size = entry.getLong("size");
                String normalized = requestKey(key.startsWith("/") ? "https://ahmedelfashny.com" + key : key);
                if (!key.equals(normalized) || !safePath(path) || !hash.matches("[a-f0-9]{64}")
                        || size <= 0 || size > MAX_FILE || !allowedMime(mime)) throw new IOException("Unsafe resource entry");
                if (key.startsWith("https://") && !path.startsWith("assets/app-content/")) throw new IOException("Unsafe mirror path");
                if (key.startsWith("/") && !key.equals("/" + path)) throw new IOException("Owned key/path mismatch");
                if (resources.put(key, new Resource(key, path, hash, (int) size, mime)) != null) throw new IOException("Duplicate key");
                total += size;
                if (total > MAX_TOTAL) throw new IOException("Content storage limit exceeded");
            }
            StringBuilder canonical = new StringBuilder();
            for (Resource entry : resources.values()) {
                canonical.append(entry.key).append('\0').append(entry.path).append('\0').append(entry.sha256)
                        .append('\0').append(entry.size).append('\0').append(entry.mime).append('\n');
            }
            if (!revision.equals(sha256(canonical.toString().getBytes(StandardCharsets.UTF_8)))) throw new IOException("Manifest revision mismatch");
            return new ContentManifest(revision, resources, encoded);
        } catch (JSONException | IllegalArgumentException error) {
            throw new IOException("Invalid content manifest", error);
        }
    }

    static String requestKey(String url) {
        try {
            URI uri = new URI(url);
            if (!"https".equals(uri.getScheme()) || uri.getUserInfo() != null || (uri.getPort() != -1 && uri.getPort() != 443)) return null;
            String host = uri.getHost(), path = uri.getPath();
            if (path == null || unsafeSegments(path)) return null;
            if ("ahmedelfashny.com".equals(host) || "www.ahmedelfashny.com".equals(host)) {
                if (path.isEmpty() || path.equals("/")) return "/index.html";
                return path.startsWith("/") && safePath(path.substring(1)) ? path : null;
            }
            for (String prefix : CDN_PREFIXES) {
                if (url.startsWith(prefix)) return url.split("#", 2)[0];
            }
        } catch (java.net.URISyntaxException | IllegalArgumentException ignored) { }
        return null;
    }

    private static boolean unsafeSegments(String path) {
        if (path.indexOf('\\') >= 0 || path.indexOf('\0') >= 0 || path.indexOf('\r') >= 0 || path.indexOf('\n') >= 0) return true;
        for (String segment : path.split("/", -1)) if (segment.equals(".") || segment.equals("..")) return true;
        return false;
    }

    static boolean safePath(String path) {
        if (path.isEmpty() || path.startsWith("/") || path.contains("%") || path.contains(":") || unsafeSegments(path)) return false;
        boolean publicPath = !path.contains("/") || path.startsWith("books/") || path.startsWith("khutab/") || path.startsWith("data/") || path.startsWith("assets/");
        return publicPath && path.matches(".+\\.(html|css|js|json|png|jpg|jpeg|webp|svg|gif|ico|woff|woff2|ttf|eot)")
                && !path.equals("data/app-content-manifest.json") && !path.equals("data/video-sync-status.json");
    }

    private static boolean allowedMime(String mime) {
        return mime.matches("(text/(html|css)|application/(javascript|json|vnd.ms-fontobject)|image/(png|jpeg|webp|svg\\+xml|gif|x-icon|vnd.microsoft.icon)|font/(woff|woff2|ttf)|application/font-woff)");
    }

    static String sha256(byte[] value) {
        return hex(digest().digest(value));
    }

    static MessageDigest digest() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }

    static String hex(byte[] value) {
        StringBuilder out = new StringBuilder();
        for (byte part : value) out.append(String.format(java.util.Locale.ROOT, "%02x", part & 255));
        return out.toString();
    }
}
