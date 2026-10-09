#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
from pathlib import Path


HEADING_RE = re.compile(r"^(?:#{1,6}\s+.*|第[一二三四五六七八九十百零〇\d]+章.*)$")


def find_textbook_files(project_root: Path, textbook_dir: str, subject: str):
    textbook_root = project_root / textbook_dir
    if not textbook_root.exists():
        return []

    return sorted(
        path / "full.md"
        for path in textbook_root.iterdir()
        if path.is_dir() and subject in path.name and (path / "full.md").exists()
    )


def extract_section(content: str, keyword: str):
    lines = content.splitlines()
    hit_index = next((index for index, line in enumerate(lines) if keyword in line), None)
    if hit_index is None:
        return None

    start = hit_index
    while start > 0 and not HEADING_RE.match(lines[start].strip()):
        start -= 1

    end = hit_index + 1
    while end < len(lines) and not HEADING_RE.match(lines[end].strip()):
        end += 1

    return "\n".join(lines[start:end]).strip()


def main():
    parser = argparse.ArgumentParser(description="从教材 full.md 中提取指定疾病章节。")
    parser.add_argument(
        "--project-root",
        default=".",
        help="项目根目录，默认是当前目录。",
    )
    parser.add_argument(
        "--textbook-dir",
        default="教材",
        help="教材目录名，默认是 教材。",
    )
    parser.add_argument(
        "--subject",
        default="内科学",
        help="要搜索的教材学科关键字，默认是 内科学。",
    )
    parser.add_argument(
        "--keyword",
        required=True,
        help="要提取的章节关键词，例如 结核性腹膜炎。",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出文件路径，默认写入 output/<关键词>_教材原文.txt。",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    textbook_files = find_textbook_files(project_root, args.textbook_dir, args.subject)

    print("=" * 60)
    print(f"正在读取 {args.subject} 教材...")
    print("=" * 60)
    print(f"找到 {len(textbook_files)} 个 full.md 文件")

    for full_md in textbook_files:
        try:
            content = full_md.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            print(f"读取失败: {full_md} ({exc})")
            continue

        section = extract_section(content, args.keyword)
        if not section:
            continue

        output_path = Path(args.output).resolve() if args.output else (
            project_root / "output" / f"{args.keyword}_教材原文.txt"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(section, encoding="utf-8")

        print(f"\n✓ 已提取: {args.keyword}")
        print(f"来源文件: {full_md}")
        print(f"输出文件: {output_path}")
        print(f"章节长度: {len(section)} 字符")
        print("\n预览（前 500 字）：")
        print(section[:500])
        return

    print(f"\n✗ 未在 {args.subject} 教材中找到关键词: {args.keyword}")


if __name__ == "__main__":
    main()
