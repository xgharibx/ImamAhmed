# Offline Android Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for the Android work. The independent bounded article publisher may be delegated in parallel. Steps use checkbox syntax for tracking.

**Goal:** Browse all current reading content offline with the unchanged UI, and synchronize future publications without APK updates.

**Architecture:** Package a complete seed and serve immutable local resources through the existing trusted HTTPS WebView origin. A hash manifest and background worker stage only changed resources, validate them, and activate a complete snapshot for the next navigation.

**Tech Stack:** Existing Java Android app, AndroidX WebKit and WorkManager, Python publishing tools, GitHub Actions, JUnit, Python unittest, Playwright/emulator smoke tests.

**Spec:** `docs/superpowers/specs/2026-10-01-offline-android-design.md`

## Global Constraints

- No public website layout, color, typography, navigation, or card redesign.
- Minimum SDK 23, target SDK 36; keep the existing application ID and upload key.
- Offline first launch must not rely on previously visited WebView HTTP cache.
- YouTube playback and new PDF downloads remain online; no downloaded YouTube media.
- Only approved public resources can enter the app seed or update manifest.
- All edits remain in the isolated clean worktree; original dirty checkout is untouched.
- User approved the design and delegated remaining review/execution decisions while away.

## Review Focus

- Corrupt/interrupted sync must keep the previous complete snapshot readable.
- First launch without internet must include fonts/icons and unvisited detail pages.
- Publication races must not combine old listing data and new detail assets in one page.
- Malicious paths/redirects/oversized resources must not escape app-private storage or trusted origins.
- Process recreation, back navigation, native downloads, and YouTube fullscreen must remain intact.

## Task 1: Deterministic Public Resource Manifest and Seed

**Files:** `scripts/generate_app_content.py`, `tests/test_app_content.py`, `content-pipeline/app-content.md`, public generated resource mirrors under `assets/app-content/`, `data/app-content-manifest.json`.

**Interfaces:** `build_manifest(root: Path) -> dict`; `prepare_seed(root: Path, output: Path) -> dict`; `--prepare-assets` resolves approved static dependencies and thumbnails; `--seed PATH` writes build assets; `--check` validates existing published bytes. Resource entries contain `key`, `path`, `sha256`, `size`, `mime`; revision is a hash of canonical entries.

- [ ] Write tests for deterministic revisions, content-change detection, excluding private/source/PDF/build files, safe keys, complete linked reading resources, and external dependency mappings.
- [ ] Run tests and confirm missing behavior fails.
- [ ] Implement generator using structured HTML parsing and URL normalization. Keep external dependency and thumbnail preparation separate from deterministic manifest generation.
- [ ] Verify the real current site's asset closure and seed bytes; retain fallback for unavailable thumbnails, but fail missing required content.
- [ ] Run full Python/Node suites and commit explicit resource-generator files.

## Task 2: Atomic Offline Resource Repository

**Files:** `android-app/app/src/main/java/com/ahmedelfashny/official/ContentManifest.java`, `OfflineContentStore.java`; matching JUnit tests; test JSON parser dependency in `android-app/app/build.gradle`.

**Interfaces:** `ContentManifest.parse(byte[])`; `OfflineContentStore(File directory, SeedSource seed)`; `snapshot()` returns an immutable revision; `open(snapshot, resourceKey)` returns local bytes/MIME; `synchronize(manifestBytes, Fetcher)` stages validated resources and returns whether the revision changed. `SeedSource` and `Fetcher` use streams/bytes and are testable without Android UI.

- [ ] Write tests for seed-only reads, unchanged revisions downloading nothing, one changed file downloading once, checksum failure rollback, failed partial downloads, hostile paths, and old snapshot consistency.
- [ ] Run JUnit and verify failures before repository implementation.
- [ ] Implement content-addressed storage and atomic manifest promotion with bounded resource sizes and safe URL keys. Keep old active snapshot usable across sync and process recreation.
- [ ] Run all Android unit tests and commit repository changes.

## Task 3: Background Sync and Local WebView Integration

**Files:** `ContentSyncWorker.java`, `MainActivity.java`, `AndroidManifest.xml`, `app-runtime.js`, `app/build.gradle`, runtime tests.

**Interfaces:** unique connected-network work fetches `https://ahmedelfashny.com/data/app-content-manifest.json`; uses Task 2 repository. Main-frame navigation pins a snapshot; its GET resources use that snapshot through `shouldInterceptRequest`. Unknown YouTube/player/download resources retain existing network handling.

- [ ] Add failing runtime/integration tests for absent horizontal progress/preloader, local catalog fetches, trusted-origin restrictions, and snapshot pinning.
- [ ] Queue unique work on foreground entry and periodic connected maintenance, with bounded timeouts and retry backoff. Add normal network-state permission only if required by scheduling.
- [ ] Integrate local responses with correct MIME/charset/CORS for public mirrored resources; retain deep links and native bridge restrictions.
- [ ] Remove native progress bar and suppress page preloader at document start only in the app. Keep the existing navigation and content design.
- [ ] Add reproducible Gradle seed generation and bump version to a code greater than the latest Play upload.
- [ ] Run Gradle unit tests, Python runtime tests, debug build and lint; commit explicit app source files.

## Task 4: Publication Integration

**Files:** `.github/workflows/content-publish.yml`, `video-sync.yml`, new `app-content.yml`; article workflow after its independent implementation; publishing docs.

**Interfaces:** invoke Task 1 generator before bot content commits; stage the manifest and any newly prepared approved public assets explicitly. Human content pushes get a manifest maintenance job using the publication lock. Each bot publication requests Pages build itself.

- [ ] Test manifest generation after simulated article/khutba/video additions and unchanged catalog runs.
- [ ] Integrate both automatic publishers and manual push flow without relying on bot push events triggering another workflow.
- [ ] Run the hosted workflow and confirm the exact live manifest/resources match the published revision.
- [ ] Commit/push integration and verify current videos remain on all correct live pages.

## Task 5: Offline, Sync, and Release Verification

**Files:** `android-app/tools/offline_smoke.py`, smoke reports/screenshots, release documentation, Play release notes.

- [ ] Fresh-install debug APK, disconnect emulator networking, and visit home, library, unvisited article/khutba detail, video categories, recitations, and local tools. Assert visible content, loaded fonts/images, no progress bar/preloader, and no blank main frames.
- [ ] Serve a controlled newer manifest to test incremental sync, then disconnect and restart. Verify new local content and failed-update retention without changing the production content for a synthetic test.
- [ ] Re-run existing native PDF/share/fullscreen/back/process-recreation smoke tests and measure navigation/network behavior.
- [ ] Build release APK/AAB, inspect signatures/package/version/contents and rerun release lint. Preserve signing material outside Git.
- [ ] Publish the downloadable APK and verified higher-version bundle to the existing Play closed test. Verify Console accepted the upload and actual review/release state, without claiming production access.
- [ ] Whole-change independent review, final full suites, explicit commit/push, live checks, and concise user handoff with uploader links and actual Play status.
