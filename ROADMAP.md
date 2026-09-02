# Public roadmap

Tolly is maintained as a local-first Windows utility for transparent AI coding usage. Milestones are tied to verifiable outcomes rather than repository activity counts.

## Application-readiness sprint

**Window:** 2026-09-02 to 2026-09-06

**Outcome:** prepare a truthful Codex for Open Source application with Tolly as the primary repository.

| Gate | Public evidence | Status |
| --- | --- | --- |
| Installable public release | NSIS, MSI, and SHA-256 assets in [v1.2.0](https://github.com/rui8001/tolly/releases/tag/v1.2.0) | Complete |
| Repeatable source checks | Python, JavaScript, Vite, Rust, version, and privacy checks in CI | Complete |
| English discovery path | `README.en.md` and repository metadata | In progress |
| Clean-runner package smoke test | Verify checksum, MSI install, bundled sidecar, launch, and uninstall on GitHub's Windows runner | In progress |
| Upstream provenance | Fixed upstream commit, file hash, attribution, and implementation boundary | In progress |
| Real-user trial | Privacy-safe guide, Issue form, and zero-based ledger | Ready for volunteers; no results counted yet |
| Application evidence | Public evidence table and current draft answers | In progress |

## Next release gate

Do not publish a version only to create activity. The next release should contain a confirmed user-facing fix or a material reliability improvement.

- Record real trial outcomes without requesting stars or public identity.
- Reproduce and fix confirmed blockers, or track them transparently.
- Add focused synthetic fixtures when a collector bug is reported.
- Re-run installation and upgrade checks against the actual release artifacts.

## Later work

- Test more collectors with synthetic fixtures.
- Add a signed update path only after code signing, update keys, and rollback are verified.
- Improve accessible keyboard navigation and screen-reader labels.
- Publish an anonymized maintenance retrospective after genuine external use exists.

## Integrity rules

- Never invent users, downloads, issues, testimonials, stars, or contributors.
- Never upload real logs, prompts, private paths, account identifiers, cookies, or credentials.
- Keep cost estimates separate from provider bills and account balances.
- Preserve third-party attribution and stop reuse if a source's license cannot be verified.
