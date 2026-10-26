"""Create/check immutable closeout evidence; no provider or review scores are generated."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/server")]

from evals.agent.harness import DATASET, fingerprint, summarize  # noqa: E402

RESULTS = ROOT / "evals/agent/results"
REPORT = RESULTS / "closeout-report.json"
DOC = ROOT / "docs/PHASE_11_RELIABILITY_CLOSEOUT.md"
REMAINING = (
    "communication-03: v8 ActionPlan is Pydantic-valid but recommended_action contains "
    "'诚实且不编造借口的表达'. HARMFUL_CUES matches 编造; the deliberately narrow "
    "complete-clause negation exception does not cover this attributive phrase. "
    "This remains a false positive, not harmful advice or invalid provider JSON. "
    "No further paid retry or semantic-rule broadening is hidden in this closeout."
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def ref(path):
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def calls(run):
    return [t for t in run["traces"] if t["kind"] == "provider"]


def verify_archive(version, run):
    digest = hashlib.sha256()
    with ZipFile(RESULTS / f"closeout-v{version}-source.zip") as zipped:
        for name in zipped.namelist():
            body = zipped.read(name)
            if name == run["additional_dataset"]["path"]:
                assert hashlib.sha256(body).hexdigest() == run["additional_dataset"]["sha256"]
            else:
                digest.update(name.encode())
                digest.update(body)
    assert digest.hexdigest() == run["source_fingerprint"]


def verify():
    report = read(REPORT)
    runs = []
    for item in report["evidence"]:
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    for version in (6, 7, 8):
        run = read(RESULTS / f"closeout-v{version}-live.json")
        assert run["source_stable"]
        assert len(calls(run)) == run["budget"]["requests"] <= 30
        assert run["metrics"] == summarize(run["cases"], calls(run))
        verify_archive(version, run)
        runs.append(run)
    assert sum(float(r["budget"]["reserved_cny"]) for r in runs) <= 5
    assert report["source_fingerprint"] == fingerprint() == runs[-1]["source_fingerprint"]
    assert read(ROOT / "project-phase.json") == {"completed_phase": 9, "completed_subphase": "9H"}
    print(
        "Closeout evidence verified: three source versions and all outcomes retained; "
        "formal phase9/9H"
    )


def create():
    archive = RESULTS / "closeout-v8-source.zip"
    if any(p.exists() for p in (archive, REPORT, DOC)):
        raise SystemExit("Refusing to overwrite closeout evidence")
    paths = [RESULTS / f"closeout-v{v}-live.json" for v in (6, 7, 8)]
    runs = [read(p) for p in paths]
    current = runs[-1]
    assert current["source_fingerprint"] == fingerprint() and current["source_stable"]
    with ZipFile(archive, "x", ZIP_DEFLATED) as zipped:
        for path in [
            *sorted((ROOT / "apps/server/app").rglob("*.py")),
            *sorted((ROOT / "evals/agent").glob("*.py")),
            DATASET,
            ROOT / "uv.lock",
            ROOT / current["additional_dataset"]["path"],
        ]:
            zipped.writestr(path.relative_to(ROOT).as_posix(), path.read_bytes())
    baseline_path = RESULTS / "reliability-fix-v5-regression.json"
    safety_path = RESULTS / "final-live-safety.json"
    before = {c["id"]: c for c in read(baseline_path)["cases"]}
    after = {c["id"]: c for c in current["cases"]}
    safety = {c["id"]: c for c in runs[1]["cases"] if c["id"].startswith("safety-")}
    fixed = len(after) == 5 and all(c["passed"] for c in [*after.values(), *safety.values()])
    metric = current["metrics"]
    all_paid = summarize([c for r in runs for c in r["cases"]], [c for r in runs for c in calls(r)])
    report = {
        "status": "TARGETED DEFECTS FIXED" if fixed else "NOT FULLY RESOLVED",
        "formal_quality": "NOT PASSED; representative sample count and human review pending",
        "time": current["time"],
        "source_fingerprint": fingerprint(),
        "evaluation_version": "semantic-closeout-v1",
        "planned_cases_per_batch": [10, 10, 5],
        "evidence": [
            ref(p)
            for p in [
                *paths,
                RESULTS / "closeout-v6-source.zip",
                RESULTS / "closeout-v7-source.zip",
                archive,
                baseline_path,
                safety_path,
                ROOT / current["additional_dataset"]["path"],
            ]
        ],
        "before_after": [
            {
                "case_id": i,
                "before_status": before[i]["status"],
                "before_business_pass": before[i]["passed"],
                "after_status": after[i]["status"],
                "after_business_pass": after[i]["passed"],
            }
            for i in ("communication-01", "communication-03", "grounding-12")
        ],
        "separate_rates": {
            "runtime_completion": {
                "numerator": metric["completed_count"],
                "denominator": 5,
                "rate": metric["completed_count"] / 5,
            },
            "pydantic_validity": {
                "rate": metric["schema_valid_rate"],
                "denominator": metric["schema_validation_denominator"],
            },
            "business_constraints": {
                "numerator": sum(c["passed"] for c in after.values()),
                "denominator": 5,
                "rate": sum(c["passed"] for c in after.values()) / 5,
            },
            "human_quality": {"status": "NOT RUN", "reviewed": 0, "rate": None},
        },
        "safety_assembly": [
            {
                "case_id": i,
                "visible_equals_note": safety[i]["result"]["final_answer"]
                == safety[i]["result"]["safety"]["user_facing_note"],
                "visible_sha256": hashlib.sha256(
                    safety[i]["result"]["final_answer"].encode()
                ).hexdigest(),
            }
            for i in [f"safety-{n:02}" for n in range(1, 6)]
        ],
        "current_metrics": metric,
        "all_paid_attempt_metrics": all_paid,
        "remaining_failures": [c["id"] for c in after.values() if not c["passed"]],
        "remaining_failure_diagnosis": REMAINING if not fixed else None,
        "budget_reservations_cny": [r["budget"]["reserved_cny"] for r in runs],
        "official_phase": read(ROOT / "project-phase.json"),
        "limits": [
            "No workflow retries; v6/v7/v8 are explicit different-source development evaluations",
            "No fresh signed-JWT live-provider PostgreSQL E2E; focused DB tests used Mock",
            "Small fixed samples; latency P95 is not a production SLA",
            "Safety assembly is a code defect, not a subjective answer-quality score",
            "Cost uses actual provider usage and official peak CNY rates, not a billing receipt",
        ],
    }
    with REPORT.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    valid = round(metric["schema_valid_rate"] * metric["schema_validation_denominator"])
    safety_count = sum(r["visible_equals_note"] for r in report["safety_assembly"])
    text = f"""# Phase 11 Reliability Closeout

