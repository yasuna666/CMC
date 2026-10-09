#!/usr/bin/env python3
"""Local, deterministic helpers for xizong-exam-suite. No model or network calls."""
from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TYPES = {"A1", "A2", "A3A4", "B", "X"}
COGNITIVE = {"memory", "understanding", "application", "integration"}
ROLES = {"lecture", "syllabus", "style", "reference"}
UPSTREAM_MODULES = {
    "dispatcher", "a1_concept", "a2_case_summary", "case_workflow",
    "b_matching", "x_multi",
}
TYPE_MODULE = {
    "A1": "a1_concept",
    "A2": "a2_case_summary",
    "A3A4": "case_workflow",
    "B": "b_matching",
    "X": "x_multi",
}


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    require(isinstance(value, dict), f"JSON 顶层必须为对象：{path}")
    return value


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def norm(text):
    return re.sub(r"\s+", "", str(text))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def resolve_source(project_path, raw):
    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else (Path(project_path).resolve().parent / path).resolve()


def output_path(project_path, raw):
    base = Path(project_path).resolve().parent
    path = Path(raw)
    path = path.resolve() if path.is_absolute() else (base / path).resolve()
    allowed = (base / "output" / "mock-exams").resolve()
    require(path.is_relative_to(allowed), "输出必须位于项目的 output/mock-exams/，防止混入真题档案。")
    return path


def get_unit(project, unit_id):
    require(project.get("schema_version") == 1, "project.schema_version 必须为 1")
    require(project.get("mode") == "unit_practice", "当前工具只发布单元练习；正式卷型需另行核对和适配。")
    require(project.get("scope_policy") == "lecture_only", "仅实现 lecture_only 范围策略")
    matches = [u for u in project.get("units", []) if u.get("id") == unit_id]
    require(len(matches) == 1, f"单元不存在或重复：{unit_id}")
    require(project.get("purpose", "practice") in {"practice", "synthetic_demo"}, "未知 purpose")
    return matches[0]


def extracted_pages(path):
    """Return (physical page or None, text); never invent book page numbers."""
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return [(None, path.read_text(encoding="utf-8-sig"))]
    if suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            info = archive.getinfo("word/document.xml")
            require(info.file_size < 30_000_000, "DOCX XML 过大，请先拆分资料")
            tree = ET.fromstring(archive.read(info))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for p in tree.findall(".//w:p", ns):
            text = "".join(t.text or "" for t in p.findall(".//w:t", ns)).strip()
            if text:
                paragraphs.append(text)
        return [(None, "\n\n".join(paragraphs))]
    if suffix == ".pdf":
        binary = shutil.which("pdftotext")
        if binary:
            result = subprocess.run([binary, "-layout", str(path), "-"], capture_output=True, timeout=90)
            require(result.returncode == 0, "PDF 文本提取失败，请检查文件或提供可读 Markdown")
            chunks = result.stdout.decode("utf-8", errors="replace").split("\f")
            if chunks and not chunks[-1].strip():
                chunks.pop()
            return list(enumerate(chunks, 1))
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise Invalid("PDF 需要 pdftotext 或 pypdf；也可提供核对后的 Markdown。不会自动下载依赖。") from exc
        reader = PdfReader(str(path))
        return [(i, p.extract_text() or "") for i, p in enumerate(reader.pages, 1)]
    raise Invalid(f"不支持直接提取 {suffix}；图片/扫描件请由宿主 OCR 并核对后转 Markdown。")


def split_blocks(pages, source_id):
    blocks, headings = [], []
    for page, text in pages:
        pending = []

        def flush():
            if pending:
                joined = "\n".join(pending).strip()
                if joined:
                    number = len(blocks) + 1
                    section = " / ".join(headings)
                    locator = f"物理页 {page}" if page is not None else f"段落 {number}"
                    blocks.append({"id": f"{source_id}:B{number:05d}", "source_id": source_id,
                                   "page": page, "section": section, "locator": locator,
                                   "text": joined})
                pending.clear()

        for line in text.splitlines():
            marker = re.fullmatch(r"\s*<!--\s*page:\s*(\d+)\s*-->\s*", line)
            heading = re.match(r"^(#{1,6})\s+(.+)$", line)
            if marker:
                flush()
                page = int(marker.group(1))
            elif heading:
                flush()
                level = len(heading.group(1))
                headings = headings[:level - 1] + [heading.group(2).strip()]
            elif not line.strip():
                flush()
            else:
                pending.append(line)
        flush()
    return blocks


