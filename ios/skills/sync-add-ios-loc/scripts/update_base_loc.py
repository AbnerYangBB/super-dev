#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

ASSIGN_RE = re.compile(r'^\s*"([^"\\]+)"\s*=\s*"((?:\\.|[^"\\])*)";\s*$')
YB_HEADER = '// === 下面是修改 (YB) ==='
YB_DESC = '// 以下key在最近的提交中被修改了值'
YC_HEADER = '// === 下面是新增 (YC) ==='
YC_DESC = '// 以下key在最近的提交中新增'


def escape_value(value: str) -> str:
    return (value or '').replace('\\"', '"').replace('"', '\\"')


def parse_entities(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    entities = data.get('entities', data if isinstance(data, list) else [])
    normalized = []
    for e in entities:
        status = e.get('status')
        key = e.get('key')
        if not key or status not in ('新增', '修改', '删除'):
            continue
        normalized.append({
            'key': key,
            'status': status,
            'value': e.get('value', ''),
        })
    return normalized


def strip_old_section_markers(lines):
    out = []
    skip_next_desc = False
    for line in lines:
        stripped = line.strip()
        if stripped in (YB_HEADER, YC_HEADER):
            skip_next_desc = True
            continue
        if skip_next_desc and stripped in (YB_DESC, YC_DESC):
            skip_next_desc = False
            continue
        skip_next_desc = False
        out.append(line)
    return out


def main():
    parser = argparse.ArgumentParser(description='Update base Localizable.strings with YB/YC sections.')
    parser.add_argument('--base-file', required=True)
    parser.add_argument('--entities-json', required=True)
    parser.add_argument('--apply-delete', action='store_true')
    args = parser.parse_args()

    base_path = Path(args.base_file)
    lines = base_path.read_text(encoding='utf-8').splitlines()
    entities = parse_entities(Path(args.entities_json))

    added = {e['key']: e['value'] for e in entities if e['status'] == '新增'}
    modified = {e['key']: e['value'] for e in entities if e['status'] == '修改'}
    deleted = {e['key'] for e in entities if e['status'] == '删除'}

    touched = set(added.keys()) | set(modified.keys()) | (deleted if args.apply_delete else set())

    # Remove touched keys from original area
    kept = []
    for line in lines:
        m = ASSIGN_RE.match(line)
        if m and m.group(1) in touched:
            continue
        kept.append(line)

    # Remove existing YB/YC headings; we regenerate below.
    kept = strip_old_section_markers(kept)

    # Trim trailing blanks
    while kept and kept[-1].strip() == '':
        kept.pop()

    out = kept[:]
    if modified:
        out.append('')
        out.append(YB_HEADER)
        out.append(YB_DESC)
        for key in sorted(modified.keys()):
            out.append(f'"{key}" = "{escape_value(modified[key])}";')

    if added:
        out.append('')
        out.append(YC_HEADER)
        out.append(YC_DESC)
        for key in sorted(added.keys()):
            out.append(f'"{key}" = "{escape_value(added[key])}";')

    out.append('')
    base_path.write_text('\n'.join(out), encoding='utf-8')

    summary = {
        'modified_count': len(modified),
        'added_count': len(added),
        'deleted_count': len(deleted) if args.apply_delete else 0,
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
