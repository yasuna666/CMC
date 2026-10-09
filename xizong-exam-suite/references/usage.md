# 使用说明

## 安装与调用

解压得到 xizong-exam-suite 文件夹，保持内部结构完整。将整个文件夹放入所用 AI 工具配置的技能目录，或明确让助手读取该文件夹的 SKILL.md。宿主需要读取本地文件；执行辅助工具还需要 Python 3.10+ 与本地命令能力。具体安装目录按该工具设置确定。

不要只复制根 SKILL.md，也不要把 references/upstream 中六个目录重复安装后期待自动串联。根入口会按需读取七个分支。

可以对助手说：

> 请使用 xizong-exam-suite。我上传的是生理学第二单元讲义。只依据这份讲义出 10 道题，A1 6 道、X 4 道，附逐项解析和出处。先列考点及出题分配，再完成命题和审核；无法独立复核就明确交付待审草稿。

命题用的讲义保存在你自己的学习项目内，后续可不断增加单元；不用改 Skill 正文。

## 工程演示（无需 API）

下面用相对路径演示，先进入解压后的 xizong-exam-suite 目录。实际医学命题仍需 AI 阅读和写题。

```bash
python3 scripts/exam_tool.py demo --workspace ../xizong-demo
```

这会生成明确虚构的 10 题工程演示，包含全部五类题型。打开 `../xizong-demo/output/mock-exams/demo/export/questions.html` 查看试题；同目录 answers.html 是答案，coverage.html 是覆盖与审核表。也同时生成 Markdown。演示默认是待复核草稿，不能作为真实医学练习。

## 建立真实单元

```bash
python3 scripts/exam_tool.py init --workspace ../my-xizong
```

将讲义放入 ../my-xizong/materials/，修改生成的 project.json：单元名、实际文件名、题型数量。PDF 可填写 pages，避免读取整本书；Markdown 可填写 sections。DOCX 没有稳定物理页，按段落定位，图片/表格需要另行核对。

以下命令仍从 Skill 目录执行，运行 r01。所有 --out 相对路径基于 project.json 的目录；--project/--index/--bank/--reviews/--history 相对路径基于当前命令目录。

先为本轮建立六模块桥接清单：

```bash
python3 scripts/exam_tool.py bridge --project ../my-xizong/project.json --unit U001 --out output/mock-exams/r01/upstream-bridge.json
```

桥接清单预置六个原模块的规则引用。处理真实真题时，再把总调度产出的路由记录和实际模块产物追加到清单；将其 SHA-256 填入题库 `integration.bridge_sha256`。每道题在 `upstream_refs` 中填写对应模块和 `transfer_goal`。桥接只约束设计来源，题目答案仍需引用讲义/教材索引块。

```bash
python3 scripts/exam_tool.py index --project ../my-xizong/project.json --unit U001 --out output/mock-exams/r01/source-index.json
```

AI 读取索引与讲义，填写考点、blueprint 和题库；以 assets/bank.template.json 为结构，在 `../my-xizong/output/mock-exams/r01/bank.json` 保存真实内容，将 index 命令输出的 sha256 填入 source_index_sha256。

```bash
python3 scripts/exam_tool.py validate --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json
python3 scripts/exam_tool.py blind --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --out output/mock-exams/r01/blind
```

只把 blind/blind-packet.json 提供给新的审题上下文或人工，收集真实复答，再填写复核模板，另存 `../my-xizong/output/mock-exams/r01/reviews.json`。修改题目后重新生成盲答包和复核。

```bash
python3 scripts/exam_tool.py render --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --stage draft --out output/mock-exams/r01/draft
python3 scripts/exam_tool.py render --project ../my-xizong/project.json --index ../my-xizong/output/mock-exams/r01/source-index.json --bank ../my-xizong/output/mock-exams/r01/bank.json --stage final --reviews ../my-xizong/output/mock-exams/r01/reviews.json --out output/mock-exams/r01/reviewed
```

每次换新输出目录，工具不覆盖旧产物。若有历史模拟题库，validate/render 可重复加 `--history 历史bank.json`。没有提供历史就只能检查同卷重复。

## 输出和依赖

生成 questions.md/html、answers.md/html、coverage.md/html 和 validation.json，并保存 project.snapshot.json、bank.snapshot.json；复核版另存 reviews.snapshot.json。快照用于追溯当次配置和题目，含答案的题库快照不能作为学生试卷分发。HTML 无网络脚本，可离线查看，用浏览器打印另存 PDF；本工具不自动生成 PDF，也不宣称动态在线阅卷。

新工具除 PDF 提取外仅用标准库。PDF 优先用已安装的 pdftotext，其次 pypdf，不自动联网安装。扫描件需可用 OCR/视觉能力，或者先提供经核对的 Markdown；无法读取就如实报告。

校验返回码：0 通过；1 结构/审核校验未通过；2 文件、格式、参数、路径或提取错误。任何失败都不会把题库标记为已审核。

## 原六模块

如需原有概念簇或整卷真题分析，直接向统一入口提出请求。先遵守 integration.md，再按路由读取原文；作者电脑路径、历史年份、固定题数不适用于你的工作目录。