def index_data(project_path, unit_id):
    project = load(project_path)
    unit = get_unit(project, unit_id)
    ids = [s.get("id") for s in project.get("sources", [])]
    require(len(ids) == len(set(ids)), "来源 ID 重复")
    sources = {s["id"]: s for s in project.get("sources", [])}
    result = {"schema_version": 1, "unit_id": unit_id, "unit_title": unit["title"],
              "project_sha256": digest(project_path), "sources": [], "blocks": [], "warnings": []}
    selected = set()
    for selection in unit.get("materials", []):
        sid = selection["source_id"]
        require(sid not in selected, f"单元内来源重复：{sid}")
        selected.add(sid)
        require(sid in sources, f"未知来源：{sid}")
        source = sources[sid]
        require(re.fullmatch(r"[A-Za-z0-9_-]+", sid), "来源 ID 只能包含英文数字下划线横线")
        require(source.get("role") in ROLES, f"未知来源角色：{sid}")
        path = resolve_source(project_path, source["path"])
        require(path.is_file(), f"来源文件不存在：{source['path']}")
        if source.get("extraction") == "ocr":
            require(source.get("ocr_reviewed") is True, f"{sid} 为未核对 OCR，先核对再命题")
        pages = extracted_pages(path)
        chosen_pages = selection.get("pages", [])
        require(all(type(p) is int and p > 0 for p in chosen_pages), "pages 必须为正整数物理页数组")
        blocks = split_blocks(pages, sid)
        if chosen_pages:
            existing = {b["page"] for b in blocks}
            require(set(chosen_pages) <= existing, f"{sid} 请求的页缺失/空白/未标注页码；请核对或 OCR")
            blocks = [b for b in blocks if b["page"] in chosen_pages]
        sections = selection.get("sections", [])
        if sections:
            for section in sections:
                require(any(section in b["section"] for b in blocks), f"{sid} 找不到章节：{section}")
            blocks = [b for b in blocks if any(s in b["section"] for s in sections)]
        require(blocks, f"{sid} 没有可读内容，不可伪造读取结果")
        blank = [n for n, text in pages if n is not None and not text.strip()]
        if blank and not chosen_pages:
            raise Invalid(f"{sid} 存在无文本物理页 {blank}，请限定已读页或核对 OCR")
        if path.suffix.lower() == ".docx":
            result["warnings"].append(f"{sid} DOCX 按段落提取，无页码；表格布局与图片需另行核对。")
        metadata = {"id": sid, "title": source.get("title", path.name), "role": source["role"],
                    "path": source["path"], "sha256": digest(path), "version": source.get("version", "未注明")}
        result["sources"].append(metadata)
        result["blocks"].extend(blocks)
    require(any(s["role"] == "lecture" for s in result["sources"]), "单元至少绑定一个 lecture 来源")
    return result


def build_index(project_path, unit_id, destination):
    result = index_data(project_path, unit_id)
    dump(destination, result)
    return result


def bridge_template(project_path, unit_id, destination):
    """Create the shared contract between upstream skills and a mock bank."""
    project = load(project_path)
    unit = get_unit(project, unit_id)
    cfg = project.get("upstream_integration", {})
    modules = cfg.get("modules", sorted(UPSTREAM_MODULES))
    require(set(modules) == UPSTREAM_MODULES, "upstream_integration.modules 必须登记全部六个模块")
    builtins = [
        ("upstream-dispatcher", "dispatcher", "routing_rules", "references/upstream/西综总调度-Skill/SKILL.md"),
        ("upstream-a1", "a1_concept", "concept_cluster_rules", "references/upstream/西综A1概念簇-Skill/SKILL.md"),
        ("upstream-a2", "a2_case_summary", "case_summary_rules", "references/upstream/西综A2病例摘要-Skill/SKILL.md"),
        ("upstream-case", "case_workflow", "case_workflow_rules", "references/upstream/西综病例-Skill/SKILL.md"),
        ("upstream-b", "b_matching", "matching_rules", "references/upstream/西综B型配伍-Skill/SKILL.md"),
        ("upstream-x", "x_multi", "multi_select_rules", "references/upstream/西综X型多选-Skill/SKILL.md"),
    ]
    value = {
        "schema_version": 1,
        "unit_id": unit_id,
        "unit_title": unit["title"],
        "policy": "design_only",
        "modules": list(modules),
        "question_type_map": TYPE_MODULE,
        "routing_refs": ["upstream-dispatcher"],
        "artifacts": [{"id": aid, "module": module, "kind": kind, "source_ref": source_ref, "role": "built_in_reference"}
                       for aid, module, kind, source_ref in builtins],
        "instructions": "填写实际上游模块产出的 artifact；它们只提供题型、认知、错误模式和病例链设计参考，医学事实仍必须引用 source-index 的 lecture/reference 块。",
    }
    dump(destination, value)
    return value


def options_for(question, groups):
    if question.get("type") == "B":
        return groups.get(question.get("group_id"), {}).get("options", {})
    return question.get("options", {})


