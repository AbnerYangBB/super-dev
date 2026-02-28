#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

STRING_ASSIGN_RE = re.compile(r'^"([^"\\]+)"\s*=\s*"((?:\\.|[^"\\])*)";\s*$')
STRING_LITERAL_RE = re.compile(r'"((?:\\.|[^"\\])*)"')
LOCAL_KEY_RE = re.compile(r'"([^"\\]+)"\s*\.\s*local\b')
HUNK_RE = re.compile(r'^@@ -(?P<old>\d+)(?:,\d+)? \+(?P<new>\d+)(?:,\d+)? @@')


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def is_probably_key(s: str) -> bool:
    if not s:
        return False
    # Common i18n key patterns: intlXxx, voice_xxx, snake_case, dot.case
    if re.match(r'^[A-Za-z0-9_.-]+$', s):
        if s.startswith(('intl', 'voice_', 'home_', 'more_', 'setting', 'language_')):
            return True
        if '_' in s or '.' in s:
            return True
    return False


def should_ignore_literal(line: str, value: str) -> bool:
    stripped = line.strip()
    if stripped.startswith(('import ', '//', '/*', '*')):
        return True
    if is_probably_key(value):
        return True
    if value in ('%d', '%@', '%s'):
        return True
    return False


def parse_swift_diff(diff_text: str):
    entities = []
    current_file = None
    new_line = 0

    # Collect for status dedupe
    added_local_keys = defaultdict(set)
    removed_local_keys = defaultdict(set)

    added_literals = defaultdict(list)
    removed_literals = defaultdict(list)

    for raw in diff_text.splitlines():
        if raw.startswith('+++ b/'):
            path = raw[6:]
            current_file = path if path.endswith('.swift') else None
            new_line = 0
            continue
        h = HUNK_RE.match(raw)
        if h:
            new_line = int(h.group('new'))
            continue
        if not current_file:
            continue

        if raw.startswith('+') and not raw.startswith('+++'):
            line = raw[1:]
            for m in LOCAL_KEY_RE.finditer(line):
                added_local_keys[current_file].add(m.group(1))
            for m in STRING_LITERAL_RE.finditer(line):
                value = m.group(1)
                if should_ignore_literal(line, value):
                    continue
                added_literals[current_file].append((new_line, value, line.strip()))
            new_line += 1
        elif raw.startswith('-') and not raw.startswith('---'):
            line = raw[1:]
            for m in LOCAL_KEY_RE.finditer(line):
                removed_local_keys[current_file].add(m.group(1))
            for m in STRING_LITERAL_RE.finditer(line):
                value = m.group(1)
                if should_ignore_literal(line, value):
                    continue
                removed_literals[current_file].append((None, value, line.strip()))
        elif raw.startswith(' '):
            new_line += 1

    # Key usage entities
    all_files = set(added_local_keys.keys()) | set(removed_local_keys.keys())
    for f in sorted(all_files):
        a = added_local_keys[f]
        r = removed_local_keys[f]
        for k in sorted(a - r):
            entities.append({
                'type': 'local_key_usage',
                'status': '新增',
                'file': f,
                'key': k,
                'value': None,
                'needs_review': False,
            })
        for k in sorted(r - a):
            entities.append({
                'type': 'local_key_usage',
                'status': '删除',
                'file': f,
                'key': k,
                'value': None,
                'needs_review': False,
            })

    # Hardcoded string entities (candidate)
    for f in sorted(set(added_literals.keys()) | set(removed_literals.keys())):
        for ln, value, source in added_literals.get(f, []):
            entities.append({
                'type': 'hardcoded_string_candidate',
                'status': '新增',
                'file': f,
                'line': ln,
                'key': None,
                'value': value,
                'source_line': source,
                'needs_review': True,
            })
        for ln, value, source in removed_literals.get(f, []):
            entities.append({
                'type': 'hardcoded_string_candidate',
                'status': '删除',
                'file': f,
                'line': ln,
                'key': None,
                'value': value,
                'source_line': source,
                'needs_review': True,
            })

    return entities


def parse_base_diff(diff_text: str):
    old_map = {}
    new_map = {}
    for raw in diff_text.splitlines():
        if raw.startswith('---') or raw.startswith('+++') or raw.startswith('@@'):
            continue
        if raw.startswith('-') and not raw.startswith('---'):
            m = STRING_ASSIGN_RE.match(raw[1:].strip())
            if m:
                old_map[m.group(1)] = m.group(2)
        if raw.startswith('+') and not raw.startswith('+++'):
            m = STRING_ASSIGN_RE.match(raw[1:].strip())
            if m:
                new_map[m.group(1)] = m.group(2)

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    added = sorted(new_keys - old_keys)
    deleted = sorted(old_keys - new_keys)
    modified = sorted(k for k in (old_keys & new_keys) if old_map[k] != new_map[k])

    return {
        'added': [{'key': k, 'value': new_map[k]} for k in added],
        'modified': [{'key': k, 'old_value': old_map[k], 'new_value': new_map[k]} for k in modified],
        'deleted': [{'key': k, 'value': old_map[k]} for k in deleted],
    }


def main():
    parser = argparse.ArgumentParser(description='Detect localization entities from git diff.')
    parser.add_argument('--repo-root', default='.')
    parser.add_argument('--base-file', required=True, help='Path to base Localizable.strings')
    parser.add_argument('--diff-ref', default='HEAD', help='Compare against this ref. Default: HEAD')
    parser.add_argument('--output', default='')
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    base_file = str(Path(args.base_file))

    swift_diff = run(['git', 'diff', '--unified=0', args.diff_ref, '--', '*.swift'], cwd=str(root))
    base_diff = run(['git', 'diff', '--unified=0', args.diff_ref, '--', base_file], cwd=str(root))

    out = {
        'base_file': base_file,
        'diff_ref': args.diff_ref,
        'swift_entities': parse_swift_diff(swift_diff),
        'base_key_changes': parse_base_diff(base_diff),
    }

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding='utf-8')
    else:
        print(text)


if __name__ == '__main__':
    main()
