# 西综 Skills Collection

这是一个面向西医综合复习的技能集合仓库，按题型拆分为多个独立 skill，并提供总调度与病例工作流能力。

## 包含的 Skill

- `西综总调度-Skill`
  - 上游调度器，负责识别题型、分发到对应 skill。
- `西综A1概念簇-Skill`
  - 面向 A1 / 部分 A2 单题的概念簇生成。
- `西综A2病例摘要-Skill`
  - 面向 A2 病例摘要单选题的病例摘要概念簇生成。
- `西综B型配伍-Skill`
  - 面向 B 型配伍题的配对概念簇生成。
- `西综X型多选-Skill`
  - 面向 X 型多选题的逐项分析与错因预警。
- `西综病例-Skill`
  - 面向病例分析题组的临床工作流生成器。

## 共享文件

- `医学准确性规范.md`
  - 多个 skill 共同遵循的医学准确性与防幻觉要求。
- `mistakes_database.yaml`
  - 通用错误模式库。

## 发布说明

- 公开仓库默认不包含 `examples/*.md`。
  - 这些示例文件可能含有真题题干、教材原文或派生内容。
- `西综病例-Skill` 目录中的辅助脚本已保留，但默认排除了本地一次性脚本 `tools/workflow_creator.py`。
- 如果你只想公开规则与结构，这套默认忽略规则是更稳妥的。

## 建议仓库名

- `xizong-skills`

## 目录结构

```text
Skills/
├── README.md
├── 医学准确性规范.md
├── mistakes_database.yaml
├── 西综总调度-Skill/
├── 西综A1概念簇-Skill/
├── 西综A2病例摘要-Skill/
├── 西综B型配伍-Skill/
├── 西综X型多选-Skill/
└── 西综病例-Skill/
```
