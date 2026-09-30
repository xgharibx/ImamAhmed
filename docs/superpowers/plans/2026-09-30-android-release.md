# Android Release Implementation Plan

**Goal:** Deliver signed APK and Play AAB while preserving the live website's exact screens and mobile navigation.

**Architecture:** Retain the existing live-site Android container. Add origin-restricted native PDF saving and sharing, fullscreen video, and fresh first-party content requests. Export the supplied logo without redrawing it.

**Constraints:** Package `com.ahmedelfashny.official`; target API 36; minimum API 23; no website restyle; no signing secrets in Git; preserve unrelated workspace changes.

## Tasks
- [x] Write failing runtime and download-policy tests, implement the origin-restricted bridge, and pass the suite.
- [x] Integrate PDF saving, native sharing, fullscreen video, safe external links, and renderer recovery in MainActivity.
- [x] Export the newly approved full PNG logo to adaptive, legacy, splash and Play assets; preserve its deep-green transparent variant separately.
- [x] Build signed APK/AAB; verify signatures; run Android lint and emulator checks against live content.
- [x] Prepare privacy policy, store listing, screenshots and release instructions; save the listing and signed bundle in Console.
- [ ] Complete remaining Play declarations and closed-test setup, then submit for review. Production remains subject to Google's tester requirements.
- [x] Review, commit and push only the scoped release changes; preserve deliverables outside the temporary worktree.

## Verification
Check first-party JSON freshness, unchanged DOM/navigation, Blob PDF bytes, safe filenames, blocked untrusted URLs/frames, back navigation, fullscreen exit, download cancellation, offline errors, icon safe bounds, API 36 metadata and release signing. Google review and account declarations cannot be claimed complete without Console evidence.

Verified: seven browser runtime regressions; three Java policy tests in debug/release; 18 website Python tests; three video-catalog JS checks; real API 36.1 emulator navigation, PDF saving, native PNG sharing, pending picker process-death restoration, busy transfer protection, binary message rejection, video playback and fullscreen Back. Release lint: no issues. A real 11-page sermon PDF was saved without exporter changes and visually inspected.
