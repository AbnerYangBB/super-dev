#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

PLACEHOLDER_RE = re.compile(
    r'%(?:(?P<pos>\d+)\$)?[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|h|ll|l|L|z|j|t)?(?P<conv>[@dDuUxXoOfeEgGcCsSpaAF])'
)
WHITESPACE_RE = re.compile(r'\s+')


def load_entity_map(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    entities = data.get('entities', data if isinstance(data, list) else [])
    out = {}
    for entity in entities:
        key = entity.get('key')
        status = entity.get('status')
        if not key or status not in ('新增', '修改'):
            continue
        out[key] = entity.get('value', '')
    return out


def extract_placeholders(value: str):
    if value is None:
        return []
    text = value.replace('%%', '')
    return [m.group('conv') for m in PLACEHOLDER_RE.finditer(text)]


def normalized_len(value: str):
    return len(WHITESPACE_RE.sub('', value or ''))


def main():
    parser = argparse.ArgumentParser(
        description='Validate translated localization entities before incremental sync.'
    )
    parser.add_argument('--source-entities', required=True, help='zh-Hans entities json')
    parser.add_argument('--translated-entities', required=True, help='target language entities json')
    parser.add_argument('--target-lang', required=True, help='target language code, e.g. en, de, zh-Hant')
    parser.add_argument('--source-lang', default='zh-Hans')
    parser.add_argument('--min-length-ratio', type=float, default=0.25)
    parser.add_argument('--max-length-ratio', type=float, default=8.0)
    parser.add_argument('--fail-on-warn', action='store_true')
    parser.add_argument('--output', default='')
    args = parser.parse_args()

    source_map = load_entity_map(Path(args.source_entities))
    target_map = load_entity_map(Path(args.translated_entities))

    errors = []
    warnings = []

    source_keys = set(source_map.keys())
    target_keys = set(target_map.keys())

    missing = sorted(source_keys - target_keys)
    extra = sorted(target_keys - source_keys)

    for key in missing:
        errors.append({'key': key, 'type': 'missing_key', 'message': 'Missing key in translated entities'})
    for key in extra:
        warnings.append({'key': key, 'type': 'unexpected_key', 'message': 'Unexpected key in translated entities'})

    cjk_expected_lang_prefixes = ('zh', 'ja', 'ko')

    for key in sorted(source_keys & target_keys):
        source_value = source_map[key] or ''
        target_value = target_map[key] or ''

        if target_value.strip() == '':
            errors.append({'key': key, 'type': 'empty_value', 'message': 'Translated value is empty'})
            continue

        source_ph = extract_placeholders(source_value)
        target_ph = extract_placeholders(target_value)
        if len(source_ph) != len(target_ph) or Counter(source_ph) != Counter(target_ph):
            errors.append({
                'key': key,
                'type': 'placeholder_mismatch',
                'message': 'Placeholder set mismatch between source and target',
                'source_placeholders': source_ph,
                'target_placeholders': target_ph,
            })

        if args.target_lang != args.source_lang and target_value == source_value:
            warnings.append({
                'key': key,
                'type': 'same_as_source',
                'message': 'Target value is identical to source value',
            })

        source_len = normalized_len(source_value)
        target_len = normalized_len(target_value)
        if source_len >= 4 and target_len > 0:
            ratio = target_len / source_len
            if ratio < args.min_length_ratio or ratio > args.max_length_ratio:
                warnings.append({
                    'key': key,
                    'type': 'length_ratio_outlier',
                    'message': f'Length ratio {ratio:.2f} is outside [{args.min_length_ratio}, {args.max_length_ratio}]',
                    'source_length': source_len,
                    'target_length': target_len,
                })

        if (
            args.target_lang.split('-')[0] not in cjk_expected_lang_prefixes
            and any('\u4e00' <= ch <= '\u9fff' for ch in target_value)
        ):
            warnings.append({
                'key': key,
                'type': 'contains_cjk',
                'message': 'Target value contains CJK characters for a non-CJK locale',
            })

    result = {
        'source_lang': args.source_lang,
        'target_lang': args.target_lang,
        'expected_key_count': len(source_keys),
        'translated_key_count': len(target_keys),
        'error_count': len(errors),
        'warning_count': len(warnings),
        'errors': errors,
        'warnings': warnings,
    }

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + '\n', encoding='utf-8')
    else:
        print(rendered)

    if errors:
        sys.exit(2)
    if args.fail_on_warn and warnings:
        sys.exit(3)
    sys.exit(0)


if __name__ == '__main__':
    main()
