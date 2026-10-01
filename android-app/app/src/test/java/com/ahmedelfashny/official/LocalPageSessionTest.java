package com.ahmedelfashny.official;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import static org.junit.Assert.*;

public class LocalPageSessionTest {
    @Rule public TemporaryFolder temporary = new TemporaryFolder();
    private static byte[] bytes(String value) { return value.getBytes(StandardCharsets.UTF_8); }
    private static byte[] manifest(String data) throws Exception {
        JSONArray entries = new JSONArray(); StringBuilder canonical = new StringBuilder();
        for (String key : new String[]{"/data/videos.json", "/index.html"}) {
            String value = key.endsWith("json") ? data : "<html><head></head><body>Original</body></html>";
            String path = key.substring(1), hash = ContentManifest.sha256(bytes(value)), mime = key.endsWith("json") ? "application/json" : "text/html";
            entries.put(new JSONObject().put("key", key).put("path", path).put("sha256", hash).put("size", bytes(value).length).put("mime", mime));
            canonical.append(key).append('\0').append(path).append('\0').append(hash).append('\0').append(bytes(value).length).append('\0').append(mime).append('\n');
        }
        return bytes(new JSONObject().put("schema", 1).put("revision", ContentManifest.sha256(bytes(canonical.toString()))).put("resources", entries).toString());
    }
    @Test public void catalogStaysPinnedUntilNextMainFrameAndOfflineHtmlSuppressesLoader() throws Exception {
        byte[] seed = manifest("old");
        Map<String, String> values = Map.of(ContentManifest.sha256(bytes("old")), "old", ContentManifest.sha256(bytes("<html><head></head><body>Original</body></html>")), "<html><head></head><body>Original</body></html>");
        OfflineContentStore store = new OfflineContentStore(temporary.newFolder(), new OfflineContentStore.SeedSource() {
            public byte[] manifest() { return seed; }
            public InputStream open(String hash) { return new ByteArrayInputStream(bytes(values.get(hash))); }
        });
        LocalPageSession page = new LocalPageSession(store);
        String html = new String(page.open("https://ahmedelfashny.com/", true).stream.readAllBytes(), StandardCharsets.UTF_8);
        assertTrue(html.contains("#preloader{display:none!important}"));
        assertTrue(html.contains("<body>Original</body>"));
        store.synchronize(manifest("new"), path -> new ByteArrayInputStream(bytes("new")));
        assertEquals("old", new String(page.open("https://ahmedelfashny.com/data/videos.json?t=1", false).stream.readAllBytes(), StandardCharsets.UTF_8));
        page.open("https://ahmedelfashny.com/index.html", true).stream.close();
        assertEquals("new", new String(page.open("https://ahmedelfashny.com/data/videos.json", false).stream.readAllBytes(), StandardCharsets.UTF_8));
        assertNull(page.open("https://youtube-nocookie.com/embed/video", false));
        assertNull(page.open("https://evil.test/index.html", true));
    }

    @Test public void unknownReadingPageUsesNetworkForAllItsResources() throws Exception {
        byte[] seed = manifest("old");
        Map<String, String> values = Map.of(ContentManifest.sha256(bytes("old")), "old", ContentManifest.sha256(bytes("<html><head></head><body>Original</body></html>")), "<html><head></head><body>Original</body></html>");
        OfflineContentStore store = new OfflineContentStore(temporary.newFolder(), new OfflineContentStore.SeedSource() {
            public byte[] manifest() { return seed; }
            public InputStream open(String hash) { return new ByteArrayInputStream(bytes(values.get(hash))); }
        });
        LocalPageSession page = new LocalPageSession(store);
        assertNull(page.open("https://ahmedelfashny.com/books/not-yet-synced.html", true));
        assertNull(page.open("https://ahmedelfashny.com/data/videos.json", false));
        assertNotNull(page.open("https://ahmedelfashny.com/index.html", true));
        assertNotNull(page.open("https://ahmedelfashny.com/data/videos.json", false));
    }
}
