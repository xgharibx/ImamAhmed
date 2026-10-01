# Sheikh Ahmed Android App

This Android Studio project preserves the website UI and bundles public content for first-launch offline reading, with incremental background updates.

## Open in Android Studio

Open this folder directly:

```text
android-app
```

Android Studio should sync the Gradle project automatically.

## Build Debug APK

```powershell
.\gradlew.bat assembleDebug
```

Output:

```text
app/build/outputs/apk/debug/app-debug.apk
```

## Build Release AAB

For updates to the existing Google Play app, reuse its upload key and local `keystore.properties`. Do not generate a replacement key. A configuration template is included at:

```text
keystore.properties.example
```

Then run:

```powershell
.\gradlew.bat bundleRelease
```

Output:

```text
app/build/outputs/bundle/release/app-release.aab
```

Do not commit `keystore.properties`, `.jks`, or `.keystore` files.

## Production Configuration

- Package name: `com.ahmedelfashny.official`
- App name: `Ahmed Elfashny | الفشني`
- Version: `1.0.2` (version code `3`)
- Support: `amr@gharib.dev`
- Privacy: `https://ahmedelfashny.com/privacy.html`
- Live site: `https://ahmedelfashny.com/`
- Minimum SDK: 23
- Target SDK: 36
- Release builds enable resource shrinking and code minification.
- Internet/network-state permissions support connected background work. No broad storage or sensitive device permissions are requested.

Current reading pages, khutab/article text, video catalogs, fonts, icons, and available thumbnails are packaged in the app. They open without internet even if never visited before. A connected WorkManager check downloads only changed resources from the public hash manifest, validates them, and activates a complete version on the next navigation. Failed updates retain the working version. YouTube playback, external services, and new PDF downloads remain online. Future content publications do not require a new app release.

Set `PYTHON` to your Python interpreter if `python` is not on PATH. Gradle generates and validates the complete offline seed during `preBuild`; see `content-pipeline/app-content.md` in the repository root. No top horizontal loading bar or page preloader is shown inside the app.

The app keeps the original website design. Its floating five-tab navigation is
shared with the website (`mobile-nav.css` and `mobile-nav.js`) and bundled
automatically during the build. Once the live website includes that navigation,
the app uses the website version without adding a duplicate bar.

PDF downloads use Android's document picker, and supported image/PDF shares use Android's chooser with temporary file access. No broad storage permission is needed. Only the owned HTTPS origins can invoke the native bridge. Release builds disable WebView debugging and device backups.

## Branding

The full gold-on-green logo is unchanged. Background-free artwork uses the approved deep blue-green variant. Sources and instructions are in `branding/`; rerun `python tools/export_logo.py` to size the original for Android and Play.

## Verification

Build and lint:

```powershell
.\gradlew.bat test assembleDebug assembleRelease bundleRelease lintRelease
python -m unittest discover -s tests -v
```

Emulator smoke tools require the Python Playwright package and a running Android emulator with the debug APK installed:

```powershell
python tools/android_smoke.py C:\path\to\adb.exe
python tools/native_transfer_smoke.py C:\path\to\adb.exe
python tools/offline_smoke.py --adb C:\path\to\adb.exe --output C:\path\to\qa
```

The native transfer test kills only the debug app process to verify that a pending save survives process recreation. It writes small test PDFs to the emulator's Downloads directory.

## Play Status

Version 1.0.1 is available to selected closed-test testers (Console verified October 1, 2026). Version 1.0.2 is the offline update; record Console's actual acceptance and review state after upload. A draft or review submission is not a public Play release. This account requires at least 12 opted-in testers for 14 continuous days before applying for production access; the three supplied email addresses do not yet meet that requirement.

Keep the upload keystore backed up privately. Play-generated APKs use Google's app-signing key, which can differ from the direct APK's upload-key signature; moving between these installation channels may require uninstalling the direct APK first.
