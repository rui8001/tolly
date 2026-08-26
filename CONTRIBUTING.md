# Contributing

Thank you for helping improve Tolly.

## Ground rules

- Do not commit real usage logs, session identifiers, API keys, account data, or absolute home-directory paths.
- Add synthetic fixtures for parser bugs and keep them minimal.
- Do not copy upstream branding, screenshots, icons, or code unless its license and attribution requirements have been verified and documented.
- Keep `tally-engine` as the only source of collector logic; `tally-win` must not gain another engine snapshot.
- A new collector should support an environment-variable path override, open data read-only, tolerate malformed records, and include a focused unit test.

## Checks

```powershell
cd tally-engine
python -m unittest discover -s tests -v
cd ..
node scripts/check-privacy.mjs
cd tally-win
pnpm install --frozen-lockfile
pnpm web:build
cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
cargo check --manifest-path src-tauri/Cargo.toml
```

Open a pull request with a short explanation of the data source, supported platforms, privacy impact, and test coverage.