def validate(project_path, index_path, bank_path, reviews_path=None, final=False, histories=()):
    project, index, bank = load(project_path), load(index_path), load(bank_path)
    errors, warnings = [], []

    def check(condition, message):
        if not condition:
            errors.append(message)

    def warn(code, message):
        warnings.append({"code": code, "message": message})

    unit = get_unit(project, bank.get("unit_id"))
    check(index == index_data(project_path, bank.get("unit_id")), "索引与实际来源/单元选择不一致，请重新生成索引")
    check(index.get("project_sha256") == digest(project_path), "项目配置已改变，必须重新索引和核对")
    check(bank.get("source_index_sha256") == digest(index_path), "来源索引哈希不匹配")
    check(index.get("unit_id") == bank.get("unit_id"), "题库与索引单元不一致")
    check(bank.get("schema_version") == 1, "题库 schema_version 必须为 1")
    check(bank.get("source_type") == "generated_mock", "题库必须标记 generated_mock")
    check(bank.get("purpose") == project.get("purpose", "practice"), "purpose 与项目不一致")
    check(nonempty(bank.get("title")), "题库缺少标题")
    sources = {s["id"]: s for s in index["sources"]}
    blocks = {b["id"]: b for b in index["blocks"]}
    check(len(blocks) == len(index["blocks"]), "来源块 ID 重复")
    for s in sources.values():
        path = resolve_source(project_path, s["path"])
        check(path.is_file() and digest(path) == s["sha256"], f"来源已改变或丢失：{s['id']}")
    for n, message in enumerate(index.get("warnings", [])):
        warn(f"source:{n}", message)

    integration_cfg = project.get("upstream_integration", {})
    integration_enabled = integration_cfg.get("enabled", False) is True
    bridge = None
    artifacts = {}
    if integration_enabled:
        configured_modules = integration_cfg.get("modules", [])
        check(integration_cfg.get("policy") == "design_only", "上游整合 policy 必须为 design_only")
        check(set(configured_modules) == UPSTREAM_MODULES, "上游整合必须登记全部六个模块")
        integration = bank.get("integration", {})
        check(integration.get("policy") == "design_only", "题库 integration.policy 必须为 design_only")
        bridge_raw = integration_cfg.get("bridge_path", "upstream-bridge.json")
        bridge_path = Path(bridge_raw)
        bridge_path = bridge_path.resolve() if bridge_path.is_absolute() else (Path(bank_path).resolve().parent / bridge_path).resolve()
        check(bridge_path.is_file(), "缺少 upstream-bridge.json，请先运行 bridge 并填写上游产物")
        if bridge_path.is_file():
            try:
                bridge = load(bridge_path)
                raw_artifacts = bridge.get("artifacts", [])
                artifacts = {a.get("id"): a for a in raw_artifacts if isinstance(a, dict)}
                check(bridge.get("schema_version") == 1, "上游桥接清单 schema_version 无效")
                check(bridge.get("unit_id") == bank.get("unit_id"), "上游桥接清单单元不一致")
                check(bridge.get("policy") == "design_only", "上游桥接清单 policy 必须为 design_only")
                check(set(bridge.get("modules", [])) == UPSTREAM_MODULES, "上游桥接清单未登记全部六个模块")
                check(integration.get("bridge_sha256") == digest(bridge_path), "上游桥接清单已改变，需更新题库桥接哈希")
                check(isinstance(bridge.get("routing_refs"), list) and bool(bridge["routing_refs"]), "桥接清单缺少总调度 routing_refs")
                artifact_list = bridge.get("artifacts", [])
                check(isinstance(artifact_list, list), "上游 artifacts 必须为数组")
                artifact_list = artifact_list if isinstance(artifact_list, list) else []
                check(all(isinstance(a, dict) for a in artifact_list), "上游 artifact 必须为对象")
                artifact_list = [a for a in artifact_list if isinstance(a, dict)]
                artifact_ids = [a.get("id") for a in artifact_list]
                check(len(artifact_ids) == len(set(artifact_ids)), "上游 artifact ID 重复")
                for artifact in artifact_list:
                    aid = artifact.get("id")
                    check(nonempty(aid), "上游 artifact ID 为空")
                    check(artifact.get("module") in UPSTREAM_MODULES, f"上游 artifact 模块无效：{aid}")
                    check(nonempty(artifact.get("kind")), f"上游 artifact 缺少 kind：{aid}")
                    if artifact.get("path"):
                        artifact_path = resolve_source(project_path, artifact["path"])
                        check(artifact_path.is_file(), f"上游 artifact 文件不存在：{aid}")
                        if artifact_path.is_file() and artifact.get("sha256"):
                            check(digest(artifact_path) == artifact["sha256"], f"上游 artifact 文件已改变：{aid}")
                dispatcher_refs = integration.get("dispatcher_refs", [])
                check(isinstance(dispatcher_refs, list) and bool(dispatcher_refs), "题库缺少 dispatcher_refs")
                for ref in dispatcher_refs:
                    check(ref in artifacts and artifacts[ref].get("module") == "dispatcher", f"dispatcher 引用无效：{ref}")
            except (OSError, ValueError, KeyError, TypeError):
                check(False, "上游桥接清单无法读取")

    def evidence_valid(evidence, label):
        check(isinstance(evidence, list) and bool(evidence), f"{label} 缺少来源摘录")
        valid = []
        if not isinstance(evidence, list):
            return valid
        for item in evidence:
            bid, quote = item.get("block_id"), item.get("quote", "")
            check(bid in blocks, f"{label} 未知来源块 {bid}")
            check(nonempty(quote), f"{label} 摘录为空")
            if bid in blocks:
                check(bool(norm(quote)) and norm(quote) in norm(blocks[bid]["text"]), f"{label} 摘录不在指定块：{bid}")
                valid.append(bid)
        return valid

    points = {p["id"]: p for p in bank.get("points", [])}
    check(len(points) == len(bank.get("points", [])), "考点 ID 重复")
    check(bool(points), "没有考点清单")
    for pid, point in points.items():
        check(nonempty(point.get("label")) and nonempty(point.get("objective")), f"{pid} 缺少名称或学习目标")
        check(point.get("status") in {"ready", "hold"}, f"{pid} 考点状态无效")
        check(all(b in blocks for b in point.get("source_blocks", [])), f"{pid} 未知来源块")
        if point.get("status") == "ready":
            check(any(b in blocks and sources[blocks[b]["source_id"]]["role"] == "lecture" for b in point.get("source_blocks", [])), f"{pid} 无讲义依据")
        else:
            check(nonempty(point.get("hold_reason")), f"{pid} 缺少搁置原因")

    groups = {g["id"]: g for g in bank.get("groups", [])}
    check(len(groups) == len(bank.get("groups", [])), "组 ID 重复")
    questions = bank.get("questions", [])
    check(isinstance(questions, list) and bool(questions), "没有题目")
    qids = [q["id"] for q in questions]
    check(len(set(qids)) == len(qids), "题目 ID 重复")
    profile = project.get("exam_profile", {})
    check(profile.get("x_scoring") == "exact_set", "目前只实现 X exact_set 练习评分")
    option_count = profile.get("option_count", 4)
    check(type(option_count) is int and 2 <= option_count <= 8, "选项数须为 2..8")
    check(type(profile.get("b_reuse_allowed")) is bool, "必须明确 B 选项复用规则")
    x_min = profile.get("x_min_correct", 2)
    x_max = profile.get("x_max_correct", option_count)
    check(type(x_min) is int and type(x_max) is int and 1 <= x_min <= x_max <= option_count, "X 正确项数量配置无效")
    for gid, group in groups.items():
        check(group.get("type") in {"B", "A3A4"}, f"{gid} 组类型无效")
        if group.get("type") == "A3A4":
            check(nonempty(group.get("stem")), f"{gid} 缺少共用题干")
        members = [i for i, q in enumerate(questions) if q.get("group_id") == gid]
        check(len(members) >= 2, f"{gid} 题组需至少两个小题")
        check(not members or max(members) - min(members) + 1 == len(members), f"{gid} 小题需连续排列")
        if group.get("type") == "B" and not profile.get("b_reuse_allowed"):
            answers = [a for q in questions if q.get("group_id") == gid for a in q.get("answer", [])]
            check(len(answers) == len(set(answers)), f"{gid} 禁止选项复用但存在重复答案")

    tested, fingerprints = Counter(), []
    for q in questions:
        qid, typ = q["id"], q.get("type")
        check(bool(re.fullmatch(r"MOCK-[A-Za-z0-9_-]+", qid)), f"{qid} ID 必须以 MOCK- 开头")
        check(typ in TYPES, f"{qid} 题型无效")
        check(nonempty(q.get("stem")), f"{qid} 缺少题干")
        check(nonempty(q.get("explanation")), f"{qid} 缺少解析")
        check(nonempty(q.get("originality_note")), f"{qid} 缺少原创/改编说明")
        check(type(q.get("high_risk")) is bool, f"{qid} 必须明确 high_risk")
        check(q.get("cognitive_level") in COGNITIVE, f"{qid} 认知层次无效")
        if integration_enabled:
            refs = q.get("upstream_refs", [])
            if integration_cfg.get("require_question_links", True):
                check(isinstance(refs, list) and bool(refs), f"{qid} 缺少上游模块引用")
            linked_modules = set()
            for ref in refs if isinstance(refs, list) else []:
                aid = ref.get("artifact_id")
                module = ref.get("module")
                check(module in UPSTREAM_MODULES, f"{qid} 上游模块无效：{module}")
                check(nonempty(aid) and aid in artifacts, f"{qid} 上游 artifact 不存在：{aid}")
                if aid in artifacts:
                    check(artifacts[aid].get("module") == module, f"{qid} 上游模块与 artifact 不一致：{aid}")
                check(nonempty(ref.get("transfer_goal")), f"{qid} 上游引用缺少 transfer_goal")
                linked_modules.add(module)
            expected_module = TYPE_MODULE.get(typ)
            check(expected_module in linked_modules, f"{qid} 未链接其题型对应模块：{expected_module}")
        difficulty = q.get("difficulty", {})
        check(difficulty.get("level") in {"easy", "medium", "hard"} and nonempty(difficulty.get("reason")), f"{qid} 难度目标/理由缺失")
        pids = q.get("point_ids", [])
        check(bool(pids) and len(pids) == len(set(pids)), f"{qid} 考点为空/重复")
        for pid in pids:
            check(pid in points and points[pid].get("status") == "ready", f"{qid} 引用未知/搁置考点 {pid}")
            tested[pid] += 1
        gid = q.get("group_id")
        if typ in {"B", "A3A4"}:
            check(gid in groups and groups[gid].get("type") == typ, f"{qid} 题组不匹配")
        else:
            check(gid is None, f"{qid} 非组题不应有 group_id")
        if typ == "B":
            check(not q.get("options"), f"{qid} B 小题不得重复定义选项")
        opts = options_for(q, groups)
        check(isinstance(opts, dict) and len(opts) == option_count, f"{qid} 选项数不匹配")
        check(set(opts) == set("ABCDEFGH"[:option_count]), f"{qid} 选项编号必须连续")
        check(all(nonempty(v) for v in opts.values()), f"{qid} 空选项")
        check(len({norm(v) for v in opts.values()}) == len(opts), f"{qid} 存在相同选项")
        answer = q.get("answer", [])
        check(isinstance(answer, list) and len(set(answer)) == len(answer) and set(answer) <= set(opts), f"{qid} 答案编号不合法")
        check((x_min <= len(answer) <= x_max) if typ == "X" else len(answer) == 1, f"{qid} 正确项数量不合法")
        bids = evidence_valid(q.get("evidence"), qid)
        check(any(sources[blocks[b]["source_id"]]["role"] == "lecture" for b in bids), f"{qid} 无讲义直接依据")
        analysis = q.get("option_analysis", {})
        check(set(analysis) == set(opts), f"{qid} 需逐项解释所有选项")
        for key, item in analysis.items():
            check(type(item.get("correct")) is bool and item["correct"] == (key in answer), f"{qid}/{key} 选项结论与答案不一致")
            check(nonempty(item.get("reason")), f"{qid}/{key} 缺少判定理由")
            check(bool(item.get("source_blocks")) and all(b in bids for b in item.get("source_blocks", [])), f"{qid}/{key} 依据必须来自本题已定位摘录")
        group_text = groups.get(gid, {}).get("stem", "")
        fingerprint = norm(group_text + q.get("stem", "") + "|".join(sorted(opts.values())))
        for previous_id, previous in fingerprints:
            if fingerprint == previous:
                check(False, f"{qid} 与 {previous_id} 完全重复")
            elif SequenceMatcher(None, fingerprint, previous).ratio() >= 0.88:
                warn(f"similar:{previous_id}:{qid}", f"{previous_id} 与 {qid} 文本接近，请复查考查任务")
        fingerprints.append((qid, fingerprint))

    requested = unit.get("request", {})
    check(type(requested.get("total_questions")) is int and len(questions) == requested["total_questions"], "题数与单元请求不一致（按小题计）")
    actual_types = Counter(q.get("type") for q in questions)
    if requested.get("type_counts"):
        check(not (set(requested["type_counts"]) - TYPES), "配置有未知题型")
        check(all(actual_types[t] == requested["type_counts"].get(t, 0) for t in TYPES), "题型数量与请求不一致")
    if requested.get("difficulty_counts"):
        actual_diff = Counter(q.get("difficulty", {}).get("level") for q in questions)
        check(actual_diff == Counter(requested["difficulty_counts"]), "难度目标数量不一致")
    blueprint = bank.get("blueprint", [])
    check(len(blueprint) == len(questions) and {b.get("question_id") for b in blueprint} == set(qids), "blueprint 必须每小题一条且完整对应")
    qmap = {q["id"]: q for q in questions}
    for b in blueprint:
        if b.get("question_id") in qmap:
            q = qmap[b["question_id"]]
            check(b.get("type") == q.get("type") and b.get("point_id") == (q.get("point_ids") or [None])[0] and b.get("cognitive_level") == q.get("cognitive_level"), f"{q['id']} 与出题分配不一致")
    for pid, point in points.items():
        if point.get("status") == "ready" and not tested[pid]:
            warn(f"coverage:{pid}", f"未覆盖考点：{pid} {point.get('label')}")
    for n, issue in enumerate(bank.get("source_issues", [])):
        warn(f"source-issue:{n}", str(issue))
    singles = [q["answer"][0] for q in questions if q.get("type") != "X" and len(q.get("answer", [])) == 1]
    if len(singles) >= 6:
        for key, count in Counter(singles).items():
            if count / len(singles) > 0.7:
                warn(f"answer-position:{key}", f"单选答案 {key} 比例较高，检查是否存在位置线索")
    for historical_path in histories:
        old = load(historical_path)
        old_groups = {g["id"]: g for g in old.get("groups", [])}
        for oldq in old.get("questions", []):
            oldtext = norm(old_groups.get(oldq.get("group_id"), {}).get("stem", "") + oldq.get("stem", "") + "|".join(sorted(options_for(oldq, old_groups).values())))
            for qid, fp in fingerprints:
                if SequenceMatcher(None, fp, oldtext).ratio() >= 0.88:
                    warn(f"history:{Path(historical_path).name}:{oldq.get('id')}:{qid}", f"{qid} 接近历史题 {oldq.get('id')}，请确认训练目的")

    if final:
        check(reviews_path is not None, "已审核版需要 reviews.json；缺少独立复答时仅可导出草稿")
        if reviews_path:
            review = load(reviews_path)
            check(review.get("schema_version") == 1, "复核 schema_version 无效")
            check(review.get("unit_id") == bank.get("unit_id"), "复核单元不一致")
            check(review.get("bank_sha256") == digest(bank_path), "题库已改变，旧复核记录失效")
            check(review.get("source_index_sha256") == digest(index_path), "复核绑定的索引不一致")
            check(review.get("reviewer_mode") in {"independent_ai", "human"}, "同上下文自查不算独立复答")
            check(nonempty(review.get("reviewer")), "需记录实际复答者/会话")
            checks = {c["question_id"]: c for c in review.get("checks", [])}
            check(len(checks) == len(review.get("checks", [])) and set(checks) == set(qids), "复核需完整逐题对应且不重复")
            for q in questions:
                c = checks.get(q["id"], {})
                check(c.get("verdict") == "pass" and c.get("source_status") == "consistent" and c.get("item_status") == "pass", f"{q['id']} 未通过来源/命题复核")
                check(nonempty(c.get("notes")) and nonempty(c.get("blind_reason")), f"{q['id']} 复核/复答理由为空")
                check(set(c.get("blind_answer", [])) == set(q.get("answer", [])), f"{q['id']} 独立复答与预设答案不一致")
                ms = c.get("medical_status")
                if bank.get("purpose") == "synthetic_demo":
                    check(ms == "not_applicable_synthetic", f"{q['id']} 虚构工程样例不得标记医学认证")
                else:
                    check(ms in {"lecture_consistent", "reference_checked"}, f"{q['id']} 医学核对状态无效")
                    if q.get("high_risk"):
                        check(ms == "reference_checked", f"{q['id']} 高风险题需参考资料核对")
                    if ms == "reference_checked":
                        rb = c.get("medical_reference_blocks", [])
                        check(bool(rb) and all(b in blocks and sources[blocks[b]["source_id"]]["role"] == "reference" for b in rb), f"{q['id']} 缺少实际教材/参考资料依据")
            ack = review.get("acknowledged_warnings", {})
            for w in warnings:
                check(nonempty(ack.get(w["code"])), f"待处理警告：{w['code']}")
    module_counts = Counter()
    if integration_enabled:
        for q in questions:
            for ref in q.get("upstream_refs", []):
                module_counts[ref.get("module")] += 1
    return {"ok": not errors, "stage": "final" if final else "draft", "errors": errors,
            "warnings": warnings, "question_count": len(questions), "type_counts": dict(actual_types),
            "coverage": [{"point_id": pid, "label": p.get("label"), "status": p.get("status"),
                          "count": tested[pid], "hold_reason": p.get("hold_reason", "")} for pid, p in points.items()],
            "integration": {"enabled": integration_enabled, "module_counts": dict(module_counts)},
            "bank_sha256": digest(bank_path), "source_index_sha256": digest(index_path),
            "limits": "检查文件绑定、结构和记录，不证明医学正确或复核记录真实。"}


