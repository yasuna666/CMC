#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真题考频分析器。
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path


CHAPTER_KEYWORDS = {
    "绪论": ["内环境", "稳态", "反馈", "神经调节", "体液调节", "细胞外液"],
    "细胞的基本功能": ["细胞膜", "物质转运", "扩散", "静息电位", "动作电位", "肌细胞", "信号转导"],
    "血液": ["血液", "红细胞", "白细胞", "血小板", "凝血", "血型", "血沉"],
    "血液循环": ["心脏", "心动周期", "心输出量", "血压", "心血管", "心肌", "微循环", "冠脉"],
    "呼吸": ["呼吸", "肺通气", "肺换气", "氧解离", "肺泡", "气道", "呼吸运动"],
    "消化和吸收": ["消化", "吸收", "胃肠", "胃液", "胰液", "胆汁", "排便"],
    "能量代谢和体温": ["能量代谢", "体温", "基础代谢", "产热", "散热"],
    "尿的生成和排出": ["肾脏", "肾小球", "肾小管", "滤过", "排尿", "尿液"],
    "神经系统的功能": ["神经", "突触", "递质", "反射", "中枢", "感觉", "运动", "脑"],
    "内分泌": ["激素", "内分泌", "甲状腺", "肾上腺", "胰岛素", "垂体"],
    "生殖": ["生殖", "睾丸", "卵巢", "月经", "妊娠"],
}


def extract_chapter_from_question(question_text):
    max_score = 0
    best_chapter = "其他"

    for chapter, keywords in CHAPTER_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in question_text)
        if score > max_score:
            max_score = score
            best_chapter = chapter

    return best_chapter


def find_exam_files(project_root: Path):
    candidates = [
        project_root / "真题" / "merged_with_pdf_answers",
        project_root / "真题" / "合并",
        project_root / "真题",
    ]

    for candidate in candidates:
        if candidate.exists():
            return sorted(candidate.rglob("*.md"))
    return []


def extract_questions(content: str):
    questions = re.findall(r"## 第 \d+ 题\s+### 题目\s+(.+?)(?=### 答案|$)", content, re.DOTALL)
    if questions:
        return questions

    return re.findall(r"\*\*题目：\*\*\s*(.+?)(?=\n[A-D]\.|\n\*\*解析)", content, re.DOTALL)


def analyze_exams(project_root: Path):
    md_files = find_exam_files(project_root)
    if not md_files:
        print(f"未找到真题 Markdown 文件: {project_root}")
        return None

    chapter_stats = defaultdict(lambda: {"count": 0, "years": []})
    total_questions = 0

    print(f"发现 {len(md_files)} 个真题 Markdown 文件\n")

    for file_path in md_files:
        year_match = re.search(r"(20\d{2})", file_path.name)
        year = year_match.group(1) if year_match else "未知年份"

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            print(f"读取 {file_path.name} 出错: {exc}")
            continue

        for question in extract_questions(content):
            total_questions += 1
            chapter = extract_chapter_from_question(question)
            chapter_stats[chapter]["count"] += 1
            chapter_stats[chapter]["years"].append(year)

    print("=" * 60)
    print("【各章节考频统计】")
    print("=" * 60)

    sorted_chapters = sorted(chapter_stats.items(), key=lambda item: item[1]["count"], reverse=True)
    for index, (chapter, data) in enumerate(sorted_chapters, 1):
        count = data["count"]
        years = sorted(set(data["years"]))
        percentage = count / total_questions * 100 if total_questions else 0
        suffix = "..." if len(years) > 5 else ""
        print(
            f"{index:2d}. {chapter:15s} : {count:3d}题 "
            f"({percentage:5.1f}%) - 出现年份: {', '.join(years[:5])}{suffix}"
        )

    print("\n" + "=" * 60)
    print(f"【总计】共分析 {len(md_files)} 个文件，{total_questions} 道题目")
    print("=" * 60)
    return chapter_stats


def main():
    parser = argparse.ArgumentParser(description="分析真题 Markdown 的考频分布。")
    parser.add_argument(
        "--project-root",
        default=".",
        help="项目根目录，默认是当前目录。",
    )
    args = parser.parse_args()

    analyze_exams(Path(args.project_root).resolve())


if __name__ == "__main__":
    main()
