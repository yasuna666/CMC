"""Versioned, design-only adapters for the six upstream modules."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

MODULE_FILES = {
    "dispatcher": "西综总调度-Skill",
    "a1_concept": "西综A1概念簇-Skill",
    "a2_case_summary": "西综A2病例摘要-Skill",
    "case_workflow": "西综病例-Skill",
    "b_matching": "西综B型配伍-Skill",
    "x_multi": "西综X型多选-Skill",
}
TYPE_MODULE = {"A1": "a1_concept", "A2": "a2_case_summary", "A3A4": "case_workflow", "B": "b_matching", "X": "x_multi"}
PAYLOAD_FIELDS = {
    "dispatcher": ("scope", "task_mode", "target_modules"),
    "a1_concept": ("core_statement", "conditions", "contrasts", "error_patterns"),
    "a2_case_summary": ("clues", "reasoning_chain", "differential_matrix"),
    "case_workflow": ("nodes", "edges"),
    "b_matching": ("option_definitions", "matching_matrix", "reuse_allowed"),
    "x_multi": ("propositions", "qualifiers", "error_patterns"),
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须为对象：{path}")
    return value


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, empty=False):
    return isinstance(value, list) and (empty or bool(value)) and all(text(x) for x in value) and len(value) == len(set(value))


def path_from(base, raw):
    if not text(raw):
        raise ValueError("文件路径为空")
    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else (Path(base) / path).resolve()


def builtin_path(module):
    return f"references/upstream/{MODULE_FILES[module]}/SKILL.md"


def build_bridge(root, unit, reuse_mode="rules_only"):
    if reuse_mode not in {"rules_only", "artifact_reuse"}:
        raise ValueError("reuse_mode 必须为 rules_only/artifact_reuse")
    return {
        "schema_version": 2, "unit_id": unit["id"], "unit_title": unit["title"],
        "policy": "design_only", "reuse_mode": reuse_mode,
        "modules": list(MODULE_FILES), "question_type_map": TYPE_MODULE,
        "routing_refs": ["rules-dispatcher"],
        "artifacts": [{"id": f"rules-{module}", "module": module, "kind": "module_rules",
                       "role": "built_in_reference", "source_ref": builtin_path(module),
                       "sha256": sha256(Path(root) / builtin_path(module))} for module in MODULE_FILES],
    }


def validate_payload(module, payload, check, label):
    if not isinstance(payload, dict):
        check(False, f"{label} payload 必须为对象")
        return
    for key in PAYLOAD_FIELDS[module]:
        check(key in payload, f"{label} 缺少设计字段 {key}")
    if module == "dispatcher":
        check(text(payload.get("scope")), f"{label} scope 为空")
        check(payload.get("task_mode") in {"study", "generate", "remediate"}, f"{label} task_mode 无效")
        targets = payload.get("target_modules")
        check(strings(targets) and set(targets) <= set(TYPE_MODULE.values()), f"{label} target_modules 无效")
    elif module == "a1_concept":
        check(text(payload.get("core_statement")), f"{label} core_statement 为空")
        for key in ("conditions", "contrasts", "error_patterns"):
            check(strings(payload.get(key)), f"{label} {key} 需要非空文本数组；无对比时明确写孤立概念及原因")
    elif module == "a2_case_summary":
        for key in PAYLOAD_FIELDS[module]:
            check(strings(payload.get(key)), f"{label} {key} 需要非空文本数组")
    elif module == "b_matching":
        for key in ("option_definitions", "matching_matrix"):
            check(strings(payload.get(key)), f"{label} {key} 需要非空文本数组")
        check(type(payload.get("reuse_allowed")) is bool, f"{label} reuse_allowed 必须为布尔值")
    elif module == "x_multi":
        for key in PAYLOAD_FIELDS[module]:
            check(strings(payload.get(key)), f"{label} {key} 需要非空文本数组")
    elif module == "case_workflow":
        nodes, edges = payload.get("nodes"), payload.get("edges")
        if not isinstance(nodes, list) or not nodes or not all(isinstance(n, dict) for n in nodes):
            check(False, f"{label} nodes 需要节点对象数组")
            return
        ids = [n.get("id") for n in nodes]
        if not strings(ids):
            check(False, f"{label} 决策节点 ID 为空或重复")
            return
        for node in nodes:
            check(text(node.get("condition")) and text(node.get("action")), f"{label} 节点需 condition/action")
        if not isinstance(edges, list) or not all(isinstance(e, dict) for e in edges):
            check(False, f"{label} edges 需要关系对象数组（独立节点可为空）")
            return
        for edge in edges:
            check(edge.get("from") in ids and edge.get("to") in ids and edge.get("from") != edge.get("to") and text(edge.get("relation")), f"{label} 决策链边无效")


def validate_bridge(project_path, bank_path, project, bank, root, check):
    """Return resolved artifacts, with parsed items, only for this validation call."""
    cfg = project.get("upstream_integration", {})
    integration = bank.get("integration", {})
    check(isinstance(integration, dict), "题库 integration 必须为对象")
    if not isinstance(integration, dict):
        return {}, "rules_only"
    mode = cfg.get("reuse_mode", "rules_only")
    check(mode in {"rules_only", "artifact_reuse"}, "配置 reuse_mode 无效")
    check(cfg.get("policy") == integration.get("policy") == "design_only", "桥接仅允许 design_only")
    check(strings(cfg.get("modules")) and set(cfg["modules"]) == set(MODULE_FILES), "配置必须登记全部六模块且不重复")
    try:
        bridge_path = path_from(Path(bank_path).resolve().parent, cfg.get("bridge_path", "upstream-bridge.json"))
        bridge = read_json(bridge_path)
        check(bridge.get("schema_version") == 2, "桥接需 schema_version=2；请重新 bridge 并按迁移说明登记产物")
        check(bridge.get("unit_id") == bank.get("unit_id"), "桥接单元不一致")
        check(bridge.get("policy") == "design_only", "桥接 policy 无效")
        check(bridge.get("reuse_mode") == integration.get("reuse_mode") == mode, "配置、桥接、题库 reuse_mode 不一致")
        check(strings(bridge.get("modules")) and set(bridge["modules"]) == set(MODULE_FILES), "桥接必须登记全部六模块且不重复")
        check(bridge.get("question_type_map") == TYPE_MODULE, "桥接 question_type_map 与标准路由不一致")
        check(integration.get("bridge_sha256") == sha256(bridge_path), "桥接清单已改变，旧题库/审核绑定失效")
        raw = bridge.get("artifacts")
        if not isinstance(raw, list) or not all(isinstance(a, dict) for a in raw):
            check(False, "artifacts 必须为对象数组")
            return {}, mode
        ids = [a.get("id") for a in raw]
        if not strings(ids):
            check(False, "artifact ID 必须非空且唯一")
            return {}, mode
        artifacts = {a["id"]: dict(a) for a in raw}
        points = {p["id"]: p for p in bank.get("points", [])}
        base = Path(project_path).resolve().parent
        for aid, artifact in artifacts.items():
            module = artifact.get("module")
            if module not in MODULE_FILES:
                check(False, f"{aid} module 无效")
                continue
            check(text(artifact.get("kind")), f"{aid} kind 为空")
            role = artifact.get("role")
            if role == "built_in_reference":
                check(artifact.get("kind") == "module_rules", f"{aid} 内置规则 kind 必须为 module_rules")
                check(artifact.get("source_ref") == builtin_path(module), f"{aid} source_ref 不是该模块的内置规则")
                p = Path(root) / builtin_path(module)
                check(p.is_file() and artifact.get("sha256") == sha256(p), f"{aid} 内置规则哈希不匹配")
            elif role == "module_output":
                p = path_from(base, artifact.get("path"))
                check(p.is_file(), f"{aid} 产物文件不存在")
                if not p.is_file():
                    continue
                check(artifact.get("sha256") == sha256(p), f"{aid} 产物缺少哈希或文件已改变")
                output = read_json(p)
                check(output.get("schema_version") == 1 and output.get("module") == module, f"{aid} 产物版本/模块不一致")
                origins = output.get("origins")
                if not isinstance(origins, list) or not origins or not all(isinstance(o, dict) for o in origins):
                    check(False, f"{aid} 缺少实际输入 origins")
                else:
                    for origin in origins:
                        op = path_from(base, origin.get("path"))
                        check(op.is_file() and origin.get("sha256") == sha256(op), f"{aid} 原始输入缺失、缺少哈希或已改变")
                        check(text(origin.get("locator")), f"{aid} 原始输入缺少定位")
                items = output.get("items")
                if not isinstance(items, list) or not items or not all(isinstance(i, dict) for i in items):
                    check(False, f"{aid} 缺少结构化 items")
                    continue
                item_ids = [i.get("id") for i in items]
                if not strings(item_ids):
                    check(False, f"{aid} item ID 为空或重复")
                    continue
                artifact["_items"] = {i["id"]: i for i in items}
                mapping = artifact.get("point_map")
                if not isinstance(mapping, dict) or set(mapping) != set(item_ids):
                    check(False, f"{aid} point_map 必须完整对应 items")
                    mapping = {}
                for item in items:
                    label = f"{aid}/{item['id']}"
                    check(text(item.get("knowledge_id")) and text(item.get("label")), f"{label} 缺少稳定知识 ID 或标签")
                    mapped = mapping.get(item["id"])
                    valid_map = strings(mapped) and all(pid in points for pid in mapped)
                    check(valid_map, f"{label} point_map 含未知考点或为空")
                    if valid_map and module != "dispatcher":
                        for pid in mapped:
                            check(item.get("knowledge_id") in points[pid].get("knowledge_ids", []), f"{label} 与考点 {pid} 的稳定知识 ID 不一致")
                    validate_payload(module, item.get("payload"), check, label)
            else:
                check(False, f"{aid} role 必须为 built_in_reference/module_output")
        routing, refs = bridge.get("routing_refs"), integration.get("dispatcher_refs")
        check(strings(routing) and strings(refs) and set(routing) == set(refs), "routing_refs 与 dispatcher_refs 必须非空且完全对应")
        for rid in routing if isinstance(routing, list) else []:
            check(isinstance(rid, str) and rid in artifacts and artifacts[rid].get("module") == "dispatcher", f"无效总调度引用：{rid}")
            if isinstance(rid, str) and rid in artifacts:
                artifacts[rid]["_routed"] = True
        if mode == "artifact_reuse":
            check(any(isinstance(rid, str) and artifacts.get(rid, {}).get("module") == "dispatcher" and artifacts[rid].get("_items") for rid in refs if isinstance(refs, list)), "实际产物复用必须提供总调度计划产物")
        return artifacts, mode
    except (OSError, ValueError, KeyError, TypeError):
        check(False, "桥接或产物无法读取；请检查 JSON、路径及字段类型")
        return {}, mode


def validate_question_links(q, artifacts, mode, check, profile=None):
    qid = q["id"]
    refs = q.get("upstream_refs")
    if not isinstance(refs, list) or not refs or not all(isinstance(r, dict) for r in refs):
        check(False, f"{qid} upstream_refs 必须为非空对象数组")
        return []
    expected = TYPE_MODULE.get(q.get("type"))
    linked, reused, trace, seen = set(), set(), [], set()
    for ref in refs:
        aid, module = ref.get("artifact_id"), ref.get("module")
        if not isinstance(aid, str) or aid not in artifacts or artifacts[aid].get("module") != module:
            check(False, f"{qid} artifact/module 引用无效")
            continue
        check(aid not in seen, f"{qid} 同一 artifact 请合并 item_ids，不能重复计数")
        seen.add(aid)
        linked.add(module)
        check(text(ref.get("transfer_goal")), f"{qid} 缺少 transfer_goal")
        artifact = artifacts[aid]
        if artifact.get("role") == "module_output":
            item_ids = ref.get("item_ids")
            if not strings(item_ids):
                check(False, f"{qid}/{aid} 必须指定非空唯一 item_ids")
                continue
            items = artifact.get("_items", {})
            mapping = artifact.get("point_map", {})
            for iid in item_ids:
                if iid not in items:
                    check(False, f"{qid}/{aid} 不存在条目 {iid}")
                    continue
                mapped = mapping.get(iid, []) if isinstance(mapping, dict) else []
                check(strings(mapped) and bool(set(q.get("point_ids", [])) & set(mapped)), f"{qid}/{aid}/{iid} 未映射到本题考点")
                if strings(mapped) and (q.get("point_ids") or [None])[0] in mapped:
                    reused.add(module)
                if module == "b_matching" and q.get("type") == "B" and isinstance(items[iid].get("payload"), dict):
                    check(items[iid]["payload"].get("reuse_allowed") == (profile or {}).get("b_reuse_allowed"), f"{qid} B 产物复用规则与 exam_profile 不一致")
                trace.append({"question_id": qid, "artifact_id": aid, "module": module,
                              "item_id": iid, "knowledge_id": items[iid].get("knowledge_id"),
                              "transfer_goal": ref["transfer_goal"] if text(ref.get("transfer_goal")) else ""})
        else:
            check(not ref.get("item_ids"), f"{qid} 内置规则不能伪装为实际条目")
    check(expected in linked, f"{qid} 未引用题型对应模块 {expected}")
    if mode == "artifact_reuse":
        check(expected in reused, f"{qid} 主考点未复用题型对应模块的实际条目")
        targets = set()
        for artifact in artifacts.values():
            if artifact.get("module") == "dispatcher" and artifact.get("_routed"):
                for item in artifact.get("_items", {}).values():
                    payload = item.get("payload")
                    values = payload.get("target_modules", []) if isinstance(payload, dict) else []
                    if strings(values):
                        targets.update(values)
        check(expected in targets, f"{qid} 题型模块未纳入调度计划")
    return trace
