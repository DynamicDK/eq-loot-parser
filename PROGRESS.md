# Progress

## 2026-05-27 — Loot-list builder + remove trash filter

**Objective:** Drop the unreliable trash filter and turn the GUI into a tool for
hand-picking loot across characters into a single copy/exportable list.

**Done:**
- Removed `--exclude-trash` from the CLI and the trash-substring filter from both
  `eq_loot.py` and the GUI (it would inevitably mis-classify items).
- GUI redesigned into three panes: characters → items → collected list.
  - "Ungroup items" toggle: show each copy on its own row vs. one row with a qty.
  - Checkbox column on the items pane (click a row to toggle); Check/Uncheck all.
  - "Add checked →" copies checked items into the collected list, tagged with the
    looting character, and clears the checkboxes. A grouped qty-N row adds N entries.
  - Remove selected / Clear on the collected list.
  - Copy ▾ and Export ▾ menubuttons, each offering "Item names only" (one per line)
    and "Items + character" (CSV with an Item,Character header).
- Added `tests/test_eq_loot.py` (stdlib `unittest`, 12 tests) covering the parser
  and the GUI's output formatting. Extracted `format_loot_text()` as a pure,
  testable function.
- Updated README.

**Status:** Complete. All 12 tests pass; GUI smoke-tested headlessly.

**Known caveat (pre-existing, not in scope):** the loot-line regex expects a single
space before the day-of-month, so single-digit days (which EQ pads with two spaces,
e.g. `Wed Dec  3`) may not match. Worth confirming against a real log before relying on it.

**Resolved (2026-05-27):** fixed — the regex now allows the doubled space and a
regression test was added. The suite later grew to 17 tests (parser + GUI).

---

## Branch workflow

Two long-lived branches:

- **`main`** — public release branch. Intentionally has **no `tests/`** folder and
  no "Tests" section in its README (kept off the branch the public browses).
  Release tags (`v*`) are cut from `main`; pushing one triggers
  `.github/workflows/release.yml`, which builds, code-signs via SignPath, and
  publishes the signed `eq-loot-viewer.exe` (see `SIGNING.md`, on `main`).
- **`develop`** — development branch. Same as `main` plus the `tests/` suite and the
  README "Tests" section. Do day-to-day work here and run the tests:

  ```
  python -m unittest discover -s tests
  ```

### Do NOT `git merge` between these branches

`main` carries a commit that *deletes* `tests/`, and the two branches also differ in
the README on purpose. A merge would therefore either delete the tests on `develop`
or re-add them to `main` (and clobber a README). Move changes with **cherry-pick**:

```
# promote a source fix from develop to main (for release)
git checkout main
git cherry-pick <sha>
#   if that commit also touched tests, drop them from main afterwards:
#   git rm -r tests && git commit --amend --no-edit

# bring a main-only change (e.g. the CI workflow) onto develop
git checkout develop
git cherry-pick <sha>
```

Keep source changes and test changes in separate commits where you can — it makes
promotion to `main` a clean, conflict-free cherry-pick.

### Release checklist

1. Land and test the change on `develop`.
2. Cherry-pick the source commit(s) onto `main`.
3. `git tag vX.Y.Z && git push origin vX.Y.Z` → CI builds, signs, and publishes
   the signed exe (one-time SignPath setup in `SIGNING.md` must be done first).

### Current divergence (2026-05-27)

`main` is ahead of `develop`: it has the CI signing pipeline
(`.github/workflows/release.yml`, `SIGNING.md`) and the Nuitka `.gitignore` entries
that `develop` lacks; `develop` still has `tests/`. Cherry-pick those infra commits
onto `develop` when convenient so it stays a superset of `main` (plus tests).
