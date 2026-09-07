# Maintenance recheck — 2026-09-07

## Completed follow-through

The initial review below is historical. Its code-maintenance findings were implemented in [PR #12](https://github.com/rui8001/tolly/pull/12), merged as `578d84e869b24e256150755e61662d88b7328d91`:

- Privacy scanning now covers tracked text, including source and documentation, with three synthetic regression tests.
- Codex subprocess parsing safely ignores non-object JSON responses; five new tests cover malformed responses, timeouts, startup failures and cleanup.
- Vite 8.2.2 and all five pending dependency upgrades were integrated. The superseded dependency PRs were closed, not represented as individually merged.
- Local suites passed: 24 Python tests and 14 JavaScript tests, plus production and standalone builds.
- [Windows/Linux CI](https://github.com/rui8001/tolly/actions/runs/34082519761) passed all five jobs, including a full Windows desktop/installer build.
- [MSI and NSIS smoke matrix](https://github.com/rui8001/tolly/actions/runs/34082519752) passed separate clean-runner install, launch and uninstall checks against published v1.2.0 assets.

The new code is on main; it is not retroactively part of v1.2.0. Automated smoke tests are not interactive usability tests or external adoption. Remaining work is genuine Windows feedback, code signing and broader tool-specific real-world validation. Private application details remain outside GitHub.

## Initial review (before the fixes above)

Source reviewed: `6d4ebd24a6de73c77188c1c3e9349cbe205def07` (public main). The downloaded source's Git tree matched the public commit tree.

## Reproduced checks

- Python 3.12 engine suite: 19 tests passed using synthetic fixtures.
- Node 24 interface suite: 11 tests passed.
- Version consistency and the existing tracked-data privacy check passed.
- Frozen-lockfile installation, production Vite build, and standalone preview build passed.
- Setup instructions now recommend Node 24, matching CI. The previous blanket Node 20+ requirement included versions below Vite's supported range.

The latest main [CI run](https://github.com/rui8001/tolly/actions/runs/33604443483) passed. The previously completed [Windows MSI smoke](https://github.com/rui8001/tolly/actions/runs/33603786413) passed. This recheck ran on macOS; it does not claim a new Windows run or an interactive Windows user test. The smoke covers MSI, not NSIS.

## Public evidence

- Latest release: v1.2.0; three public releases total.
- Stars: 0; forks: 0.
- [Trial invitation #9](https://github.com/rui8001/tolly/issues/9): no comments; no verified external trials recorded.
- v1.2.0 asset download counters: checksum 3, MSI 3, NSIS 0. Automated and maintainer activity may be included; these are not user counts.

## Remaining improvements

- Obtain voluntary Windows 10/11 feedback and add NSIS installation coverage.
- Expand synthetic collector coverage and exercise subprocess failures directly.
- Expand the privacy scanner beyond selected data extensions to documentation and source text.
- Review five pending dependency upgrades against current main, especially the Vite major upgrade and standalone packaging.

The application can enter final maintainer review while disclosing early adoption. The official program does not state a minimum of three trial users. Identity fields stay outside this repository; form submission requires the applicant's explicit confirmation.
