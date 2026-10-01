package com.ahmedelfashny.official;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

public class OfflineContentStoreTest {
    @Rule public TemporaryFolder temporary = new TemporaryFolder();

    private static byte[] bytes(String value) { return value.getBytes(StandardCharsets.UTF_8); }

    private static byte[] manifest(Map<String, String> values) throws Exception {
        JSONArray resources = new JSONArray();
        StringBuilder canonical = new StringBuilder();
        for (String key : new java.util.TreeSet<>(values.keySet())) {
            String path = key.substring(1);
            byte[] data = bytes(values.get(key));
            String hash = ContentManifest.sha256(data);
            resources.put(new JSONObject().put("key", key).put("path", path).put("sha256", hash)
                    .put("size", data.length).put("mime", "text/html"));
            canonical.append(key).append('\0').append(path).append('\0').append(hash).append('\0')
                    .append(data.length).append('\0').append("text/html").append('\n');
        }
        return bytes(new JSONObject().put("schema", 1).put("revision", ContentManifest.sha256(bytes(canonical.toString())))
                .put("resources", resources).toString());
    }

    private static OfflineContentStore.SeedSource seed(Map<String, String> values) throws Exception {
        byte[] manifest = manifest(values);
        Map<String, byte[]> objects = new HashMap<>();
        for (String value : values.values()) objects.put(ContentManifest.sha256(bytes(value)), bytes(value));
        return new OfflineContentStore.SeedSource() {
            public byte[] manifest() { return manifest; }
            public InputStream open(String hash) { return new ByteArrayInputStream(objects.get(hash)); }
        };
    }

