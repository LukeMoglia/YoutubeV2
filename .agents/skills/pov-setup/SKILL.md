---
name: pov-setup
description: Guide a new user through configuring a fresh clone of the Hierarchy POV project for their channel. Use when setting up the repository, checking prerequisites, or preparing local configuration.
---

# Set up the Hierarchy POV project

Walk the user through a fresh clone, configure only the local settings they need, and report what is ready. The repository root must be open in Codex so it can discover `.agents/skills/`.

## Setup flow

1. Confirm the current workspace is the repository root by checking for `.git`, `.agents/skills/`, `POV niche/`, and `pov-automation/`. If not, explain how to open the cloned repository root and stop before writing files.
2. Read `POV niche/Codex Setup.md` and inspect the existence of local setup files. Do not print or expose `.env` values. Preserve existing settings and assets.
3. Explain that the default route uses Codex for script writing and Codex's built-in image tool (`IMAGE_PROVIDER=codex`). It needs no Claude or Kie API key. Ask for a channel name if `channel_config.txt` is missing or has no `CHANNEL_NAME`; accept the default `the channel` if the user prefers to continue without one.
4. Create or update `pov-automation/channel_config.txt` only after the channel name is known. Preserve unrelated existing keys and set only missing defaults:

   ```text
   CHANNEL_NAME=<user's channel name>
   IMAGE_PROVIDER=codex
   BRAND_COLOR_PRIMARY=#FFFFFF
   BRAND_COLOR_SECONDARY=#1A1A1A
   BRAND_COLOR_ACCENT=#E63946
   ```

   Never replace an existing value without asking. Do not add credentials to this file.
5. Check whether `pov-automation/character/character_ref.png` exists. Do not invent or download a protagonist image. If it is missing, tell the user to add their own image at that path before image work; continue with other setup steps.
6. Establish the channel's fixed art authority once during setup:
   - Explain which version is active (`v1` when `pov-automation/style/active_version.txt` is absent), and offer to keep the included approved style as-is.
   - If the user wants a channel-specific or content-neutral reference sheet, gather their chosen existing approved artwork and desired style traits. Use only user-selected, approved images as style sources; never use the latest generated scene or rejected images.
   - Prepare a neutral style-sheet and bible candidate that separates rendering technique from story subjects. Preserve the existing level of readable environmental detail and character identity; do not flatten or redesign the channel style just to make a sheet.
   - Show the candidate beside the source artwork at full resolution and explain any visible differences. Save candidates under a new version in `pov-automation/style/proposals/` with immutable asset hashes and `pending_user_approval` status.
   - Do not activate, change the active pointer, or change a production's recorded authority until the user explicitly approves the candidate. If the candidate does not match, revise it or keep the current approved version active.
   - Treat this as a one-time channel setup choice. Normal image generation reuses the fixed approved library; it must not create or replace reference sheets per scene or per video.
7. Check for a usable Python installation. The script finalizer needs Python 3.10 or newer; the documented audio environment uses Python 3.12. Check Pillow availability only if preparing the style/image or thumbnail tooling. Report missing prerequisites with the relevant setup document; do not install packages or heavyweight runtimes without the user's request.
8. Explain optional setup only if relevant to the user's chosen workflow:
   - Claude script generation needs `ANTHROPIC_API_KEY` in the ignored `pov-automation/.env` and may incur API charges.
   - The legacy Kie image route needs its provider credentials and configuration; leave `IMAGE_PROVIDER=codex` unless the user explicitly selects Kie.
   - Audio needs the isolated Chatterbox environment, a user-provided narrator reference audio file, and FFmpeg/ffprobe. Defer this setup until audio is requested; follow `POV niche/generate_audio_pov.md`.
   - Automated MP4 assembly also needs FFmpeg/ffprobe and completed scene images and audio; follow `POV niche/generate_final_pov.md`.
9. Finish with a short checklist of configured items, missing user-provided assets, active style version, and any unapproved style proposal. Point to `POV niche/Codex Setup.md` for the full workflow and the appropriate source document for any chosen optional stage.

## Local data and credentials

- Local config, the character reference, `.env`, audio runtime, and generated productions are ignored by Git. Never add them to version control.
- Never ask the user to paste a credential into chat. Tell them which local file/key name is needed and let them enter it locally. When checking credentials, check file existence or key presence without printing values.
- Do not generate video scripts, scene images, audio, or final videos during setup. A style-reference candidate is configuration, not scene content; create it only if the user chooses that setup step, and leave it pending until approved.
- Do not call paid providers, install dependencies, or download model weights during setup.