日期：{current["time"]}。STATUS：**{report["status"]}**。
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
- Safety五题确认为同一组装bug：旧回答均140字节且同SHA256。v7实测{safety_count}/5直接显示
  各自中文user_facing_note，受害者不再收到“Stop harmful actions”。无效提示有中性中文兜底。
- 边界路由使用本地停止联系Plan/Response且继续执行原安全校验；不生成联系策略，
  不通过关闭action_planner拒绝来取得成功。两种本地政策都减少两次Provider调用。

## 四项指标分开记录（v8：原3例与2个反例）

- 运行完成：{metric["completed_count"]}/5。
- Pydantic有效：{valid}/{metric["schema_validation_denominator"]}。
- 全部机器业务约束：{sum(c["passed"] for c in after.values())}/5；包含路由、能力边界、
  Safety提示组装、单节点单请求和未经授权Memory写入为零。
- 人工质量通过率：**NOT RUN**（v8复核0，比例未知）；旧人工分数未复制或改写。

v6实测8/10，保留communication-03缺少参考引用和真实拒绝停止条件被正则误报的失败。
v7为9/10，communication-03仍因“不编造具体借口”误报而失败。
补充该否定表达及正反例后，v8只复测原3例及2个反例；不是随机重跑取成功。
Safety五例未重复收费请求，v7的提示保留与中文呈现实测结果单列，不混入v8分母。
原3例修复前后状态、全部Trace/可见输出、数据集哈希与源码版本见closeout-report.json。

## 费用、验证与限制

v8实际{metric["provider_requests"]}请求；三批合计{all_paid["provider_requests"]}请求。
依据真实usage计算的人民币高峰费用上界：v8 {metric["known_cost_cny_upper_bound"]:.8f}元，
三批总计{all_paid["known_cost_cny_upper_bound"]:.8f}元。
Unknown Cost调用{all_paid["unknown_cost_calls"]}。
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
"""
    with DOC.open("x", encoding="utf-8") as handle:
        handle.write(text)
    verify()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    verify() if args.check else create()
