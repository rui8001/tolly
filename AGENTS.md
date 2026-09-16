# Repository guidance

Tolly is a local-first Windows usage viewer. Read the relevant README section, then only the documentation and source needed for the task.

## Change routing and validation

- `tally-engine/` is the single Python engine. Parser, aggregation, or price changes need synthetic fixtures and relevant `unittest` cases; run `python -m unittest discover -s tests -v` from that directory before an engine change is complete.
- `tally-win/` owns the web UI. For UI changes, use its existing `pnpm web:test`, `pnpm web:build`, and relevant preview checks. Do not use the installer build as a substitute for checking visible behavior.
- `tally-win/src-tauri/` owns the Windows shell. Rust, sidecar, packaging, dependency, or release changes require the corresponding Windows CI and installer checks; a successful macOS/Linux check does not prove Windows compatibility.
- Documentation-only changes need factual and link checks locally. Preserve existing CI and required checks; do not skip or rename them without inspecting repository rules and their downstream effects.
- Release work also follows `docs/RELEASING.md`, `docs/RELEASE_CHECKLIST.md`, and existing version/privacy checks. Separate source validation, installer validation, released version, and real user feedback.

## Product and privacy boundaries

- Use synthetic or anonymized fixtures; never commit real logs, prompts, usernames, account identifiers, local project paths, credentials, or private usage data.
- Cost is a price-table estimate, not a bill. Balances require explicit provider quota fields; do not infer them from token usage or silently turn on network queries.
- Keep the engine single-sourced and preserve upstream attribution in `docs/UPSTREAM_PROVENANCE.md` and `THIRD_PARTY_NOTICES.md`.
- Preserve unrelated changes and lockfiles. Complete authorized work and relevant validation; publishing a release, purchases, external recruitment, or access changes need their own applicable authorization.
