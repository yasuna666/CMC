# 六模块薄适配协议

统一入口先决定 study / generate / remediate。study 遵守 integration.md 和原真题 SOP；generate/remediate 只按下表提取设计产物。原 SKILL 是方法参考，不是自动调用的子程序；脚本不替 AI 阅读或命题。

| module | 读取重点 | payload 必填字段 | 用于命题和补学 |
|---|---|---|---|
| dispatcher | 范围、路由、可用知识 | scope（文本）、task_mode（study/generate/remediate）、target_modules（题型模块数组） | 规划任务，按需加载；不强求每题调用六模块 |
| a1_concept | 核心概念、对比、干扰预警 | core_statement（文本）、conditions、contrasts、error_patterns（文本数组） | 构造有条件的命题与干扰项；可供其他题型复用 |
| a2_case_summary | 线索、诊断思路、鉴别矩阵 | clues、reasoning_chain、differential_matrix（文本数组） | 提取线索，形成单一应用任务，定位鉴别错误 |
| case_workflow | 决策链、前提、多题关系 | nodes（id/condition/action 对象数组）、edges（from/to/relation 对象数组） | 按节点设计题组，明确时间/因果/独立关系 |
| b_matching | 选项定义、配对矩阵 | option_definitions、matching_matrix（文本数组）、reuse_allowed（布尔） | 以整组设计，保持定义、鉴别维度及复用规则一致 |
| x_multi | 限定词、逐项判断、错误模式 | propositions、qualifiers、error_patterns（文本数组） | 每项独立核对；漏选/多选不能直接当作已确认错因 |

文本数组非空，无对比时明确写“孤立概念”及原因。病例节点 ID 唯一，边必须引用实际节点；独立节点可使用空 edges。B 的复用规则须符合本轮 exam_profile。结构检查不证明推理和医学内容正确。

## 交接步骤

1. 查找已有稳定 knowledge_id，有则沿用，无则按科目/主题创建，记录别名，避免同义重复。不用本轮题号作知识 ID。
2. 提取最小可复用条目，保留条件、鉴别维度与定位，不复制整个长篇概念簇到每道题。
3. 保存 JSON，origins 登记真实原文件路径、哈希、定位。跨题型共用知识 ID，不生成独立的同义知识库。
4. 总调度给出 scope、task_mode、target_modules；bank.blueprint 分配题目，point_map 对应条目与本轮考点。
5. 模块提供设计材料，AI 再写题干和选项。每项 evidence 独立绑定讲义/教材；历史比例、固定题号、示例答案及 verified 标记不继承为本次事实。

## 再练与隔离

读取 learning-loop.md 和真实计划，按 parent_question_ids、knowledge_ids、upstream_refs.item_ids 回到具体条目。错因分未知/假设/已确认；仅确认后才能写“用户混淆某概念”。否则采用一般诊断练习。

变式改变有依据的条件、鉴别线索、配对维度或推理任务，填写 variation_note；不只改姓名数字。原模块的真题呈现、年度报告、考频累加及原 .progress.yaml 不在 generate/remediate 分支执行。反馈通过知识 ID 回链概念卡，不自动改写原知识结论或统计。
