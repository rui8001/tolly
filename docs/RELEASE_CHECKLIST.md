# Public release checklist

## Public release gates

- [x] Verify the upstream Tokei repository's current license declaration and update `THIRD_PARTY_NOTICES.md`.
- [x] Review upstream-derived implementation and keep explicit attribution; do not reuse upstream branding, screenshots, icons, copywriting, or release binaries.
- [x] Publish from a new root commit so the old local history containing real `sample_usage.json` data is never pushed.
- [x] Run `node scripts/check-privacy.mjs` and manually search the public snapshot for usernames, absolute paths, API keys, account IDs, project names, and session IDs.
- [x] Replace repository/security placeholders with the `rui8001/tolly` project identity.
- [x] Clone `main` again from the public GitHub repository and build both NSIS and MSI from that clone.
- [x] Confirm the public commit passes the Windows/Linux, Python 3.10/3.12 GitHub Actions matrix.
- [x] Generate SHA-256 checksums alongside tagged release installers.
- [x] Enable GitHub private vulnerability reporting.
- [ ] Build and test on a clean Windows 10/11 VM with no system Python installed.
- [x] Install Visual Studio Build Tools with the “Desktop development with C++” workload.
- [ ] Configure Windows code signing. Unsigned installers commonly trigger SmartScreen warnings.
- [x] Verify NSIS/MSI install, bundled-sidecar launch, uninstall, single-instance behavior, and hide-to-tray/restore behavior on a real Windows host. See [Windows installer verification](WINDOWS_INSTALL_TEST.md).
- [ ] Verify an in-place upgrade from an older tagged version once one exists.
- [x] Confirm that 0.1.0 does not expose an autostart feature; test startup-at-login behavior only if that feature is implemented.
- [ ] Tag only from a clean tree after CI passes.

## History-cleaning record

The first public branch was prepared as a new root commit. The pre-publication local `master` history was retained only as an offline reference and was not pushed. This avoids publishing the following historical sample paths:

```text
tally-engine/scripts/sample_usage.json
tally-win/scripts/sample_usage.json
tally-win/src/sample_usage.json
```

Only the current synthetic `tally-win/src/sample_usage.json` belongs in the public root commit. Never push the legacy `master` branch or tags that can reach its earlier objects.

## Upgrade strategy

Tagged releases build versioned NSIS/MSI installers. This provides manual upgrades now. Add Tauri's signed updater only after a stable GitHub repository URL, updater public key, signed artifacts, and a tested rollback policy exist; shipping a placeholder updater would create a false security boundary.
