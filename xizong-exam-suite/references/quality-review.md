# 审核规范

## 区分四类证据

1. 来源定位：文件、块与摘录真实存在，脚本可检查，不能据此证明医学正确。
2. 资料内一致：实际回查讲义后确认题目与资料一致，记录 lecture_consistent。
3. 医学参考核对：实际阅读教材/参考资料，引用 reference 块，记录 reference_checked；不是临床认证。
4. 独立复答：新上下文或人工只获得题目和资料，不获得预设答案解析，提交答案及依据。

## 逐题检查

来源：范围、页/段落、摘录、OCR、版本、题干与原文一致性。

医学：指标方向、单位、阈值、病理部位、首选/金标准、药物适应证与禁忌、病程及情境合理性。上游示例不能作为教材。

命题：答案唯一/集合完整、选项同层次、干扰项合理、条件完整、否定措辞、答案泄露、病例连续性与配伍关系。

新颖性：同卷及提供的历史库中的重复、仅换姓名/数字、同考点同推理过密。文本相似度仅提示，语义重复仍需判断。

## 盲答交接

`blind` 生成 blind-packet.json 和 reviews.template.json。只给复答人 blind-packet，不给题库、预设结果、想验证的错误或先前结论。完成后再比较。

如实记录 reviewer_mode（independent_ai/human/self_review）、reviewer 和会话/时间标识。self_review 不可冒充盲审，只能交付草稿。脚本检查记录完整性，不能证明身份和审核真实性。

答案分歧或依据不足写 revise/block，回查后修改。修改题库或索引后旧 reviews 哈希失效；不得手改哈希冒充重新审核。

## 已审核版门槛

- 每题 verdict=pass、source_status=consistent、item_status=pass，并给具体 notes。
- blind_answer 与答案集合一致，blind_reason 非空。
- 一般题 medical_status=lecture_consistent 或 reference_checked；high_risk 必须 reference_checked 并引用实际 reference 块和核对说明。
- 医学核对状态必须反映真实讲义或教材/参考资料核对结果。
- 错误清零；相似度/答案分布警告需修改或逐项写接受理由，不能借警告接受绕过硬错误。
- 冲突/模糊考点不可参与已审核题，未覆盖点仍显示。

final 是本工作流“完成复核”的等级，导出仍注明实际复核方式，不使用权威认证或保证正确的描述。
