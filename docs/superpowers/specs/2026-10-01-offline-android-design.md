# Offline Android Content Design

## Intent and Approval

The user wants the existing Android app to open and browse all current public
content without internet, including pages never previously visited. Keep the
exact website typography, colors, cards, navigation, and reading layout. Remove
the native horizontal progress bar and app-only page preloaders. Do not make the
website behave differently. New articles, khutab, and video metadata must arrive
without requiring another APK update.

The user approved the direction on October 1, 2026: bundle offline content with
background updates. This document is the detailed design for review before
implementation. It does not assert that an offline release has been built.

## Alternatives

1. **Bundled snapshot plus incremental sync (selected):** retain the existing
   rendering and navigation, but serve reading resources from app storage. Works
   on the first launch in airplane mode. Larger install, with explicit sync and
   validation responsibilities.
2. **Visited-page HTTP cache:** smaller implementation, but never-visited pages
   and evicted resources remain unavailable offline. Does not meet the request.
3. **Rewrite every screen natively:** can support local data, but changes the
   existing rendering and risks violating the user's unchanged-design priority.

The selected approach follows Android's local-source-first guidance; a rendering
engine alone does not imply that page navigation must depend on the network.
Reference: https://developer.android.com/topic/architecture/data-layer/offline-first

## Offline Scope

- Bundle all public first-party HTML reading pages, including `books/` article
  pages, `khutab/` detail pages, home, library, videos, recitations, tools, and the
  JSON consumed by those pages.
- Bundle their CSS, JavaScript, public illustrations, approved logo, fonts,
  icon fonts, and animation libraries. Preserve original URLs and rendering.
- Bundle available video thumbnails for existing catalog entries; they are
  metadata images, not video media. Unavailable thumbnails must not make a
  complete text/catalog snapshot unusable. Existing fallback imagery stays.
- Exclude source DOCX files, admin/GitHub upload pages, development artifacts,
  private signing material, APK/AAB downloads, and bulk PDF/media archives.
- YouTube playback, external links, contact submission, and downloading a PDF
  not already saved remain online operations. Existing saved downloads remain
  accessible through Android's document provider. Do not download YouTube video
  or audio for offline playback.
- Purely local tools keep working. Features requiring remote services, such as
  location-dependent network data, cannot promise fresh results offline.

## Components

### Public Content Manifest

A deterministic generator produces `data/app-content-manifest.json`. Each entry
has a normalized resource key, public source URL, SHA-256, byte length, and MIME
type. The manifest has a schema version and a content-derived revision. Exclude
the manifest itself and health timestamps, so an unchanged catalog does not
cause unnecessary large downloads.

Only known public paths and approved CDN assets enter the manifest. Reject path
traversal, unsupported schemes, credentials in URLs, excessive entry counts,
oversized files, and unsupported MIME types. Never crawl arbitrary links or
include repository files simply because they exist.

The Word publishers and twice-weekly video workflow regenerate the manifest
before their bot commits. A separate push-triggered manifest workflow handles
ordinary human content commits, using the same publication lock and explicit
Pages rebuild. Bot-generated commits do not depend on triggering another
workflow with `GITHUB_TOKEN`.

### Build-Time Seed

The Android build packages a generated offline seed in assets, using the current
production content manifest and matching resource bytes. Build tooling validates
all required resources. Missing required fonts, scripts, reading pages, or data
fail the build rather than producing a deceptively partial offline app.

Do not commit generated Android build caches. Stable public dependency mirrors
and thumbnail assets can be retained as generated public assets when required
for reproducible builds and future manifest updates. Report the resulting AAB
and installed storage size after measuring them.

### Local Resource Store

A small Java repository serves immutable resources by their hashes. The seed is
always a complete fallback. Downloaded revisions live in app-private files, not
evictable WebView HTTP cache. A complete validated manifest selects the active
revision; a partial update never replaces it.

`WebViewClient.shouldInterceptRequest` serves GET resources from this repository,
under the existing owned HTTPS origin. Preserve public deep links, native save
and share policies, and the current restricted bridge origins. Do not enable
`file://` access or weaken TLS, mixed-content, or Safe Browsing protections.

Pin a revision for each page navigation and its subresources. Updating the
background store must not mix old HTML with new JSON/scripts mid-read. A newly
completed revision becomes visible on the next navigation or intentional
refresh. No automatic page reload steals the current reading position.

### Background Sync

Use unique WorkManager work with a connected-network constraint, bounded
timeouts, and retry backoff. Queue checks on launch/resume, connectivity recovery,
and periodic maintenance. A conditional manifest request is small; unchanged
content results in no resource downloads. No exact background timing guarantee
is made because Android may defer work.

Download changed resource hashes only, verify each size and checksum, then
atomically promote the complete revision. Reuse unchanged seed/disk objects.
Interrupted, corrupt, 404, offline, or incompatible-schema updates retain the
last working revision. Bound disk usage; retain the current reading revision
until it is no longer in use before pruning older resources.

Reference: https://developer.android.com/develop/ui/views/layout/webapps/load-local-content

### App-Only Loading Behavior

Remove the native horizontal `ProgressBar`. Suppress the site's `#preloader` at
document start in the app only, including the WebView compatibility fallback.
Normal navigation reads local resources and does not show a network loading
screen. Preserve the same visible layouts and navigation controls.

User-requested network actions may show an appropriate failure or retry message
when offline. Never show a full-screen connectivity error over available local
reading content. Existing explicit pull-to-refresh may request sync, but must
not cause silent loss of the current local snapshot.

## Verification and Release

1. Unit tests: safe resource keys/origins; manifest validation; seed fallback;
   checksum rejection; partial-update retention; revision pinning; unchanged
   revision downloads nothing; changed revision downloads only changed files.
2. Browser tests: article/khutba/video catalogs match production; existing mobile
   and desktop website views are unchanged. Verify bundled fonts and icons.
3. Emulator: fresh install in airplane mode; home, articles, unvisited article,
   written khutab, unvisited khutba, all video categories, recitations, and tools.
   Confirm no horizontal bar or page preloader and no blank/broken asset views.
4. Emulator online-to-offline: new test content syncs, survives process death,
   works after disconnecting; interrupted update retains the old snapshot.
   Check navigation latency and ensure networking does not block the UI thread.
5. Re-run native PDF saving/sharing, deep links, fullscreen YouTube, back,
   rotation, process recreation, accessibility, Gradle tests and release lint.
6. Build a higher-version signed APK and AAB using the existing upload key.
   Verify package, version, signature, min/target SDK, and bundle contents.
7. Upload the verified bundle to the existing Play closed-test track and prepare
   accurate release notes. Verify Console acceptance. Public production access
   still depends on Google's account/testing/review requirements; uploading a
   bundle is not a claim that it is publicly released.

## Acceptance

An installed user can browse all bundled reading text and video catalog metadata
without internet, even on the first launch. With connectivity restored, new
published content becomes locally available without a Play update or visible
forced reload. The website and app keep their existing visual design. Playback
and new external downloads still legitimately need internet.
