"""Reproducible synthetic regression tests; fixtures are NOT real review records."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import exam_tool as tool
from learning_bridge import build_bridge
from learning_loop import assess, attempt_template


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ExamToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / "project"
        tool.initialize(self.workspace, demo=True)
        self.project = self.workspace / "project.json"
        self.run = self.workspace / "output/mock-exams/demo"
        self.index = self.run / "source-index.json"
        self.bank = self.run / "bank.json"
        self.bridge = self.run / "upstream-bridge.json"

    def report(self, **kwargs):
        return tool.validate(self.project, self.index, self.bank, **kwargs)

    def bad(self, fragment):
        report = self.report()
        self.assertFalse(report["ok"], report)
        self.assertTrue(any(fragment in e for e in report["errors"]), report["errors"])

    def change_bridge(self, change):
        bridge = tool.load(self.bridge)
        change(bridge)
        write(self.bridge, bridge)
        bank = tool.load(self.bank)
        bank["integration"]["bridge_sha256"] = tool.digest(self.bridge)
        write(self.bank, bank)

    def change_bank(self, change):
        bank = tool.load(self.bank)
        change(bank)
        write(self.bank, bank)

    def actual_artifact(self, bridge):
        return next(a for a in bridge["artifacts"] if a["id"] == "demo-a1_concept")

    def attempt(self):
        attempt = attempt_template(self.bank, self.index)
        attempt.update(attempt_id="TEST-ATTEMPT", learner_id="TEST-FIXTURE", completed_at="2026-10-16T00:00:00-07:00")
        for response, q in zip(attempt["responses"], tool.load(self.bank)["questions"]):
            response["selected"] = q["answer"][:]
        path = self.run / "attempt.json"
        write(path, attempt)
        return path, attempt

    def reviews(self):
        review = tool.load(self.run / "blind/reviews.template.json")
        review.update(reviewer_mode="human", reviewer="TEST FIXTURE ONLY; not a real review",
                      acknowledged_warnings={w["code"]: "TEST FIXTURE" for w in self.report()["warnings"]})
        answers = {q["id"]: q["answer"] for q in tool.load(self.bank)["questions"]}
        for check in review["checks"]:
            check.update(verdict="pass", source_status="consistent", item_status="pass",
                         medical_status="not_applicable_synthetic", blind_answer=answers[check["question_id"]],
                         blind_reason="TEST FIXTURE ONLY", notes="TEST FIXTURE ONLY")
        path = self.run / "reviews.fixture.json"
        write(path, review)
        return path

    def test_demo_uses_real_items_all_modules_and_cross_type(self):
        report = self.report()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["integration"]["reuse_mode"], "artifact_reuse")
        self.assertEqual(report["integration"]["reused_item_count"], 12)
        self.assertEqual(set(report["type_counts"]), tool.TYPES)
        self.assertIn("demo-dispatcher", tool.load(self.bank)["integration"]["dispatcher_refs"])

    def test_rules_only_mode_remains_usable(self):
        project = tool.load(self.project)
        project["upstream_integration"]["reuse_mode"] = "rules_only"
        write(self.project, project)
        write(self.index, tool.index_data(self.project, "DEMO"))
        bridge = build_bridge(ROOT, project["units"][0])
        write(self.bridge, bridge)
        bank = tool.load(self.bank)
        bank["source_index_sha256"] = tool.digest(self.index)
        bank["integration"].update(reuse_mode="rules_only", bridge_sha256=tool.digest(self.bridge), dispatcher_refs=["rules-dispatcher"])
        for q in bank["questions"]:
            module = tool.TYPE_MODULE[q["type"]]
            q["upstream_refs"] = [{"artifact_id": "rules-"+module, "module": module, "transfer_goal": "TEST: rule use only"}]
        write(self.bank, bank)
        self.assertTrue(self.report()["ok"], self.report())
        self.assertEqual(self.report()["integration"]["reused_item_count"], 0)

    def test_nonexistent_routing_ref_rejected(self):
        self.change_bridge(lambda b: b.update(routing_refs=["missing"]))
        self.bad("总调度引用")

    def test_wrong_question_type_map_rejected(self):
        self.change_bridge(lambda b: b["question_type_map"].update(A1="x_multi"))
        self.bad("question_type_map")

    def test_wrong_builtin_path_rejected(self):
        self.change_bridge(lambda b: b["artifacts"][0].update(source_ref="missing.md"))
        self.bad("source_ref")

    def test_missing_artifact_hash_rejected(self):
        self.change_bridge(lambda b: self.actual_artifact(b).pop("sha256"))
        self.bad("缺少哈希")

    def test_modified_artifact_rejected_without_manifest_change(self):
        p = self.workspace / "learning/a1_concept.json"
        p.write_text(p.read_text() + "\n", encoding="utf-8")
        self.bad("文件已改变")

    def test_modified_origin_rejected_even_after_lecture_reindex(self):
        p = self.workspace / "lecture.md"
        p.write_text(p.read_text()+"\n", encoding="utf-8")
        write(self.index, tool.index_data(self.project, "DEMO"))
        self.change_bank(lambda b: b.update(source_index_sha256=tool.digest(self.index)))
        self.bad("原始输入")

    def test_unknown_item_rejected(self):
        self.change_bank(lambda b: b["questions"][0]["upstream_refs"][0].update(item_ids=["missing"]))
        self.bad("不存在条目")

    def test_rules_cannot_claim_actual_reuse(self):
        def change(bank):
            q = bank["questions"][0]
            q["upstream_refs"] = [{"artifact_id": "rules-a1_concept", "module": "a1_concept", "transfer_goal": "TEST"}]
        self.change_bank(change)
        self.bad("主考点未复用")

    def test_point_map_must_match_stable_knowledge(self):
        self.change_bridge(lambda b: self.actual_artifact(b)["point_map"].update({"item-K2": ["K1"]}))
        self.bad("稳定知识 ID 不一致")

    def test_only_selected_dispatcher_counts(self):
        def change(bridge):
            artifact = next(a for a in bridge["artifacts"] if a["id"] == "demo-dispatcher")
            p = self.workspace / artifact["path"]
            out = tool.load(p)
            out["items"][0]["payload"]["target_modules"] = ["x_multi"]
            write(p, out)
            artifact["sha256"] = tool.digest(p)
        self.change_bridge(change)
        self.bad("未纳入调度计划")

    def test_missing_payload_field_rejected(self):
        def change(bridge):
            a = self.actual_artifact(bridge)
            p = self.workspace/a["path"]
            out = tool.load(p); out["items"][0]["payload"].pop("contrasts")
            write(p, out); a["sha256"] = tool.digest(p)
        self.change_bridge(change)
        self.bad("contrasts")

    def test_old_bridge_requires_migration(self):
        self.change_bridge(lambda b: b.update(schema_version=1))
        self.bad("schema_version=2")

    def test_b_reuse_rule_must_match_profile(self):
        def change(bridge):
            a = next(a for a in bridge["artifacts"] if a["id"] == "demo-b_matching")
            p = self.workspace/a["path"]
            out = tool.load(p)
            for item in out["items"]:
                item["payload"]["reuse_allowed"] = False
            write(p, out); a["sha256"] = tool.digest(p)
        self.change_bridge(change)
        self.bad("B 产物复用规则")

    def test_invalid_array_is_reported(self):
        self.change_bridge(lambda b: b.update(artifacts=None))
        self.bad("artifacts")

    def test_student_and_blind_outputs_do_not_leak_design(self):
        packet = tool.load(self.run/"blind/blind-packet.json")
        self.assertNotIn("upstream_refs", json.dumps(packet))
        self.assertNotIn("option_analysis", json.dumps(packet))
        self.assertTrue(all("answer" not in q for q in packet["questions"]))
        exam = (self.run/"export/questions.html").read_text()
        self.assertNotIn("transfer_goal", exam)
        self.assertIn("demo-a1_concept", (self.run/"export/coverage.html").read_text())

    def test_fake_evidence_quote_rejected(self):
        self.change_bank(lambda b: b["questions"][0]["evidence"][0].update(quote="THIS IS NOT IN THE SOURCE"))
        self.bad("摘录不在指定块")

    def test_hold_point_rejected(self):
        self.change_bank(lambda b: b["points"][1].update(status="hold", hold_reason="TEST"))
        self.bad("搁置考点")

    def test_answer_option_disagreement_rejected(self):
        def change(bank):
            q = bank["questions"][0]
            q["option_analysis"][q["answer"][0]]["correct"] = False
        self.change_bank(change)
        self.bad("结论与答案不一致")

    def test_final_requires_independent_review_and_fresh_bank(self):
        self.assertFalse(self.report(final=True)["ok"])
        p = self.reviews()
        self.assertTrue(self.report(reviews_path=p, final=True)["ok"])
        review = tool.load(p); review["reviewer_mode"] = "self_review"; write(p, review)
        self.assertFalse(self.report(reviews_path=p, final=True)["ok"])
        review["reviewer_mode"] = "human"; write(p, review)
        self.change_bank(lambda b: b.update(title="Changed title"))
        self.assertTrue(any("旧复核" in e for e in self.report(reviews_path=p, final=True)["errors"]))

    def test_output_safety_and_overwrite(self):
        with self.assertRaises(ValueError):
            tool.output_path(self.project, "output/年度报告/bad.json")
        with self.assertRaises(FileExistsError):
            tool.dump(self.bank, {})

    def test_attempt_template_is_blank(self):
        attempt = attempt_template(self.bank, self.index)
        self.assertTrue(all(r["selected"] is None for r in attempt["responses"]))
        self.assertEqual(attempt["attempt_id"], "")

    def test_feedback_null_blank_and_x_differences(self):
        path, attempt = self.attempt()
        attempt["responses"][0]["selected"] = None
        attempt["responses"][1]["selected"] = []
        q = tool.load(self.bank)["questions"][-1]
        attempt["responses"][-1]["selected"] = [k for k in q["options"] if k not in q["answer"]]
        write(path, attempt)
        feedback, plan = assess(self.bank, self.index, path)
        self.assertEqual(feedback["summary"], {"correct": 7, "submitted": 9, "not_attempted": 1, "accuracy_on_submitted": 7/9})
        self.assertEqual(len(plan["targets"]), 2)
        self.assertEqual(feedback["grading_status"], "provisional_draft")
        self.assertTrue(all(t["status"] == "needs_review" for t in plan["targets"]))
        self.assertEqual(feedback["responses"][0]["observed_outcome"], "not_attempted")
        self.assertEqual(feedback["responses"][1]["observed_outcome"], "blank")
        self.assertTrue(feedback["responses"][-1]["missed_options"])

    def test_invalid_attempts_rejected(self):
        path, attempt = self.attempt()
        mutations = [lambda a: a.update(bank_sha256="stale"),
                     lambda a: a["responses"].append(a["responses"][0]),
                     lambda a: a["responses"][0].update(selected=["Z"]),
                     lambda a: a["responses"][0].update(selected=["A", "B"]),
                     lambda a: a.update(completed_at="2026-10-16"),
                     lambda a: a.update(record_type="user_attempt")]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(attempt); mutate(changed); write(path, changed)
                with self.assertRaises(ValueError):
                    assess(self.bank, self.index, path)

    def test_confirmed_cause_requires_actual_explanation(self):
        path, attempt = self.attempt()
        attempt["responses"][0]["reason_assessment"] = {"status": "confirmed", "reason": "TEST", "basis": "TEST", "confirmed_by": "TEST"}
        write(path, attempt)
        with self.assertRaisesRegex(ValueError, "实际作答解释"):
            assess(self.bank, self.index, path)

    def test_remediation_bindings_and_stable_ids(self):
        path, attempt = self.attempt(); attempt["responses"][0]["selected"] = []
        write(path, attempt)
        _, plan = assess(self.bank, self.index, path)
        plan_path = self.run/"remediation-plan.json"; write(plan_path, plan)
        old_bank = self.run/"parent-bank.json"; write(old_bank, tool.load(self.bank))
        plan["bindings"]["bank_path"] = str(old_bank); write(plan_path, plan)
        def change(bank):
            bank["remediation"] = {"plan_path": str(plan_path), "plan_sha256": tool.digest(plan_path)}
            bank["questions"][0]["remediation_refs"] = [{"target_id": "REMEDIATE-001", "variation_note": "TEST FIXTURE: variant relation, not a real generated question"}]
        self.change_bank(change)
        self.assertTrue(self.report()["ok"], self.report())
        self.change_bank(lambda b: b["questions"][0]["remediation_refs"][0].update(target_id="invented"))
        self.bad("目标不存在")

    def test_feedback_cli_and_no_unrequested_mutations(self):
        path, attempt = self.attempt()
        before = {p: tool.digest(p) for p in [self.bank, self.index, self.bridge, self.project]}
        command = [sys.executable, "-B", str(ROOT/"scripts/exam_tool.py"), "feedback", "--project", str(self.project), "--index", str(self.index), "--bank", str(self.bank), "--attempt", str(path), "--out", "output/mock-exams/demo/feedback"]
        result = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["grading_status"], "provisional_draft")
        for p, digest in before.items():
            self.assertEqual(tool.digest(p), digest)
        self.assertFalse((self.workspace/".progress.yaml").exists())
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_forged_remediation_target_rejected_even_with_new_plan_hash(self):
        path, attempt = self.attempt()
        attempt["responses"][0]["selected"] = []
        write(path, attempt)
        _, plan = assess(self.bank, self.index, path)
        parent = self.run/"parent-bank.json"; write(parent, tool.load(self.bank))
        plan["bindings"]["bank_path"] = str(parent)
        plan["targets"][0]["parent_question_ids"] = ["MOCK-DEMO-002"]
        plan_path = self.run/"plan.json"; write(plan_path, plan)
        self.change_bank(lambda b: b.update(remediation={"plan_path": str(plan_path), "plan_sha256": tool.digest(plan_path)}))
        self.bad("与实际作答不一致")

    def test_feedback_reviewed_cli_is_bound_to_actual_fixture(self):
        path, attempt = self.attempt()
        reviews = self.reviews()
        result = subprocess.run([sys.executable, "-B", str(ROOT/"scripts/exam_tool.py"), "feedback",
                                 "--project", str(self.project), "--index", str(self.index), "--bank", str(self.bank),
                                 "--attempt", str(path), "--reviews", str(reviews),
                                 "--out", "output/mock-exams/demo/reviewed-feedback"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = tool.load(self.run/"reviewed-feedback/remediation-plan.json")
        self.assertEqual(plan["grading_status"], "reviewed_bank")
        self.assertEqual(plan["bindings"]["reviews_sha256"], tool.digest(reviews))

    def test_upstream_files_byte_identical(self):
        manifest = tool.load(ROOT/"assets/upstream-manifest.json")
        for filename, expected in manifest["files"].items():
            self.assertEqual(tool.digest(ROOT/"references/upstream"/filename), expected, filename)


if __name__ == "__main__":
    unittest.main(verbosity=2)
