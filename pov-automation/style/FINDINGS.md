# Visual style implementation — 26 October 2026

The existing Codex workflow is retained. A permanent style authority, request
builder, isolated production manifests and hash-bound visual review gate now
sit around it. No Kie restoration, third-party API or bulk regeneration was used.
No existing approved artwork, narration, captions or finished video was replaced.

## What caused drift

1. The local Codex route was agent-operated, one built-in tool call per image;
   the Python worker pool in the old documentation belonged to Kie. There was
   no executable Codex request builder or durable per-call provenance.
2. Instructions conflicted. Shared text demanded sparse, matte, two-tone scenes;
   the kitchen production explicitly recorded the user's preference for richer
   equipment detail and illustrated metal shading in approved scene 1. The
   global reference itself also contained more tonal variation than the strict
   prose allowed. Simply repeating those sentences could not resolve the target.
3. Per-video rendering anchors and editable style profiles could redefine the
   channel appearance between productions. Different retry instructions used
   different reference combinations. All of that depended on agent memory.
4. Canonical references were in an ignored local character folder and had no
   immutable hashes. `style_checked.txt` stored filenames rather than image
   bytes, style version, review findings or request identity. There were two
   checklist locations in the Roman production.
5. Existing approved images visibly varied: kitchen scenes 4 and 16 soften the
   background and introduce detailed reflective surfaces; scene 17 gives props
   a richer glossy/material treatment than scene 67. Approved did not mean a
   uniform rendering standard. These original files remain untouched.
6. The script finalizer had a literal Roman-clothing fallback and hard-coded
   protagonist/age strings. It could import Roman clothing into unrelated topics
   or override local character-bank refinements. Date + truncated topic folder
   names could also collide and overwrite a previous script.
7. Retries were unbounded in the Codex instructions. No assembly gate verified
   that an approved PNG was still the exact visually inspected candidate.

## What now enforces consistency

- `style/v1/STYLE_BIBLE.md`, six curated PNGs and a SHA-256 manifest establish one
  drawing system. They preserve the documented richer local treatment, shared
  warm-tan bald identity, and existing age/costume controls. They cover the nine
  reference roles without promoting new smoke-test images into the library.
- `style_pipeline.py` constructs every request from immutable global style,
  isolated video context and a unique shot. It removes legacy medium boilerplate,
  normalizes ambiguous positive medium modifiers, preserves negative exclusions
  and stores the original shot plus transformation log. It fails rather than
  truncating an oversized prompt.
- The actual supported `referenced_image_paths` parameter is used. Main shots
  receive fixed style plus identity; supporting scenes receive people style
  only; object-only shots receive a people-free style example. Reference roles
  are explicitly described. No generational chain or video-local style anchor.
- SQLite transactions persist a production UUID, script/style hashes, all
  attempts and reviews. Explicit folders replace repeated active-pointer reads.
  Separate productions have separate banks, manifests and candidates. Dispatch
  claims prevent cooperating workers from making duplicate calls.
- Codex opens the actual image and the canonical library. Nine independent
  checks and six regional observations are recorded; style failures cannot be
  compensated by correct identity or composition. Uncertainty blocks approval.
- Rejections preserve the original candidate and feed targeted corrections into
  a fresh canonical request. Default three total attempts, then needs_attention;
  the final attempt rebuilds offending regions from simple shapes. Identical
  previously failed tool arguments are blocked. Technical failures are separate.
- Assembly verifies every enrolled scene's current approved bytes. Legacy
  productions remain usable until deliberately enrolled; old approvals are not
  silently relabelled as v1 passes. Authorized replacements archive old artwork.

## Tests and actual evidence

Automated tests passed: see `evidence/structural-tests.txt`. The suite covers two
parallel 300-scene productions (600 requests), all four scene classifications,
complete style text, fixed reference hashes and settings, separate identities,
resumption and technical retries at 1/100/200/300, concurrent dispatch protection,
uncertainty/retry limits, review provenance, tampered references and approved
bytes, copied-folder rejection, original-art preservation, negative prompt
constraints and local character-bank preservation. These tests use synthetic
fixtures for approval-state checks and make **no artistic fidelity claim**.

