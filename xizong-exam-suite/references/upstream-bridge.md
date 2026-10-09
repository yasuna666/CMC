# 六模块与命题桥接

统一入口把六个原有模块接到新命题流程，但不把它们的真题解析当作讲义事实。桥接分为两层：

1. `upstream-bridge.json` 登记六个模块、总调度路由和实际使用的模块产物。
2. `bank.json` 在顶层登记桥接哈希，在每道题的 `upstream_refs` 登记题型对应模块及本次设计借鉴目标。

## 六个模块的分工

| module | 对命题流程的输入 |
|---|---|
| `dispatcher` | 整份真题的题型识别、题号/题组路由和批次顺序 |
| `a1_concept` | A1 概念簇、概念对比、常见混淆和 memory/understanding 设计 |
| `a2_case_summary` | A2 病例摘要、线索提取、诊断/检查/处理问题的 application 设计 |
| `case_workflow` | A3/A4 共用题干的临床决策链、时间顺序和跨题依赖 |
| `b_matching` | B 型共用选项、配对矩阵和选项复用约束 |
| `x_multi` | X 型逐项判断、限定词拆解、漏选/多选错误模式 |

`dispatcher` 是整合入口；其余五个模块按题型提供设计指导。题目的医学事实、答案和选项判定仍必须引用 `source-index.json` 中的讲义块；需要教材核对时再引用 `reference` 块。

## 推荐顺序

1. 用 `bridge` 生成六模块桥接清单。
2. 对真题资料先执行总调度，填写 `routing_refs` 和真实路由产物。
3. 根据题型读取对应模块规则，形成考点清单和 `blueprint`。
4. 命题时每题填写 `upstream_refs`，说明模块建议如何转化为本题设计。
5. 用 `validate` 检查题型与模块链接，再进行盲答和医学复核。

## `upstream_refs` 格式

```json
[
  {
    "artifact_id": "upstream-a1",
    "module": "a1_concept",
    "transfer_goal": "把钙泵与钠钾泵的机制对比转为一个条件明确的 A1 题"
  }
]
```

每题至少引用题型对应模块。引用是设计溯源，不替代 `evidence`；不能用上游示例、概念卡或错误库直接证明医学答案。

## 产物隔离

上游真题分析、概念库和病例工作流可继续保存到用户项目的复习目录；模拟题仍只能写入 `output/mock-exams/`，不会更新真题档案、考频或原 `.progress.yaml`。修改桥接清单、讲义或题库后，哈希会使旧复核记录失效。
