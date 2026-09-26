# 狗头军师 App Runtime

This monorepo is the independent server and mobile implementation of the
[goutoujunshi Skill](https://github.com/shengjidaguai-china/goutoujunshi).
The original specification is preserved unchanged under `upstream/goutoujunshi/`.
Its source revision and file hashes are recorded in `upstream/manifest.json`.

Current milestone: **Phase 1, contract and golden evaluation data**. The API,
agent runtime, and mobile app are future phases; this repository does not yet
claim to run relationship advice independently.

Use `make doctor`, `make test`, `make eval`, and `make verify` on systems with
GNU Make. On Windows without Make, use `python scripts/verify.py doctor|test|eval|verify`.
The verifier reports which phase gates are active and which are deferred.

See [the master plan](docs/MASTER_PLAN.md) and [architecture](docs/ARCHITECTURE.md).

## Attribution

The upstream snapshot is MIT licensed, copyright (c) 2026 powerycy. Its
original [license](upstream/goutoujunshi/LICENSE) is retained with the snapshot.
