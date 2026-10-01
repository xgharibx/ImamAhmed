package com.ahmedelfashny.official;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

final class LocalPageSession {
    private final OfflineContentStore store;
    private volatile ContentManifest page;

    LocalPageSession(OfflineContentStore store) { this.store = store; this.page = store.snapshot(); }

    OfflineContentStore.LocalResource open(String url, boolean mainFrame) throws IOException {
        String key = ContentManifest.requestKey(url);
        if (key == null) return null;
        if (mainFrame && key.startsWith("/") && key.endsWith(".html")) page = store.snapshot();
        ContentManifest snapshot = page;
        OfflineContentStore.LocalResource resource = store.open(snapshot, key);
        if (resource == null || !resource.mime.equals("text/html")) return resource;
        String html = new String(OfflineContentStore.readLimited(resource.stream, ContentManifest.MAX_FILE), StandardCharsets.UTF_8);
        String appOnly = "<style id=\"app-offline-preloader\">#preloader{display:none!important}</style>"
                + "<meta name=\"app-content-revision\" content=\"" + snapshot.revision + "\">";
        int head = html.toLowerCase(java.util.Locale.ROOT).indexOf("<head>");
        html = head >= 0 ? html.substring(0, head + 6) + appOnly + html.substring(head + 6) : appOnly + html;
        return new OfflineContentStore.LocalResource(new ByteArrayInputStream(html.getBytes(StandardCharsets.UTF_8)), resource.mime);
    }
}