Both existing scripts also passed isolated request preflight: Roman 296/296,
kitchen 257/257, **553 total**. No image calls or writes to those original
productions occurred. Results are in `evidence/existing-script-preflight.json`.
Python compilation passed for the bridge, finalizer, final-video assembler and
existing Chatterbox module. `git diff --check` passed; Git emitted only line-ending
warnings for unrelated existing local files. Full audio synthesis/video rendering
was not rerun because this change does not alter their processing algorithms.

Phase A reused inspected assets covering full body, close-up (identity sheet),
secondary people, interaction, building exterior, interior, landscape and object
views. `evidence/canonical-library.jpg` and `evidence/before-existing-approvals.jpg`
show the scope; the latter includes inconsistent historical approvals as evidence,
not newly approved masters. `evidence/calibration.json` records exact hashes and
qualitative expected pass/fail observations for the reference assets and the real
smoke-test failures/corrections. This is reviewer calibration, not a trained or
quantitatively validated automatic classifier.

Phase B/D used two distinct fictional contexts with the same authority:

| Actual output | Initial review | Corrected review | Leakage observations |
|---|---|---|---|
| 1890 railway-workshop pocket watch | FAIL: scratches, dense wood grain, soft distance, extra tools | PASS after targeted redraw: smooth illustrated bands, simple bench, watch/chain only | No kitchen subjects or people transferred from object reference |
| Contemporary submarine officer | FAIL: white sclera, different face construction, fine map/panel texture, wrong hair | PASS after targeted redraw: solid oval eyes, short curls, simplified map and equipment | No Roman clothes, weapons, banners or architecture transferred from people reference |

**Four built-in image calls total; four actual candidates inspected; two rejected,
two approved after one retry each; zero unresolved smoke scenes.** Both isolated
smoke production manifests pass the assembly verification gate. The second scene
was generated after the first in the same chat; explicit inputs plus review
prevented visible subject transfer in this small observed sample. Structural
parallelism was tested; paid image generation was intentionally sequential.

`evidence/smoke-before-after.jpg`: each row is initial failure, corrected result,
canonical generation reference. Full-resolution before/after PNGs, exact request
JSON and individual reviews are included beside it. The immutable authority was
not changed after seeing failures. The evidence demonstrates actual improvement
from targeted corrections, not a statistically controlled old-vs-new model study.

## Files added or changed for this task

- Added `pov-automation/style_pipeline.py`, `pov-automation/tests/test_style_pipeline.py`.
- Added `pov-automation/style/v1/` bible, manifests and six references.
- Added `pov-automation/style/README.md`, this report and `style/evidence/` artifacts.
- Added `.gitattributes` to prevent newline conversion invalidating the locked bytes.
- Updated `.agents/skills/pov-images/SKILL.md` and `POV niche/generate_images_codex.md`
  to require the bridge and remove conflicting/unbounded Codex instructions.
- Updated `POV niche/finalize_pov_script.py` to preserve bank identity/age,
  reject missing costumes, use unique production folder suffixes and atomically
  update the interactive current-folder pointer. Updated the POV script skill
  and script instructions to isolate draft files per job and pass returned
  production folders directly to downstream parallel workers.
- Updated `pov-automation/generate_final_video.py` with the enrolled-production gate.
- Added Codex authority pointers to `generate_images_pov.md`, `generate_script_pov.md`
  and `Hierarchy_POV_Claude_Code_Automation_System_v38.md`; preserved legacy code.
- Added two isolated smoke folders under ignored `pov-automation/videos/`; did not
  change the active production pointer. Other pre-existing local changes remain.

## Unavoidable practical limits

The tool exposes neither a fresh-session guarantee nor hard style/identity
separation, pinned model/seed, or programmatic vision endpoint. The bridge cannot
call the image tool from Python, cryptographically prove that a reviewer viewed
pixels, or guarantee zero hallucinations. Codex must execute the generation and
real visual-review loop specified in the skill. Direct bypasses also bypass the
gate. Style checks are qualitative observations, without invented confidence.

These tests support improved practical consistency and fail-closed review, not
perfect fidelity across unlimited future generations. Every future candidate
still needs visual comparison. A full 300-image visual re-audit was neither
claimed nor performed. Existing historical artwork has not been regenerated.
