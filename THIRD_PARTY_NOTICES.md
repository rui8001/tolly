# Third-party notices

Tolly uses open-source dependencies whose own licenses remain in force. The principal runtime and build-time components include Tauri, Vite, Rust crates in `tally-win/src-tauri/Cargo.lock`, Python, PyInstaller, and the optional `zstandard` Python package. Exact resolved JavaScript and Rust dependency versions are recorded in `tally-win/pnpm-lock.yaml` and `tally-win/src-tauri/Cargo.lock`.

## Tokei reference project

Tolly is inspired by [cclank/tokei](https://github.com/cclank/tokei). Some local-log collector behavior and pricing mappings were refactored from or informed by that project. Tolly is not an official port. Its Windows shell, interface assets, product name, documentation, and release binaries are maintained separately and do not reuse Tokei branding.

The upstream README at commit `cd942dfb6a8aa409f92adde020ebdf4d9514ba9b` declared the project to be MIT licensed when reviewed on 2026-08-26. The checked repository did not contain a separate root license text or a more specific copyright notice. Tolly therefore preserves this source attribution to **cclank/Tokei and its contributors**. If upstream publishes a complete license notice later, maintainers should update this file to reproduce it verbatim.

Upstream source: <https://github.com/cclank/tokei>

The reviewed commit, identical pricing-data hash, independently maintained components, and conservative future-import rule are recorded in [`docs/UPSTREAM_PROVENANCE.md`](docs/UPSTREAM_PROVENANCE.md). This record exists because the reviewed upstream revision identified itself as MIT in its README but did not include a separate root license file or a more specific copyright notice.

## Pricing data

`tally-engine/pricing.json` contains model identifiers and public API pricing used only for estimates. Prices can change and may not match subscriptions, discounts, taxes, or invoices. Model and provider names remain trademarks of their respective owners; their presence does not imply endorsement.
