# ADR 0001: immutable upstream snapshot

Status: accepted, Phase 0.

The local checkout of `shengjidaguai-china/goutoujunshi` at
`6db7354a4002dc7c448a9c87ffdad8132570c9d3` is copied under
`knowledge/goutoujunshi`. `knowledge/upstream-manifest.json` records every
preserved Skill file's SHA-256. Upstream repository automation metadata is not
part of this knowledge snapshot.
The original MIT license and attribution remain inside that directory.

Reason: behavior, reference routes, safety boundaries and the local memory
script form a versioned specification. Runtime code may interpret them, but
must not silently mutate them. An upstream update requires a new manifest,
contract review, eval update and regression run.
