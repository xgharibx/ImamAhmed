package com.ahmedelfashny.official;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.WeakHashMap;

final class OfflineContentStore {
    interface SeedSource {
        byte[] manifest() throws IOException;
        InputStream open(String hash) throws IOException;
    }
    interface Fetcher { InputStream fetch(String publicPath) throws IOException; }
    static final class LocalResource {
        final InputStream stream;
        final String mime;
        LocalResource(InputStream stream, String mime) { this.stream = stream; this.mime = mime; }
    }

    private final File directory, objects;
    private final SeedSource source;
    private final ContentManifest seed;
    private final Set<String> seedHashes = new HashSet<>();
    private final WeakHashMap<ContentManifest, Boolean> pinned = new WeakHashMap<>();
    private final Object syncLock = new Object();
    private volatile ContentManifest active;
    private ContentManifest previous;
    private long sequence;

    OfflineContentStore(File directory, SeedSource source) throws IOException {
        this.directory = directory; this.objects = new File(directory, "objects"); this.source = source;
        this.seed = ContentManifest.parse(source.manifest());
        for (ContentManifest.Resource entry : seed.resources.values()) seedHashes.add(entry.sha256);
        if (!objects.isDirectory() && !objects.mkdirs()) throw new IOException("Content storage unavailable");
        active = seed;
        File[] commits = directory.listFiles((dir, name) -> name.matches("[0-9]{16}-[a-f0-9]{64}\\.json"));
        if (commits != null) {
            Arrays.sort(commits, (left, right) -> right.getName().compareTo(left.getName()));
            for (File commit : commits) {
                sequence = Math.max(sequence, Long.parseLong(commit.getName().substring(0, 16)));
                try {
                    ContentManifest snapshot = ContentManifest.parse(readLimited(new FileInputStream(commit), ContentManifest.MAX_MANIFEST));
                    if (complete(snapshot)) { if (active == seed) active = snapshot; else { previous = snapshot; break; } }
                } catch (IOException ignored) { /* Incomplete/corrupt revisions never replace the seed. */ }
            }
        }
        prune();
    }

    synchronized ContentManifest snapshot() {
        pinned.put(active, Boolean.TRUE);
        return active;
    }

    LocalResource open(ContentManifest snapshot, String resourceKey) throws IOException {
        if (snapshot == null || resourceKey == null) return null;
        ContentManifest.Resource entry = snapshot.resources.get(resourceKey);
        if (entry == null) return null;
        InputStream stream = seedHashes.contains(entry.sha256) ? source.open(entry.sha256) : new FileInputStream(new File(objects, entry.sha256));
        return new LocalResource(stream, entry.mime);
    }

    boolean synchronize(byte[] encoded, Fetcher fetcher) throws IOException {
        synchronized (syncLock) { return synchronizeLocked(encoded, fetcher); }
    }

    private boolean synchronizeLocked(byte[] encoded, Fetcher fetcher) throws IOException {
        ContentManifest next = ContentManifest.parse(encoded);
        if (next.revision.equals(active.revision)) return false;
        for (ContentManifest.Resource entry : next.resources.values()) {
            if (seedHashes.contains(entry.sha256)) continue;
            File object = new File(objects, entry.sha256);
            if (verified(object, entry)) continue;
            enforceDiskBudget(entry.size);
            File pending = new File(objects, entry.sha256 + ".pending");
            try (InputStream input = fetcher.fetch(entry.path); FileOutputStream output = new FileOutputStream(pending)) {
                MessageDigest digest = ContentManifest.digest();
                byte[] buffer = new byte[16384];
                int count, total = 0;
                while ((count = input.read(buffer)) != -1) {
                    total += count;
                    if (total > entry.size) throw new IOException("Oversized content response");
                    digest.update(buffer, 0, count); output.write(buffer, 0, count);
                }
                if (total != entry.size || !entry.sha256.equals(ContentManifest.hex(digest.digest()))) throw new IOException("Content checksum/length mismatch");
                output.getFD().sync();
            } catch (IOException error) { pending.delete(); throw error; }
            if (object.exists() && !object.delete()) throw new IOException("Cannot replace corrupt resource");
            if (!pending.renameTo(object)) throw new IOException("Cannot commit resource");
        }
        // Immutable, increasing journal names make activation one atomic rename.
        // There is no mutable pointer that can be truncated by process death.
        String name = String.format(java.util.Locale.ROOT, "%016d-%s.json", ++sequence, next.revision);
        File pending = new File(directory, name + ".pending");
        try (FileOutputStream output = new FileOutputStream(pending)) { output.write(encoded); output.getFD().sync(); }
        if (!pending.renameTo(new File(directory, name))) throw new IOException("Cannot activate content revision");
        synchronized (this) { previous = active; active = next; prune(); }
        return true;
    }

    private void enforceDiskBudget(int incoming) throws IOException {
        if (diskBytes() + incoming <= ContentManifest.MAX_TOTAL * 2) return;
        prune();
        if (diskBytes() + incoming > ContentManifest.MAX_TOTAL * 2) throw new IOException("Content disk budget exceeded");
    }

    private long diskBytes() {
        long total = 0;
        File[] files = objects.listFiles();
        if (files != null) for (File file : files) total += file.length();
        return total;
    }

    private boolean complete(ContentManifest snapshot) throws IOException {
        for (ContentManifest.Resource entry : snapshot.resources.values()) {
            if (!seedHashes.contains(entry.sha256) && !verified(new File(objects, entry.sha256), entry)) return false;
        }
        return true;
    }

    private boolean verified(File file, ContentManifest.Resource entry) throws IOException {
        if (!file.isFile() || file.length() != entry.size) return false;
        MessageDigest digest = ContentManifest.digest();
        try (InputStream input = new FileInputStream(file)) {
            byte[] buffer = new byte[16384]; int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        return entry.sha256.equals(ContentManifest.hex(digest.digest()));
    }

    private synchronized void prune() {
        Set<String> keep = new HashSet<>(), revisions = new HashSet<>();
        List<ContentManifest> snapshots = new ArrayList<>(pinned.keySet());
        snapshots.add(active); if (previous != null) snapshots.add(previous);
        for (ContentManifest snapshot : snapshots) {
            if (snapshot == null) continue;
            revisions.add(snapshot.revision);
            for (ContentManifest.Resource entry : snapshot.resources.values()) keep.add(entry.sha256);
        }
        File[] files = objects.listFiles();
        if (files != null) for (File file : files) if (!keep.contains(file.getName())) file.delete();
        File[] commits = directory.listFiles();
        if (commits != null) for (File file : commits) {
            if (file.getName().endsWith(".pending")) file.delete();
            else if (file.getName().matches("[0-9]{16}-[a-f0-9]{64}\\.json") && !revisions.contains(file.getName().substring(17, 81))) file.delete();
        }
    }

    static byte[] readLimited(InputStream input, int limit) throws IOException {
        try (InputStream stream = input; ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[16384]; int count;
            while ((count = stream.read(buffer)) != -1) {
                if (output.size() + count > limit) throw new IOException("Response size limit exceeded");
                output.write(buffer, 0, count);
            }
            return output.toByteArray();
        }
    }
}
