# 作答反馈与定向再练

## 收集真实作答

用 attempt-template 从已校验题库生成空模板。填入实际 attempt_id、learner_id、带时区的 completed_at（ISO 8601）及逐题 responses。题库与索引哈希自动绑定。

- selected=null：未作答；selected=[]：明确提交空答案。单选最多一个字母，X 可提交任意合法选项集合。
- learner_explanation：用户真实说明，可为空；不得代写冒充。
- reason_assessment 省略时默认 unknown；hypothesis 需 reason/basis；confirmed 还需 confirmed_by 及真实 learner_explanation。程序不能验证身份，执行者必须实际询问或查阅作答解释。
- 作答记录只能来自真实用户作答，不得用预设答案生成记录。

## 比对与计划

feedback 按选项集合完全匹配，生成 feedback.json 与 remediation-plan.json。统计是本次提交正确率，不是官方分数或掌握率。

提供有效 --reviews 时先执行 final 校验；否则标记 provisional_draft，需先回查原题。即使答案已复核，错因也不能仅凭选项确认。

计划为已提交但未答对的题创建目标，包含原题、知识 ID、模块条目和错因状态。null 不制造错题；提交空答案记 blank。缺少稳定知识映射或原题未复核时标记 needs_review。

不更新原 .progress.yaml、真题考频、mistakes_database 或个人掌握统计。重复处理同一记录不算多个学习事件；后续汇总必须按 attempt_id 和题库哈希去重。

## 生成下一轮

1. 回查原题与来源；草稿原题有错时先修正，再重新绑定和评价作答，不将错误答案当补学目标。
2. 按模块适配协议补学，保留错因等级，从讲义范围内设计新条件或推理任务。脚本只生成计划，AI 负责新题。
3. 新建运行目录、题库与复核。bank 顶层填 remediation：plan_path（相对 project.json 的实际计划路径）、plan_sha256（实际哈希）。
4. 相关新题填写 remediation_refs，例如 `[{"target_id":"REMEDIATE-001","variation_note":"说明实际改变的条件或推理任务"}]`；普通题可不带。
5. 沿用知识 ID，不硬套旧 point_id。校验验证知识交集、计划与原题/索引/作答哈希，并从原始作答重新计算目标，拒绝凭空添加错题。原始文件变化则重新规划。
6. 同单元可跨轮再练；跨单元需先按用户授权材料重做范围规划。新题仍须来源核对、独立复答和导出。

盲答包和学生试卷不含 upstream_refs、错因或再练计划，避免泄露设计意图及答案。
