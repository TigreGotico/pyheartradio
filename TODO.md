# TODO — pyheartradio

## Open issues

- [ ] #4 Dependency Dashboard (Renovate bot)

## Gaps

- [ ] No typecheck configured (no mypy/pyright); dataclasses are typed but `Artist.albums/tracks/related_artists` are `List[dict]` (untyped passthrough of raw API data).
- [ ] `requires-python = ">=3.8"` but CI build matrix tests only 3.10–3.13; 3.8/3.9 are claimed but unverified.

(Tests present: mock, models, edge cases, import, live. CI present: build-tests, coverage, lint, license_check, pip_audit, release_workflow, release-preview, publish_stable, repo-health, conventional-label, nightly-live — all gh-automations reusable workflows at @dev. README, pyproject, remote, mediavocab integration all present.)

## Code TODOs

None found.
