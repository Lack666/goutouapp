# ICA-BQ 首轮验收

日期：2026-11-04；源码基线HEAD `c9551b8`。本报告所在提交为实际交付版本。

**ICA-BQ QUALITY FAIL / PARTIAL**

用户批准DeepSeek整轮¥20、禁止自动重试。本轮已完成限定安全角色修复、离线评测工具、一次冻结真实批次、
失败重放和定向工程回归。真实聊天分析未达到最基本的完成率；不进入ICA-C、长范围扩容或Phase12。
历史Phase11 QUALITY FAIL、人工评分/失败、Phase10 DEFERRED、Phase12 PENDING、Marker9/9H均不改。

## 真实结果

[冻结计划](evidence/ica-bq/batch-v1/plan.json)包含模型、价格、32个holdout、两臂、来源hash、预算和停止条件。
[逐调用账本](evidence/ica-bq/batch-v1/calls.jsonl)、[逐case结果](evidence/ica-bq/batch-v1/results.jsonl)、
[质量摘要](evidence/ica-bq/batch-v1/quality-summary.json)、[用量与延迟](evidence/ica-bq/batch-v1/observed-summary.json)均保留原始失败。

- 安全角色已知回归：**6/6完成且角色与预期一致**，见[实际结果](evidence/ica-bq/batch-v1/role-results.jsonl)。
  受害者、施害者、角色不明各2例，含原持刀受害者故事；这是开发回归，不是新的独立保留集。
- 结构化候选event臂：**0/32可发布**；逐片摘要prompt对照baseline臂：**0/32可发布**。
  每臂普通holdout分母22，完成率**0/22**，低于要求21/22；失败没有被移出分母。
- 64次分析失败中：`invalid_evidence`48、`content_review_rejected`9、`invalid_model_output`6、`model_statistics`1。
  没有把未发布报告转成成功、零发现或安全报告。
- 独立人评**0**；三类precision/主要模式召回、引用语义、反证语义和人类可接受度未获验证。
  已知完成率FAIL优先记录，未评维度仍为PENDING，不用PENDING掩盖既有失败。

比较结论仅为本次两臂均失败，不能据此宣称两种方案等价或事件结构更优。
baseline只在同图/安全/Schema/全Core反证/最终复核下改变局部摘要提示；
**独立层级摘要与事件索引架构比较尚未实现**。当前小故事自定义时间窗也不证明900/2100条、月、季或年的真实模型质量。

## 三个可复现的实际失败

新 [test_ica_bq_replay.py](../apps/server/tests/test_ica_bq_replay.py)读取固定真实返回并核对SHA256，
3项离线重放通过，没有产生新付费请求：

1. `ica-v1-em-ho-exam`，event安全检查call7：返回`decision=normal`但`risks`非空，违反跨字段合同。
2. 同case的baseline互动call9：quote与UUID正确，原文17个Unicode code points却填`end=21`；
   另一条18字符填24。来源校验按实际原文拒绝。Python切片会截短，不能只用切片结果相同就放行。
3. `ica-v1-rc-ho-different-topics`，event复核call42：批准字段为true但附`reason_codes=[uncertain]`；
   实际图前序可重放，最终拒绝发布。没有删掉复核以提高完成率。

未发现这些样例存在runner消息、UUID或Mock响应队列接线错误。
模型生成的Unicode位置不可靠，是本批主要可确认的机械失败来源；48项出处失败不武断归为同一种错误。
本批开始后没有改Prompt、Runtime、Schema、案例或费率，没有自动重试和结果驱动的付费修复。

## 安全角色修复与边界

原根因：`SafetyResult`没有角色，模型自由note随后被`protective_v1`覆盖，
程序无条件先拼施害者段。原测试甚至要求受害者输出含该段。

现在使用严格`user_role=at_risk|causing_harm|unclear`，缺失默认unclear；
Prompt明确分类，受控中英`protective_role_v2`按角色选择，不按词表猜身份、不插入模型自由建议。
未知角色不归责，最终`validate_safety_answer`相等性发布校验仍保留。
修改仅涉及contracts、安全Prompt、安全模板及定向fixture/测试；OpenAPI和generated client同步。

6/6真实识别与Mock矩阵支持该限定修复，**SAFETY-ROLE-P1质量关闭仍待独立人工评审**。
旧受害者人工失败分数、自主性2分与历史3/8可接受结果不追认、不重写。
当前结果不足以证明所有安全角色、历史引用/否认情形及表达接受度均已过关。

## 费用、真实调用与停止

[持久预算摘要](evidence/ica-bq/batch-v1/budget-summary.json)：

- **147次真实Provider调用**（角色6次、ICA141次）；147次都有usage/缓存用量，未知请求0，重试0。
- 实际input764,840、output26,937、总791,777 Token；缓存命中317,440、未命中447,400。
- 用官方高峰费率按实际缓存明细计算的保守估算 **¥1.12299360**，不是已结算发票。
- 每次发送前按完整适配器payload字节、Schema、4096 framing和输出上限预留，累计 **¥12.109270**，
  4,248,299保守预留Token；整轮未超¥20/400请求/10,000,000预留Token。
- API返回model为`deepseek-flash`；文档对应DeepSeek-V4.1-Flash-1017，未声称远端别名是不可变权重。
- 单次请求延迟均值1,662.49ms、p50 939.59ms、p95 4,046.65ms；不是端到端App性能承诺。

