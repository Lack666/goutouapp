# ICA-B0/B1 参考复核

日期：2026-11-04；范围：匿名合成案例与 Mock 报告执行工程。

复用 [v4 研究记录](ICA_LONGITUDINAL_ROADMAP_V4.md#3-外部研究结论与采用边界)
和 [ICA 外部审查](ICA_EXTERNAL_REFERENCE_REVIEW.md)。本文件补记本轮具体落点，
不声称又运行了外部仓库，也不把既有论文结果当作本产品质量成绩。

1. **LangGraph Graph API**：采用现有锁定依赖 `langgraph==1.2.12`，不升级、不增加依赖。
   2026-11-04复核[官方 Graph API 文档](https://docs.langchain.com/oss/python/langgraph/graph-api)
   的 State/Nodes/Edges，以及[MIT 许可](https://github.com/langchain-ai/langgraph/blob/main/LICENSE)。
   在线文档无固定发布日期，实施版本以 `uv.lock` 为准，源码清单同时记录 lockfile SHA256。
   落点是独立 `ImportedAnalysisRuntime` 的五类节点和显式安全分支；签名权限、调用准入和幂等由本仓库SQL事务承担。
   不引入 checkpointer：本阶段没有安全自动恢复付费调用的需求，不能把图重放当恰好一次。
   小型工程对照为“无候选2K+2、有候选3K+2、安全退出K+1”，实际Mock图均有定向测试。
2. **RAPTOR / GraphRAG**：论文、实现与许可链接沿用v4记录；只借鉴“中间结构与最终结论分开、结论回到来源”的思路。
   本轮先用全Core反证和有限候选，未移植二者代码、未运行其评测、未引入实体图或向量基础设施。
   月/季/年层级事件与摘要留到ICA-C；当前K≤32，不能把top-k检索称作完整覆盖。
3. **冻结 Skill**：使用仓库MIT快照 `6db7354a4002dc7c448a9c87ffdad8132570c9d3`；
   按现有registry路由安全、ChatLab适配、冲突修复三篇参考，不修改上游。
   B0三类发现与规则见 [ICA_B0_CONTRACT](ICA_B0_CONTRACT.md)，不是外部项目的心理学效度背书。

ChatLab/Weport仍只复用ICA-A独立格式适配器，没有复制其受限许可实现。
本轮研究复核没有新增真实模型调用，也没有引入新生产服务。
