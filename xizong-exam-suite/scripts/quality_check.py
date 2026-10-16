#!/usr/bin/env python3
"""Deterministic Markdown checks for generated xizong documents."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


SEVERITIES = {"error", "warning"}


def _is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def _frontmatter_end(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index + 1
    return 0


def _issue(issues: list[dict], line: int, severity: str, code: str, message: str) -> None:
    if severity not in SEVERITIES:
        raise ValueError(f"invalid severity: {severity}")
    issues.append({"line": line, "severity": severity, "code": code, "message": message})


def _math_state(lines: list[str], issues: list[dict], start: int) -> None:
    inline_open = False
    display_open = False
    for line_number, line in enumerate(lines[start:], start=start + 1):
        if line.strip().startswith("```"):
            continue
        index = 0
        while index < len(line):
            if line[index] == "\\":
                index += 2
                continue
            if line.startswith("$$", index):
                display_open = not display_open
                index += 2
                continue
            if line[index] == "$" and not display_open:
                inline_open = not inline_open
            index += 1
    if display_open:
        _issue(issues, len(lines), "error", "unclosed_display_math", "display math block is not closed")
    if inline_open:
        _issue(issues, len(lines), "error", "unclosed_inline_math", "inline math has an unmatched $ delimiter")


def check_markdown(path: str | Path, kind: str = "generic") -> dict:
    source = Path(path)
    if not source.is_file():
        return {"ok": False, "path": str(source), "issues": [{
            "line": 0, "severity": "error", "code": "missing_file", "message": "Markdown file does not exist"
        }]}
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    issues: list[dict] = []
    start = _frontmatter_end(lines)
    in_code = False
    table_width: int | None = None
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            table_width = None
            continue
        if in_code:
            continue
        if any(ord(char) < 32 and char not in "\t" for char in line):
            _issue(issues, line_number, "error", "control_character", "control character found in Markdown")
        if line_number > start and stripped == "---":
            _issue(issues, line_number, "error", "horizontal_rule", "standalone --- is not allowed in generated content")
        if re.search(r"[²³⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻₀₁₂₃₄₅₆₇₈₉]", line):
            _issue(issues, line_number, "warning", "unicode_subscript", "convert Unicode subscripts/superscripts to explicit notation")
        for index, char in enumerate(line):
            if char in "\"'" and ((index and _is_cjk(line[index - 1])) or (index + 1 < len(line) and _is_cjk(line[index + 1]))):
                _issue(issues, line_number, "warning", "straight_quote", "possible ASCII quote adjacent to Chinese text")
                break
        if line.lstrip().startswith("|") and line.rstrip().endswith("|"):
            cells = line.strip().split("|")[1:-1]
            if table_width is None:
                table_width = len(cells)
            elif len(cells) != table_width and not all(set(cell.strip()) <= {"-", ":", " "} for cell in cells):
                _issue(issues, line_number, "error", "table_width", "table row has a different number of cells")
        else:
            table_width = None
        if kind == "questions" and re.search(r"(?:^|\s)(?:答案|解析|出处|依据摘录)\s*[:：]", line):
            _issue(issues, line_number, "error", "answer_leak", "questions document contains answer or evidence text")
    if in_code:
        _issue(issues, len(lines), "error", "unclosed_code_fence", "code fence is not closed")
    _math_state(lines, issues, start)
    errors = [issue for issue in issues if issue["severity"] == "error"]
    return {"ok": not errors, "path": str(source), "issues": issues,
            "summary": {"errors": len(errors), "warnings": len(issues) - len(errors)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Markdown file to check")
    parser.add_argument("--kind", choices=("generic", "questions"), default="generic")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    report = check_markdown(args.input, args.kind)
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if not report["issues"]:
            print(f"OK: {args.input}")
        for issue in report["issues"]:
            print(f"Line {issue['line']}: [{issue['severity']}] {issue['code']} - {issue['message']}")
        summary = report.get("summary", {})
        print(f"Errors: {summary.get('errors', 0)}; warnings: {summary.get('warnings', 0)}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
