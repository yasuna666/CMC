# 六模块实际产物桥接（v2）

## 模式与边界

- `rules_only`：仅借用模块方法；允许无历史概念库。不得宣称已复用学习积累。
- `artifact_reuse`：复用实际结构化条目；每题主考点必须关联其题型模块的真实条目，并提供总调度计划。可附加其他模块，例如 A2 同时借用 A1 对比关系。

project.upstream_integration、bridge、bank.integration 必须有相同的 reuse_mode。新项目默认 rules_only；有产物时主动使用 artifact_reuse。两者固定 policy=design_only；答案仍需本轮讲义/教材 evidence。

## 生成与登记

1. 运行 bridge，生成 schema_version=2 的清单。内置规则路径和版本自动登记。
2. 按 [模块适配协议](module-adapters.md) 提取已有概念簇/病例工作流的相关部分，生成项目内 JSON 产物；没有历史资料时从已授权讲义提炼并注明实际来源。不为出题重跑整份真题 SOP。
3. 追加 artifacts。path 和 origins.path 均相对 project.json 所在目录；内置 source_ref 相对 Skill 根目录。
4. 将稳定知识 ID 写入 bank.points[].knowledge_ids，用 point_map 对应本轮考点。不同题型讨论同一知识时复用相同 knowledge_id，不随轮次或题号变化。
5. bridge.routing_refs 与 bank.integration.dispatcher_refs 必须相同；artifact_reuse 指向真实总调度产物。
6. 填写 bank.integration.bridge_path 和每题 upstream_refs，再校验、盲答、审核。结构校验不能证明已正确理解或采用产物。

## 产物格式

以 assets/module-output.template.json 起步，文件包含 schema_version=1、module、origins、items：

- origins 每项含 path、version、locator，记录实际概念卡、真题分析或讲义输入。原始输入变化后重新确认来源定位。
- items 每项含 id、knowledge_id、label、payload。id 在产物内唯一；knowledge_id 在项目内稳定。
- payload 按模块适配协议填写实际概念对比、推理链等，不能用“已调用模块”代替。
- 总调度的 knowledge_id 是计划 ID，不要求等于医学知识 ID；其 point_map 仍需完整映射本轮考点范围。

清单条目示例：

```json
{
  "id": "a1-pumps", "module": "a1_concept", "kind": "concept_cluster",
  "role": "module_output", "path": "learning/a1-pumps.json",
  "version": "2026-10-16",
  "point_map": {"contrast-001": ["P001"]}
}
```

每题指明实际使用的条目：

```json
{
  "artifact_id": "a1-pumps", "module": "a1_concept",
  "item_ids": ["contrast-001"],
  "transfer_goal": "用此条目的驱动力对比设计干扰项，保留题干成立条件"
}
```

内置规则 role=built_in_reference、kind=module_rules，不带 item_ids，不充当实际复用。同题对同一 artifact 只引用一次，合并多个 item_ids。

## 迁移与报告

project/bank 的 schema_version 仍为 1；bridge 从 1 升到 2。旧清单明确拒绝，不能仅改版本号：保留旧运行目录，新建 r02，确定 reuse_mode 后重新 bridge。内置 ID 采用 rules-dispatcher、rules-a1_concept 等，以新清单为准。重新登记真实文件路径、版本、条目和知识映射；配置改变后重建 index，再绑定新题库并重新盲答，不能沿用旧 reviews 的结论。

coverage.md/html 分开显示模块引用次数与实际条目明细。引用次数不是复习次数、掌握程度或考频。
