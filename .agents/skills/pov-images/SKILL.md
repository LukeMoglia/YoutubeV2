---
name: pov-images
description: Generate or regenerate the scene images for the active Hierarchy POV video using the Kie.ai image API. Use when asked to generate POV images or retry rejected scenes.
---

# Generate POV scene images

Run the image workflow from `pov-automation/` at the repository root. Read source documents from the repository root; when your working directory is `pov-automation/`, prefix their paths with `../`.

## Instructions

1. Read `POV niche/generate_images_pov.md` and follow its current Python implementation and response parsing exactly. Do not use older snippets or change the Kie.ai result URL parsing.
2. Check `pov-automation/.env` and `pov-automation/channel_config.txt` for the required Kie.ai key and public `PROTAGONIST_URL`. Inspect key presence only; never display or log secret values.
3. Confirm the active script JSON exists and identify which scenes need images. Respect approved, pending, and rejected scene state so completed images are not charged again. Keep the route distinction: protagonist scenes get the reference; supporting and object scenes do not.
4. This stage makes paid Kie.ai requests and can take close to an hour for a full video. Before a new batch, tell the user the number of scenes and that image generation consumes account credits. Proceed when the user has requested image generation.
5. Use a bounded worker count as specified in the source. Run long jobs in a monitored shell session, report progress, and poll that same process to completion. If interrupted, inspect files and logs before retrying; the source workflow is resumable.
6. Report generated, skipped, and failed scene counts. Do not mark images approved; the user reviews pending images and moves accepted ones to `approved/`.
