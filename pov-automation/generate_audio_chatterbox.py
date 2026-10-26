"""Generate POV scene narration locally with expressive Chatterbox.

Run from the repository root with the dedicated Chatterbox Python environment.
The script prefers CUDA, falls back to CPU if CUDA/model loading fails or
the GPU runs out of memory, and resumes by skipping complete MP3s.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def is_cuda_compat_or_oom(exc: BaseException) -> bool:
    message = str(exc).lower()
    markers = (
        "out of memory",
        "no kernel image is available",
        "invalid device function",
        "not compiled with cuda",
        "not compatible with the current pytorch installation",
        "unsupported gpu architecture",
        "unsupported cuda",
        "unsupported device",
        "cuda driver",
        "driver version",
        "cuda runtime",
        "no cuda gpus are available",
        "compute capability",
        "sm_61",
    )
    return any(marker in message for marker in markers)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
    automation_dir = Path(__file__).resolve().parent
    env = read_env(automation_dir / ".env")
    pointer = automation_dir / "videos/current_video_folder.txt"
    if not pointer.exists():
        print("ERROR: videos/current_video_folder.txt is missing.", flush=True)
        return 1

    video_folder = Path(pointer.read_text(encoding="utf-8-sig").strip())
    if not video_folder.is_absolute():
        video_folder = automation_dir / video_folder
    script_path = video_folder / "current_script.json"
    if not script_path.exists():
        print(f"ERROR: active script is missing: {script_path}", flush=True)
        return 1

    script = json.loads(script_path.read_text(encoding="utf-8"))
    scenes = script["scenes"]
    total = len(scenes)
    missing = [
        scene["scene_number"]
        for scene in scenes
        if not (video_folder / "images/approved" / f"scene_{scene['scene_number']:03d}.png").exists()
    ]
    if missing:
        print(f"ERROR: {len(missing)} approved images are missing: {missing}", flush=True)
        return 1

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ERROR: ffmpeg is required to convert generated WAV files to MP3.", flush=True)
        return 1
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        print("ERROR: ffprobe is required to validate MP3s and create accurate subtitles.", flush=True)
        return 1

    def is_valid_mp3(path: Path) -> bool:
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return float(result.stdout.strip()) > 0
        except (OSError, subprocess.SubprocessError, ValueError):
            return False

    try:
        import torch
        import torchaudio
        from chatterbox.tts import ChatterboxTTS
    except ImportError as exc:
        print(
            "ERROR: Chatterbox is not installed in this Python environment. "
            "Follow the local setup commands in POV niche/generate_audio_pov.md.",
            flush=True,
        )
        print(f"Import detail: {exc}", flush=True)
        return 1

    audio_dir = video_folder / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    reference_value = env.get("CHATTERBOX_REFERENCE_AUDIO", "").strip().strip('"')
    reference_audio = None
    reference_wav = None
    if reference_value:
        reference_audio = Path(reference_value).expanduser()
        if not reference_audio.is_absolute():
            reference_audio = Path(__file__).resolve().parents[1] / reference_audio
        if not reference_audio.is_file():
            print(f"ERROR: CHATTERBOX_REFERENCE_AUDIO does not exist: {reference_audio}", flush=True)
            return 1
        print(f"Using male voice reference: {reference_audio}", flush=True)
        try:
            reference_offset = max(0.0, float(env.get("CHATTERBOX_REFERENCE_OFFSET_SECONDS", "0")))
        except ValueError:
            print("ERROR: CHATTERBOX_REFERENCE_OFFSET_SECONDS must be a number.", flush=True)
            return 1
        reference_wav = Path(tempfile.gettempdir()) / f"chatterbox_voice_reference_{os.getpid()}.wav"
        try:
            subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(reference_offset),
                 "-t", "15", "-i", str(reference_audio), "-vn", "-ac", "1", "-ar", "24000",
                 "-c:a", "pcm_s16le", str(reference_wav)],
                check=True,
                capture_output=True,
                text=True,
            )
            if not is_valid_mp3(reference_wav):
                # ffprobe's duration probe works for WAV too; keep validation generic.
                raise RuntimeError("Could not validate the extracted voice reference clip.")
        except Exception as exc:
            reference_wav.unlink(missing_ok=True)
            print(f"ERROR: could not extract the voice reference clip: {exc}", flush=True)
            return 1
    force_regenerate = env.get("CHATTERBOX_FORCE_REGENERATE", "false").lower() in {"1", "true", "yes", "on"}
    if force_regenerate:
        print("Force regeneration is enabled; existing MP3s will be replaced from scene 1.", flush=True)
    failed: list[int] = []
    completed = 0
    skipped = 0
    fatal_setup_error: str | None = None
    started = time.time()
    requested_device = env.get("CHATTERBOX_DEVICE", "auto").lower()
    cuda_available = torch.cuda.is_available()
    device = "cuda" if requested_device in {"auto", "cuda"} and cuda_available else "cpu"
    fallback_reason = None
    if device == "cpu" and requested_device in {"auto", "cuda"}:
        fallback_reason = "CUDA is unavailable in this PyTorch environment."

    exaggeration = float(env.get("CHATTERBOX_EXAGGERATION", "0.6"))
    cfg_weight = float(env.get("CHATTERBOX_CFG_WEIGHT", "0.3"))
    eq_filter = env.get(
        "CHATTERBOX_EQ_FILTER",
        "bass=g=1.1:f=160:w=0.7,treble=g=-0.6:f=5500",
    )

    def load_model(target_device: str):
        print(f"Loading expressive Chatterbox on {target_device.upper()}...", flush=True)
        return ChatterboxTTS.from_pretrained(device=target_device)

    def prepare_reference(target_model) -> None:
        if reference_wav:
            print("Preparing the voice reference once for the scene batch...", flush=True)
            target_model.prepare_conditionals(str(reference_wav), exaggeration=exaggeration)

    try:
        model = load_model(device)
        prepare_reference(model)
    except Exception as exc:
        if device != "cuda":
            print(f"SETUP ERROR: could not load Chatterbox on CPU: {exc}", flush=True)
            print(f"Newly generated: 0; skipped: 0; failed scenes: {total}.", flush=True)
            return 1
        if not is_cuda_compat_or_oom(exc):
            print(f"SETUP ERROR: CUDA model initialization failed: {exc}", flush=True)
            print("No CPU fallback was attempted because this does not look like a CUDA compatibility or VRAM error.", flush=True)
            print(f"Newly generated: 0; skipped: 0; failed scenes: {total}.", flush=True)
            return 1
        print(f"CUDA model load failed; switching to CPU ({exc})", flush=True)
        fallback_reason = f"CUDA model initialization failed: {exc}"
        torch.cuda.empty_cache()
        device = "cpu"
        try:
            model = load_model(device)
            prepare_reference(model)
        except Exception as cpu_exc:
            print(f"SETUP ERROR: could not load Chatterbox on CPU: {cpu_exc}", flush=True)
            print(f"Newly generated: 0; skipped: 0; failed scenes: {total}.", flush=True)
            return 1

    if device == "cuda":
        props = torch.cuda.get_device_properties(0)
        print(f"Using {props.name} ({props.total_memory / (1024**3):.1f} GB VRAM).", flush=True)
    else:
        print(f"Using CPU. {fallback_reason or 'CPU was selected in CHATTERBOX_DEVICE.'}", flush=True)
        print("No external TTS service or account quota is used.", flush=True)

    for scene in scenes:
        if model is None:
            fatal_setup_error = "No Chatterbox model is loaded; stopped before the next scene."
            break
        number = scene["scene_number"]
        final_mp3 = audio_dir / f"scene_{number:03d}.mp3"
        if not force_regenerate and final_mp3.exists() and final_mp3.stat().st_size > 1024 and is_valid_mp3(final_mp3):
            print(f"[SKIP] Scene {number}: complete MP3 already exists.", flush=True)
            skipped += 1
            continue
        if final_mp3.exists():
            final_mp3.unlink()

        temp_wav = audio_dir / f"scene_{number:03d}.{os.getpid()}.wav"
        temp_mp3 = audio_dir / f"scene_{number:03d}.{os.getpid()}.part.mp3"
        try:
            with torch.inference_mode():
                wav = model.generate(scene["voiceover"], exaggeration=exaggeration, cfg_weight=cfg_weight)
            torchaudio.save(str(temp_wav), wav.cpu(), model.sr)
            subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(temp_wav),
                    "-af",
                    eq_filter,
                    "-codec:a",
                    "libmp3lame",
                    "-q:a",
                    "2",
                    str(temp_mp3),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            if not is_valid_mp3(temp_mp3):
                raise RuntimeError("FFmpeg output is not a valid MP3.")
            os.replace(temp_mp3, final_mp3)
            completed += 1
            processed = completed + skipped
            if processed % 10 == 0 or processed == total:
                print(f"Progress: {processed}/{total} scenes ({completed} generated, {skipped} skipped).", flush=True)
        except Exception as exc:
            if device == "cuda" and is_cuda_compat_or_oom(exc):
                print(f"Scene {number}: CUDA generation failed; switching to CPU and retrying ({exc}).", flush=True)
                try:
                    del model
                    model = None
                    fallback_reason = f"CUDA inference failed on scene {number}: {exc}"
                    torch.cuda.empty_cache()
                    device = "cpu"
                    model = load_model(device)
                    prepare_reference(model)
                    with torch.inference_mode():
                        wav = model.generate(scene["voiceover"], exaggeration=exaggeration, cfg_weight=cfg_weight)
                    torchaudio.save(str(temp_wav), wav.cpu(), model.sr)
                    subprocess.run(
                        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(temp_wav),
                         "-af", eq_filter,
                         "-codec:a", "libmp3lame", "-q:a", "2", str(temp_mp3)],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    if not is_valid_mp3(temp_mp3):
                        raise RuntimeError("FFmpeg CPU-fallback output is not a valid MP3.")
                    os.replace(temp_mp3, final_mp3)
                    completed += 1
                    print(f"[OK] Scene {number} generated on CPU.", flush=True)
                except Exception as cpu_exc:
                    failed.append(number)
                    fatal_setup_error = f"CPU fallback failed on scene {number}: {cpu_exc}"
                    print(f"SETUP ERROR: {fatal_setup_error}", flush=True)
                    print("Stopping because no model is available for the remaining scenes.", flush=True)
                    model = None
                    break
            else:
                failed.append(number)
                print(f"[FAIL] Scene {number} ({device} inference): {exc}", flush=True)
        finally:
            temp_wav.unlink(missing_ok=True)
            temp_mp3.unlink(missing_ok=True)

    elapsed = (time.time() - started) / 60
    print(f"\nNewly generated: {completed}; already present and skipped: {skipped}; expected total: {total}.", flush=True)
    print(f"Failed scene count: {len(failed)}; failed scenes: {failed}", flush=True)
    print(f"Elapsed: {elapsed:.1f} min. Device at end: {device.upper()}.", flush=True)
    if fallback_reason:
        print(f"CPU fallback reason: {fallback_reason}", flush=True)
    if fatal_setup_error:
        print(f"Setup stop reason: {fatal_setup_error}", flush=True)
    if reference_wav:
        reference_wav.unlink(missing_ok=True)
    # Build subtitles from the exact final MP3 durations so timings include the
    # generated pacing and encoding delay, and the script text stays in sync.
    if not failed and not fatal_setup_error and completed + skipped == total:
        def srt_time(seconds: float) -> str:
            total_ms = int(round(seconds * 1000))
            hours, rem = divmod(total_ms, 3_600_000)
            minutes, rem = divmod(rem, 60_000)
            seconds_int, milliseconds = divmod(rem, 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"

        entries: list[str] = []
        current_time = 0.0
        for scene in scenes:
            number = scene["scene_number"]
            audio_path = audio_dir / f"scene_{number:03d}.mp3"
            probe = subprocess.run(
                [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)],
                check=True, capture_output=True, text=True,
            )
            duration = float(json.loads(probe.stdout)["format"]["duration"])
            entries.extend([
                str(number),
                f"{srt_time(current_time)} --> {srt_time(current_time + duration)}",
                scene["voiceover"],
                "",
            ])
            current_time += duration
        final_output = video_folder / "final_output"
        final_output.mkdir(parents=True, exist_ok=True)
        srt_path = final_output / "subtitles.srt"
        srt_path.write_text("\n".join(entries), encoding="utf-8")
        print(f"[OK] Subtitle file: {srt_path}", flush=True)
        print(f"Combined audio duration: {current_time/60:.1f} minutes.", flush=True)
    print(f"Provider: Chatterbox expressive (local); failed scenes: {failed}", flush=True)
    return 1 if failed or fatal_setup_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
