# Permanent channel style workflow

Run commands from `pov-automation/`. Python 3.10+ and Pillow are required (both
already available in the local setup). No API service or key is added.

## Authority and reference library

`v1/STYLE_BIBLE.md` describes the actual local illustrated style. `v1/manifest.json`
hashes it and every reference; `v1/manifest.sha256` locks the manifest itself.
The library lives outside ignored production folders, so it can travel with Git.
Preserve exact bytes; `.gitattributes` disables newline conversion for the lock.
Do not rehash changed assets to bypass a failure.
Normal production has no command to update the style. A user-directed change
requires a separately reviewed version, with deliberate migration of productions.

`active_version.txt` optionally names the active version; when absent, v1 remains
active. `proposals/v2/` contains a neutral-reference candidate with review
contract 2, but its manifest says `pending_user_approval`. It is intentionally
not a runnable active version. Do not copy it into the active library or change
the pointer until the user approves the reference image and bible. The proposal
and its limitations are described in `proposals/v2/README.md`.

The references are selected existing approved assets, visually inspected during
this implementation, not the newest generated images. Their source and reason
for selection are recorded in the manifest. Six originals collectively cover
nine requested roles: close-up/full-body protagonist (identity sheet), full-body
and indoor rendering (kitchen scene 1), supporting people (Roman scene 114),
objects (kitchen scene 67), exterior/establishing view (Roman scene 105), and
interaction/low-light (kitchen scene 66). Age wrinkles or source costumes do not
override the active character bank. These are rendering examples, not whole-shot
content approvals for future productions.

Main shots receive fixed interior style + global identity. Supporting shots
receive fixed supporting-people style without the protagonist. Object shots
receive a people-free object style image. All routes contain the identical full
bible and reviewers compare the complete library. Scene classification remains
`pov_scene`, `world_scene`, `object_scene`, `cost_scene`. No per-video image becomes
a new rendering authority. No reference chain or nearest-scene anchor is used.

The installed built-in tool supports `prompt`, explicit `referenced_image_paths`
and `transparent_background`. It does not expose a typed style-vs-identity field,
style weight, fixed seed, pinned model version, or session reset. Reference roles
are explicit prompt instructions and therefore still require output inspection.

## Commands

Use a fixed absolute folder for `$productionFolder`. Resolve the global active
pointer only once when dispatching work; all subsequent commands use this path.

```powershell
$productionFolder = 'C:/path/to/pov-automation/videos/production-folder'
python style_pipeline.py --production $productionFolder init --max-attempts 3
python style_pipeline.py --production $productionFolder prepare 1
python style_pipeline.py --production $productionFolder claim 1 'codex-session-worker-identifier'
```

Read the returned request's exact `tool_arguments`, inspect its references, and
call `image_gen.imagegen` with those arguments. Do not call the tool twice for a
claimed request. Do not supply recent conversation images. `prepare` is idempotent;
`claim` is deliberately single-use. If a call is interrupted, find its original
output first. No automatic lease expiry causes duplicate spending.

```powershell
python style_pipeline.py --production $productionFolder ingest 1 'C:/actual/tool-output.png' --receipt 'actual-tool-output-id'
python style_pipeline.py --production $productionFolder review-template 1
```

Save the template as a review JSON. **Open the actual candidate and canonical
images with `view_image` at full resolution before filling it.** All nine checks
and six image regions require specific observations. Set the actual evaluator,
`method=actual_images_viewed` and `full_resolution_viewed=true` only after this
inspection. Keep all provenance hashes unchanged. Mark uncertainties honestly.
There is no automatic numerical style score and no placeholder pass.

```powershell
python style_pipeline.py --production $productionFolder review 1 'C:/review.json'
python style_pipeline.py --production $productionFolder status
python style_pipeline.py --production $productionFolder verify
python style_pipeline.py contact-sheet 'C:/contact.jpg' 'C:/first.png' 'C:/second.png'
```

