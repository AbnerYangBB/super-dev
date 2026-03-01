# Claude iOS Config Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `claude-ios` profile support to portable installer with official-style project-level Claude Code config delivery.

**Architecture:** Reuse manifest+profile pipeline. Add one new merge strategy `merge_json_keys` for non-destructive `.claude/settings.json` updates, and introduce `ios/claude` templates mapped by new `claude-ios` metadata.

**Tech Stack:** Python 3 (`json`, `pathlib`, `unittest`), Markdown docs, existing installer scripts.

---

### Task 1: Add failing tests for claude metadata and apply flow

**Files:**
- Modify: `tests/portable_config/test_portable_apply.py`
- Modify: `tests/portable_config/test_repo_basics.py`
- Modify: `tests/portable_config/test_docs.py`

**Step 1: Write the failing tests**

1. Assert `load_profile_and_manifest(REPO_ROOT, "claude-ios")` succeeds.
2. Assert apply with `--profile claude-ios` creates `CLAUDE.md` and `.claude/settings.json`.
3. Assert existing `.claude/settings.json` keeps user keys and receives missing defaults.
4. Assert README/INSTALL include `claude-ios`.

**Step 2: Run tests to verify they fail**

Run:
`python3 -m unittest tests.portable_config.test_portable_apply tests.portable_config.test_repo_basics tests.portable_config.test_docs -v`

Expected: FAIL (missing metadata/template/docs).

### Task 2: Implement claude metadata and template

**Files:**
- Create: `common/install/profiles/claude-ios.json`
- Create: `common/install/manifests/claude-ios.json`
- Create: `ios/claude/CLAUDE.md`
- Create: `ios/claude/settings.json`

**Step 1: Add minimal implementation**

1. Define targets for `CLAUDE.md` and `.claude/settings.json`.
2. Define actions: `append_block` + `merge_json_keys`.
3. Add safe default settings (permissions baseline).

**Step 2: Run tests**

Run:
`python3 -m unittest tests.portable_config.test_portable_apply -v`

Expected: still FAIL until strategy implemented.

### Task 3: Implement `merge_json_keys` strategy in installer

**Files:**
- Modify: `common/install/scripts/portable_config.py`

**Step 1: Add strategy support**

1. Implement JSON recursive missing-key merge helper.
2. Add `_merge_json_keys` handler with conflict output for invalid target JSON.
3. Register `merge_json_keys` in `apply_profile` strategy switch.

**Step 2: Run targeted tests**

Run:
`python3 -m unittest tests.portable_config.test_portable_apply -v`

Expected: PASS.

### Task 4: Update user docs for profile selection

**Files:**
- Modify: `README.md`
- Modify: `common/install/INSTALL.md`

**Step 1: Document `claude-ios`**

1. Update support scope to Codex + Claude.
2. In INSTALL, mention optional profiles and add `claude-ios` execution example.

**Step 2: Run docs tests**

Run:
`python3 -m unittest tests.portable_config.test_repo_basics tests.portable_config.test_docs -v`

Expected: PASS.

### Task 5: Full verification

**Files:**
- Modify: none (verification)

**Step 1: Run full tests**

Run:
`python3 -m unittest discover -s tests -v`

Expected: PASS all tests.

**Step 2: Commit**

```bash
git add common/install ios tests docs/plans README.md
git commit -m "feat: 支持claude-ios配置下发"
```
