# Sheikh Ahmed Android App

This Android Studio project packages the production website as a release-ready Android app.

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

For Google Play, create a local signing key and a local `keystore.properties` file. A template is included at:

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
- Version: `1.0.1` (version code `2`)
- Support: `amr@gharib.dev`
- Privacy: `https://ahmedelfashny.com/privacy.html`
- Live site: `https://ahmedelfashny.com/`
- Minimum SDK: 23
- Target SDK: 36
- Release builds enable resource shrinking and code minification.
- The app uses only the internet permission.

Fresh videos, khutab, articles, books, and JSON content load from the live website, so content updates do not require a new app release.

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
```

The native transfer test kills only the debug app process to verify that a pending save survives process recreation. It writes small test PDFs to the emulator's Downloads directory.

## Play Status

The signed bundle and store graphics are prepared for closed testing. A saved draft is not a live Play release. Complete Console's app-content declarations and release review before inviting testers. This account requires at least 12 opted-in testers for 14 continuous days before applying for production access; the three supplied email addresses do not yet meet that requirement.

Keep the upload keystore backed up privately. Play-generated APKs use Google's app-signing key, which can differ from the direct APK's upload-key signature; moving between these installation channels may require uninstalling the direct APK first.
