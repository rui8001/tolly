# Upstream provenance

This record makes Tolly's relationship to [cclank/Tokei](https://github.com/cclank/tokei) reviewable. It does not imply endorsement or official port status.

## Reviewed source

- Repository: `cclank/tokei`
- Fixed commit: `cd942dfb6a8aa409f92adde020ebdf4d9514ba9b`
- Review date: 2026-08-26
- License declaration at that commit: the README badge and License section state `MIT`
- Repository state at review: no separate root `LICENSE` file and no more specific copyright notice was present

## Reused or informed material

Tolly's local-log collector behavior and pricing identifiers were refactored from or informed by the reviewed project. `tally-engine/pricing.json` is byte-for-byte identical to the upstream file at the fixed commit:

```text
SHA-256: 927376b971fb28f50b301c0f2b8741a3f9986c15f4831fc81cf67474fd99eb79
```

Tolly preserves the upstream repository and contributor attribution in `THIRD_PARTY_NOTICES.md`.

## Independently maintained material

Tolly's Windows Tauri shell, Vite interface, product name, icons, screenshots, documentation, release workflow, installer artifacts, project aggregation behavior, and current user-facing interaction are maintained in this repository. Tolly does not reuse Tokei branding, screenshots, icons, release binaries, or claim affiliation.

## Maintenance rule

Do not import additional upstream code, data, or assets unless the applicable license and required notice are verified at the exact source revision. If the upstream project publishes a complete license or copyright notice, reproduce the required notice here and in `THIRD_PARTY_NOTICES.md` before the next release.
