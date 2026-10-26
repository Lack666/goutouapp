# Phase11 结构化输出可靠性修复后报告

日期：2026-10-26。范围仅限当前 Agent 的真实模型结构化输出可靠性。

STATUS: **PARTIAL RELIABILITY FIX / QUALITY GATE FAIL / FINAL REGRESSION PENDING**。
原5个失败案例在v5全部完成；扩展回归仍有2个运行失败、1个已完成但行为断言失败。
不能据此宣布普通分析路径稳定、Phase11功能验收全部完成或质量PASS。
Phase10继续DEFERRED，Phase11 IN PROGRESS，Phase12 PENDING；正式Marker仍为9/9H。

## 从原始证据确定的根因

逐一对齐原始JSON内的run_id、provider trace、visible output与节点终止事件，
重新执行正式Pydantic校验并保留错误位置。诊断结果为
`evals/agent/results/reliability-fix-v3-diagnosis.json`；脚本
`scripts/diagnose_phase11_structured.py`不调用模型。

- communication-02：relationship_analysis，risks[0]，tentative仅引用U2/U4。
- communication-04：同节点，risks[0]，tentative仅引用U1/U3。
- communication-05：同节点，risks[0]，tentative仅引用U1/U2；额外reference不构成F/I依据。
- grounding-07：同节点，risks[1]，tentative仅引用U4。
- grounding-01：Pydantic已经通过；core_issue在反驳用户结论时引用“一定不爱我”，
  正则跨越引号，把被否定的用户推断当成Agent自己的确定性断言。

