package com.ahmedelfashny.official;

import android.content.Context;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class OfflineSyncDeviceTest {
    private static byte[] bytes(String value) { return value.getBytes(StandardCharsets.UTF_8); }

    private byte[] updated(ContentManifest base, Map<String, byte[]> files) throws Exception {
        TreeMap<String, JSONObject> entries = new TreeMap<>();
        JSONArray original = new JSONObject(new String(base.encoded, StandardCharsets.UTF_8)).getJSONArray("resources");
        for (int i = 0; i < original.length(); i++) entries.put(original.getJSONObject(i).getString("key"), original.getJSONObject(i));
        for (Map.Entry<String, byte[]> file : files.entrySet()) {
            String path = file.getKey(); byte[] content = file.getValue();
            entries.put("/" + path, new JSONObject().put("key", "/" + path).put("path", path).put("sha256", ContentManifest.sha256(content))
                    .put("size", content.length).put("mime", path.endsWith(".json") ? "application/json" : "text/html"));
        }
        StringBuilder canonical = new StringBuilder(); JSONArray resources = new JSONArray();
        for (JSONObject entry : entries.values()) {
            resources.put(entry);
            canonical.append(entry.getString("key")).append('\0').append(entry.getString("path")).append('\0').append(entry.getString("sha256"))
                    .append('\0').append(entry.getInt("size")).append('\0').append(entry.getString("mime")).append('\n');
        }
        return bytes(new JSONObject().put("schema", 1).put("revision", ContentManifest.sha256(bytes(canonical.toString())))
                .put("resources", resources).toString());
    }

    @Test public void incrementalDeviceSyncSurvivesRestartAndRejectsCorruptFollowup() throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        OfflineContentStore store = ContentSyncWorker.store(context);
        ContentManifest old = store.snapshot();
        byte[] catalog = OfflineContentStore.readLimited(store.open(old, "/data/videos.json").stream, ContentManifest.MAX_FILE);
        JSONArray videos = new JSONArray(new String(catalog, StandardCharsets.UTF_8));
        videos.getJSONObject(0).put("title", videos.getJSONObject(0).getString("title") + " [OFFLINE SYNC QA]");
        Map<String, byte[]> changed = new HashMap<>();
        changed.put("data/videos.json", bytes(videos.toString()));
        changed.put("books/offline-sync-qa.html", bytes("<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><link rel='stylesheet' href='../style.css'></head>"
                + "<body><h1>OFFLINE SYNC QA</h1><p>New downloaded article is available without internet.</p></body></html>"));
        byte[] manifest = updated(old, changed);
        AtomicInteger downloads = new AtomicInteger();
        assertTrue(store.synchronize(manifest, path -> { downloads.incrementAndGet(); assertTrue(changed.containsKey(path)); return new ByteArrayInputStream(changed.get(path)); }));
        assertEquals(2, downloads.get());
        assertFalse(store.synchronize(manifest, path -> { fail("Unchanged revision fetched a resource"); return null; }));
        ContentManifest active = store.snapshot();
        assertArrayEquals(catalog, OfflineContentStore.readLimited(store.open(old, "/data/videos.json").stream, ContentManifest.MAX_FILE));
        Map<String, byte[]> corrupt = new HashMap<>(); corrupt.put("books/offline-sync-qa.html", bytes("Different valid expected content"));
        try { store.synchronize(updated(active, corrupt), path -> new ByteArrayInputStream(bytes("corrupt"))); fail("Corrupt update accepted"); }
        catch (IOException expected) { }
        assertEquals(active.revision, store.snapshot().revision);
        android.util.Log.i("OfflineSyncQA", "PASSED: two changed downloads, unchanged=0, pinned old catalog, corrupt rollback. Revision " + active.revision);
    }
}
