# Generate POV images with Codex

This is the local route for `IMAGE_PROVIDER=codex`. Keep using the installed
`image_gen.imagegen` tool. No Kie.ai, new API keys, SDK or paid vision service.

Read `pov-automation/style/README.md` for exact commands and the review contract.
The runtime authority is the version selected by
`pov-automation/style/active_version.txt` (v1 when absent), its SHA-256 lock,
the complete STYLE_BIBLE.md and its immutable reference PNGs. Per-video style
profiles, nearest/last approved scenes and historical prompt boilerplate no
longer override it. Existing files and the user's refined protagonist survive.
The `style/proposals/v2/` candidate is pending visual approval and must stay
inactive until the user approves it.

## Required generate -> inspect -> decide loop

1. Resolve the active video folder once; thereafter use an explicit absolute
   `--production` path. Initialize the persistent manifest. It binds a unique
   UUID to that folder, script hash, style version and retry bound.
2. `prepare SCENE` creates a resumable request with three layers. Read the exact
   `tool_arguments`. Inspect reference PNGs before using them. Claim the request once with `claim SCENE WORKER`. Invoke the built-in
   tool with those arguments, never with `num_last_images_to_include` and never
   with references from another production. One call per scene. Do not rewrite,
   truncate or append ambient conversation context to the prepared prompt.
3. Save the tool output locally and `ingest` it with its actual output identifier.
   The tool manages model/settings; do not invent seed, model-version or style
   weight controls. Account limits are those of the installed built-in tool.
4. Open the actual candidate at full resolution and the canonical references.
   Fill the generated review template from visible evidence, including numeric
   drift scores (0 = close, 1 = acceptable variation, 2 = drift) for all six
   rendering dimensions and an explicit content-isolation observation. Compare lines,
   shapes, colours, shading, backgrounds and finish across every region; also
   separately check identity/age/costume, story/era/props, and composition.
   Supporting characters must not copy reference identities; object frames must
   contain no people. Inspect batch contact sheets, but never substitute a
   contact sheet for individual full-resolution review.
5. `review` routes the candidate and updates legacy checked/rejected lists.
   Failures/uncertainty need concrete corrective feedback; `prepare` rebuilds
   the next attempt from the immutable original authority. Three total attempts
   by default, then needs_attention. Do not repeatedly send the identical failed
   request. On a technical failure, record its cause before retrying.
6. Resume prepared requests without spending again if a tool output already
   exists; ingest it first. Pending requests must be reviewed before another
   generation. An interrupted external call cannot be deduplicated by Python:
   locate its original output or explicitly record the failure before retrying.
7. Every new Codex production uses the strengthened review contract, regardless
   of the active approved style version. Audit each hash-bound 20-scene batch
   before continuing to the next batch; the first batch includes all scene
   classes. Existing contract-1 productions upgrade in place and need fresh
   batch audits before assembly. Existing approved images are preserved. Never automatically replace them,
   and never treat their old filename-only checklists as current hash-bound
   visual evidence. Report unresolved and uncertain scenes honestly.

The bridge enforces request provenance, isolation and approval records; it
cannot force a stochastic image model to obey or prove a reviewer looked at an
image. Actual Codex vision inspection is mandatory. Explicit paths restrict
inputs, but the tool exposes no fresh-session/reset guarantee: content leakage
must also fail the visual gate. No workflow can promise mathematically identical
artwork over unlimited calls.
