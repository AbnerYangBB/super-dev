# Portable AI Config Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a transaction-safe, non-destructive installer/rollback system for codex-ios AI configuration templates, with namespaced skills under `.agents/skills/super-dev`.

**Architecture:** Use a manifest+profile model and a Python installer engine that applies strategies (`append_block`, `merge_toml_keys`, `sync_additive_dir`) while recording transaction state and backups under `.codex/portable/`. Rollback restores from transaction backups and removes files created by that transaction only.

**Tech Stack:** Python 3 (stdlib: `argparse`, `json`, `pathlib`, `shutil`, `tomllib`, `datetime`, `hashlib`), Markdown docs, shell verification commands.

---

### Task 1: Define Install Metadata

**Files:**
- Create: `common/install/profiles/codex-ios.json`
- Create: `common/install/manifests/codex-ios.json`

**Step 1: Write the failing test**

```python
# tests/portable_config/test_portable_apply.py

def test_profile_and_manifest_load_successfully(tmp_path):
    # Arrange: create template root with metadata files
    # Act: call loader
    # Assert: profile/manfiest parsed and required keys exist
    assert metadata["profile"] == "codex-ios"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.portable_config.test_portable_apply.TestPortableApply.test_profile_and_manifest_load_successfully -v`
Expected: FAIL because loader or files do not exist.

**Step 3: Write minimal implementation**

- Add minimal JSON profile and manifest with required keys and actions.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.portable_config.test_portable_apply.TestPortableApply.test_profile_and_manifest_load_successfully -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add common/install/profiles/codex-ios.json common/install/manifests/codex-ios.json
git commit -m "feat: add codex ios metadata"
```

### Task 2: Build Apply Engine with TDD

**Files:**
- Create: `common/install/scripts/portable_config.py`
- Create: `common/install/scripts/portable_apply.py`
- Create: `tests/portable_config/test_portable_apply.py`

**Step 1: Write the failing test**

```python
def test_apply_creates_transaction_state_and_files(self):
    result = run_apply(...)
    self.assertEqual(result.returncode, 0)
    self.assertTrue((project_root / ".codex/portable/state.json").exists())
    self.assertTrue((project_root / "AGENTS.md").exists())
    self.assertTrue((project_root / ".codex/config.toml").exists())
    self.assertTrue((project_root / ".agents/skills/super-dev/xcode-builder/SKILL.md").exists())
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.portable_config.test_portable_apply.TestPortableApply.test_apply_creates_transaction_state_and_files -v`
Expected: FAIL because apply script does not exist.

**Step 3: Write minimal implementation**

- Implement metadata loading.
- Implement `append_block`, `merge_toml_keys`, `sync_additive_dir`.
- Implement transaction state writing and backup layout.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.portable_config.test_portable_apply.TestPortableApply.test_apply_creates_transaction_state_and_files -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add common/install/scripts/portable_config.py common/install/scripts/portable_apply.py tests/portable_config/test_portable_apply.py
git commit -m "feat: add portable apply engine"
```

### Task 3: Add Non-Destructive Merge and Conflict Safety

**Files:**
- Modify: `tests/portable_config/test_portable_apply.py`
- Modify: `common/install/scripts/portable_config.py`

**Step 1: Write the failing test**

```python
def test_apply_preserves_existing_user_toml_values(self):
    # target has custom model value
    # source has default model value
    # expect target keeps custom value
    self.assertIn('model = "custom-model"', config_text)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.portable_config.test_portable_apply.TestPortableApply.test_apply_preserves_existing_user_toml_values -v`
Expected: FAIL due replacement/incorrect merge.

**Step 3: Write minimal implementation**

- Merge only missing TOML keys recursively.
- Keep user existing values unchanged.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.portable_config.test_portable_apply.TestPortableApply.test_apply_preserves_existing_user_toml_values -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add common/install/scripts/portable_config.py tests/portable_config/test_portable_apply.py
git commit -m "fix: preserve user config values"
```

### Task 4: Build Rollback Engine with TDD

**Files:**
- Create: `common/install/scripts/portable_rollback.py`
- Create: `tests/portable_config/test_portable_rollback.py`

**Step 1: Write the failing test**

```python
def test_rollback_restores_previous_files_and_removes_created_files(self):
    run_apply(...)
    run_rollback(...)
    self.assertEqual((project_root / "AGENTS.md").read_text(), original_agents)
    self.assertFalse((project_root / ".agents/skills/super-dev/xcode-builder/SKILL.md").exists())
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.portable_config.test_portable_rollback.TestPortableRollback.test_rollback_restores_previous_files_and_removes_created_files -v`
Expected: FAIL because rollback script does not exist.

**Step 3: Write minimal implementation**

- Load latest unapplied transaction.
- Restore backups for modified files.
- Remove files created by the transaction.
- Mark transaction rolled back.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.portable_config.test_portable_rollback.TestPortableRollback.test_rollback_restores_previous_files_and_removes_created_files -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add common/install/scripts/portable_rollback.py tests/portable_config/test_portable_rollback.py
git commit -m "feat: add portable rollback engine"
```

### Task 5: Publish AI Entry Docs

**Files:**
- Create: `common/install/INSTALL.md`
- Create: `common/install/ROLLBACK.md`

**Step 1: Write the failing test**

```python
def test_install_doc_contains_hard_rules_and_apply_command(self):
    text = install_doc.read_text(encoding="utf-8")
    self.assertIn("Hard Rules", text)
    self.assertIn("portable_apply.py", text)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.portable_config.test_docs.TestInstallDocs.test_install_doc_contains_hard_rules_and_apply_command -v`
Expected: FAIL because docs/tests do not exist.

**Step 3: Write minimal implementation**

- Add INSTALL/ROLLBACK docs with direct AI-invokable commands and safety rules.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.portable_config.test_docs -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add common/install/INSTALL.md common/install/ROLLBACK.md tests/portable_config/test_docs.py
git commit -m "docs: add install and rollback guides"
```

### Task 6: End-to-End Verification

**Files:**
- Modify: `tests/portable_config/test_portable_apply.py`
- Modify: `tests/portable_config/test_portable_rollback.py`

**Step 1: Write the failing test**

```python
def test_apply_then_rollback_round_trip(self):
    run_apply(...)
    run_rollback(...)
    self.assert_project_restored()
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.portable_config.test_portable_apply tests.portable_config.test_portable_rollback -v`
Expected: FAIL if transaction state tracking is incomplete.

**Step 3: Write minimal implementation**

- Complete missing state/history fields and restoration edge cases.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest -v`
Expected: PASS all tests.

**Step 5: Commit**

```bash
git add tests/portable_config common/install
git commit -m "test: add round trip coverage"
```
