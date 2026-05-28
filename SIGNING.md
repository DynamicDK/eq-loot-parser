# Code signing (SignPath OSS)

The released `eq-loot-viewer.exe` is **Authenticode code-signed** via
[SignPath.io](https://about.signpath.io/)'s free program for open-source
projects, so Windows Defender, SmartScreen, and other engines trust it instead
of flagging unsigned PyInstaller output as a false positive.

Signing happens in CI only (`.github/workflows/release.yml`): SignPath's free
program requires a **verified build system**, so it will not sign a
locally-built file. The workflow builds the exe on a clean Windows runner,
submits it to SignPath, and attaches the signed exe to the GitHub Release.

> Until the one-time setup below is complete, the workflow's "Submit signing
> request" step will fail (no token / org id). That's expected.

## One-time setup

Authoritative docs: <https://docs.signpath.io/trusted-build-systems/github>

1. **Apply to the SignPath Foundation OSS program**
   (<https://about.signpath.io/product/open-source>). Approval can take a few
   days. Once approved you get a SignPath **Organization** for the project.

2. **Configure the project in the SignPath web app** (<https://app.signpath.io>):
   - **Project** — create one; its slug must match `project-slug` in the
     workflow (currently `eq-loot-parser`).
   - **Artifact Configuration** — configure it to expect the uploaded artifact
     (a zip containing `eq-loot-viewer.exe`) and to Authenticode-sign that
     `.exe`.
   - **Signing Policy** — create one; its slug must match `signing-policy-slug`
     in the workflow (currently `release-signing`).
   - **Trusted Build Systems** — enable **GitHub.com** and link this repo.
   - Copy your **Organization ID**.

3. **Install the SignPath GitHub App** on `DynamicDK/eq-loot-parser` (the
   Trusted Build Systems / GitHub setup page links to it). This lets SignPath
   verify that signing requests really come from this repo's CI.

4. **Add the API token as a GitHub secret.** In SignPath create a CI user / API
   token, then in GitHub go to **Settings → Secrets and variables → Actions →
   New repository secret** and add:
   - Name: `SIGNPATH_API_TOKEN`
   - Value: the token

5. **Fill in the non-secret values** in `.github/workflows/release.yml`:
   - replace `REPLACE_WITH_SIGNPATH_ORGANIZATION_ID` with your Organization ID
   - confirm `project-slug` and `signing-policy-slug` match what you created.

## Releasing a signed build

Push a version tag; CI builds, signs, and publishes:

```
git tag v1.0.1
git push origin v1.0.1
```

The signed `eq-loot-viewer.exe` is attached to the `v1.0.1` Release, and the
README download link (`/releases/latest/download/eq-loot-viewer.exe`) keeps
working with no change.

You can also run the workflow manually from the **Actions** tab
(**workflow_dispatch**) to test signing without cutting a tag — it will sign but
only publish to a release when triggered by a tag.

## Notes

- The current `v1.0.0` asset is the old **unsigned** PyInstaller build and will
  keep being flagged. After your first signed release works, consider deleting
  or replacing that asset.
- The OSS certificate is issued under the SignPath Foundation; this is normal
  for open-source projects and is trusted by Windows.
- SmartScreen reputation still builds with download volume over time; signing
  is what removes the "unknown publisher" distrust that drives the false
  positives.
