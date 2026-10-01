# Offline Release 1.0.2

Verified October 1, 2026. Package `com.ahmedelfashny.official`, version code 3, Android 6.0+, target SDK 36. The existing design, navigation, fonts and branding are retained.

## Delivery

- [Signed APK](https://ahmedelfashny.com/downloads/android/ahmed-elfashny-1.0.2.apk), 29,229,148 bytes, SHA256 `35445e0a454b14819fbc9785996d019169747c2f6be0ba40c0bb42df72512f56`. The downloaded live bytes matched this hash.
- Signed AAB: 29,613,595 bytes, SHA256 `470585ab823e030070c334894a65e23861e3bf3914797eb60e4b387b486ab86f`. Official bundletool validation and signature checks passed. The same existing upload key was used; no signing secret is committed.
- Google Play accepted version 3 / 1.0.2 in the existing Alpha closed-test track. Quick checks passed and Console confirmed changes in review. This is not a public production release. The account still requires 12 opted-in testers for 14 continuous days; the three supplied addresses are insufficient.
- Support remains `amr@gharib.dev`. Ads declaration remains Yes because the YouTube player can show ads; no advertising-ID SDK or permission was added.

## Content And Publishing

[The mobile upload chooser](https://ahmedelfashny.com/admin/) has separate article and khutba GitHub forms. Authorized article uploads run the real Word parser, existing article/page/card design, Arabic PDF, sitemap, commit/push and live verification. Khutba publishing retains its existing pipeline. All publishers rebuild and verify the app manifest after rebasing. Concurrent requests queue instead of cancelling waiting uploads.

[The hosted article dry-run](https://github.com/xgharibx/ImamAhmed/actions/runs/36820443552) passed actual DOCX/page/card/Arabic PDF/download/sitemap/offline-manifest integration in temporary storage. No synthetic article was published on the production site.

The catalog contains 1,543 videos, including the 28 additions from both official channels. All nine categories and the three video views use the same validated catalog and exact source dates. The [latest hosted video run](https://github.com/xgharibx/ImamAhmed/actions/runs/36832712278) passed both catalog and app-content live verification. Its audit time was 2026-10-01 07:51:21 UTC. The automatic schedule is Monday and Thursday at 06:17 Africa/Cairo; GitHub can delay scheduled jobs.

## Offline Verification

- Public snapshot: 1,786 resources, 38,335,542 bytes, revision `08356a783e08db5b3d21fd5f810318c5f892c30c848ad457ac36ce997b0c04ab`. The full live check verified all 1,786 hashes and sizes. [Hosted maintenance](https://github.com/xgharibx/ImamAhmed/actions/runs/36829911348) also passed.
- Fresh debug installation in airplane mode: 15 pages including unvisited article/khutba text, catalogs, fonts, icons and images; no JavaScript errors or failed page requests. Original navigation, Back and process restart passed.
- The exact signed optimized APK passed first-launch airplane checks for home, articles, written sermons, videos and an unvisited article. Release WebView debugging is disabled.
- Real production HTTPS worker activated the newer public snapshot. The changed article and its revision survived a disconnected process restart with no failed page resources.
- Controlled latest-device incremental sync downloaded two changed resources and zero resources for an unchanged revision. Old pinned reads stayed consistent; a corrupt follow-up was rejected and the complete snapshot survived restart.
- Actual YouTube playback advanced; native fullscreen, landscape rotation, leaving fullscreen with Back, closing the modal with the second Back, and restored navigation passed.
- Native transfer tests passed competing-transfer rejection, binary-message handling, save-picker restoration after process death, exact saved PDF bytes and native PNG sharing. Renderer termination recovery passed its device regression.
- Python suite: 96 tests passed. Android JUnit: 15 passed. App runtime: 8 passed. All three JavaScript catalog renderers passed. Debug/release lint reports contain no issues. Gradle release APK/AAB builds passed.
- Independent review found six actionable issues; each was reproduced and fixed with a RED-to-GREEN regression: quota pruning, seed replacement, renderer recovery, mixed page revisions, post-rebase manifest drift, and unsafe mirror redirect contact.

The APK seed remains a self-consistent earlier snapshot; the small later text line-ending correction was successfully received through production background sync without rebuilding the app. This directly exercises the content-update contract.

## Boundaries

The engine still renders local HTML; local rendering is not zero work, but page navigation no longer depends on the network or displays the browser-style progress bar or app page preloader. Connected foreground checks and six-hour maintenance download only changed content, with complete-snapshot activation and no forced reading-page reload. Android can defer background work to preserve battery.

YouTube playback, new PDF downloads and external services remain online. Eight thumbnail URLs for unavailable old videos have fallbacks. Two preserved legacy videos have no verifiable date; no dates were invented. One known pending stream is blocked by YouTube metadata checks and remains explicitly deferred, never published with incomplete data. Unknown metadata failures still fail safely.

## Decisions

- Immutable increasing journals use atomic rename on API 23. Recovery may select an older complete snapshot, never a partial one.
- Controlled device updates use the real repository Fetcher; production HTTPS is tested separately. Some transport-only edge cases remain beyond the fixture.
- Previously audited pending streams are retained only against the matching catalog hash and a current official feed. A finished stream can be delayed until complete metadata becomes verifiable.
- The article publisher was tested without posting a fake public issue/article. The first genuine issue submission remains the first real end-to-end public article publication.
- Online media/PDF/external behavior follows the approved design; these functions are unavailable without connectivity.
- Hosted publication and Play acceptance were explicit release gates, not inferred from local tests. Google may still request changes during review.