def blind(project_path, index_path, bank_path, destination):
    report = validate(project_path, index_path, bank_path)
    require(report["ok"], "请先修复结构问题：" + "; ".join(report["errors"]))
    bank, index = load(bank_path), load(index_path)
    require(not destination.exists(), "盲答目录已存在，请用新目录")
    questions = []
    for q in bank["questions"]:
        questions.append({k: q.get(k) for k in ("id", "type", "group_id", "stem", "options")})
    packet = {"unit_id": bank["unit_id"], "purpose": bank["purpose"], "title": bank["title"],
              "instructions": "仅依据资料独立作答。逐题给答案及推理，标记歧义、无依据或冲突；不推测预设答案。",
              "groups": [{k: g[k] for k in ("id", "type", "stem", "options") if k in g} for g in bank.get("groups", [])], "questions": questions,
              "sources": [{k: s[k] for k in ("id", "title", "role", "version")} for s in index["sources"]],
              "blocks": index["blocks"]}
    template = {"schema_version": 1, "unit_id": bank["unit_id"], "bank_sha256": digest(bank_path),
                "source_index_sha256": digest(index_path), "reviewer_mode": "self_review", "reviewer": "",
                "acknowledged_warnings": {}, "checks": [{"question_id": q["id"], "verdict": "pending",
                  "source_status": "pending", "item_status": "pending", "medical_status": "pending",
                  "medical_reference_blocks": [], "blind_answer": [], "blind_reason": "", "notes": ""} for q in bank["questions"]]}
    dump(destination / "blind-packet.json", packet)
    dump(destination / "reviews.template.json", template)


