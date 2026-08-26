# Windows installer verification

This record covers an interactive installation test of installers built from the public repository.

## Test environment

- Date: 2026-08-26
- Public source commit: `cbb709dee8855fe50316d388448493208ccefcaf`
- Host: Windows 11 x64, build 26200
- Scope: real host verification; this was not a clean virtual machine and the host has a system Python installation

## Artifacts

| Installer | SHA-256 | Signature |
| --- | --- | --- |
| `Tolly_0.1.0_x64-setup.exe` | `7706BCE4C491907E43FAA5BE2AB364E2EAFEB51B15ACC785012EEE7D406096B8` | Unsigned |
| `Tolly_0.1.0_x64_en-US.msi` | `79961C06F6CF3415F654830F2B70446D945A9CBB3E65E8ED53B1495DD45CABE0` | Unsigned |

Both installers were produced by a clean clone of public `main`, rather than from the pre-publication working tree.

## Results

### NSIS

- [x] Completed the interactive installer flow.
- [x] Installed the desktop executable and bundled `tally-engine.exe` sidecar under `%LOCALAPPDATA%\Tolly`.
- [x] Created a Start menu shortcut and launched the application.
- [x] A second launch reused the existing process instead of starting a second application instance.
- [x] The bundled uninstaller completed successfully and removed the application files, running process, and shortcut.

### MSI

- [x] Completed the interactive installer flow and registered Tolly 0.1.0 with Windows Installer.
- [x] Installed and launched the desktop executable with its bundled sidecar.
- [x] Loaded live Codex and WorkBuddy usage data without remaining on the loading state.
- [x] A second launch reused the existing instance and restored its window.
- [x] Closing the window hid it while the tray process remained running; relaunching restored the same instance.
- [x] Windows Installer removal deleted the application files and uninstall registration.
- [x] No Tolly shortcuts or processes remained after removal.

## Follow-up work

- The binaries are not Authenticode-signed, so Windows displayed an unknown-publisher elevation prompt. Code signing remains a release blocker.
- Repeat the build, install, launch, and uninstall checks in a clean Windows VM with no system Python installed. The installed application used the bundled sidecar in this test, but the host was not suitable for proving the absence of hidden Python dependencies.
- Verify an in-place upgrade after an older tagged installer exists.
- Version 0.1.0 does not expose an autostart feature, so startup-at-login behavior is outside this release's test scope.
- The installer removes program files, registration, and shortcuts. WebView2 may retain application cache or other user data under `%LOCALAPPDATA%\app.tolly.windows`; the test-only cache was removed manually after verification.
