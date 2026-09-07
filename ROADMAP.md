# Public roadmap

Tolly is maintained as a local-first Windows utility for transparent AI coding usage. Milestones are tied to verifiable outcomes rather than repository activity counts.

## Completed readiness work

**Original window:** 2026-09-02 to 2026-09-06; maintenance gates rechecked September 7.

The time-boxed application preparation is over. Ongoing work prioritizes reliability and genuine usage. Private application fields and submission status are maintained outside this public repository.

| Gate | Public evidence | Status |
| --- | --- | --- |
| Installable public release | NSIS, MSI, and SHA-256 assets in [v1.2.0](https://github.com/rui8001/tolly/releases/tag/v1.2.0) | Complete |
| Repeatable source checks | Python, JavaScript, Vite, Rust, version, and privacy checks in CI | Complete |
| English discovery path | `README.en.md` and bilingual navigation | Complete |
| Clean-runner package smoke test | [MSI and NSIS checks](https://github.com/rui8001/tolly/actions/runs/34082519752): checksum, install, bundled sidecar, launch without Python, and uninstall | Complete for published v1.2.0 |
| Upstream provenance | Fixed upstream commit, file hash, attribution, and implementation boundary | Complete |
| Real-user trial | Privacy-safe guide, Issue form, zero-based ledger, and [public invitation #9](https://github.com/rui8001/tolly/issues/9) | Recruiting; no results counted yet |
| Application evidence | Public evidence table and maintenance record | Preparation complete; private application status is not tracked here |

## Continuing maintenance

- Daily: inspect new Issues, dependency PRs and failing CI. Reproduce actionable reports, add a synthetic regression, and ship a focused fix through a reviewed PR with passing checks. Do not create commits solely to record a healthy check.
- Weekly: review collector coverage, dependency changes and the next release gate. Keep verified provider quota separate from locally estimated usage.
- Next release candidate: package the privacy, collector and dependency improvements already on main; verify clean installation and upgrade from v1.2.0 using both MSI and NSIS before promoting new artifacts. Do not move existing tags or imply these fixes are already in v1.2.0.
- Real-user feedback: keep the existing invitation open, process genuine responses, and record only consented, anonymized outcomes. Do not post repeated invitations or promise test results before people participate.
- Code signing and automatic updates remain gated on signing identity, keys and rollback validation; do not purchase certificates or create signing credentials as routine maintenance.

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
