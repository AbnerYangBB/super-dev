# Web Multi-Platform Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a full web configuration delivery path that mirrors the existing iOS flow across Codex, Claude, and Trae, including dispatcher generation, installation, rollback, docs, and verification.

**Architecture:** Keep the current profile-per-platform-per-tool structure and add parallel `*-web` profiles/manifests/templates. Reuse the existing installer and dispatcher cores, but extend template path resolution and prompt parsing so web artifacts are generated independently from iOS artifacts. Prevent iOS/web co-install conflicts by separating managed block IDs, MCP server keys, and skill destination directories while preserving merge-only semantics for shared config files.

**Tech Stack:** Python 3 stdlib installer/dispatcher scripts, JSON manifests/profiles/capability matrix, Markdown/TOML/JSON templates, unittest-based verification.

---

### Task 1: Lock down expected behavior with failing tests

**Files:**
- Modify: `tests/verification/test_installer_e2e.py`
- Modify: `tests/verification/test_template_golden.py`
- Modify: `tests/verification/test_dispatch_from_prompt.py`
- Modify: `tests/verification/test_skill_blackbox.py`
- Modify: `tests/verification/skill_blackbox_cases.json`
- Create: `tests/verification/fixtures/intents/web-frontend-skill.json`

**Step 1: Write failing tests for web apply/rollback and mixed iOS+web install**

Add cases that:
- apply `codex-web`, `claude-web`, `trae-web` successfully
- install `codex-ios` then `codex-web` into the same project and assert both managed blocks / skill directories remain
- rollback the latest transaction and confirm the other platform’s files remain

**Step 2: Write failing dispatcher/template tests**

Add cases that:
- parse prompts like `增加一个 web skill: frontend-design`
- generate changes under `web/codex`, `web/claude`, `web/trae`
- keep existing iOS fixtures passing

**Step 3: Run targeted tests to verify red**

Run:
- `python3 -m unittest tests.verification.test_dispatch_from_prompt -v`
- `python3 -m unittest tests.verification.test_template_golden -v`
- `python3 -m unittest tests.verification.test_installer_e2e -v`
- `python3 -m unittest tests.verification.test_skill_blackbox -v`

Expected: failures mentioning missing web profiles/templates/behavior.

### Task 2: Add web template inventory

**Files:**
- Create: `web/codex/AGENTS.md`
- Create: `web/codex/config.toml`
- Create: `web/claude/CLAUDE.md`
- Create: `web/claude/settings.json`
- Create: `web/claude/mcp.json`
- Create: `web/trae/RULES.md`
- Create: `web/trae/mcp.json`

**Step 1: Create minimal web baseline templates**

Use the iOS structure as reference, but keep instructions web-specific and avoid copying iOS-only skills or tool guidance.

**Step 2: Ensure coexistence-safe defaults**

Use MCP server names and instruction text that do not collide with iOS-only semantics; shared config files must still merge cleanly via existing strategies.

### Task 3: Add install profiles and manifests for web

**Files:**
- Create: `common/install/profiles/codex-web.json`
- Create: `common/install/profiles/claude-web.json`
- Create: `common/install/profiles/trae-web.json`
- Create: `common/install/manifests/codex-web.json`
- Create: `common/install/manifests/claude-web.json`
- Create: `common/install/manifests/trae-web.json`

**Step 1: Mirror iOS profile structure**

Map shared config targets to the same destination files (`AGENTS.md`, `.codex/config.toml`, etc.) but direct skills into separate namespaces/directories:
- Codex: `.agents/skills/{skill_namespace}`
- Claude: `.claude/skills`
- Trae: `.trae/skills`

**Step 2: Keep state and rollback independent per tool/profile family**

Reuse tool-level state roots so rollback still works, but rely on transaction ordering and managed block/action IDs to keep iOS/web updates isolated.

### Task 4: Extend dispatcher and template generation for web

**Files:**
- Modify: `.agents/skills/platform-feature-dispatcher/scripts/dispatch_from_prompt.py`
- Modify: `common/install/scripts/portable_dispatch.py`
- Modify: `common/install/scripts/portable_generate_templates.py`

**Step 1: Add prompt parsing for web target scope**

Recognize web context from prompts such as `web`, `frontend`, `网页`, `前端`, and carry that into intent metadata.

**Step 2: Route template writes by domain**

Update template path resolution so generated actions for web land in `web/...` instead of `ios/...`, while existing iOS intents continue to resolve unchanged.

**Step 3: Preserve iOS/web coexistence**

Managed block IDs must include the intent/domain so appending instructions for web does not replace iOS blocks in shared files.

### Task 5: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `common/install/INSTALL.md`
- Modify: `common/install/ROLLBACK.md` if needed
- Modify: `CONTRIBUTING.md` if needed

**Step 1: Document web support and full matrix**

Explain what `codex-web`, `claude-web`, and `trae-web` install.

**Step 2: Document customization and mixed install guidance**

Show how to run dispatcher for web requests and explicitly explain iOS/web co-install behavior and rollback semantics.

### Task 6: Verify end to end

**Files:**
- No new files unless fixtures need updates

**Step 1: Run targeted unit tests**

Run:
- `python3 -m unittest tests.verification.test_dispatch_from_prompt -v`
- `python3 -m unittest tests.verification.test_template_golden -v`
- `python3 -m unittest tests.verification.test_installer_e2e -v`
- `python3 -m unittest tests.verification.test_skill_blackbox -v`

**Step 2: Run full verification**

Run:
- `bash scripts/verification/run_all.sh`
- `python3 scripts/verification/run_skill_blackbox.py --repo-root . --cases tests/verification/skill_blackbox_cases.json --pretty`

Expected: `status=ok` and web profiles appear in generated/install results with no regression for iOS.
