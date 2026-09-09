# Windows candidate verification

This workflow builds **test-only 1.2.1 artifacts** from the checked-out source and a recorded six-file version stamp. It does not create tags or GitHub Releases, overwrite existing release assets, change signing keys, or update installed user software.

Run `Windows candidate verification` manually on the reviewed source branch. A PR changing its scripts/workflow also triggers it. Source files remain at 1.2.0; candidate stamping runs only in disposable CI and rejects unexpected source versions. Before another version is tested, explicitly update the baseline, version contracts and tests.

The build uploads MSI, NSIS, SHA256SUMS.txt, candidate.json (source SHA, run ID, binary hashes) and version-stamp.patch as one 14-day Actions artifact. These unsigned test packages must not be presented as a public release.

Four isolated Windows jobs cover MSI/NSIS × clean/upgrade. Upgrade jobs download the actual v1.2.0 release and verify its exact checksum entry, install and launch it, create synthetic settings in the application's roaming configuration directory and a synthetic local-data sentinel, then install the newer candidate. Tests check the installed version and executable/sidecar hashes against the candidate build, preservation of both files before and after launch, launch without Python on PATH, and successful uninstall/removal. Clean jobs independently validate candidate installation, binary identity, launch and uninstall.

This covers installer-level preservation of synthetic configuration, not all real-user data, all Windows versions, UI correctness or verified external user trials. Only a passing complete workflow is evidence of candidate verification. A successful build alone is insufficient. Cross-installer migrations (MSI to NSIS or vice versa) are not tested.

References: [Tauri Windows packaging](https://v2.tauri.app/distribute/windows-installer/) and [app_config_dir](https://docs.rs/tauri/latest/tauri/path/struct.PathResolver.html#method.app_config_dir).
