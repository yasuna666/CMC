# CMC · 西综讲义命题与复习套件

**把真题解析、知识整理、讲义命题和错题再练连接起来的 AI Skill。**

统一入口：[`xizong-exam-suite/SKILL.md`](xizong-exam-suite/SKILL.md)

技能名称：`xizong-exam-suite`

适用对象：希望按单元讲义练习，并持续复用概念簇、病例摘要和临床决策链的西医综合学习者。

你提供讲义、教材或已有学习笔记，AI 按技能流程阅读、整理和命题；配套 Python 工具负责来源索引、结构校验、版本绑定、导出与作答比对。**脚本本身不调用模型 API，也不会单独阅读讲义后自动写题。**

本文放在仓库根目录；文中的相对文件链接需要与完整仓库一起使用。只想快速体验，先看“快速开始”；希望了解每一步如何执行，再看“完整使用教程”。

## 目录

- [能做什么](#能做什么)
- [六个原模块如何协作](#六个原模块如何协作)
- [安装与准备](#安装与准备)
- [快速开始](#快速开始)
- [完整使用教程](#完整使用教程)
- [如何复用已有概念簇和病例工作流](#如何复用已有概念簇和病例工作流)
- [如何记录作答并定向再练](#如何记录作答并定向再练)
- [常用提示词](#常用提示词)
- [文件说明与命令速查](#文件说明与命令速查)
- [常见问题](#常见问题)
- [验证范围与版本迁移](#验证范围与版本迁移)

## 能做什么

| 你的需求 | 套件如何处理 | 主要结果 |
|---|---|---|
| 整理整份真题 | 识别题型，按需路由到原模块 | 真题分类、概念簇或病例工作流 |
| 按讲义进行单元练习 | 提取考点、安排题型，再生成模拟题 | 试题、逐项解析、来源定位、覆盖表 |
| 利用已有复习积累出题 | 引用实际概念对比、鉴别矩阵和决策节点 | 可追溯到知识条目的模拟题 |
| 检查题目质量 | 结构校验、来源回查、独立复答 | 待审草稿或流程复核完成的练习版 |
| 批改自己的作答 | 对照绑定版本的题库进行选项集合比对 | 正误、漏选/多选、待确认错因 |
| 针对薄弱点再练 | 按知识 ID 回到原条目，再设计变式 | 再练计划及 AI 后续生成的新题 |

支持 A1、A2、A3/A4 共用题干题组、B 型配伍和 X 型多选。题数按**计分小题**计算：一组共用材料下有 3 个问题，就计 3 题。

命令行工具当前发布的是 `unit_practice` 单元练习。指定某年仿真卷时，需先实际核对该年的官方要求，不能将默认练习配置直接称为官方卷型。

## 六个原模块如何协作

原模块完整保存在 `xizong-exam-suite/references/upstream/`。统一入口通过外层适配协议读取它们的方法，并把实际学习内容交给命题流程。

| 模块 | 负责什么 | 交给出题流程的内容 |
|---|---|---|
| 西综总调度 | 任务与题型路由 | 本轮范围、任务模式、需要的模块 |
| 西综 A1 概念簇 | 核心概念与易混知识 | 成立条件、概念对比、错误模式 |
| 西综 A2 病例摘要 | 情境应用与鉴别 | 关键线索、推理链、鉴别矩阵 |
| 西综病例工作流 | 多题关联与决策顺序 | 决策节点、前置条件、节点关系 |
| 西综 B 型配伍 | 相似概念的精确配对 | 选项定义、配对矩阵、选项复用规则 |
| 西综 X 型多选 | 逐项判断与条件辨析 | 命题、限定词、漏选和多选模式 |

例如，一道 A2 题可用 A2 模块构造情境，同时引用 A1 的概念对比设计干扰项；一道病例组可按工作流的决策节点安排各小题。只加载本次需要的模块，无需每题运行全部六模块。

协作有两种模式：

| 模式 | 何时使用 | 需要什么 |
|---|---|---|
| `rules_only` | 第一次按讲义出题，暂时没有结构化学习产物 | 模块规则引用与本轮讲义；新项目默认此模式 |
| `artifact_reuse` | 要具体复用概念簇、病例工作流或本轮提炼的条目 | 总调度计划、实际条目、知识映射及文件哈希 |

同一知识使用稳定的 `knowledge_id`，贯穿学习条目、本轮考点和再练目标。`point_id` 是当前题库的考点编号，`item_id` 是某份产物内的条目编号；三者有不同用途。

无论哪种模式，学习条目负责指导设计，**答案和每个选项的判定仍需讲义、教材依据**。

## 安装与准备

### 1. 保留完整目录

解压仓库，找到 `xizong-exam-suite` 文件夹。将整个文件夹放到你所用 AI 工具支持的技能目录；具体目录和启用方式以该工具为准。

如果工具允许直接读取本地文件，也可以把完整文件夹保存在工作区，然后告诉助手：

> 请读取当前工作区中 xizong-exam-suite/SKILL.md，并按其中的流程处理我的西综学习任务。

`SKILL.md` 会按需引用其他文件，因此不能只复制它。原六模块是统一入口的参考资源，不需要重复安装成六个独立技能后再手工切换。

### 2. 确认运行能力

| 项目 | 要求 |
|---|---|
| AI 助手 | 能读取提供的文件；完整工具流程还需本地命令执行能力 |
| Python | 3.10 或更高版本 |
| Markdown / TXT / DOCX | 配套脚本可提取文本；DOCX 图片与表格布局需另行核对 |
| 文本型 PDF | 已安装 `pdftotext` 或 `pypdf` 之一 |
| 扫描 PDF / 图片 | 先通过可用 OCR 或视觉能力识别并核对，再提供可读文本 |

以下命令使用 `python3`；若你的环境使用 `python` 或 `py -3`，替换命令前缀即可。普通流程主要使用 Python 标准库，不需要配置模型 API Key。

只有对话能力、没有文件与命令能力时，可以让 AI 按流程帮助整理或写草稿，但不能声称已完成脚本校验、文件哈希绑定或本地导出。

### 3. 准备自己的资料

优先从一个单元开始，提供：讲义、明确的范围、题型与题数。已有概念簇或病例工作流时一起提供；需要医学核对时提供相应教材/参考资料。

| 资料角色 | 用途 |
|---|---|
| `lecture` | 控制本轮命题范围，至少需要一个 |
| `reference` | 教材或其他参考资料，用于事实核对 |
| `style` | 真题等表达或题型参考，不替代讲义证据 |
| `syllabus` | 指定考试范围的考纲材料 |

## 快速开始

### 方式一：让 AI 带你完成

将讲义和完整技能文件夹交给助手，复制下面的提示词，并替换单元名称和题数：

> 请使用 xizong-exam-suite。根据我提供的生理学第二单元讲义，生成 10 道单元练习：A1 6 道、X 4 道。只使用该单元内容，先列考点和出题分配，再完成命题。请给出每个选项的解释、真实来源定位和考点覆盖表，试题与答案分别保存。没有已有概念库时采用 rules_only；不能完成独立复答时交付待审草稿，不编造审核记录。

你主要负责提供材料、确认学习范围和真实作答；配置、索引与题库 JSON 可以由助手按协议完成。

## 完整使用教程

以下所有命令均从 `xizong-exam-suite` 目录执行。使用 `../my-xizong` 保存你的资料，以 `r01` 表示第一轮练习；数据不放进技能安装目录。

### 第一步：创建学习项目

```bash
python3 scripts/exam_tool.py init --workspace ../my-xizong
```

把讲义保存为 `../my-xizong/materials/lecture.md`，或把实际 PDF/TXT/DOCX 文件放进 `materials/`，然后修改生成的 `project.json`。

至少检查以下内容：

| 配置位置 | 应填写的内容 |
|---|---|
| `project_name` | 你的学习项目名称 |
| `sources[0].title / path / version` | 实际讲义名称、相对项目目录的路径与版本 |
| `units[0].id / title` | 单元 ID 与名称；以下示例沿用 `U001` |
| `units[0].materials` | 本轮使用的来源和页码/章节范围 |
| `units[0].request` | 总题数与题型数量，例如 10 题、A1 6 题、X 4 题 |
| `upstream_integration.reuse_mode` | 起步用 `rules_only`，实际条目复用用 `artifact_reuse` |

保留模板中的其他必要字段。题型数量之和应等于总题数；指定 `type_counts` 后，未列出的题型按 0 题处理。

PDF 的 `pages` 使用物理页码；Markdown 可以使用 `sections` 筛选标题路径。两者都填时取交集，都为空时选择该文件的全部可读内容。OCR 材料须先核对数值、符号等，再标记 `ocr_reviewed=true`。

### 第二步：建立模块桥接和来源索引

```bash
python3 scripts/exam_tool.py bridge --project ../my-xizong/project.json --unit U001 --out output/mock-exams/r01/upstream-bridge.json
python3 scripts/exam_tool.py index --project ../my-xizong/project.json --unit U001 --out output/mock-exams/r01/source-index.json
```

桥接登记模块及其版本；索引记录本轮材料的真实来源块。不要手工修改索引来迎合题目。

路径规则：`--out` 相对 `project.json` 所在目录；其他文件参数如 `--project`、`--bank`、`--index`、`--attempt` 相对当前命令目录。配置中的材料路径也相对项目目录。

### 第三步：让 AI 生成考点、蓝图和题库

这一步由 AI 完成，**没有自动命题 CLI 命令**。可以使用：

> 请读取 project.json、r01 的来源索引和桥接清单，按 assets/bank.template.json 及 references/data-contract.md 生成 bank.json。先建立 ready/hold 考点清单，再按 blueprint 分配每个计分小题。每题填写对应模块引用、答案、逐项解析和真实 evidence。使用实际文件的 SHA-256 完成索引与桥接绑定。资料不足的考点标为 hold，不为凑数编造依据。

将实际完成的题库保存到 `../my-xizong/output/mock-exams/r01/bank.json`。空白题库模板不能通过校验；需要根据真实讲义完整填写。

### 第四步：校验并导出草稿

```bash
python3 scripts/exam_tool.py validate --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json
python3 scripts/exam_tool.py render --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --stage draft --out output/mock-exams/r01/draft
```

有错误时先修正再导出。脚本检查引用、结构和版本，不会仅凭字段齐全就证明医学答案正确。

### 第五步：独立复答与复核版导出

```bash
python3 scripts/exam_tool.py blind --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --out output/mock-exams/r01/blind
```

只把 `blind/blind-packet.json` 交给新的独立上下文或人工审题者，不提供 `bank.json`、预设答案或命题思路。根据真实复答和来源核对结果填写 `reviews.template.json`，另存为 `r01/reviews.json`。

没有独立复答条件时保留草稿。当前上下文的自查不能标记为独立复答；诊断阈值、用药、治疗顺序等高风险题还须有实际参考依据。

```bash
python3 scripts/exam_tool.py render --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --stage final --reviews ../my-xizong/output/mock-exams/r01/reviews.json --out output/mock-exams/r01/reviewed
```

`final` 表示完成本工作流的复核门槛，不是官方试题或权威医学认证。修改题库、来源或桥接后应重新校验及复答，不能只替换审核记录里的哈希。

## 如何复用已有概念簇和病例工作流

准备好实际笔记后，告诉助手：

> 请在 artifact_reuse 模式下，复用我提供的概念簇和病例工作流。按 module-adapters.md 提取最小结构化条目，保留实际 origins 路径、哈希和定位；统一 knowledge_id，并通过 point_map 映射本轮考点。每道题明确引用 item_ids，说明用了哪一项对比、线索或决策节点。可跨模块复用，答案仍需本轮讲义/教材证据。

具体流程如下：

1. 把已有笔记放在学习项目的 `learning/` 等目录，保留原文件。
2. 由 AI 按 [`module-output.template.json`](xizong-exam-suite/assets/module-output.template.json) 和[模块适配协议](xizong-exam-suite/references/module-adapters.md)提取条目。已有 Markdown 不会由脚本自动解析成全部条目。
3. 在产物 `origins` 中登记实际输入文件及哈希；在桥接 `artifacts` 中登记适配 JSON 的路径、哈希和 `point_map`。
4. 将同一知识的稳定 ID 写入 `bank.points[].knowledge_ids`，用 `upstream_refs.item_ids` 指向实际使用的条目。
5. project、bridge、bank.integration 的 `reuse_mode` 都设为 `artifact_reuse`，并登记真实总调度计划。若配置改变，重建索引。
6. 校验、审题后，在 `coverage.html` 中查看逐题模块、产物、条目、知识 ID 与设计转化说明。

没有历史笔记也可以先从本轮讲义提炼真实条目再复用，但应说明这是本轮新建内容。完整结构、哈希绑定和旧版迁移见[桥接协议](xizong-exam-suite/references/upstream-bridge.md)。

## 如何记录作答并定向再练

### 1. 生成空作答模板

```bash
python3 scripts/exam_tool.py attempt-template --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --out output/mock-exams/r01/attempt.template.json
```

填写自己的真实作答，另存为 `r01/attempt.json`。保留模板绑定的题库与索引哈希，补充 `attempt_id`、`learner_id` 和带时区的 `completed_at`，每题保留一条记录。

`selected` 的格式示例（仅说明写法，不代表任何题的答案）：

| 写法 | 含义 |
|---|---|
| `["B"]` | 提交 B |
| `["A", "C"]` | 多选题提交 A、C |
| `[]` | 明确提交空答案，作为已提交但未答对记录 |
| `null` | 尚未作答，不制造错题目标 |

`learner_explanation` 可填写你实际的解题理由。单选题最多提交一个选项；X 型按完整答案集合判断。不要由 AI 从标准答案生成“用户作答”。

### 2. 生成反馈和再练计划

```bash
python3 scripts/exam_tool.py feedback --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --attempt ../my-xizong/output/mock-exams/r01/attempt.json --out output/mock-exams/r01/feedback-01
```

输出 `feedback.json` 和 `remediation-plan.json`。未提供审核记录时标记 `provisional_draft`；若已有有效独立复核，在命令中追加 `--reviews ../my-xizong/output/mock-exams/r01/reviews.json`，通过门槛后按已复核题库反馈。

错因分为 `unknown`、`hypothesis`、`confirmed`。仅凭选错选项不能确认你误解了某个概念；确认需要真实作答解释、判断依据和确认者。提交正确率也不等于个人掌握率。

### 3. 让 AI 设计下一轮变式

> 请读取本轮 remediation-plan.json，先回查原题答案与讲义依据，再按 knowledge_id 和 upstream_refs 回到对应概念或病例节点。保留错因确认等级，对已确认的薄弱点设计实质变式；未知错因先安排诊断性练习。新题仍限定在当前单元，保存为 r02，绑定 remediation_refs 并写清 variation_note，重新完成来源校验与独立复答。

脚本输出的是计划，不是自动生成的新题。若原题为草稿或缺少稳定知识映射，目标会标记 `needs_review`，应先回查或补映射。

新一轮使用新的文件/目录；若题数配置改变，也要重建索引和桥接绑定。需要长期独立回溯多轮配置时，为每轮保存独立项目配置及相应输出，避免覆盖旧配置。旧审核不能直接复用于新题。

模拟练习不会写入真题考频、原 `.progress.yaml` 或自动更新个人掌握统计。再练的具体绑定格式见[学习闭环](xizong-exam-suite/references/learning-loop.md)。

## 常用提示词

### 分析整份真题

> 请使用 xizong-exam-suite，分析我提供的这份西综真题。先识别实际题型与题组，再按总调度路由到对应模块，生成概念簇和病例工作流。题号、题数和年份以材料为准；没有提供的历年真题不要参与考频统计。教材依据无法核对时明确标注。

### 建立概念对比卡

> 请整理这份讲义中容易混淆的概念。使用 A1 概念簇方法，保留定义、成立条件、对比维度和实际来源，并建立可供后续命题复用的稳定知识 ID。错误模式仅作为设计分析，不当作我的真实错因。

### 构建病例决策链并出题

> 请基于我提供的病例材料和讲义构建决策链，明确每个节点的前提、行动和先后关系，再按有依据的节点设计共用题干题组。不要把上一题的选择当作下一题的已知事实；试题和答案分开，记录实际条目引用。

### 练习 B 型或 X 型

> 请根据本单元讲义生成 B 型配伍和 X 型多选练习。B 型先构建选项定义与配对矩阵，X 型逐项标出成立条件和限定词；每个选项都需要实际依据。先按资料可支持的内容给出题数方案，避免为凑数重复考查。

### 处理错题

> 这是我本轮的真实作答和解题理由。请使用学习闭环先比对答案，再区分观察到的选项差异与推测的错因；无法确认的原因保留 unknown 或 hypothesis。按对应知识条目提出补学任务，再设计有实质变化的练习。

## 文件说明与命令速查

### 主要目录

| 路径 | 作用 |
|---|---|
| `README.md` | 本文，面向使用者的介绍和教程 |
| `xizong-exam-suite/SKILL.md` | AI 读取的统一技能入口 |
| `xizong-exam-suite/references/upstream/` | 原六模块及辅助资源 |
| `xizong-exam-suite/references/` | 命题、桥接、适配、审核、反馈协议 |
| `xizong-exam-suite/scripts/exam_tool.py` | 命令行入口 |
| `xizong-exam-suite/scripts/learning_bridge.py` | 实际产物桥接校验 |
| `xizong-exam-suite/scripts/learning_loop.py` | 作答比对和再练目标绑定 |
| `xizong-exam-suite/assets/` | 配置、题库和产物模板 |

### 命令用途

| 命令 | 用途 |
|---|---|
| `init` | 新建学习项目及配置模板 |
| `bridge` | 生成 v2 模块规则桥接清单 |
| `index` | 按本单元选择生成来源索引 |
| `validate` | 校验题库、桥接、来源和可选审核记录 |
| `blind` | 生成不含预设答案的复答包与审核模板 |
| `render` | 导出草稿或通过复核门槛的练习版 |
| `attempt-template` | 生成空作答记录模板 |
| `feedback` | 比对真实作答，生成反馈及再练计划 |

查看具体参数：`python3 scripts/exam_tool.py <命令> --help`，将 `<命令>` 替换为表中的名称。

### 哪些输出给谁看

| 文件 | 用途与阅读者 |
|---|---|
| `questions.md / questions.html` | 学习者作答用试卷 |
| `answers.md / answers.html` | 作答后的答案与逐项解析 |
| `coverage.md / coverage.html` | 考点覆盖、模块条目追踪与审核状态 |
| `validation.json` | 校验结果，便于定位错误 |
| `blind-packet.json` | 独立复答者使用，只给此包，不给预设答案 |
| `bank.json / bank.snapshot.json` | 包含标准答案与设计信息，供作者维护，不作为试卷分发 |
| `feedback.json / remediation-plan.json` | 作答反馈和后续补学、再练设计 |

HTML 可离线打开和通过浏览器打印另存 PDF；工具不自动生成 PDF 文件。

## 常见问题

**为什么运行脚本后没有自动生成医学题？**

脚本负责确定性操作。真实命题需要 AI 阅读你的材料并填写题库，然后执行校验与导出。

**没有概念库，可以使用吗？**

可以。使用默认 `rules_only` 从讲义开始；后续逐步积累结构化条目，再切换实际复用模式。

**文件明明存在，为什么提示找不到？**

先检查路径基准：来源与 `--out` 基于项目目录；其他 CLI 文件参数基于当前目录；桥接默认文件位于 bank.json 同目录。不要照搬原模块作者电脑里的示例路径。

**为什么提示“输出已存在”？**

工具拒绝覆盖已有输出。使用新运行目录或新导出目录，例如 `r02`、`draft-02`，保留旧结果用于追溯。

**为什么只改了 JSON 排版也使审核失效？**

哈希绑定的是文件实际字节。排版变化也会改变哈希；应重新建立相关绑定并复核，不能手改旧审核哈希伪装为已检查。

**桥接报“条目不存在”或“知识 ID 不一致”怎么办？**

检查 artifact 路径和哈希、item_ids、point_map，以及 bank.points 的 knowledge_ids。实际复用模式下，每题主考点须关联其题型模块的真实条目，总调度也要登记该模块。

**扫描 PDF 或复杂表格提取不完整怎么办？**

先 OCR/视觉核对并整理成可读 Markdown。不能用空白页、错位数字或未核对符号继续命题；局部不可靠内容可标记为 hold。

**校验通过是否代表医学正确？**

不代表。仍需来源回查、条件审查和实际独立复答。未完成这些步骤的题目保持待审草稿。

**如何避免跨轮重复题？**

给 `validate` 或 `render` 增加 `--history 历史bank.json`，可重复提供多个历史库。文本相似度仅为提示，语义重复仍需 AI/人工判断。

## 验证范围与版本迁移

工具的校验范围和限制见[验证记录](xizong-exam-suite/references/validation-report.md)。这不等于真实医学材料验收，也不代表特定年度考纲适配；只有实际材料和执行记录才能支持相关结论。

旧版用户注意：`project.json` 和 `bank.json` 的 schema_version 仍为 1，**桥接清单升级为 2**。保留旧运行目录，重新 bridge，迁移真实产物、条目和知识映射；配置变化后重建索引，并重新进行题库与审核绑定。不能只把旧清单版本号改为 2。

## 深入阅读

- [详细命令与使用说明](xizong-exam-suite/references/usage.md)
- [讲义命题流程](xizong-exam-suite/references/lecture-workflow.md)
- [题型规则](xizong-exam-suite/references/question-rules.md)
- [六模块适配协议](xizong-exam-suite/references/module-adapters.md)
- [实际产物桥接与迁移](xizong-exam-suite/references/upstream-bridge.md)
- [作答反馈与学习闭环](xizong-exam-suite/references/learning-loop.md)
- [配置及数据约定](xizong-exam-suite/references/data-contract.md)
- [质量审核规范](xizong-exam-suite/references/quality-review.md)
- [原模块来源与版本](xizong-exam-suite/references/provenance.md)
