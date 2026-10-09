#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path


def analyze_file(filepath: Path, name: str):
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    result = {
        "name": name,
        "total_lines": len(lines),
        "total_chars": len(content),
        "has_yaml_header": content.startswith("---"),
        "has_jiaocai_yuanwen": "（教材原文）" in content,
        "has_define": "【定义】" in content,
        "has_fenlei": "临床分类" in content,
        "has_sugan": "干湿冷暖" in content,
        "has_zhuji": "考频" in content or "exam_frequency" in content,
        "has_shenhe": "审核清单" in content,
        "has_xunlian": "训练" in content or "实战" in content,
        "source_markers": content.count("（教材原文）"),
    }
    return result


def build_report(left, right):
    output = []
    output.append("=" * 60)
    output.append("FILE COMPARISON ANALYSIS")
    output.append("=" * 60)

    output.append("\n[BASIC INFO]")
    output.append(f'{left["name"]}: {left["total_lines"]} lines, {left["total_chars"]} chars')
    output.append(f'{right["name"]}: {right["total_lines"]} lines, {right["total_chars"]} chars')

    output.append("\n[FEATURE COMPARISON]")
    features = [
        ("YAML front matter", "has_yaml_header"),
        ("Jiaocai yuanwen tag", "has_jiaocai_yuanwen"),
        ("Define section", "has_define"),
        ("Classification", "has_fenlei"),
        ("Gan-shi-leng-nuan", "has_sugan"),
        ("Exam frequency", "has_zhuji"),
        ("Review checklist", "has_shenhe"),
        ("Training questions", "has_xunlian"),
    ]

    for label, key in features:
        left_value = "YES" if left[key] else "NO"
        right_value = "YES" if right[key] else "NO"
        output.append(f"{label}: {left['name']}[{left_value}] vs {right['name']}[{right_value}]")

    output.append("\n[JIAOCAI YUANWEN COUNT]")
    output.append(f"{left['name']}: {left['source_markers']} times")
    output.append(f"{right['name']}: {right['source_markers']} times")
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="比较两个工作流 Markdown 文件的结构特征。")
    parser.add_argument("file1", help="第一个文件路径。")
    parser.add_argument("file2", help="第二个文件路径。")
    parser.add_argument("--name1", default="FILE1", help="第一个文件的显示名称。")
    parser.add_argument("--name2", default="FILE2", help="第二个文件的显示名称。")
    parser.add_argument(
        "--output",
        default="output/compare_result.txt",
        help="输出报告路径，默认写入 output/compare_result.txt。",
    )
    args = parser.parse_args()

    file1 = Path(args.file1).resolve()
    file2 = Path(args.file2).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(
        analyze_file(file1, args.name1),
        analyze_file(file2, args.name2),
    )
    output_path.write_text(report, encoding="utf-8")
    print(f"Analysis saved to {output_path}")


if __name__ == "__main__":
    main()
