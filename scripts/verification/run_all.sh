#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 -m unittest \
  tests.verification.test_dispatch_contract \
  tests.verification.test_template_golden \
  tests.verification.test_installer_e2e -v

python3 -m unittest discover -s tests -p 'test_*.py' -v
