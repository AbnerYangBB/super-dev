#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

ASSIGN_RE = re.compile(r'^\s*"([^"\\]+)"\s*=\s*"((?:\\.|[^"\\])*)";\s*$')


def escape_value(value: str) -> str:
    return (value or '').replace('\\"', '"').replace('"', '\\"')


def load_entities(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    entities = data.get('entities', data if isinstance(data, list) else [])
    out = []
    for e in entities:
        status = e.get('status')
        key = e.get('key')
        if not key or status not in ('新增', '修改', '删除'):
            continue
        out.append({
            'key': key,
            'status': status,
            'value': e.get('value', ''),
        })
    return out


def index_keys(lines):
    idx = {}
    for i, line in enumerate(lines):
        m = ASSIGN_RE.match(line)
        if m:
            idx[m.group(1)] = i
    return idx


def main():
    parser = argparse.ArgumentParser(description='Incremental key sync for iOS Localizable.strings.')
    parser.add_argument('--target-file', required=True)
    parser.add_argument('--entities-json', required=True)
    parser.add_argument('--apply-delete', action='store_true')
    args = parser.parse_args()

    target_path = Path(args.target_file)
    lines = target_path.read_text(encoding='utf-8').splitlines()
    entities = load_entities(Path(args.entities_json))

    key_to_entity = {e['key']: e for e in entities}

    # Apply updates/replacements in place first
    idx = index_keys(lines)
    updated = 0
    added = 0
    deleted = 0

    for key, entity in key_to_entity.items():
        status = entity['status']
        value = escape_value(entity.get('value', ''))

        if status in ('新增', '修改'):
            if key in idx:
                lines[idx[key]] = f'"{key}" = "{value}";'
                updated += 1
            else:
                lines.append(f'"{key}" = "{value}";')
                added += 1
        elif status == '删除' and args.apply_delete:
            if key in idx:
                lines[idx[key]] = None
                deleted += 1

    if args.apply_delete and deleted > 0:
        lines = [line for line in lines if line is not None]

    target_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'updated': updated, 'added': added, 'deleted': deleted}, ensure_ascii=False))


if __name__ == '__main__':
    main()
