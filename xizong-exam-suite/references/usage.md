# 使用说明

## 安装与调用

解压得到 xizong-exam-suite 文件夹，保持内部结构完整。将整个文件夹放入所用 AI 工具配置的技能目录，或明确让助手读取该文件夹的 SKILL.md。宿主需要读取本地文件；执行辅助工具还需要 Python 3.10+ 与本地命令能力。具体安装目录按该工具设置确定。

不要只复制根 SKILL.md，也不要把 references/upstream 中六个目录重复安装后期待自动串联。根入口会按需读取七个分支。

可以对助手说：

> 请使用 xizong-exam-suite。我上传的是生理学第二单元讲义。只依据这份讲义出 10 道题，A1 6 道、X 4 道，附逐项解析和出处。先列考点及出题分配，再完成命题和审核；无法独立复核就明确交付待审草稿。

命题用的讲义保存在你自己的学习项目内，后续可不断增加单元；不用改 Skill 正文。

## 建立真实单元

```bash
python3 scripts/exam_tool.py init --workspace ../my-xizong
```

将讲义放入 ../my-xizong/materials/，修改生成的 project.json：单元名、实际文件名、题型数量和 `mode`。可用四种模式：`unit_practice` 单元练习、`study_guide` 单元讲义、`review_book` 复习全书、`practice_only` 纯练习。PDF 可填写 pages，避免读取整本书；Markdown 可填写 sections。DOCX 没有稳定物理页，按段落定位，图片/表格需要另行核对。

以下命令仍从 Skill 目录执行，运行 r01。所有 --out 相对路径基于 project.json 的目录；--project/--index/--bank/--reviews/--history 相对路径基于当前命令目录。

先为本轮建立六模块桥接清单：

```bash
python3 scripts/exam_tool.py bridge --project ../my-xizong/project.json --unit U001 --out output/mock-exams/r01/upstream-bridge.json
```

桥接清单预置六个原模块的规则引用，schema_version=2。默认 rules_only；有实际学习产物时按 upstream-bridge.md 切换 artifact_reuse，登记产物路径、版本、定位、条目和知识映射。处理真实真题时，再把总调度产出的路由记录和实际模块产物追加到清单。每道题在 `upstream_refs` 中填写对应模块和 `transfer_goal`。桥接只约束设计来源，题目答案仍需引用讲义/教材索引块。

```bash
python3 scripts/exam_tool.py index --project ../my-xizong/project.json --unit U001 --out output/mock-exams/r01/source-index.json
```

AI 读取索引与讲义，填写考点、blueprint、变式题组和题库；以 assets/bank.template.json 为结构，在 `../my-xizong/output/mock-exams/r01/bank.json` 保存真实内容。每个递进式变式题组至少包含 `basic` 和一个更高阶段，并在题目中填写 `variant_set_id`、`transfer_stage`。

```bash
python3 scripts/exam_tool.py validate --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json
python3 scripts/exam_tool.py blind --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --out output/mock-exams/r01/blind
```

只把 blind/blind-packet.json 提供给新的审题上下文或人工，收集真实复答，再填写复核模板，另存 `../my-xizong/output/mock-exams/r01/reviews.json`。修改题目后重新生成盲答包和复核。

```bash
python3 scripts/exam_tool.py doctor
python3 scripts/exam_tool.py render --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --stage draft --out output/mock-exams/r01/draft
python3 scripts/exam_tool.py render --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --stage final --reviews ../my-xizong/output/mock-exams/r01/reviews.json --out output/mock-exams/r01/reviewed --pdf
```

每次换新输出目录，工具不覆盖旧产物。若有历史模拟题库，validate/render 可重复加 `--history 历史bank.json`。没有提供历史就只能检查同卷重复。

## 输出和依赖

生成文件由 `mode` 决定：单元练习输出 questions、answers、coverage；纯练习只输出 questions 和 coverage；单元讲义输出 study-guide 和 coverage；复习全书输出 review-book 和 coverage。每份文档同时生成 Markdown 和 HTML；追加 `--pdf` 后在 `pdf/` 目录生成 PDF，并保留编译日志。快照用于追溯当次配置和题目，含答案的快照不能作为学生试卷分发。

新工具除 PDF 提取外仅用标准库。PDF 优先用已安装的 pdftotext，其次 pypdf；PDF 导出需要 pandoc、xelatex 和中文字体，不自动联网安装。`quality-check` 会检查 Markdown 结构、表格、公式分隔符、控制字符和学生试卷中的答案泄露。扫描件需可用 OCR/视觉能力，或者先提供经核对的 Markdown；无法读取就如实报告。

校验返回码：0 通过；1 结构/审核校验未通过；2 文件、格式、参数、路径或提取错误。任何失败都不会把题库标记为已审核。

## 原六模块

如需原有概念簇或整卷真题分析，直接向统一入口提出请求。先遵守 integration.md，再按路由读取原文；作者电脑路径、历史年份、固定题数不适用于你的工作目录。

## 作答反馈与再练

以下路径沿用前文 r01。生成空作答模板：

```bash
python3 scripts/exam_tool.py attempt-template --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --out output/mock-exams/r01/attempt.template.json
```

填写实际记录后另存 attempt.json；不要把标准答案填入模板冒充作答。示例格式和错因确认要求见 learning-loop.md。

```bash
python3 scripts/exam_tool.py feedback --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --attempt ../my-xizong/output/mock-exams/r01/attempt.json --out output/mock-exams/r01/feedback-01
```

没有 --reviews 时按草稿答案暂定比对；追加 `--reviews ../my-xizong/output/mock-exams/r01/reviews.json` 才会执行已复核题库门槛。生成 feedback.json 和 remediation-plan.json，后者用于指导 AI 在 r02 命题，不是自动生成的题库。新题通过 remediation_refs 绑定计划目标。
