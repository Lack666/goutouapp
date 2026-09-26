# ADR 0004: align Phase 0 layout with the requested monorepo

Status: accepted, Phase 0 revalidation.

The preserved Skill snapshot moved from `upstream/goutoujunshi` to
`knowledge/goutoujunshi`; its manifest moved to
`knowledge/upstream-manifest.json`. All 63 preserved files retain their exact
SHA-256 values and match the local upstream checkout at commit
`6db7354a4002dc7c448a9c87ffdad8132570c9d3`. The server placeholder moved
from `apps/api` to `apps/server`. Tests, documentation and validation commands
now use the new paths.

`docs/ARCHITECTURE.md` now states only the confirmed technology and deployment
boundaries for Phase 0. Detailed Agent behavior already documented in the
Phase 1 Skill Contract remains there; implementation decisions belong to their
later phases. The move does not change the upstream Skill's content or license.
