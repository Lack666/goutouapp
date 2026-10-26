# Phase 11 Reliability Closeout

日期：2026-10-26T09:42:02.193495+00:00。STATUS：**NOT FULLY RESOLVED**。
正式Phase11质量验收：**未通过**，代表样本数量及新版本人工复核仍待完成。

剩余缺陷：communication-03的v8 ActionPlan写出“诚实且不编造借口的表达”，
仍被HARMFUL_CUES的“编造”命中；现有完整否定分句豁免不覆盖这个定语结构。
这是已定位但未完全解决的业务误报，不能宣称可靠性修复全部完成。

- communication-01：只对无历史、纯日程不便的封闭表达校正误加的explicit_refusal；
  Safety结果和Router一致。真实拒绝、撤回同意、高风险和带历史上下文不降级。
- communication-03：只豁免完整的“不必/不要/无需编造理由”等否定分句；双重否定、
  引用后附危险建议仍被拦截。缺少实际参考引用仍严格失败，提示明确提供合法别名。
- grounding-12：明确未连接导入聊天和上传文件；本地能力说明经正式Plan/Response校验，
  有停止条件、说话人和范围要求，不承诺以后收到文件就能读取。
- Safety五题确认为同一组装bug：旧回答均140字节且同SHA256。v7实测5/5直接显示
  各自中文user_facing_note，受害者不再收到“Stop harmful actions”。无效提示有中性中文兜底。
- 边界路由使用本地停止联系Plan/Response且继续执行原安全校验；不生成联系策略，
  不通过关闭action_planner拒绝来取得成功。两种本地政策都减少两次Provider调用。

## 四项指标分开记录（v8：原3例与2个反例）

- 运行完成：4/5。
- Pydantic有效：20/20。
- 全部机器业务约束：4/5；包含路由、能力边界、
  Safety提示组装、单节点单请求和未经授权Memory写入为零。
- 人工质量通过率：**NOT RUN**（v8复核0，比例未知）；旧人工分数未复制或改写。

v6实测8/10，保留communication-03缺少参考引用和真实拒绝停止条件被正则误报的失败。
v7为9/10，communication-03仍因“不编造具体借口”误报而失败。
补充该否定表达及正反例后，v8只复测原3例及2个反例；不是随机重跑取成功。
Safety五例未重复收费请求，v7的提示保留与中文呈现实测结果单列，不混入v8分母。
原3例修复前后状态、全部Trace/可见输出、数据集哈希与源码版本见closeout-report.json。

## 费用、验证与限制

v8实际20请求；三批合计70请求。
依据真实usage计算的人民币高峰费用上界：v8 0.06513536元，
三批总计0.21568816元。
Unknown Cost调用0。
每批硬上限30请求，三批保守预留合计不超过5元，没有自动重试或重复Memory执行。
价格以测试日[DeepSeek官方人民币价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)为准；
详细Token、缓存用量、延迟和预算在JSON中。小样本延迟不代表生产SLA。

最终定向245测试通过（含真实PostgreSQL、REST/SSE、Safety/Memory及Provider故障）；
Ruff通过。原始日志在docs/evidence/phase11/closeout-*，中间失败记录未覆盖。
真实DeepSeek本轮运行的是LangGraph路径；不把Mock数据库测试冒充新的真实Provider数据库E2E。
源码v6/v7/v8分别归档，使用PYTHONPATH=apps/server;.运行
`python scripts/phase11_closeout_report.py --check`可离线核对证据和指标。

未改正式Pydantic Schema、Golden83、冻结Skill、Memory权限、删除合同及0–9验收证据。
正式Marker仍9/9H，Phase10 DEFERRED、Phase11 IN PROGRESS；未启动Phase12。
FULL REGRESSION：DEFERRED TO FINAL CLOSEOUT；未运行Root Verify、Android或历史全套。
有限词法规则和固定案例不证明通用语义质量，正式质量验收仍需既定样本和人工评审。
