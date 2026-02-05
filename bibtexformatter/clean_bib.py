#!/usr/bin/env python3
"""Clean up BibTeX files.

Rules:
- Convert @misc to @article.
- Rename fields: archivePrefix -> journal, eprint -> volume.
- Ensure title values are wrapped in double braces: {{...}}.
- Normalize conference booktitle values for ICML/NeurIPS/ICLR.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Tuple


CONFERENCE_RULES: Dict[str, Dict[str, List[str] | str]] = {
    "ICML": {
        "canonical": "International Conference on Machine Learning (ICML)",
        "patterns": [
            r"\binternational conference on machine learning\b",
            r"\bicml\b",
            r"proceedings of the .* international conference on machine learning",
        ],
        "fuzzy_targets": [
            "international conference on machine learning",
            "icml",
        ],
    },
    "NeurIPS": {
        "canonical": "Advances in Neural Information Processing Systems (NeurIPS)",
        "patterns": [
            r"\bneural information processing systems\b",
            r"\bneurips\b",
            r"\bnips\b",
            r"advances in neural information processing systems",
        ],
        "fuzzy_targets": [
            "neural information processing systems",
            "neurips",
            "nips",
        ],
    },
    "ICLR": {
        "canonical": "International Conference on Learning Representations (ICLR)",
        "patterns": [
            r"\binternational conference on learning representations\b",
            r"\biclr\b",
            r"\bicrl\b",
        ],
        "fuzzy_targets": [
            "international conference on learning representations",
            "iclr",
            "icrl",
        ],
    },
    "COLM": {
        "canonical": "Conference on Language Modeling (COLM)",
        "patterns": [
            r"\bconference on language modeling\b",
            r"\bcolm\b",
        ],
        "fuzzy_targets": [
            "conference on language modeling",
            "colm",
        ],
    },
    "EMNLP": {
        "canonical": "Conference on Empirical Methods in Natural Language Processing (EMNLP)",
        "patterns": [
            r"\bconference on empirical methods in natural language processing\b",
            r"\bemnlp\b",
        ],
        "fuzzy_targets": [
            "conference on empirical methods in natural language processing",
            "emnlp",
        ],
    },
}


@dataclass
class Field:
    name: Optional[str]
    value: str
    raw: Optional[str] = None


@dataclass
class MatchInfo:
    key: str
    field: str
    original_value: str
    normalized_value: str
    rule: str


def split_entries(text: str) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
    i = 0
    n = len(text)
    while i < n:
        at = text.find("@", i)
        if at == -1:
            entries.append(("text", text[i:]))
            break
        if at > i:
            entries.append(("text", text[i:at]))
        brace = text.find("{", at)
        if brace == -1:
            entries.append(("text", text[at:]))
            break
        level = 0
        j = brace
        while j < n:
            ch = text[j]
            if ch == "{":
                level += 1
            elif ch == "}":
                level -= 1
                if level == 0:
                    j += 1
                    break
            j += 1
        entries.append(("entry", text[at:j]))
        i = j
    return entries


def split_fields(s: str) -> List[str]:
    fields: List[str] = []
    buf: List[str] = []
    level = 0
    in_quotes = False
    escape = False

    for ch in s:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == "\\":
            buf.append(ch)
            escape = True
            continue
        if ch == '"':
            in_quotes = not in_quotes
            buf.append(ch)
            continue
        if not in_quotes:
            if ch == "{":
                level += 1
            elif ch == "}":
                level = max(0, level - 1)
            elif ch == "," and level == 0:
                part = "".join(buf).strip()
                if part:
                    fields.append(part)
                buf = []
                continue
        buf.append(ch)

    tail = "".join(buf).strip()
    if tail:
        fields.append(tail)
    return fields


def normalize_title_value(value: str) -> str:
    v = value.strip()
    if v.startswith("{{") and v.endswith("}}"):
        return v
    if v.startswith("{") and v.endswith("}"):
        v = v[1:-1].strip()
    elif v.startswith('"') and v.endswith('"'):
        v = v[1:-1].strip()
    return "{{" + v + "}}"


def normalize_non_title_value(value: str) -> str:
    v = value.strip()
    if v.startswith("{") and v.endswith("}"):
        return v
    if v.startswith('"') and v.endswith('"'):
        v = v[1:-1].strip()
    return "{" + v + "}"


def unwrap_value(value: str, max_depth: int = 2) -> str:
    v = value.strip()
    for _ in range(max_depth):
        if (v.startswith("{") and v.endswith("}")) or (v.startswith('"') and v.endswith('"')):
            v = v[1:-1].strip()
        else:
            break
    return v


def normalize_for_match(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def match_conference(value: str) -> Tuple[Optional[str], Optional[str]]:
    raw = unwrap_value(value)
    raw_lower = raw.lower()
    raw_norm = normalize_for_match(raw)
    for rule_name, rule in CONFERENCE_RULES.items():
        for pattern in rule["patterns"]:  # type: ignore[index]
            if re.search(pattern, raw_lower, flags=re.IGNORECASE):
                return rule["canonical"], rule_name  # type: ignore[index]

    for rule_name, rule in CONFERENCE_RULES.items():
        for target in rule["fuzzy_targets"]:  # type: ignore[index]
            if raw_norm == target or target in raw_norm:
                return rule["canonical"], rule_name  # type: ignore[index]
    return None, None


def parse_entry(entry_text: str) -> Tuple[str, str, List[Field]]:
    at = entry_text.find("@")
    brace = entry_text.find("{", at)
    entry_type = entry_text[at + 1 : brace].strip()
    body = entry_text[brace + 1 :].rstrip()
    if body.endswith("}"):
        body = body[:-1]

    if "," not in body:
        return entry_type, body.strip(), []

    key, rest = body.split(",", 1)
    key = key.strip()
    fields_raw = split_fields(rest)
    fields: List[Field] = []
    for part in fields_raw:
        if "=" not in part:
            fields.append(Field(name=None, value="", raw=part))
            continue
        name, value = part.split("=", 1)
        fields.append(Field(name=name.strip(), value=value.strip()))
    return entry_type, key, fields


def format_entry(entry_type: str, key: str, fields: List[Field]) -> str:
    lines = [f"@{entry_type}{{{key},"]
    for field in fields:
        if field.name is None and field.raw is not None:
            lines.append(f"  {field.raw},")
            continue
        name = field.name or ""
        value = field.value
        lines.append(f"  {name} = {value},")
    if len(lines) > 1:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


def transform_entry(entry_text: str) -> Tuple[str, List[MatchInfo]]:
    entry_type, key, fields = parse_entry(entry_text)
    if entry_type.lower() == "misc":
        entry_type = "article"

    matches: List[MatchInfo] = []
    for field in fields:
        if field.name is None:
            continue
        lname = field.name.lower()
        if lname == "archiveprefix":
            field.name = "journal"
        elif lname == "eprint":
            field.name = "volume"
        elif lname == "title":
            field.value = normalize_title_value(field.value)
        elif lname == "booktitle":
            canonical, rule = match_conference(field.value)
            if canonical and rule:
                original_value = field.value
                field.value = "{" + canonical + "}"
                matches.append(
                    MatchInfo(
                        key=key,
                        field="booktitle",
                        original_value=original_value,
                        normalized_value=field.value,
                        rule=rule,
                    )
                )
            else:
                field.value = normalize_non_title_value(field.value)
        else:
            field.value = normalize_non_title_value(field.value)

    return format_entry(entry_type, key, fields), matches


def clean_bibtex(text: str) -> Tuple[str, List[str], List[MatchInfo]]:
    parts = split_entries(text)
    out: List[str] = []
    matched_entries: List[str] = []
    match_infos: List[MatchInfo] = []
    for kind, payload in parts:
        if kind == "text":
            out.append(payload)
        else:
            entry_text, matches = transform_entry(payload)
            out.append(entry_text)
            if matches:
                matched_entries.append(entry_text)
                match_infos.extend(matches)
    return "".join(out), matched_entries, match_infos


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and rewrite BibTeX files.")
    parser.add_argument("input", help="Input .bib file path")
    parser.add_argument("output", help="Output .bib file path")
    parser.add_argument(
        "--print-matched",
        action="store_true",
        help="Print entries whose booktitle matches a venue rule",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    cleaned, matched_entries, _ = clean_bibtex(text)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(cleaned)

    if args.print_matched:
        for entry in matched_entries:
            print(entry)
            print()


if __name__ == "__main__":
    main()
