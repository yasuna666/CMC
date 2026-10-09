#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从真题 Markdown 中提取循环系统相关的知识链。
"""

import argparse
import re
from pathlib import Path


circulatory_keywords = [
    "心衰",
    "心力衰竭",
    "心律失常",
    "高血压",
    "冠心病",
    "心肌",
    "心脏",
    "房颤",
    "室颤",
    "室早",
    "房早",
    "传导阻滞",
    "瓣膜",
    "心包",
    "扩张型心肌病",
    "肥厚型心肌病",
    "限制型心肌病",
    "心肌炎",
    "动脉粥样硬化",
    "心绞痛",
    "心肌梗死",
    "心脏骤停",
    "猝死",
    "呋塞米",
    "利尿剂",
    "洋地黄",
    "地高辛",
    "ACEI",
    "ARB",
    "β受体阻滞剂",
]


def extract_circulatory_questions(exam_file: Path):
    content = exam_file.read_text(encoding="utf-8", errors="ignore")
    question_blocks = re.findall(r"(### 第(\d+)题.*?)(?=### 第\d+题|$)", content, re.DOTALL)
    circulatory_questions = []

    for block, question_num in question_blocks:
        if not any(keyword in block for keyword in circulatory_keywords):
            continue

        stem_match = re.search(r"\*\*题目：\*\*\s*(.*?)(?=\n[A-D]\.|(?:\n\*\*解析))", block, re.DOTALL)
        analysis_match = re.search(r"\*\*解析：\*\*\s*(.*?)(?=\n### |\Z)", block, re.DOTALL)

        circulatory_questions.append(
            {
                "num": question_num,
                "stem": stem_match.group(1).strip() if stem_match else "",
                "analysis": analysis_match.group(1).strip() if analysis_match else "",
            }
        )

    return circulatory_questions


def analyze_knowledge_chain(question):
    stem = question["stem"]
    analysis = question["analysis"]
    text = f"{stem} {analysis}"

    chain = {
        "basic_disease": [],
        "drug": [],
        "complication": [],
        "manifestation": [],
    }

    if "扩张型心肌病" in text or "扩心病" in text:
        chain["basic_disease"].append("扩张型心肌病")
    if "高血压" in text:
        chain["basic_disease"].append("高血压")
    if "冠心病" in text:
        chain["basic_disease"].append("冠心病")
    if "心衰" in text or "心力衰竭" in text:
        chain["basic_disease"].append("心力衰竭")

    if "呋塞米" in text:
        chain["drug"].append(("呋塞米", "排钾利尿剂"))
    if "地高辛" in text or "洋地黄" in text:
        chain["drug"].append(("地高辛", "正性肌力药"))

    if "低钾" in text or "低钾血症" in text:
        chain["complication"].append("低钾血症")
    if "室早" in text or "室性早搏" in text:
        chain["complication"].append("室性早搏")
    if "意识" in text or "晕厥" in text:
        chain["manifestation"].append("意识障碍")

    return chain


def main():
    parser = argparse.ArgumentParser(description="提取真题中的循环系统知识链。")
    parser.add_argument(
        "exam_file",
        nargs="?",
        default="真题/合并/2025年考研西医综合_真题+解析.md",
        help="真题 Markdown 文件路径。",
    )
    parser.add_argument(
        "--output",
        default="output/循环系统真题知识链分析.md",
        help="输出文件路径。",
    )
    parser.add_argument("--limit", type=int, default=20, help="最多输出多少道题。")
    args = parser.parse_args()

    exam_file = Path(args.exam_file).resolve()
    output_file = Path(args.output).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("正在提取循环系统相关真题...")
    questions = extract_circulatory_questions(exam_file)
    print(f"找到 {len(questions)} 道相关题目")

    with output_file.open("w", encoding="utf-8") as handle:
        handle.write("# 循环系统真题知识链分析\n\n")

        for question in questions[: args.limit]:
            handle.write(f'## 第{question["num"]}题\n\n')
            handle.write(f'**题干：**\n{question["stem"]}\n\n')

            chain = analyze_knowledge_chain(question)
            handle.write("**知识链拆解：**\n")
            if chain["basic_disease"]:
                handle.write(f'- 基础疾病：{" → ".join(chain["basic_disease"])}\n')
            if chain["drug"]:
                handle.write(f'- 用药：{" → ".join(item[0] for item in chain["drug"])}\n')
            if chain["complication"]:
                handle.write(f'- 并发症：{" → ".join(chain["complication"])}\n')
            if chain["manifestation"]:
                handle.write(f'- 临床表现：{" → ".join(chain["manifestation"])}\n')

            preview = question["analysis"][:500]
            if preview:
                handle.write(f"\n**解析：**\n{preview}...\n\n")
            handle.write("---\n\n")

    print(f"分析完成，结果保存在：{output_file}")


if __name__ == "__main__":
    main()
