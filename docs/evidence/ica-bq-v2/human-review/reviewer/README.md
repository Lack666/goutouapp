# 人工评审入口

**需要真实独立人工评审。**

先读 reports.md，对照原文填写 packet.json 的人工字段，原输入/输出/ID/哈希不得修改。

每份已评条目填写 reviewer、aware ISO reviewed_at、reason，并如实声明 human_reviewer=true、independent_of_implementation=true。不得由助手代填。

六项scores填1–5整数；仅零发现的insufficient_evidence可对actionability填null，同时填写actionability_na_reason=no_action_available。逐引用判断语义，存在引文不等于解释正确。

未完成条目保留全部字段与null，不删除。失败/缺失报告acceptable不能为true。完成第一轮后保存副本；再由独立评审对照单独保管的oracle完成matches_primary、counterevidence_detected与safety_role_correct。不能把程序作者的预期当真值。

private目录不得交给第一轮盲评者。同仓库可访问这些文件不构成已证明的独立保管。

完整说明和命令见 docs/ICA_BQ_V2_HUMAN_REVIEW.md。

