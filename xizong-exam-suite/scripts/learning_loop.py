"""Record actual responses and prepare source-bound remediation; never infer mastery."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from learning_bridge import TYPE_MODULE, path_from, read_json, sha256, strings, text


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    if not text(value):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def attempt_template(bank_path, index_path):
    bank = read_json(bank_path)
    return {
        "schema_version": 1, "unit_id": bank["unit_id"], "bank_sha256": sha256(bank_path),
        "source_index_sha256": sha256(index_path), "attempt_id": "", "learner_id": "",
        "completed_at": "", "record_type": "synthetic_demo" if bank["purpose"] == "synthetic_demo" else "user_attempt",
        "instructions": "仅填写真实作答；null=未作答，[]=提交空答案。不得由标准答案生成用户作答。",
        "responses": [{"question_id": q["id"], "selected": None, "learner_explanation": ""} for q in bank["questions"]],
    }


def assess(bank_path, index_path, attempt_path, reviewed=False):
    bank, attempt = read_json(bank_path), read_json(attempt_path)
    require(attempt.get("schema_version") == 1 and attempt.get("unit_id") == bank["unit_id"], "作答版本或单元不一致")
    require(attempt.get("bank_sha256") == sha256(bank_path) and attempt.get("source_index_sha256") == sha256(index_path), "题库/索引已改变，作答绑定失效")
    require(text(attempt.get("attempt_id")) and text(attempt.get("learner_id")), "需实际 attempt_id 和 learner_id")
    require(timestamp(attempt.get("completed_at")), "completed_at 需带时区的 ISO 时间")
    expected_type = "synthetic_demo" if bank["purpose"] == "synthetic_demo" else "user_attempt"
    require(attempt.get("record_type") == expected_type, "作答 record_type 与题库用途不一致")
    responses = attempt.get("responses")
    require(isinstance(responses, list) and all(isinstance(r, dict) for r in responses), "responses 必须为对象数组")
    ids = [r.get("question_id") for r in responses]
    qmap = {q["id"]: q for q in bank["questions"]}
    require(strings(ids) and set(ids) == set(qmap), "作答需逐题完整对应且不重复；未作答填 null")
    groups = {g["id"]: g for g in bank.get("groups", [])}
    points = {p["id"]: p for p in bank["points"]}
    results, targets = [], []
    for response in responses:
        qid = response["question_id"]
        q = qmap[qid]
        require("selected" in response, f"{qid} 缺少 selected；未作答明确填 null")
        selected = response.get("selected")
        opts = groups[q["group_id"]]["options"] if q["type"] == "B" else q["options"]
        require(selected is None or (strings(selected, empty=True) and set(selected) <= set(opts)), f"{qid} selected 非法")
        require(selected is None or q["type"] == "X" or len(selected) <= 1, f"{qid} 单选不能提交多个选项")
        require(isinstance(response.get("learner_explanation", ""), str), f"{qid} learner_explanation 需为文本")
        diagnosis = response.get("reason_assessment", {"status": "unknown", "reason": "尚未确认错误原因"})
        require(isinstance(diagnosis, dict) and diagnosis.get("status") in {"unknown", "hypothesis", "confirmed"}, f"{qid} 错因状态无效")
        if diagnosis["status"] != "unknown":
            require(text(diagnosis.get("reason")) and text(diagnosis.get("basis")), f"{qid} 错因判断需理由与依据")
        if diagnosis["status"] == "confirmed":
            require(text(diagnosis.get("confirmed_by")) and text(response.get("learner_explanation")), f"{qid} 已确认错因需实际作答解释及确认者，不可仅凭选项推断")
        answered = selected is not None
        correct = set(selected) == set(q["answer"]) if answered else None
        result = {"question_id": qid, "selected": selected, "correct": correct,
                  "observed_outcome": "not_attempted" if not answered else "blank" if not selected else "correct" if correct else "incorrect",
                  "missed_options": sorted(set(q["answer"]) - set(selected)) if answered else [],
                  "extra_options": sorted(set(selected) - set(q["answer"])) if answered else [],
                  "point_ids": q["point_ids"], "reason_assessment": diagnosis,
                  "upstream_refs": q.get("upstream_refs", [])}
        results.append(result)
        if answered and not correct:
            knowledge = sorted({kid for pid in q["point_ids"] for kid in points[pid].get("knowledge_ids", [])})
            modules = sorted({TYPE_MODULE[q["type"]]} | {r["module"] for r in q.get("upstream_refs", [])})
            targets.append({"id": f"REMEDIATE-{len(targets)+1:03d}", "parent_question_ids": [qid],
                            "point_ids": q["point_ids"], "knowledge_ids": knowledge,
                            "modules": modules, "upstream_refs": q.get("upstream_refs", []),
                            "reason_assessment": diagnosis,
                            "status": "ready_for_design" if knowledge and reviewed else "needs_review",
                            "next_action": "先回查对应知识条目与原始依据；确认错因后改变考查条件或推理任务生成变式，重新审核。"})
    correct_count = sum(r["correct"] is True for r in results)
    answered_count = sum(r["correct"] is not None for r in results)
    bindings = {"bank_path": str(Path(bank_path).resolve()), "bank_sha256": sha256(bank_path),
                "source_index_path": str(Path(index_path).resolve()), "source_index_sha256": sha256(index_path),
                "attempt_path": str(Path(attempt_path).resolve()), "attempt_sha256": sha256(attempt_path)}
    common = {"schema_version": 1, "unit_id": bank["unit_id"], "attempt_id": attempt["attempt_id"],
              "record_type": expected_type, "bindings": bindings,
              "grading_status": "reviewed_bank" if reviewed else "provisional_draft",
              "limits": "按所绑定答案比对；不证明医学正确、记录真实性或掌握程度。草稿反馈仅为暂定，不更新真题考频或个人掌握统计。"}
    feedback = {**common, "learner_id": attempt["learner_id"], "responses": results,
                "summary": {"correct": correct_count, "submitted": answered_count, "not_attempted": len(results)-answered_count,
                            "accuracy_on_submitted": correct_count/answered_count if answered_count else None}}
    plan = {**common, "targets": targets,
            "constraints": ["沿用已授权讲义范围；跨单元需用户明确指定材料", "不复制原题或仅换姓名数字", "缺少知识映射先补映射", "未确认错因只列假设", "新题执行完整来源校验与独立复答"],
            "instructions": "将实际使用的目标写入新题 remediation_refs；本文件是再练计划，不是已生成或已审核的新题。"}
    return feedback, plan


def validate_remediation(project_path, bank, check):
    """Bind newly generated variants to an immutable prior attempt and plan."""
    config = bank.get("remediation")
    refs_present = any(q.get("remediation_refs") for q in bank.get("questions", []))
    if config is None:
        check(not refs_present, "remediation_refs 缺少题库 remediation 计划绑定")
        return
    try:
        require(isinstance(config, dict), "remediation 必须为对象")
        plan_path = path_from(Path(project_path).resolve().parent, config.get("plan_path"))
        require(config.get("plan_sha256") == sha256(plan_path), "再练计划已改变")
        plan = read_json(plan_path)
        require(plan.get("schema_version") == 1, "再练计划版本无效")
        require(plan.get("unit_id") == bank.get("unit_id"), "跨单元再练需先在新范围重新规划，不能直接复用旧计划")
        require(plan.get("record_type") == ("synthetic_demo" if bank.get("purpose") == "synthetic_demo" else "user_attempt"), "虚构作答不能用于真实再练")
        bindings = plan["bindings"]
        for key in ("bank", "source_index", "attempt"):
            p = path_from(plan_path.parent, bindings[f"{key}_path"])
            require(bindings.get(f"{key}_sha256") == sha256(p), f"再练来源 {key} 已改变")
        require(plan.get("grading_status") in {"reviewed_bank", "provisional_draft"}, "再练 grading_status 无效")
        if plan["grading_status"] == "reviewed_bank":
            review_path = path_from(plan_path.parent, bindings.get("reviews_path"))
            require(bindings.get("reviews_sha256") == sha256(review_path), "原题复核记录已改变或缺失")
            review = read_json(review_path)
            require(review.get("bank_sha256") == bindings["bank_sha256"] and review.get("source_index_sha256") == bindings["source_index_sha256"], "原题复核版本与计划不一致")
        # Recompute targets from the bound raw responses; reject invented remediation history.
        _, rebuilt = assess(bindings["bank_path"], bindings["source_index_path"], bindings["attempt_path"])
        raw_targets = plan.get("targets")
        require(isinstance(raw_targets, list) and all(isinstance(t, dict) for t in raw_targets), "再练 targets 无效")
        ids = [t.get("id") for t in raw_targets]
        require(strings(ids, empty=True), "再练 target ID 为空或重复")
        expected = {t["id"]: t for t in rebuilt["targets"]}
        targets = {t["id"]: t for t in raw_targets}
        require(set(targets) == set(expected), "再练目标与原始作答不一致")
        for tid, target in targets.items():
            for key in ("parent_question_ids", "point_ids", "knowledge_ids", "modules", "upstream_refs", "reason_assessment"):
                require(target.get(key) == expected[tid][key], f"{tid} {key} 与实际作答不一致")
        points = {p["id"]: p for p in bank.get("points", [])}
        used = set()
        for q in bank.get("questions", []):
            refs = q.get("remediation_refs", [])
            require(isinstance(refs, list) and all(isinstance(r, dict) for r in refs), "remediation_refs 需对象数组")
            seen = set()
            for ref in refs:
                tid = ref.get("target_id")
                require(text(tid) and tid in targets and tid not in seen, "再练目标不存在或重复")
                seen.add(tid)
                require(text(ref.get("variation_note")), "再练题需说明条件或推理任务的实质变化")
                kids = {k for pid in q.get("point_ids", []) for k in points.get(pid, {}).get("knowledge_ids", [])}
                require(bool(kids & set(targets[tid]["knowledge_ids"])), "再练题与目标知识点不一致；先补稳定知识映射")
                used.add(tid)
        require(bool(used), "已绑定再练计划但没有题目使用目标")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        check(False, f"再练绑定无效：{exc}")