    private static String read(OfflineContentStore store, ContentManifest snapshot, String key) throws Exception {
        try (InputStream stream = store.open(snapshot, key).stream) {
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    @Test public void firstOfflineLaunchReadsUnvisitedSeedPages() throws Exception {
        OfflineContentStore store = new OfflineContentStore(temporary.newFolder(), seed(Map.of("/index.html", "home", "/books/article.html", "article")));
        assertEquals("article", read(store, store.snapshot(), "/books/article.html"));
        assertNull(store.open(store.snapshot(), "/unknown.html"));
    }

    @Test public void unchangedRevisionPerformsNoResourceFetches() throws Exception {
        Map<String, String> values = Map.of("/index.html", "home");
        OfflineContentStore store = new OfflineContentStore(temporary.newFolder(), seed(values));
        AtomicInteger calls = new AtomicInteger();
        assertFalse(store.synchronize(manifest(values), path -> { calls.incrementAndGet(); throw new java.io.IOException("No network"); }));
        assertEquals(0, calls.get());
    }

    @Test public void changedRevisionFetchesOnlyChangedFileAndOldPageStaysPinned() throws Exception {
        OfflineContentStore store = new OfflineContentStore(temporary.newFolder(), seed(Map.of("/index.html", "home", "/books/article.html", "old")));
        ContentManifest old = store.snapshot();
        AtomicInteger calls = new AtomicInteger();
        assertTrue(store.synchronize(manifest(Map.of("/index.html", "home", "/books/article.html", "new")), path -> {
            calls.incrementAndGet(); assertEquals("books/article.html", path); return new ByteArrayInputStream(bytes("new"));
        }));
        assertEquals(1, calls.get());
        assertEquals("old", read(store, old, "/books/article.html"));
        assertEquals("new", read(store, store.snapshot(), "/books/article.html"));
    }

    @Test public void checksumFailureKeepsOldSnapshotAcrossRestart() throws Exception {
        File dir = temporary.newFolder();
        OfflineContentStore.SeedSource seed = seed(Map.of("/index.html", "seed"));
        OfflineContentStore store = new OfflineContentStore(dir, seed);
        store.synchronize(manifest(Map.of("/index.html", "good")), path -> new ByteArrayInputStream(bytes("good")));
        String revision = store.snapshot().revision;
        try {
            store.synchronize(manifest(Map.of("/index.html", "next")), path -> new ByteArrayInputStream(bytes("evil")));
            fail("Corrupt sync accepted");
        } catch (java.io.IOException expected) { }
        OfflineContentStore restarted = new OfflineContentStore(dir, seed);
        assertEquals(revision, restarted.snapshot().revision);
        assertEquals("good", read(restarted, restarted.snapshot(), "/index.html"));
    }

    @Test public void partialDownloadNeverPromotesAndRetryReusesVerifiedObject() throws Exception {
        OfflineContentStore store = new OfflineContentStore(temporary.newFolder(), seed(Map.of("/index.html", "seed")));
        byte[] update = manifest(Map.of("/index.html", "home2", "/books/new.html", "article"));
        try {
            store.synchronize(update, path -> { if (path.equals("index.html")) throw new java.io.IOException("disconnect"); return new ByteArrayInputStream(bytes("article")); });
            fail("Partial snapshot promoted");
        } catch (java.io.IOException expected) { }
        assertEquals("seed", read(store, store.snapshot(), "/index.html"));
        AtomicInteger calls = new AtomicInteger();
        store.synchronize(update, path -> { calls.incrementAndGet(); return new ByteArrayInputStream(bytes(path.equals("index.html") ? "home2" : "article")); });
        assertEquals(1, calls.get());
        assertEquals("article", read(store, store.snapshot(), "/books/new.html"));
    }

    @Test public void manifestRejectsPrivateTraversalAndRevisionTampering() throws Exception {
        for (String path : new String[]{"../secret", "admin/index.html", "downloads/app.apk", "data/%2e%2e/secret", "https://evil.test/x"}) {
            try { ContentManifest.parse(manifest(Map.of("/" + path, "home"))); fail("Unsafe manifest accepted: " + path); }
            catch (java.io.IOException expected) { }
        }
    }

    @Test public void requestKeysNormalizeOwnedCacheQueriesAndRejectOtherOrigins() {
        assertEquals("/index.html", ContentManifest.requestKey("https://ahmedelfashny.com/"));
        assertEquals("/books/a.html", ContentManifest.requestKey("https://www.ahmedelfashny.com/books/a.html?v=3"));
        assertNull(ContentManifest.requestKey("https://ahmedelfashny.com/data/%2e%2e/private"));
        assertNull(ContentManifest.requestKey("http://ahmedelfashny.com/index.html"));
        assertNull(ContentManifest.requestKey("https://ahmedelfashny.com.evil.test/index.html"));
        assertEquals("https://fonts.googleapis.com/css2?family=Amiri%3Awght%40400", ContentManifest.requestKey("https://fonts.googleapis.com/css2?family=Amiri%3Awght%40400"));
    }

    @Test public void slowNetworkSyncDoesNotBlockSnapshotReads() throws Exception {
        OfflineContentStore store = new OfflineContentStore(temporary.newFolder(), seed(Map.of("/index.html", "seed")));
        java.util.concurrent.CountDownLatch started = new java.util.concurrent.CountDownLatch(1);
        java.util.concurrent.CountDownLatch release = new java.util.concurrent.CountDownLatch(1);
        Thread thread = new Thread(() -> {
            try { store.synchronize(manifest(Map.of("/index.html", "next")), path -> {
                started.countDown(); try { release.await(); } catch (InterruptedException e) { throw new java.io.IOException(e); }
                return new ByteArrayInputStream(bytes("next"));
            }); } catch (Exception e) { throw new RuntimeException(e); }
        });
        thread.start(); assertTrue(started.await(2, java.util.concurrent.TimeUnit.SECONDS));
        java.util.concurrent.ExecutorService reader = java.util.concurrent.Executors.newSingleThreadExecutor();
        try {
            assertEquals("seed", reader.submit(() -> read(store, store.snapshot(), "/index.html")).get(300, java.util.concurrent.TimeUnit.MILLISECONDS));
        } finally { release.countDown(); thread.join(2000); reader.shutdownNow(); }
    }
}