这5次均finish_reason=stop、JSON完整，输出708–1114 tokens，配置上限4096。
证据不支持“Token不足、截断或DeepSeek接口不可用”为这些失败的根因。
JSON mode保证JSON格式，不保证项目跨字段合同；仍需本地严格校验。
参考[DeepSeek官方JSON说明](https://api-docs.deepseek.com/guides/json_mode/)。

## 最小修复与边界

分析提示改为先按来源确定kind，再选择risks等列表；U-only必须是uncertainty，
给出合法实例，禁止补造F/I以满足验证。此变化没有改写任何已保存的模型输出。

后续实测确认FIU会自创current_user_message来源标签，故将原有允许枚举明确写入
FIU提示。另一次最终回答在退出条件中列举“威胁”触发保守过滤，因此补充中性、
保护性的退出条件示例。仍有类似否定误报的风险，见下方扩展失败。

v4再次证明引用误报不能单靠提示解决。v5仅在分析节点区分一个窄范围：句子明确
归属于用户的推断/等同，引用内容位于成对中文引号内，且句末明确否定该结论的
证据充分性时，跨引号匹配不算Agent断言。完整武断断言、引号外的另一个断言、
无否定结论的引文、模糊归属均继续拒绝。新增负面测试覆盖这些情况。
该检查仍是有限的词法规则，不构成对所有中文引文、否定和语义正确性的保证。

未修改Pydantic Schema、来源ID校验、Safety路由规则、Memory/Delete或Owner隔离。
没有自动修复JSON、静默重试、补写回答、删除失败案例或降低评分标准。
Provider仍然逐节点只调用一次，错误时运行保持failed。

## 四批实测，全部保留

- v3原5例：3/5完成；27次请求，27/27 Pydantic有效。新暴露FIU来源枚举和回答过滤问题。
- v4原5例：4/5完成；28次请求，28/28有效。grounding-01仍被引用误报拦截。
- v5原5例：5/5完成；30次请求，30/30有效，无未经授权Memory写入。
- v5扩展5例：3/5完成；28次请求，28/28有效；仅2/5通过全部行为结构断言。

扩展样本事先选为communication-01、grounding-03、grounding-12（旧成功案例），
communication-03、grounding-02（新增普通代表案例）。未因失败替换选样。
它们与原5例合计10个不同普通场景，不是20个独立质量样本。

每批明确opt-in，独立预算最多30请求/5元；共113次真实请求，包含全部中间失败。
没有将重复开发复测隐藏成单次成功。四批JSON都记录预算预留、实际usage、模型参数、
Graph/Prompt/数据集/评测器版本、来源指纹及起止一致性。模型deepseek-flash，
thinking=disabled，max_output_tokens=4096，timeout=90秒。

## 当前v5指标与成本

- 运行完成8/10=80%；全部机器行为约束通过7/10=70%，均不是人工质量通过率。
- Pydantic有效58/58=100%；Provider请求错误0/58。另有2次Agent业务校验失败，
  不得因Provider错误率为0而隐藏这20%的运行失败。
- 平均运行延迟13.530秒，P50 11.966秒，P95 17.851秒，包含失败运行；小样本非生产SLA。
- 输入77449 tokens，其中缓存命中32768、未命中44681；输出13934，总计91383。
  逐调用分布保存在报告JSON的token_distribution。
- v5费用估计上界0.20214472元；每Provider调用均值0.00348525元，按10次运行
  计算均值0.02021447元。Unknown Cost调用0。
- 含v3/v4的全部开发复测共175770 tokens，113次请求，总费用上界0.39533016元。
  这是20次运行尝试，完成15次；不可把重复样本当成20个不同代表案例。

按测试当天[DeepSeek官方人民币价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)
记录的高峰上界：缓存输入0.04元/百万、未缓存输入2元/百万、输出8元/百万。
价格版本deepseek-flash-2026-10-26-peak-cny。费用来自真实usage计算，非账户账单凭据。

## 尚未解决，必须保留的失败与风险

1. communication-01：SafetyResult错误附加explicit_refusal，同时说明“单个时间不方便
   不等于永久拒绝”。因此实际进入boundary；ActionPlan却选择reply。action_planner
   正确拒绝与边界路由冲突的计划，运行failed。属于模型类别/说明不一致，不是JSON截断。
2. communication-03：ActionPlan的“不必编造理由”触发HARMFUL_CUES中的编造匹配。
   是否定表达误报；本次未扩展成通用中文否定解析，也未关闭过滤。运行failed。
3. grounding-12：运行completed但stop_conditions为空，现有action_structure断言失败。
   回答还声称收到导入文件后即可核对引用，超过当前Imported RelationshipMessage未进
   Agent上下文的真实能力。保留原文供人工评审，不宣称已实现导入聊天引用功能。

故质量门槛维持FAIL。结构有效率100%不能替代语义、安全类别、可用性和建议质量。
新版本只有10个不同普通案例，未达到20例代表样本且缺少新人工复核，未做本轮真实
高风险专项，不能从这些普通样本声称高风险识别已经全面验证。
10次运行的未经授权Memory写入均为0；本轮未修改Memory或身份隔离代码。
本轮没有新FastAPI/PostgreSQL E2E，不能把真实LangGraph复测冒充完整transport/DB E2E。

## 人工评审与可复现证据

你原有15/15实际人工评分及意见保持原样，旧汇总为10/15可接受，不迁移到新输出。
新包为`evals/agent/results/reliability-fix-v5-human-review-15.json`，初始0/15：
10个v5普通案例全部纳入（包括两个failed和一个行为断言失败），加5个原v2安全输出。
后5个明确标明旧版本，并未算作新的v5线上安全测试。六项规则保持human-rubric-v1，
分数、身份、时间和理由全部留空，由实际用户填写，automated_proxy不代填。

本机新界面http://127.0.0.1:8766/，旧8765及其进度保留。使用命令见HUMAN_REVIEW_UI.md。
新包sources绑定文件SHA256和原始输出哈希，支持独立保存/修改/返回/最终导出汇总。

机器报告：`evals/agent/results/reliability-fix-v5-report.json`。
v3/v4/v5均有独立source.zip，可按原路径重建相应源码并用冻结Provider输出离线复现。
v5来源指纹：`cd9042ef181ad029eaa31279aee1d95fd189ac931701d782cf5a761e6d7c5c93`。
数据集agent-v1、评测器behavior-structural-v1保持原样，真实模型不承诺逐字复现。

```powershell
$env:PYTHONPATH='apps/server;.'
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/check_phase11_reliability.py
```

本次独立校验核对四批结果、三份源码归档、旧报告引用的证据哈希、指标重算、新人工
包的原文/状态/规则/来源及Marker。旧check_phase11.py针对v2当前源码一致性的检查
未被放宽或冒充v5验收工具。所有旧final-live、aggregate-final和原始源码包均未覆盖。

## 定向验证与收尾

最终110项定向测试通过，6.72秒，包含真实失败输出离线回放、严格Schema、分析与
建议校验、Safety/语义、Memory、Provider故障边界、观测隐私、新评分包隔离。
命令及原输出：`docs/evidence/phase11/reliability-targeted-tests.txt`与同目录
`reliability-commands.md`。Ruff lint/format通过。实际Chrome只读验证新评分界面：
15题初始为空、2个真实失败、来源版本可见；未保存或代填任何评分。

Golden83、冻结Skill、正式Schema、Phase0–9验收证据及Marker未变，旧证据哈希通过。
未引入依赖，未记录私密聊天、Key、Authorization或隐藏推理；保存的模型内容仅来自
已授权合成输入。可见输出用于诊断，生产Trace依然只保存受限元数据。

FULL REGRESSION: DEFERRED TO FINAL CLOSEOUT。没有执行Root Verify、历史全套或Android。
RAG继续DEFERRED：本次已确认的来源类型、过滤误报与路由矛盾不能由新增检索解决。
NEXT: 先审查新评分包和上述剩余缺陷；不启动Phase12或新增聊天分析功能。