价格与JSON模式官方来源、模型配置、协议和预算规则见 [ICA_BQ_EVAL_CONTRACT](ICA_BQ_EVAL_CONTRACT.md)。
本轮仅通过既有LLMProvider发送匿名合成内容，没有工具调用、网络搜索能力、私人聊天或模型密钥日志。
一次性`claimed.json`、发送前fsync准入、失败/未知保留预算；不能重新执行同目录来重置费用或覆盖结果。
生产导入执行API仍默认关闭且只接受Mock，本次实验没有放开真实用户分析权限。

## 人评、保留集与独立性

[人评包](evidence/ica-bq/batch-v1/human-review-packet.json)遮蔽arm/case_id/family/expected并随机排列，
[映射](evidence/ica-bq/batch-v1/review-private-mapping.json)单独保存。分数、判断、身份、理由均未代填。
缺失人工结果不能自动得到语义分；失败不可被评为可接受。当前没有20份可读普通报告，不能满足人评门槛。
两份文件都在本仓库，不声称已经实现独立盲评保管；评审者仍需真实独立性声明。

原48份案例及manifest字节未修改，16/32 split不改。此次32份保留集已经使用；
其中exam、family-call、family-privacy、different-topics及工具tail接触的renegotiated/separate-actors
已被用于诊断。后续修复调试必须将本批视为已知开发资料，**用新的独立保留集验收**，保留本轮FAIL。

## 工程与隐私回归

[后端日志](evidence/ica-bq/backend-tests.txt)：**428 passed in128.01s**。
包括ICA导入/分片/来源、签名PostgreSQL授权/撤销/生命周期/原生Restore、11R两条Memory P0真实HTTP+SQL、
共用Agent REST/stream、安全角色及11R边界、评测/预算/人评工具。
另新增固定真实输出重放**3项PASS**，见[日志](evidence/ica-bq/replay-tests.txt)；与428不重复。
没有把其他代理曾跑的重叠测试相加为新总数。

[Mobile日志](evidence/ica-bq/mobile-tests.txt)：**116项/5 suites PASS**。
TypeScript通过；OpenAPI确定性52个操作且保留原26合同；generated-client3项PASS；
本轮12个Python文件Ruff与Format通过，`git diff --check`通过。

复用既有PG16 ASCII路径的隔离localhost15435实例，未initdb、改角色、清空未知库或接触生产。
每项恢复测试使用自己的随机测试DB，全部迁移和finally清理；结束测试库0、活动测试连接0，测试服务已停止。
没有新增DB迁移、App分析报告页面、Memory权限、服务基础设施或依赖。
未执行完整Root Verify、Phase0–9历史全量或Android原生历史全集；不登记正式工程阶段/生产发布PASS。

本轮发现并修正的工具问题：pytest默认临时目录被Windows权限阻止，改用明确授权的隔离basetemp后通过；
Ruff格式化后长行通过；人评摘要初稿会优先PENDING，已在真实批次前修正为任一已知FAIL优先并增加回归。
这些修正均在冻结真实批次之前，未针对保留集结果改变判据。
既有ICA-B1测试会固定路径写演示JSON；本轮将新签名快照另存ICA-BQ的`regression-signed-*`，
并按Git blob与原manifest SHA256恢复三份旧B1证据，未用新结果覆盖历史证据。

## 源码与实际修改文件

完整文件清单与实际raw-byte SHA256见 [source-manifest.json](evidence/ica-bq/source-manifest.json)。
冻结真实批次源指纹为`c72f2862cceb2544c3aa0e2702ad91a30443f5e469ca90bce101c9ac0af4102d`，
运行后重新核对一致。该指纹包含Agent、Provider、评测源码、知识实际文件、冻结案例和依赖；
本报告、回放测试及生成物由交付清单另行覆盖。

主要修改：Agent contracts/safety prompt/safety_validation；原phase11q safety测试和新safety_roles测试；
`evals/ica/{runner,review,live}.py`与6例角色回归；四个新增评测/重放测试；
MASTER_PLAN/ARCHITECTURE/本轮合同报告、字节保留属性及原始证据。
OpenAPI/generated client已重新生成并核验，无内容漂移，因此不产生生成物差异。
用户原有人工评分、未提交报告、summary和human_review_ui修改均未纳入本轮提交。

复现命令（根目录，`PYTHONPATH=apps/server;.`，uv cache与ASCII basetemp按本轮隔离目录设置）：

```powershell
uv run --no-sync python -m evals.ica.live plan <new-batch-directory>
uv run --no-sync python -m evals.ica.live run <new-batch-directory>
# 上两条仅展示已执行协议；本授权已消费，不能自动创建第二轮付费批次。
uv run --no-sync pytest apps/server/tests/test_ica_bq_replay.py -q
pnpm --filter @goutou/mobile typecheck
uv run --no-sync python scripts/export_openapi.py
pnpm api:check
```

## 下一次有限修复建议

优先验证“精确quote+合法alias→服务端唯一定位Unicode span”的新证据输入合同，
将字符计数交给代码；歧义、跨来源、不存在quote仍拒绝，不通过截短或模糊匹配放行。
其次让安全决定/风险项、复核决定/理由的生成协议更清楚，保留跨字段拒绝与内容复核。
先用开发集与本批失败做Mock/离线重放，冻结新版来源合同，再以新保留集和新明确预算验收。
这只是下一轮建议，本轮没有进行该修复或第二批真实调用。
真实质量和独立人评过关后再做Android报告或扩大到月/季/年。
