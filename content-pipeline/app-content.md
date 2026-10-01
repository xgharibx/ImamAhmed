# Android Offline Content

The app bundles the current public reading pages and metadata. The website's
HTML/CSS/navigation stay unchanged. YouTube playback, external services, and new
PDF downloads need connectivity; reading and catalog navigation do not.

## Generate and Validate

```powershell
python scripts/generate_app_content.py --prepare-assets
python scripts/generate_app_content.py --check
python scripts/generate_app_content.py --seed android-app/app/build/generated/offlineContent/offline
```

`--prepare-assets` mirrors approved fonts, libraries, and available video
thumbnail images to public `assets/app-content/`. It does not download video or
audio. Required dependency failures stop publication. Missing thumbnails are
reported and retried next time; they do not discard complete reading content.
The deterministic generator requires every linked reading dependency. It
excludes Word/PDF sources, admin pages, signing files, build outputs, and health
reports. Public text bytes use Git's LF line endings on Windows as on Pages.

The generated `data/app-content-manifest.json` uses schema 1. Each resource has:
`key`, `path`, `sha256`, `size`, `mime`. Owned URL keys are decoded absolute paths
without cache queries; `/` becomes `/index.html`. Approved CDN keys retain their
queries. All update download paths are public paths on the owned HTTPS site.
The revision hashes UTF-8 entries in key order, each represented as
`key NUL path NUL sha256 NUL size NUL mime LF`. File hashes cover original public
bytes, before the app's loader-suppression injection.

## App Behavior

Gradle generates the seed during `preBuild`; set `PYTHON` to your interpreter
path if `python` is not on PATH. Assets are immutable SHA-256 objects. Connected
WorkManager checks run on foreground entry, restored connectivity, and periodic
maintenance. Android may defer background work. Conditional manifest requests
avoid downloading unchanged resources.

A complete verified update is activated by one atomic rename of an immutable
manifest journal entry. Interrupted, corrupt, missing, or incompatible updates
keep the previous complete version. Each reading page pins its revision until
the next navigation. Sync never forces a reload while reading.

The repository bounds manifest size (5 MB), individual resources (32 MB),
snapshot size (384 MB), and downloaded objects (768 MB). It retains the active,
previous, and currently read snapshots, and prunes unused objects after a
successful update. The packaged seed remains the final fallback.

## Publication

Word publishers and video sync regenerate and commit the manifest and dependency
mirrors alongside their public output. Human content pushes are handled by the
app-content maintenance workflow. All publishers share the publication lock and
request a Pages build explicitly, because GitHub token commits do not trigger
other workflows. The live manifest is verified before publication is confirmed.
