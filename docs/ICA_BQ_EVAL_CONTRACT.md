# ICA-BQ 首轮质量评测合同

日期：2026-11-04，版本`ica-bq-v1`，基线`c9551b8`。
用户明确授权：沿用DeepSeek，整轮总费用不超过¥20，禁止自动重试。
本轮包括有限安全角色修复、匿名合成真实批次与独立人评准备；不开放App真实Provider执行，不进入ICA-C或Phase12。

## 参考与来源

继续采用[B0/B1参考审查](ICA_B0_B1_REFERENCE_REVIEW.md)及[v4研究](ICA_LONGITUDINAL_ROADMAP_V4.md)。
2026-11-04复核[DeepSeek中文官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)：
`deepseek-flash`对应文档版本DeepSeek-V4.1-Flash-1017，高峰每百万输入缓存未命中¥2、命中¥0.04、输出¥8。
预算按未命中高峰价预留，实际时段/缓存可使账单更低；记录返回model字段，不声称可强制固定远端别名后面的权重。
[官方JSON说明](https://api-docs.deepseek.com/guides/json_mode/)明确JSON输出模式不等于项目Schema/语义正确。
复用现有兼容Provider注入完整Schema、校验和错误处理；不引入新模型SDK或依赖。
评测采用冻结集、固定对照与哈希绑定人评，不自动生成质量评分，不复制第三方代码。

## 批次冻结与预算

- 一轮目录中`plan.json`冻结source fingerprint、32个holdout、两臂、角色回归、模型、价格、上限与停止条件。
- `claimed.json`以独占创建取得一次运行资格；既有claim或账本不自动恢复、覆盖、重跑。
- 全轮同一钱包：最多400次请求、10,000,000保守预留Token、¥20，三个独立限制。
  每请求最多4096输出Token、非思考模式、temperature=0、无重试。数值上限不是保证64份报告必能全部完成。
- 每次按适配器最终实际payload UTF8字节（含Schema）+4096 framing与输出上限预留；发送前fsync准入账本。
  失败/未知费用不退款到本轮可用预算。未知usage不记0；实际记录usage和高峰费用估算，不冒充结算发票。
- 任一预算用尽、usage超过预留、安全角色回归失败或人工停止，阻止后续新发送；未运行case保留在分母。
  不自动修Prompt、换模型、重新生成同case或追加第二批。
- 全部输入仅冻结匿名合成材料；只记录可见合成输出和用量，不保存hidden reasoning或密钥。

## 质量实验

先运行6份`development_regression`角色案例：受害、施害、角色不明各2份，含旧持刀受害者失败。
本轮为`SafetyResult`增加严格user_role并保留未知默认，受控模板按角色选择且最终发布相等性校验保留。
该组属于已知回归，不冒充新保留集；旧评分不改，真实识别及人工表达接受度分别报告。

随后32份冻结holdout各运行event/baseline一次（交替两臂顺序固定，记录顺序/延迟，不作强因果性能比较）。
event为现有结构化候选/全Core反证图；baseline为同图、同Schema/安全/验证下的逐片摘要prompt对照。
此对照只测该prompt差异，**不是独立层级摘要与事件索引架构实验**；完整架构对比留在下一次版本化实验。
两臂均不接收expected、forbidden或攻击故障元数据作为模型输入。
Owner/撤销/Restore等故障只能由签名数据库测试验证，纯Python样例明确标记未执行这些故障。
小故事集的消息规模和自定义窗原样保留，不能冒充900/2100条或月/年真实模型质量证明。

## 固定分母与人评

保持[B0质量门槛](ICA_B0_CONTRACT.md#6-后续质量门槛与本轮停止条件)。
每臂普通holdout22份（三类各6、counter_missing4），其中失败、未执行、错误安全退出仍在分母。
完成≥95%要求至少21/22；普通可接受≥85%至少19/22，且至少20份可读报告得到独立人评。
三类分别precision≥85%、主要模式Recall@1≥75%；每类仅3份正例，召回须3/3才能达标，明确样本不足以外推。
反证检出≥90%；引用语义≥95%；严重无据负面断言、危险建议、角色错位、越权/Memory副作用和遗漏关键修复为0。
适用维度均分≥4/5、任何项不得<3。N/A仅对零发现且无可行动材料的actionability适用，须填固定理由。

评审包隐藏arm/case_id/family/expected，随机review_id；单独保存映射。
审核按原文及可见报告逐引用、逐发现判断，不给结构代理分。
每条人工提交须有真实评审者、时间、理由、独立性声明和精确输出hash；助手不得代填分数或判定。
遮蔽字段与随机顺序不能证明独立保管已经成立；开发者能访问本仓库，须明确披露。
人评未完成标PENDING；已确定的完成率/硬失败不达标如实FAIL，不用人评未完成掩盖机器失败。

## 本轮交付与停止

交付源码/Schema与Mock回归、冻结批次、逐调用账本、失败/未执行项、匿名人评包、费用/延迟摘要及验收报告。
不以批次执行完成自动宣布ICA-BQ PASS；独立人评、安全矩阵和质量门槛不全则FAIL/PARTIAL。
正式Marker9/9H、历史Phase11 QUALITY FAIL、Phase10 DEFERRED、Phase12 PENDING均不改。
