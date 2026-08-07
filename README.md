# exekite-ios-runner

The Codemagic runner for Exekite's iOS export lane. **This repo is not the thing
being built.**

Codemagic apps bind to a git repository, but the thing Exekite builds is an
arbitrary user's generated game, which lives in R2 — not in any repo. So this
repo exists only to hold `codemagic.yaml` and be connected to Codemagic once.
Every per-project build is the same workflow triggered through the API with
different environment variables; the first build script pulls the real project
from a presigned R2 URL.

That is the same source-handoff contract the Android leg already uses in
production, which is why iOS is a second *executor* rather than a second
protocol.

## Source of truth

`codemagic.yaml` is **generated from** the Exekite monorepo at
`apps/export-builder/codemagic/codemagic.yaml`. Edit it there and re-copy —
edits made directly in this repo will be overwritten and are not covered by the
monorepo's tests.

## Setup

See `docs/future/ios-export-lane.md` in the monorepo. In short:

1. Connect this repo to Codemagic as an app (Codemagic → Add application).
2. Create a secure variable group named `exekite_ios` containing
   `EXPORT_CALLBACK_SECRET` — the same value the router and export-builder
   share. It belongs in a *group*, not the per-build payload: anyone with team
   access can read a build's injected environment, and that secret is
   long-lived.
3. Put `CODEMAGIC_API_TOKEN` and `CODEMAGIC_APP_ID` on the export-builder
   Worker, then set `EXEKITE_IOS_EXPORT=1`.

Nothing here is triggered by pushes — `triggering: {}` in the workflow keeps
macOS minutes from being burned on commits to this repo.
