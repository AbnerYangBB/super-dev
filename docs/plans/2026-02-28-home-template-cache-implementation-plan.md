# Home Template Cache Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate template repository cache from project-local `.codex/portable/template/*` to `$HOME/.super-dev/templates/*` so installation does not leave commitable template residue in user projects.

**Architecture:** Keep project-local transaction state/backups under `.codex/portable/*`, but move template source checkout to a global home directory controlled by `SUPER_DEV_HOME`. Update INSTALL/ROLLBACK/README prompts and shell snippets to use the new home cache path while preserving apply/rollback behavior.

**Tech Stack:** Markdown docs, Python `unittest`, existing Python installer scripts.

---

### Task 1: Add failing docs constraints for HOME cache path

**Files:**
- Modify: `tests/portable_config/test_docs.py`
- Modify: `tests/portable_config/test_repo_basics.py`

**Step 1: Write the failing test**

Add assertions requiring:
- `INSTALL.md` and `ROLLBACK.md` contain `SUPER_DEV_HOME` and `$HOME/.super-dev` path.
- docs no longer contain `.codex/portable/template/super-dev`.
- `README.md` includes migration note about removing legacy project-local template clone.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.portable_config.test_docs tests.portable_config.test_repo_basics -v`
Expected: FAIL because current docs still reference project-local template path.

**Step 3: Write minimal implementation**

Do not change scripts yet; only update docs in next task to satisfy assertions.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.portable_config.test_docs tests.portable_config.test_repo_basics -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/portable_config/test_docs.py tests/portable_config/test_repo_basics.py common/install/INSTALL.md common/install/ROLLBACK.md README.md
git commit -m "docs: use home cache path"
```

### Task 2: Update INSTALL/ROLLBACK/README to home cache flow

**Files:**
- Modify: `common/install/INSTALL.md`
- Modify: `common/install/ROLLBACK.md`
- Modify: `README.md`

**Step 1: Write the failing test**

Use Task 1 tests as the failing gate.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.portable_config.test_docs tests.portable_config.test_repo_basics -v`
Expected: FAIL until docs are updated.

**Step 3: Write minimal implementation**

Update command snippets to:
- define `SUPER_DEV_HOME="${SUPER_DEV_HOME:-$HOME/.super-dev}"`
- use `TEMPLATE_DIR="$SUPER_DEV_HOME/templates/super-dev"`
- remove project-local `.codex/portable/template/...` references
- add migration note for legacy path cleanup.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.portable_config.test_docs tests.portable_config.test_repo_basics -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add common/install/INSTALL.md common/install/ROLLBACK.md README.md
git commit -m "docs: migrate cache to home"
```

### Task 3: End-to-end remote verification with home cache

**Files:**
- Modify: `tests/portable_config/test_portable_apply.py`
- Modify: `tests/portable_config/test_portable_rollback.py`

**Step 1: Write the failing test**

Add assertions to simulate docs command behavior and verify project tree does not create `.codex/portable/template/super-dev`.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.portable_config.test_portable_apply tests.portable_config.test_portable_rollback -v`
Expected: FAIL until tests reflect new flow and command simulation uses home cache path.

**Step 3: Write minimal implementation**

Adjust test harness paths so template root can point to temporary home cache directory outside project root.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.portable_config.test_portable_apply tests.portable_config.test_portable_rollback -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/portable_config/test_portable_apply.py tests/portable_config/test_portable_rollback.py
git commit -m "test: cover home cache flow"
```

### Task 4: Full regression + remote validation script run

**Files:**
- Modify: none (verification only)

**Step 1: Write the failing test**

N/A (verification task).

**Step 2: Run verification commands**

Run:
- `python3 -m unittest discover -s tests -p 'test_*.py' -v`
- one remote validation script:
  - clone remote template to `$HOME/.super-dev/templates/super-dev` (or temp HOME)
  - apply + rollback against temp project
  - assert no `.codex/portable/template/*` in project

**Step 3: Confirm expected output**

Expected:
- all tests PASS
- remote validation PASS
- project contains state/backups but no template repository residue.

**Step 4: Commit (if any final doc tweaks)**

```bash
git add -A
git commit -m "docs: finalize home cache migration"
```
