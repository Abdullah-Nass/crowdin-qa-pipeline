import os
import sys
import re
import json
  
import polib
from lxml import etree


SAME_IN_AR = ["OK", "PDF", "SMS", "PIN", "ID"]


def get_ns_and_version(tree):
    root = tree.getroot()
    version = root.attrib.get("version", "1.2")
    ns_uri = (
        root.tag.split("}")[0].lstrip("{")
        if root.tag.startswith("{")
        else "urn:oasis:names:tc:xliff:document:1.2"
    )
    return version, {"xliff": ns_uri}


def extract_placeholders(text):
    if not text:
        return []
    pattern = r"\{[\w\d_]+\}|%\([\w]+\)[sdif]|%[sdif]"
    return sorted(re.findall(pattern, text))


def check_identical(source, target):
    return source == target and source not in SAME_IN_AR


def check_placeholders(source, target):
    src_ph = extract_placeholders(source)
    tgt_ph = extract_placeholders(target)
    if src_ph == tgt_ph:
        return None
    missing = set(src_ph) - set(tgt_ph)
    extra = set(tgt_ph) - set(src_ph)
    parts = []
    if missing:
        parts.append(f"missing: {', '.join(missing)}")
    if extra:
        parts.append(f"extra: {', '.join(extra)}")
    return " | ".join(parts)


def run_po(filepath):
    po = polib.pofile(filepath)
    translated = po.translated_entries()
    untranslated = po.untranslated_entries()
    fuzzy = po.fuzzy_entries()

    lines = []
    issues = 0

    lines.append(f"  Total     : {len(po)}")
    lines.append(f"  Translated: {len(translated)}")
    lines.append(f"  Untranslated: {len(untranslated)}")
    lines.append(f"  Fuzzy     : {len(fuzzy)}")

    if untranslated:
        issues += len(untranslated)
        lines.append(f"\n  Untranslated strings ({len(untranslated)}):")
        for e in untranslated:
            lines.append(f'    - "{e.msgid}"')

    ph_issues = []
    idc_issues = []
    for entry in translated:
        ph = check_placeholders(entry.msgid, entry.msgstr)
        if ph:
            ph_issues.append((entry.msgid, entry.msgstr, ph))
        if check_identical(entry.msgid, entry.msgstr):
            idc_issues.append(entry.msgid)

    if ph_issues:
        issues += len(ph_issues)
        lines.append(f"\n  Placeholder mismatches ({len(ph_issues)}):")
        for src, tgt, detail in ph_issues:
            lines.append(f'    Source : "{src}"')
            lines.append(f'    Target : "{tgt}"')
            lines.append(f'    → {detail}')
    else:
        lines.append("\n  No placeholder mismatches")

    if idc_issues:
        issues += len(idc_issues)
        lines.append(f"\n  Identical source/target ({len(idc_issues)}):")
        for src in idc_issues:
            lines.append(f'    - "{src}"')
    else:
        lines.append("  No identical source/target")

    return issues, lines


def extract_units_v2(root, ns):
    units = []
    for unit in root.findall(".//xliff:unit", ns):
        unit_id = unit.attrib.get("id", "unknown")
        for segment in unit.findall(".//xliff:segment", ns):
            source_el = segment.find("xliff:source", ns)
            target_el = segment.find("xliff:target", ns)
            source = "".join(source_el.itertext()) if source_el is not None else ""
            target = "".join(target_el.itertext()) if target_el is not None else ""
            units.append({"id": unit_id, "source": source, "target": target})
    return units


def run_xliff(filepath):
    tree = etree.parse(filepath)
    root = tree.getroot()
    version, ns = get_ns_and_version(tree)

    if version == "2.0":
        raw_units = extract_units_v2(root, ns)
        pairs = [(u["source"], u["target"]) for u in raw_units]
    else:
        pairs = []
        for unit in root.findall(".//xliff:trans-unit", ns):
            src_el = unit.find("xliff:source", ns)
            tgt_el = unit.find("xliff:target", ns)
            src = (src_el.text or "") if src_el is not None else ""
            tgt = (tgt_el.text or "") if tgt_el is not None else ""
            pairs.append((src, tgt))

    total = len(pairs)
    untranslated = [(s, t) for s, t in pairs if not t.strip()]
    translated = [(s, t) for s, t in pairs if t.strip()]
    pct = round(len(translated) / total * 100, 1) if total else 0

    lines = []
    issues = 0

    lines.append(f"  Total     : {total}")
    lines.append(f"  Translated: {len(translated)}  ({pct}%)")
    lines.append(f"  Untranslated: {len(untranslated)}")

    if untranslated:
        issues += len(untranslated)
        lines.append(f"\n  Untranslated strings ({len(untranslated)}):")
        for src, _ in untranslated:
            lines.append(f'    - "{src}"')

    ph_issues = []
    idc_issues = []
    for src, tgt in translated:
        ph = check_placeholders(src, tgt)
        if ph:
            ph_issues.append((src, tgt, ph))
        if check_identical(src, tgt):
            idc_issues.append(src)

    if ph_issues:
        issues += len(ph_issues)
        lines.append(f"\n  Placeholder mismatches ({len(ph_issues)}):")
        for src, tgt, detail in ph_issues:
            lines.append(f'    Source : "{src}"')
            lines.append(f'    Target : "{tgt}"')
            lines.append(f'    → {detail}')
    else:
        lines.append("\n  No placeholder mismatches")

    if idc_issues:
        issues += len(idc_issues)
        lines.append(f"\n  Identical source/target ({len(idc_issues)}):")
        for src in idc_issues:
            lines.append(f'    - "{src}"')
    else:
        lines.append("  No identical source/target")

    return issues, lines

