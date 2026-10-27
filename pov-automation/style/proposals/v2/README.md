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
