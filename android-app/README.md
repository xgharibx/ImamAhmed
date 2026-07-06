# Sheikh Ahmed Android App

This Android project packages the live website as a production-ready mobile app.

## How Fresh Content Works

The app loads:

```text
https://ahmedelfashny.com/
```

as the source of truth. New videos, khutab, articles, books, and JSON content appear in the app as soon as they are published to the website. A new Google Play release is only needed for native app changes such as icons, package name, permissions, or WebView behavior.

## Features

- Native Android WebView shell for the live website.
- JavaScript, DOM storage, cookies, and responsive viewport enabled.
- Pull-to-refresh.
- Native loading progress.
- Friendly offline/retry screen.
- Android back button navigates website history before exiting.
- Internal links stay inside the app.
- External links, YouTube, social links, mail, tel, WhatsApp, and downloads open outside the app.
- Deep links for `https://ahmedelfashny.com/...`.
- Minimal permissions: internet only.

## Change the Live URL

Edit:

```text
app/build.gradle
```

and update:

```groovy
buildConfigField "String", "LIVE_SITE_URL", "\"https://ahmedelfashny.com/\""
buildConfigField "String", "LIVE_SITE_HOST", "\"ahmedelfashny.com\""
```

## Build

From this folder:

```powershell
.\gradlew.bat assembleDebug
```

Debug APK:

```text
app/build/outputs/apk/debug/app-debug.apk
```

## Release AAB for Google Play

Create a signing key using Android Studio or `keytool`, then either configure signing in Android Studio or add a local `keystore.properties` file and a signing config.

Typical release command:

```powershell
.\gradlew.bat bundleRelease
```

Release AAB:

```text
app/build/outputs/bundle/release/app-release.aab
```

Do not commit keystores or `keystore.properties`.

## Google Play Notes

- Package name: `com.ahmedelfashny.official`
- App name: `الشيخ أحمد الفشني`
- The app is intentionally a live WebView app so content updates do not require APK/AAB updates.
- Keep the website mobile experience healthy because this app displays the same production website.