def doc_html(title, elements):
    esc = html.escape
    contents = []
    for kind, text in elements:
        if kind == "table":
            headers, rows = text
            contents.append("<table><thead><tr>" + "".join(f"<th>{esc(str(x))}</th>" for x in headers) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{esc(str(x))}</td>" for x in r) + "</tr>" for r in rows) + "</tbody></table>")
        else:
            tag = {"title": "h1", "heading": "h2", "sub": "h3", "p": "p"}[kind]
            contents.append(f"<{tag}>" + esc(text).replace("\n", "<br>") + f"</{tag}>")
    return "<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>" + esc(title) + "</title><style>body{max-width:900px;margin:36px auto;padding:0 28px;font-family:system-ui,'Noto Sans CJK SC',sans-serif;line-height:1.75;color:#182a38}h1{font-size:26px;border-bottom:3px solid #147d82;padding-bottom:12px}h2{font-size:20px;margin-top:30px;color:#14585d}h3{font-size:17px;margin-top:24px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #cbd7da;padding:9px;text-align:left;vertical-align:top}th{background:#eef5f5}p{white-space:normal;overflow-wrap:anywhere}@media print{body{margin:0;max-width:none;font-size:11pt;padding:0}h2,h3{break-after:avoid}table{font-size:9pt}tr{break-inside:avoid}}@page{size:A4;margin:18mm}</style><main>" + "\n".join(contents) + "</main></html>"


def doc_markdown(elements):
    lines = []
    for kind, text in elements:
        if kind == "table":
            headers, rows = text
            clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
            lines.append("| " + " | ".join(map(clean, headers)) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            lines.extend("| " + " | ".join(map(clean, row)) + " |" for row in rows)
        else:
            prefix = {"title": "# ", "heading": "## ", "sub": "### ", "p": ""}[kind]
            lines.append(prefix + text)
        lines.append("")
    return "\n".join(lines)


def render(project_path, index_path, bank_path, destination, stage="draft", reviews_path=None, histories=()):
    report = validate(project_path, index_path, bank_path, reviews_path, stage == "final", histories)
    require(report["ok"], "不能导出：" + "; ".join(report["errors"]))
    require(not destination.exists(), "导出目录已存在，请使用新的目录避免覆盖")
    project, index, bank = load(project_path), load(index_path), load(bank_path)
    groups = {g["id"]: g for g in bank.get("groups", [])}
    blocks = {b["id"]: b for b in index["blocks"]}
    sources = {s["id"]: s for s in index["sources"]}
    label = "待独立复核草稿" if stage == "draft" else "流程复核完成的练习版"
    if bank["purpose"] == "synthetic_demo":
        label += "｜虚构工程样例，不是医学学习材料"
    notice = label + "。AI 模拟题；非真题、非官方试卷。题数按小题计算。"
    present_types = {q["type"] for q in bank["questions"]}
    instructions = [f"共 {len(bank['questions'])} 题。"]
    if present_types - {"X"}:
        instructions.append("单选只选一个最佳项。")
    if "X" in present_types:
        instructions.append("X 型为多选，须选中所有正确项且不选错误项。")
    if "B" in present_types:
        instructions.append("B 型同组选项" + ("可以复用。" if project["exam_profile"]["b_reuse_allowed"] else "不可复用。"))
    exam = [("title", bank["title"] + " · 试题"), ("p", notice),
            ("p", "".join(instructions))]
    answers = [("title", bank["title"] + " · 答案与解析"), ("p", notice)]
    shown = set()
    for i, q in enumerate(bank["questions"], 1):
        gid = q.get("group_id")
        if gid and gid not in shown:
            g = groups[gid]
            exam.append(("heading", f"题组 {gid}"))
            if g.get("stem"):
                exam.append(("p", g["stem"]))
            if g["type"] == "B":
                exam.extend(("p", f"{k}. {v}") for k, v in g["options"].items())
            shown.add(gid)
        exam.extend([("sub", f"{i}. [{q['type']}] {q['stem']}")])
        if q["type"] != "B":
            exam.extend(("p", f"{k}. {v}") for k, v in q["options"].items())
        answers.extend([("heading", f"第 {i} 题 · {q['id']}"), ("p", "答案：" + "、".join(q["answer"])),
                        ("p", q["explanation"]), ("p", "考点：" + "、".join(q["point_ids"]) + "；难度目标：" + q["difficulty"]["level"] + "；理由：" + q["difficulty"]["reason"])])
        opts = options_for(q, groups)
        for key, a in q["option_analysis"].items():
            answers.append(("p", f"{key}. {opts[key]}｜{'正确' if a['correct'] else '错误'}：{a['reason']}"))
        for ev in q["evidence"]:
            b = blocks[ev["block_id"]]
            s = sources[b["source_id"]]
            answers.append(("p", f"出处：{s['title']}（{s['version']}），{b['locator']}，{b['section']}，{b['id']}\n依据摘录：{ev['quote']}"))
    coverage = [("title", bank["title"] + " · 覆盖与审核"), ("p", notice),
                ("p", "结构检查通过；来源匹配不等于医学正确。"),
                ("table", (["考点", "名称", "状态", "题数", "搁置原因"], [[x["point_id"], x["label"], x["status"], x["count"], x["hold_reason"]] for x in report["coverage"]]))]
    if report.get("integration", {}).get("enabled"):
        coverage.append(("heading", "上游模块追踪"))
        coverage.append(("p", "上游模块仅作为题型、认知和错误模式的设计参考；医学事实仍以题目 evidence 为准。"))
        coverage.append(("table", (["模块", "题目引用次数"], [[k, v] for k, v in sorted(report["integration"]["module_counts"].items())])))
    if reviews_path and stage == "final":
        review = load(reviews_path)
        coverage.append(("p", f"复核方式：{review['reviewer_mode']}；记录：{review['reviewer']}。这不是权威医学认证。"))
        coverage.append(("table", (["题目", "结论", "医学依据状态", "复核说明"], [[c["question_id"], c["verdict"], c["medical_status"], c["notes"]] for c in review["checks"]])))
    else:
        coverage.append(("p", "尚无有效独立复答记录；目前为草稿，不得宣称医学审核通过。"))
    for w in report["warnings"]:
        coverage.append(("p", w["code"] + "：" + w["message"]))
        if reviews_path and stage == "final":
            coverage.append(("p", "处置说明：" + review["acknowledged_warnings"][w["code"]]))
    destination.mkdir(parents=True)
    for filename, document in [("questions", exam), ("answers", answers), ("coverage", coverage)]:
        (destination / (filename + ".md")).write_text(doc_markdown(document), encoding="utf-8")
        (destination / (filename + ".html")).write_text(doc_html(bank["title"], document), encoding="utf-8")
    dump(destination / "validation.json", report)
    dump(destination / "project.snapshot.json", project)
    dump(destination / "bank.snapshot.json", bank)
    if reviews_path and stage == "final":
        dump(destination / "reviews.snapshot.json", load(reviews_path))
    return report


def initialize(workspace, demo=False):
    require(not workspace.exists(), "工作目录已存在；请选择新目录，避免覆盖资料")
    workspace.mkdir(parents=True)
    if demo:
        for filename in ("project.json", "lecture.md", "bank.json"):
            shutil.copyfile(ROOT / "assets" / "demo" / filename, workspace / filename)
        project_path = workspace / "project.json"
        index_path = workspace / "output/mock-exams/demo/source-index.json"
        build_index(project_path, "DEMO", index_path)
        bank = load(workspace / "bank.json")
        bank["source_index_sha256"] = digest(index_path)
        bank_path = workspace / "output/mock-exams/demo/bank.json"
        dump(bank_path, bank)
        (workspace / "bank.json").unlink()
        blind(project_path, index_path, bank_path, workspace / "output/mock-exams/demo/blind")
        render(project_path, index_path, bank_path, workspace / "output/mock-exams/demo/export")
    else:
        shutil.copyfile(ROOT / "assets/project.template.json", workspace / "project.json")
        (workspace / "materials").mkdir()
    return {"workspace": str(workspace), "demo": demo}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "demo"):
        p = commands.add_parser(name)
        p.add_argument("--workspace", required=True)
    p = commands.add_parser("index")
    p.add_argument("--project", required=True)
    p.add_argument("--unit", required=True)
    p.add_argument("--out", required=True)
    p = commands.add_parser("bridge")
    p.add_argument("--project", required=True)
    p.add_argument("--unit", required=True)
    p.add_argument("--out", required=True)
    for name in ("validate", "blind", "render"):
        p = commands.add_parser(name)
        p.add_argument("--project", required=True)
        p.add_argument("--index", required=True)
        p.add_argument("--bank", required=True)
        if name != "blind":
            p.add_argument("--stage", choices=("draft", "final"), default="draft")
            p.add_argument("--reviews")
            p.add_argument("--history", action="append", default=[])
        if name in {"blind", "render"}:
            p.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        if args.command in {"init", "demo"}:
            result = initialize(Path(args.workspace).resolve(), args.command == "demo")
        elif args.command == "index":
            out = output_path(args.project, args.out)
            index = build_index(args.project, args.unit, out)
            result = {"index": str(out), "sha256": digest(out), "blocks": len(index["blocks"]), "warnings": index["warnings"]}
        elif args.command == "bridge":
            out = output_path(args.project, args.out)
            bridge = bridge_template(args.project, args.unit, out)
            result = {"bridge": str(out), "sha256": digest(out), "modules": bridge["modules"]}
        elif args.command == "validate":
            result = validate(args.project, args.index, args.bank, args.reviews, args.stage == "final", args.history)
        elif args.command == "blind":
            out = output_path(args.project, args.out)
            blind(args.project, args.index, args.bank, out)
            result = {"blind_directory": str(out)}
        else:
            out = output_path(args.project, args.out)
            result = render(args.project, args.index, args.bank, out, args.stage, args.reviews, args.history)
            result["output_directory"] = str(out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok", True) else 1
    except (Invalid, OSError, ValueError, KeyError, TypeError, AttributeError, ET.ParseError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
