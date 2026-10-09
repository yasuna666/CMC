#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2025年真题答案提取 - 最终融合版 (V4)
结合V2的关键词匹配 + V3的理解型分析
目标是最大化提取率，同时保证准确性
"""

import json
import re
import argparse
from pathlib import Path


def extract_answer_final(q_num, question_text, options, analysis_text):
    """
    融合多种方法提取答案
    优先级：明确标记 > 逻辑推理 > 理解分析
    """
    
    # ========== 第一层：最明确的标记 ==========
    
    # 1. 找 "(X对)" 或 "（X对）" - 最可靠的标记
    match = re.search(r'[（(]([A-D])对[)）]', analysis_text)
    if match:
        return {
            'answer': match.group(1),
            'method': 'explicit_right_mark',
            'confidence': 'high'
        }
    
    # 2. 找 "故答 X" / "答案为 X" / "应选 X"
    patterns = [
        r'故答\s*[:：]?\s*([A-D])',
        r'故答案为\s*([A-D])',
        r'答案为\s*([A-D])',
        r'答案是\s*([A-D])',
        r'应选\s*([A-D])',
        r'选\s*([A-D])\s*正确',
    ]
    for pattern in patterns:
        match = re.search(pattern, analysis_text)
        if match:
            return {
                'answer': match.group(1),
                'method': 'answer_indicator',
                'confidence': 'high'
            }
    
    # ========== 第二层：排除法 ==========
    
    # 3. 通过 "(X错)" 排除
    wrong_matches = re.findall(r'[（(]([A-D])错[)）]', analysis_text)
    if wrong_matches and len(wrong_matches) >= 2:
        all_options = ['A', 'B', 'C', 'D']
        remaining = [opt for opt in all_options if opt not in wrong_matches]
        if len(remaining) == 1:
            return {
                'answer': remaining[0],
                'method': 'exclusion_by_wrong_mark',
                'confidence': 'high'
            }
    
    # ========== 第三层：语义理解 ==========
    
    # 4. 分析题目类型并采取对应策略
    q_type = classify_question_type(question_text)
    
    if '不属于' in question_text or '不属于' in question_text:
        # 分类排除型
        result = analyze_exclusion_type(options, analysis_text)
        if result:
            return result
    
    if '正确' in question_text:
        # 正确性判断型
        result = analyze_correctness_type(options, analysis_text)
        if result:
            return result
    
    # 5. 通用语义匹配
    result = analyze_by_semantic_matching(options, analysis_text)
    if result and result['confidence'] in ['high', 'medium']:
        return result
    
    # ========== 无法判断 ==========
    return {
        'answer': None,
        'method': 'unknown',
        'confidence': 'none'
    }


def classify_question_type(question_text):
    """分类题目类型"""
    if '不属于' in question_text:
        return 'exclusion'
    elif '属于' in question_text:
        return 'inclusion'
    elif '正确' in question_text:
        return 'correctness'
    elif '是' in question_text:
        return 'identification'
    else:
        return 'general'


def analyze_exclusion_type(options, analysis_text):
    """分析"不属于"类型题目"""
    # 找"不属于"、"不是"等否定表述后面的内容
    analysis_lower = analysis_text.lower()
    
    for opt, text in options.items():
        text_clean = text.strip().lower()
        
        # 如果这个选项出现在"不属于"、"不是"等表述附近
        if text_clean in analysis_lower:
            idx = analysis_lower.find(text_clean)
            context = analysis_lower[max(0, idx-30):min(len(analysis_lower), idx+len(text_clean)+30)]
            
            # 如果被明确说"不属于"或"不是"
            if any(phrase in context for phrase in ['不属于', '不是', '非', '除外']):
                # 这道题的答案是"不属于"的那个
                return {
                    'answer': opt,
                    'method': 'exclusion_analysis',
                    'confidence': 'high'
                }
    
    return None


def analyze_correctness_type(options, analysis_text):
    """分析"正确的是"类型题目"""
    option_status = {}
    
    for opt in ['A', 'B', 'C', 'D']:
        if opt not in options:
            continue
        
        opt_text = options[opt].lower()
        
        # 找"(X错)"或"(X对)"
        if re.search(f'[（(]{opt}错[)）]', analysis_text):
            option_status[opt] = 'wrong'
        elif re.search(f'[（(]{opt}对[)）]', analysis_text):
            option_status[opt] = 'right'
        else:
            # 检查选项内容是否被否定
            if opt_text in analysis_text.lower():
                idx = analysis_text.lower().find(opt_text)
                context = analysis_text[max(0, idx-20):min(len(analysis_text), idx+len(opt_text)+20)]
                
                if any(word in context for word in ['错', '不对', '不正确', '不属于', '不是']):
                    option_status[opt] = 'wrong'
                elif any(word in context for word in ['对', '正确', '属于', '是']):
                    option_status[opt] = 'right'
                else:
                    option_status[opt] = 'unknown'
            else:
                option_status[opt] = 'unknown'
    
    # 找正确的选项
    right_opts = [opt for opt, status in option_status.items() if status == 'right']
    if len(right_opts) == 1:
        return {
            'answer': right_opts[0],
            'method': 'correctness_analysis',
            'confidence': 'high'
        }
    
    # 用排除法
    wrong_opts = [opt for opt, status in option_status.items() if status == 'wrong']
    if len(wrong_opts) == 3:
        all_opts = ['A', 'B', 'C', 'D']
        remaining = [opt for opt in all_opts if opt not in wrong_opts]
        if remaining:
            return {
                'answer': remaining[0],
                'method': 'exclusion_3_wrong',
                'confidence': 'medium'
            }
    
    return None


def analyze_by_semantic_matching(options, analysis_text):
    """通过语义匹配分析"""
    scores = {}
    
    for opt, text in options.items():
        text_clean = text.strip().lower()
        score = 0
        
        # 选项内容是否出现在解析中
        if text_clean in analysis_text.lower():
            idx = analysis_text.lower().find(text_clean)
            context_start = max(0, idx - 40)
            context_end = min(len(analysis_text), idx + len(text_clean) + 40)
            context = analysis_text[context_start:context_end]
            context_lower = context.lower()
            
            # 检查肯定/否定词
            positive_words = ['正确', '对', '是', '属于', '为', '肯定的']
            negative_words = ['错', '不对', '不正确', '不属于', '不是', '非', '否定的']
            
            pos_count = sum(1 for w in positive_words if w in context_lower)
            neg_count = sum(1 for w in negative_words if w in context_lower)
            
            if neg_count > 0:
                score -= neg_count * 5  # 被否定的选项
            elif pos_count > 0:
                score += pos_count * 5  # 被肯定的选项
            else:
                score += 1  # 中性提及
        
        scores[opt] = score
    
    # 找最高分
    if scores:
        best_opt = max(scores.items(), key=lambda x: x[1])
        if best_opt[1] > 0:
            return {
                'answer': best_opt[0],
                'method': 'semantic_matching',
                'confidence': 'medium' if best_opt[1] < 10 else 'high'
            }
    
    return None


def parse_exam(input_file):
    """解析真题文件"""
    input_path = Path(input_file).resolve()
    content = input_path.read_text(encoding='utf-8', errors='ignore')
    
    # 提取所有题目块
    pattern = r'(### 第(\d+)题\s+.*?)(?=### 第|$)'
    questions = re.findall(pattern, content, re.DOTALL)
    
    results = []
    
    for q_content, q_num in questions:
        # 提取题目主干
        question_match = re.search(r'\*\*题目：\*\*\s+(.*?)(?=A\.|\*\*解析)', q_content, re.DOTALL)
        question_text = question_match.group(1).strip() if question_match else ""
        
        # 提取选项
        options = {}
        option_pattern = r'([A-D])\.\s*(.+?)(?=[A-D]\.|\*\*解析|\Z)'
        option_matches = re.findall(option_pattern, q_content, re.DOTALL)
        for opt, text in option_matches:
            options[opt] = text.strip()
        
        # 提取解析
        analysis_match = re.search(r'\*\*解析：\*\*\s+(.*?)(?=### |$)', q_content, re.DOTALL)
        analysis_text = analysis_match.group(1).strip() if analysis_match else ""
        
        # 提取答案
        result = extract_answer_final(q_num, question_text, options, analysis_text)
        
        results.append({
            'num': int(q_num),
            'question': question_text[:80] + "..." if len(question_text) > 80 else question_text,
            'options': options,
            'answer': result['answer'],
            'method': result['method'],
            'confidence': result['confidence']
        })
    
    return results


def generate_final_report(results):
    """生成最终报告"""
    total = len(results)
    success = sum(1 for r in results if r['answer'] is not None)
    success_rate = success / total * 100 if total else 0
    unknown_rate = (total - success) / total * 100 if total else 0
    
    # 按方法统计
    method_stats = {}
    for r in results:
        m = r['method']
        method_stats[m] = method_stats.get(m, 0) + 1
    
    # 按置信度统计
    conf_stats = {
        'high': sum(1 for r in results if r['confidence'] == 'high'),
        'medium': sum(1 for r in results if r['confidence'] == 'medium'),
        'none': sum(1 for r in results if r['confidence'] == 'none')
    }
    
    report = []
    report.append("=" * 80)
    report.append("2025年西医综合真题 - 最终答案提取报告 (V4融合版)")
    report.append("=" * 80)
    report.append(f"\n总题数: {total}")
    report.append(f"成功提取: {success}题 ({success_rate:.1f}%)")
    report.append(f"未识别: {total-success}题 ({unknown_rate:.1f}%)")
    
    report.append(f"\n【置信度分布】")
    report.append(f"  高置信度: {conf_stats['high']}题 ({conf_stats['high']/total*100 if total else 0:.1f}%)")
    report.append(f"  中置信度: {conf_stats['medium']}题 ({conf_stats['medium']/total*100 if total else 0:.1f}%)")
    report.append(f"  未识别: {conf_stats['none']}题 ({conf_stats['none']/total*100 if total else 0:.1f}%)")
    
    report.append(f"\n【提取方法分布】")
    for method, count in sorted(method_stats.items(), key=lambda x: -x[1]):
        report.append(f"  {method}: {count}题")
    
    report.append(f"\n【前20题答案预览】")
    report.append("-" * 80)
    for r in results[:20]:
        ans = r['answer'] if r['answer'] else '??'
        conf_symbol = {'high': '★★★', 'medium': '★★☆', 'none': '??'}.get(r['confidence'], '?')
        report.append(f"第{r['num']:3d}题: [{ans}] {conf_symbol} | {r['method']}")
    
    report.append(f"\n【未识别题目列表（前20题）】")
    report.append("-" * 80)
    unknown_count = 0
    for r in results:
        if r['answer'] is None:
            unknown_count += 1
            if unknown_count <= 20:
                report.append(f"第{r['num']:3d}题: {r['question'][:50]}...")
    report.append(f"\n...共{unknown_count}题未识别")
    
    return '\n'.join(report), results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="提取真题答案并生成标准版输出。")
    parser.add_argument(
        "input_file",
        nargs="?",
        default="真题/合并/2025年考研西医综合_真题+解析.md",
        help="输入真题 Markdown 文件路径。",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="输出目录，默认是 output。",
    )
    parser.add_argument(
        "--year",
        default=None,
        help="年份标签，默认从输入文件名自动识别。",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    year_match = re.search(r'(20\d{2})', input_path.name)
    year = args.year or (year_match.group(1) if year_match else "未知年份")

    print(f"开始用V4融合算法解析真题: {input_path}")
    results = parse_exam(input_path)

    print(f"共解析 {len(results)} 道题目")
    print("\n生成最终报告...")

    report, results = generate_final_report(results)

    report_file = output_dir / f"{year}年最终答案提取报告.txt"
    report_file.write_text(report, encoding='utf-8')
    print(f"\n报告已保存: {report_file}")

    json_file = output_dir / f"{year}年最终答案提取结果.json"
    json_file.write_text(
        json.dumps(
            {
                'year': year,
                'algorithm': 'V4_final_fusion',
                'total_questions': len(results),
                'success_count': sum(1 for r in results if r['answer'] is not None),
                'questions': results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )
    print(f"JSON结果已保存: {json_file}")

    content = input_path.read_text(encoding='utf-8', errors='ignore')
    for result in results:
        if result['answer']:
            old_pattern = f'### 第{result["num"]}题\\s+\\*\\*\\[答案\\]待确认\\*\\*'
            new_text = f'### 第{result["num"]}题\\n\\n**【答案】{result["answer"]}**'
            content = re.sub(old_pattern, new_text, content)

    output_file = output_dir / f"{year}年真题_最终标准版.md"
    output_file.write_text(content, encoding='utf-8')
    print(f"最终标准版真题已保存: {output_file}")

    unknown_questions = [result for result in results if result['answer'] is None]
    if unknown_questions:
        unknown_file = output_dir / f"{year}年待人工确认题目.txt"
        with unknown_file.open('w', encoding='utf-8') as handle:
            handle.write("=" * 80 + "\n")
            handle.write(f"{year}年真题 - 待人工确认题目列表\n")
            handle.write("=" * 80 + "\n\n")
            handle.write(f"共 {len(unknown_questions)} 题需要人工确认\n\n")

            for result in unknown_questions:
                handle.write(f"\n{'='*80}\n")
                handle.write(f"第{result['num']}题\n")
                handle.write(f"{'='*80}\n")
                handle.write(f"题目: {result['question']}\n\n")
                handle.write("选项:\n")
                for option, text in result['options'].items():
                    handle.write(f"  {option}. {text}\n")
                handle.write("\n")
        print(f"待确认题目列表已保存: {unknown_file}")

    print("\n" + "=" * 80)
    print("V4融合算法处理完成!")
    print("=" * 80)
