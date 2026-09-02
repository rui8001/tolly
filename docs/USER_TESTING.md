# Real-user testing guide

This voluntary test checks whether a Windows user can install and understand Tolly without private help from the maintainer. It is not a request for stars, promotion, public identity, or access to real usage logs.

## Who can test

Use a Windows 10 or Windows 11 x64 computer. You may test even if none of Tolly's supported AI coding tools are installed; installation, launch, empty-state, navigation, and uninstall feedback are still useful.

Do not participate on a managed work computer unless you are authorized to install unsigned software.

## Before starting

1. Open the latest [GitHub Release](https://github.com/rui8001/tolly/releases/latest).
2. Download `SHA256SUMS.txt` and one installer.
3. Verify the installer's SHA-256 value against the matching line.
4. Expect an unknown-publisher warning because the current installer is not Authenticode-signed.

Do not disable organizational security controls to run the test.

## Suggested 15–20 minute test

1. Install Tolly using the NSIS setup executable or MSI package.
2. Launch Tolly from the Start menu and confirm that its tray panel appears.
3. Check Overview, Models, Projects, and Settings.
4. Change the time range and refresh frequency.
5. If supported tools are detected, verify only whether the totals look plausible. Do not share the totals or raw data.
6. Close and reopen the panel, then launch Tolly a second time to check single-instance behavior.
7. Uninstall Tolly using Windows Settings or the installer.

Stop immediately if the application requests unexpected privileges, attempts to upload a log, exposes a private path, or behaves in a way you consider unsafe.

## Report the result

Use the [usability report form](https://github.com/rui8001/tolly/issues/new?template=usability_report.yml). A GitHub Issue is public, so report only:

- Windows version in broad form, such as Windows 11 x64;
- installer type;
- completed/stopped/blocked outcome;
- the first reproducible problem;
- synthetic or redacted reproduction steps.

Never include your name, employer, email, username, home directory, repository name, prompt, model output, account ID, session ID, API key, cookie, raw log, database, screenshot containing private data, or exact token totals.

Private feedback may be summarized only with permission. Maintainer self-tests and automated checks are recorded separately and never counted as real-user trials.
