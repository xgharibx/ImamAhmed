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
- App name: `الشيخ أحمد الفشني`
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
