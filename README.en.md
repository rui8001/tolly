# Tolly for Windows

[![CI](https://github.com/rui8001/tolly/actions/workflows/ci.yml/badge.svg)](https://github.com/rui8001/tolly/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/rui8001/tolly)](https://github.com/rui8001/tolly/releases/latest)

[中文说明](README.md)

Tolly is a local-first Windows tray application that aggregates verifiable usage written by AI coding tools to local JSONL files, read-only databases, or local provider interfaces. It reports tokens, credits, calls, projects, and estimated API cost without uploading conversation logs to an analytics service.

Tolly is inspired by the product direction of the macOS project [Tokei](https://github.com/cclank/tokei). Collector behavior and pricing provenance are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [docs/UPSTREAM_PROVENANCE.md](docs/UPSTREAM_PROVENANCE.md). Tolly is not an official Windows version of Tokei and is not affiliated with any model or tool provider.

![Tolly 1.2.0 usage overview](docs/assets/v1.2.0/overview.png)

## Download

Download the latest release from [GitHub Releases](https://github.com/rui8001/tolly/releases/latest):

- `Tolly_1.2.0_x64-setup.exe` — recommended interactive installer.
- `Tolly_1.2.0_x64_en-US.msi` — MSI package for managed deployment.
- `SHA256SUMS.txt` — SHA-256 checksums for both installers.

The installers are not Authenticode-signed yet, so Windows may show an unknown-publisher warning. Download only from this repository and verify the matching checksum before installation.

## What Tolly does

- Reads 20 AI coding tools through local JSONL, SQLite, and provider-authored local interfaces.
- Aggregates today, yesterday, week, month, year, and all-time usage.
- Groups usage by model, project, day, and yearly recap.
- Runs as a single-instance Windows tray panel with manual and scheduled refresh.
- Shows provider-authored weekly limits or remaining credits only when a trustworthy field is available.
- Labels estimates and non-token metrics explicitly instead of presenting them as invoices or account balances.
- Bundles the Python engine as a PyInstaller sidecar, so end users do not need Python.

Estimated cost is not a bill. Tolly never converts token use or estimated cost into an invented account balance.

## Architecture

```text
local logs / read-only databases / local provider interfaces
                         |
                         v
                tally-engine collectors
                         |
                stable JSON contract
                         |
                         v
         Tauri command <-> Vite UI <-> tray window
```

`tally-engine/` is the single source of collector logic. `tally-win/` contains the Vite interface and Tauri 2 Windows shell. Development invokes the source engine; release builds freeze the same engine into the bundled sidecar.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the contract and failure boundaries.

## Develop and test

Prerequisites: Python 3.10+, Node.js 20+, pnpm 11, Rust stable, and Visual Studio Build Tools with the Desktop development with C++ workload.

```powershell
# Engine tests and output
cd tally-engine
python -m unittest discover -s tests -v
python -m engine --json

# Anonymous browser preview
cd ../tally-win
pnpm install --frozen-lockfile
pnpm dev

# Full desktop development
$env:TALLY_PYTHON = "C:\path\to\python.exe" # only if Python is not on PATH
pnpm tauri dev
```

For a release build:

```powershell
python -m pip install -e ".\tally-engine[build]"
cd tally-win
pnpm build
```

Every push and pull request runs the Python test matrix, JavaScript tests, Vite builds, Rust formatting and type checks, version consistency checks, and privacy scans. Tagged releases build NSIS/MSI installers and publish their checksums.

## Privacy

Collection, aggregation, and settings storage are local by default. Tolly does not include analytics or crash reporting and does not persist a copy of raw logs. Optional network behavior is documented in [docs/PRIVACY.md](docs/PRIVACY.md).

Bug reports must use synthetic examples. Never attach prompts, raw logs, paths, usernames, account IDs, repository names, session IDs, cookies, or API keys.

## Help test Tolly

Tolly is an early-stage public project seeking voluntary Windows 10/11 x64 usability tests. A test takes about 15–20 minutes and does not require a star, public identity, or real log upload.

- Follow [docs/USER_TESTING.md](docs/USER_TESTING.md).
- Submit the privacy-safe [usability report](https://github.com/rui8001/tolly/issues/new?template=usability_report.yml).
- See the zero-based [public results ledger](docs/USER_TEST_RESULTS.md).

Maintainer self-tests, CI runs, and download counts are not counted as real-user feedback.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before adding a collector. Security and privacy reports should use GitHub private vulnerability reporting as described in [SECURITY.md](SECURITY.md).

Tolly is licensed under the [MIT License](LICENSE). Third-party dependencies and upstream references retain their own rights and are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
