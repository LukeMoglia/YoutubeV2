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
6. Check for a usable Python installation. The script finalizer needs Python 3.10 or newer; the documented audio environment uses Python 3.12. Check Pillow availability only if preparing the style/image or thumbnail tooling. Report missing prerequisites with the relevant setup document; do not install packages or heavyweight runtimes without the user's request.
7. Explain optional setup only if relevant to the user's chosen workflow:
   - Claude script generation needs `ANTHROPIC_API_KEY` in the ignored `pov-automation/.env` and may incur API charges.
   - The legacy Kie image route needs its provider credentials and configuration; leave `IMAGE_PROVIDER=codex` unless the user explicitly selects Kie.
   - Audio needs the isolated Chatterbox environment, a user-provided narrator reference audio file, and FFmpeg/ffprobe. Defer this setup until audio is requested; follow `POV niche/generate_audio_pov.md`.
   - Automated MP4 assembly also needs FFmpeg/ffprobe and completed scene images and audio; follow `POV niche/generate_final_pov.md`.
8. Finish with a short checklist of configured items, missing user-provided assets, and optional steps deferred. Point to `POV niche/Codex Setup.md` for the full workflow and the appropriate source document for any chosen optional stage.

## Local data and credentials

- Local config, the character reference, `.env`, audio runtime, and generated productions are ignored by Git. Never add them to version control.
- Never ask the user to paste a credential into chat. Tell them which local file/key name is needed and let them enter it locally. When checking credentials, check file existence or key presence without printing values.
- Do not generate content, call paid providers, install dependencies, or download model weights during setup. These are separate user-requested workflow steps.
