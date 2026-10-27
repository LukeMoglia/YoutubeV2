# Style v2 proposal — pending approval

This folder contains a proposed neutral illustration-style sheet, a copy of the
existing protagonist identity reference, and a revised style bible. It is not
active. The neutral sheet contains generic character, hand, material, room and
landscape studies without story-specific equipment or period cues. The identity
image is byte-for-byte the existing v1 identity reference.

The proposal separates shared rendering technique from subject matter. All scene
classes would use the neutral style reference; only protagonist scenes would
also receive the identity image. The accompanying review contract adds numeric
style-drift scores, scene-content leakage checks, and hash-bound visual batch
audits every 20 scenes. Requests still use the built-in image tool, which does
not expose a pinned model, fixed seed, style weight or session reset. Visual
inspection remains necessary; no finite checks can guarantee identical results
across unlimited generations.

`manifest.json` is locked by `manifest.sha256`. Its status remains
`pending_user_approval`; do not activate or silently substitute it for v1. The
user should review the neutral sheet and bible before this proposal is promoted.

## Bounded visual validation (2026-10-27)

The same two isolated production scenes were prepared through the proposal
pipeline and generated with the built-in Codex image tool: a contemporary
Michelin kitchen and a first-century Roman campaign camp. The neutral-only style
route kept the scene content isolated in all samples; no kitchen equipment
appeared in the Roman scene and no Roman equipment appeared in the kitchen.

The first neutral sheet produced a kitchen frame with glossy gradients, reflective
steel and a softly rendered background. That image failed the style gate and is
preserved as `validation/modern-kitchen-trial.png`. I revised the reference sheet
and bible to require flat color planes, crisp outlines and hard-edged shadows.
A second kitchen sample still drifted, so it was also rejected. After a further
revision, a correction-guided retry produced the current `neutral_style_sheet.png`
and a kitchen frame with crisp outlines, flat fills and grouped background
equipment. The final kitchen review scored all six drift dimensions 0 or 1; the
Roman sample did as well. The two final outputs and separate batch contact-sheet
audits passed, and both one-scene sample productions verified through the gate.

The current kitchen retest is preserved as
`validation/modern-kitchen-flat-retest.png`; the matching Roman sample is
`validation/roman-camp-flat-retest.png`. These are bounded examples, not a full
300-image run. The automatic image tool does not expose a pinned model or seed,
so this limited pass cannot guarantee that future outputs never drift. The
production gates continue to require actual visual review and stop on any score
of 2, content leak, uncertainty, or failed batch audit.

The current reference and bible are ready for the user's review. The proposal
remains pending until approval; v1 remains active.