def run_json(filepath):
    with open(filepath, encoding="utf-8") as f:
        target_data = json.load(f)
 
    repo_root = filepath
    for _ in range(4):  
        repo_root = os.path.dirname(repo_root)
        source_filename = os.path.basename(filepath) 
        source_path = os.path.join(repo_root, "source", source_filename)
        if os.path.exists(source_path):
            break
    else:
        return 1, ["  ✗ Could not locate source/en.json — skipping placeholder checks"]
 
    with open(source_path, encoding="utf-8") as f:
        source_data = json.load(f)
 
    lines = []
    issues = 0
 
    total = len(source_data)
    untranslated = [k for k, v in source_data.items() if not target_data.get(k, "").strip()]
    translated = [(k, source_data[k], target_data[k]) for k in source_data if target_data.get(k, "").strip()]
 
    pct = round(len(translated) / total * 100, 1) if total else 0
    lines.append(f"  Total     : {total}")
    lines.append(f"  Translated: {len(translated)}  ({pct}%)")
    lines.append(f"  Untranslated: {len(untranslated)}")
 
    if untranslated:
        issues += len(untranslated)
        lines.append(f"\n  ✗ Untranslated strings ({len(untranslated)}):")
        for k in untranslated:
            lines.append(f'    - "{k}": "{source_data[k]}"')
 
    ph_issues = []
    idc_issues = []
    for key, src, tgt in translated:
        ph = check_placeholders(src, tgt)
        if ph:
            ph_issues.append((src, tgt, ph))
        if check_identical(src, tgt):
            idc_issues.append(src)
 
    if ph_issues:
        issues += len(ph_issues)
        lines.append(f"\n  ✗ Placeholder mismatches ({len(ph_issues)}):")
        for src, tgt, detail in ph_issues:
            lines.append(f'    Source : "{src}"')
            lines.append(f'    Target : "{tgt}"')
            lines.append(f'    {detail}')
    else:
        lines.append("\n  ✓ No placeholder mismatches")
 
    if idc_issues:
        issues += len(idc_issues)
        lines.append(f"\n  ✗ Identical source/target ({len(idc_issues)}):")
        for src in idc_issues:
            lines.append(f'    - "{src}"')
    else:
        lines.append("  ✓ No identical source/target")
 
    return issues, lines
def collect_files(path):
    supported = (".po", ".xliff", ".xlf", ".json")
    if os.path.isfile(path):
        return [path] if path.endswith(supported) else []
    found = []
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith(supported):
                found.append(os.path.join(root, f))
    return sorted(found)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_qa.py <file_or_directory>")
        sys.exit(1)

    target = sys.argv[1]
    files = collect_files(target)

    if not files:
        print(f"There is no translation yet")
        sys.exit(0)

    total_issues = 0
    separator = "=" * 50

    for filepath in files:
        ext = os.path.splitext(filepath)[1].lower()
        label = "PO" if ext == ".po" else "JSON" if ext == ".json" else "XLIFF"

        print(f"\n{separator}")
        print(f"  {label}: {filepath}")
        print(separator)

        try:
            if ext == ".po":
                issues, lines = run_po(filepath)
            elif ext == ".json":
                issues, lines = run_json(filepath)
            else:
                issues, lines = run_xliff(filepath)

            for line in lines:
                print(line)

            total_issues += issues

        except Exception as e:
            print(f"  ERROR parsing file: {e}")
            total_issues += 1

    print(f"\n{separator}")
    print(f"  FILES CHECKED : {len(files)}")
    print(f"  TOTAL ISSUES  : {total_issues}")

    if total_issues > 0:
        print("  RESULT        : FAILED")
        print(separator)
        sys.exit(1)
    else:
        print("  RESULT        : PASSED")
        print(separator)
        sys.exit(0)


if __name__ == "__main__":
    main()