Any style, identity, story or composition failure/uncertainty blocks approval.
`not_applicable` is limited to absent characters/identity/backgrounds with reasons;
main-character identity cannot be waived. Failure requires a targeted `correction`.
Run `prepare` again to obtain the next request, then claim/generate/ingest/review.
The last bounded attempt explicitly rebuilds offending regions from simple
outlined shapes. Never weaken the global standard to accept a candidate.

Technical errors use a separate transition:

```powershell
python style_pipeline.py --production $productionFolder technical-failure 1 'actual error and recovery action'
```

After the configured total attempts, the scene becomes `needs_attention` and
generation stops for that scene. Continue independent scenes and report it.
Do not delete state or reinitialize to reset the attempt budget.

## Batch drift audits (review contract 2)

Authorities using review contract 2 require an individual style score (0 = close,
1 = acceptable variation, 2 = drift) for linework, face construction, colour
regions, cel shading, material rendering and background finish. A score of 2 or
an unexpected subject, period cue or prop prevents scene approval. After all
images in a batch pass individual review, generate the hash-bound audit packet:

```powershell
python style_pipeline.py --production $productionFolder checkpoint-template 1
```

Open the generated contact sheet, authority sheet and all approved images at full
resolution. Complete the JSON with the actual evaluator, observations, scores,
unexpected content and verdict, then submit it:

```powershell
python style_pipeline.py --production $productionFolder checkpoint 1 'C:/batch-review.json'
```

The first audit includes at least one scene of every class; later batches contain
20 scenes. A failed or uncertain audit must identify scenes for rework. Use
`reopen SCENE REASON`, then repeat generation and individual review before
re-auditing the batch. A passing audit is bound to exact approved-image and
reference hashes; changing or omitting any image invalidates it. The audit is a
human/model attestation supported by files, not an automated visual classifier.

## Storage, recovery and compatibility

- Each production has a UUID, absolute root, script hash, style hash and attempt
  bound in `images/style_state/manifest.sqlite3`. SQLite transactions serialize
  cooperating writers. Separate productions never share database, bank or output.
- Requests, references, raw shot text, normalizations, candidate hashes, actual
  tool receipt and full reviews are persisted. Canonical assets and script are
  verified on every operation. Script changes or copied folders fail closed;
  make a new explicit production with its revised script rather than attaching
  old approvals to changed content. Requests are never silently truncated.
- Candidate originals remain in `style_state`; compatible paths are maintained
  in `pending`, `approved`, `style_rejected`, `style_checked.txt`, `rejected.txt`.
  A stale pending file never overrides the actual hash-bound candidate. Unknown
  legacy rejection numbers are merged, not erased.
- Existing approved artwork is never replaced by default. After explicit user
  authorization, `review --replace-approved` first archives the original bytes.
- Old productions are not automatically enrolled or retroactively approved.
  Existing artwork is `legacy_unverified` after enrollment. To audit it, prepare
  the scene and ingest its existing approved PNG with receipt `legacy-audit:<path>`;
  no image-generation claim or call is needed. Review the actual image. Matching
  bytes may retain their existing approved path without replacement permission.
- Final-video assembly preserves legacy behavior for unenrolled productions.
  Once enrolled, **every scene** must have a current hash-bound visual pass;
  missing, pending, rejected and altered approved images block assembly.
- The generator cannot be invoked from this Python module: Codex remains the
  generation/vision operator. Review attestations are auditable, not proof that
  a human/model truly viewed pixels. Directly bypassing the bridge bypasses its
  controls; the POV skill and Codex workflow therefore require its use.

## Regression checks

From the repository root:

```powershell
python -m unittest discover -s pov-automation/tests -v
```

Tests use temporary folders and synthetic grey PNGs for state-machine checks.
Those fixtures are explicitly **not visual style evidence**. The 300-request
tests make no image-generation calls. Run this suite after changing the pipeline;
it does not require a production folder or external image-generation calls.
