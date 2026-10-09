# 配置与数据约定

## project.json

以 assets/project.template.json 为起点。Python 新工具读取 JSON，不依赖 PyYAML；原真题模块仍用原 project.yaml。相对来源路径基于 project.json 所在目录。

- schema_version: 1；mode: unit_practice；scope_policy: lecture_only。
- purpose: practice，只有自编工程测试才设 synthetic_demo。
- target_year、official_alignment_verified：记录实际情况。本版发布单元练习，不直接生成宣称符合官方计分的整卷。
- exam_profile：option_count、x_min_correct、x_max_correct、x_scoring=exact_set、b_reuse_allowed。
- sources：id/title/role/path/version/extraction/ocr_reviewed。role 为 lecture/syllabus/style/reference。extraction 为 native 或 ocr。
- units：id/title/materials/request。materials 每条 source_id 加 pages 和 sections；空数组表示全部。pages 是物理页白名单；Markdown 可用 `<!-- page: 12 -->`。sections 匹配 Markdown 标题路径，PDF 标题识别不可靠时使用 pages 或先转 Markdown。页面与章节同时指定时取交集。
- request：total_questions、type_counts、difficulty_counts。type_counts 非空时未列出的类型按 0 题；difficulty_counts 可为空。所有题数按计分小题计算。
- upstream_integration：新项目可启用六模块桥接。固定 `policy=design_only`，登记 `dispatcher`、`a1_concept`、`a2_case_summary`、`case_workflow`、`b_matching`、`x_multi` 六个模块；桥接清单路径默认是每轮输出目录中的 `upstream-bridge.json`。

## source-index.json

由 index 命令生成，不手改：包含 project_sha256、unit_id、sources（文件哈希）、blocks（id、source_id、page、section、locator、text）。题库必须引用这个索引中真实存在的块。资料变更须重建索引与复核。

## bank.json

以 assets/bank.template.json 开始，示例结构见 assets/demo/bank.json。空模板不能通过校验；需要 AI 根据真实讲义填写。

顶层：schema_version=1、unit_id、title、source_type=generated_mock、purpose、source_index_sha256、source_issues、integration、points、blueprint、groups、questions。启用桥接时 integration 至少含 `policy=design_only`、`bridge_sha256` 和 `dispatcher_refs`。

points 每条：id、label、objective、status（ready/hold）、source_blocks（块 ID 列表）、hold_reason。ready 至少一个 lecture 来源；hold 有原因，不能用于出题。

blueprint 每条：question_id、type、point_id（主考点）、cognitive_level，每个小题一条。

groups 每条：id、type（B/A3A4）、stem；B 额外包含 options 对象，如 A/B/C/D。共用题组至少两小题且连续排列。

questions 每条：

| 字段 | 要求 |
|---|---|
| id | MOCK- 开头，仅英文、数字、横线、下划线 |
| type | A1/A2/A3A4/B/X |
| group_id | 组题绑定组，其余 null |
| stem | 完整题干；组题可含局部新增信息 |
| options | A/B/C/D 等连续字母键；B 小题为空对象，引用组内选项 |
| answer | 正确选项字母数组 |
| point_ids | 第一个为主考点，其余为次考点 |
| upstream_refs | 启用桥接时至少一条；每条含 artifact_id、module、transfer_goal，且必须包含题型对应模块 |
| cognitive_level | memory/understanding/application/integration |
| difficulty | level（easy/medium/hard）和 reason，不是实测难度 |
| high_risk | 必须显式 true/false，不可遗漏 |
| explanation | 完整推导；不能只有答案复述 |
| originality_note | 原创或变式的说明 |
| evidence | 每条 block_id、quote（必须是该块内的真实短摘录） |
| option_analysis | 每项含 correct 布尔、reason、source_blocks；依据必须属于本题 evidence |

仅结构字段合法还不够；自然语言依据与答案是否成立，必须实际审题。引用片段尽量短，覆盖判定所需条件；整段摘录仅在工程样例中为了演示字段。

## reviews.json

blind 命令生成 reviews.template.json，需真实审题后另存 reviews.json。不要让自动填默认通过。

顶层：schema_version、unit_id、bank_sha256、source_index_sha256、reviewer_mode、reviewer、acknowledged_warnings、checks。

reviewer_mode 为 independent_ai/human/self_review；只有前两种可用于 final。reviewer 填实际复答者或上下文标识。checks 按 question_id 一一对应：verdict、source_status、item_status、medical_status、medical_reference_blocks、blind_answer、blind_reason、notes。具体通过条件见 quality-review.md。

acknowledged_warnings 为“警告 code: 实际接受理由”的对象。错误不能用该字段绕过。题库变化不能只换哈希沿用旧结论。

## 版本与路径

默认每轮创建 output/mock-exams/下的新运行目录。所有脚本拒绝覆盖已有文件/导出目录；修改后使用 r02、r03 等新目录。哈希以 UTF-8 文件实际字节计算，格式化 JSON 也会让复核失效，这是有意设计。

校验器不判断模型是否真做过医学核对，也不能证明复答人未看到答案；这些必须由工作流程和真实执行记录保证。
