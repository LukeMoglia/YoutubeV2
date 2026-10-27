# Style v2 proposal — pending approval

This folder contains a proposed neutral illustration-style sheet, a copy of the
existing protagonist identity reference, and a revised style bible. It is not
active. The neutral sheet contains generic face, hand, fabric, material and
landscape studies without story-specific Roman or kitchen subjects. The identity
image is byte-for-byte the existing v1 identity reference.

The proposal separates shared rendering technique from subject matter. All scene
classes would use the neutral style reference; only protagonist scenes would
also receive the identity image. The accompanying review contract adds numeric
style-drift scores, scene-content leakage checks, and hash-bound visual batch
audits every 20 scenes. Requests still use the built-in image tool, which does
not expose a pinned model, fixed seed, style weight or session reset. Those limits
mean that visual inspection remains necessary and no finite set of checks can
guarantee identical results across unlimited generations.

`manifest.json` is locked by `manifest.sha256`. Its status remains
`pending_user_approval`; do not activate or silently substitute it for v1. The
next step is for the user to review the neutral sheet and bible, then approve or
request changes before this proposal is promoted to an active version.

## Bounded visual validation (2026-10-27)

Two exact requests were prepared through the proposal pipeline and generated
with the built-in Codex image tool: a modern Michelin kitchen scene and a Roman
campaign-camp scene. The actual outputs are preserved in `validation/` for
comparison. Neither output showed the other production's equipment or setting,
so the neutral reference route avoided an obvious story-content leak in this
small sample.

Both were inspected at full resolution beside the proposed sheet and existing
v1 examples. The Roman camp remained a clean outlined illustration with simple
faces, broad colour regions and coherent detailed scenery; its six style scores
were 0 or 1, so it passed the bounded trial review. The modern kitchen scene
used the right content and medium, but glossy gradients and reflective equipment
scored 2 for cel shading, material rendering and background finish. It was
rejected with a targeted correction. This is evidence that context isolation
works in these two samples, while the candidate style authority still does not
reliably hold the kitchen rendering to the approved standard. Keep v1 active;
revise and revalidate v2 before considering activation.

These two outputs are a small stochastic sample, not proof of universal
consistency or a full production run. The synthetic regression tests described
in `../../README.md` verify pipeline state and gates, not artwork quality.
