"""Assemble the active POV project with gentle Ken Burns zoom and captions."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont
from generate_thumbnail import make_thumbnail, write_upload_metadata

FPS = 30
WIDTH = 1920
HEIGHT = 1080
PROFILE = "kenburns-burned-captions-v4"
CARD_PROFILE = "black-level-card-v3-complete-narration"
CARD_DURATION = 2.0
LEVEL_WORDS = {
    1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE",
    6: "SIX", 7: "SEVEN", 8: "EIGHT", 9: "NINE", 10: "TEN",
}
CAPTION_STYLE = (
    "FontName=Arial,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
    "Alignment=2,MarginV=14"
)


def run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=capture, text=True)


def probe_duration(ffprobe: str, path: Path) -> float:
    result = run([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(result.stdout.strip())


def probe_stream_durations(ffprobe: str, path: Path) -> tuple[float, float]:
    result = run([
        ffprobe, "-v", "error", "-show_entries", "stream=codec_type,duration",
        "-of", "json", str(path),
    ])
    streams = json.loads(result.stdout).get("streams", [])
    video = next((float(s["duration"]) for s in streams if s.get("codec_type") == "video" and s.get("duration")), 0.0)
    audio = next((float(s["duration"]) for s in streams if s.get("codec_type") == "audio" and s.get("duration")), 0.0)
    return video, audio


def srt_time(seconds: float) -> str:
    ms_total = int(round(seconds * 1000))
    hours, rest = divmod(ms_total, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds_part, milliseconds = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_part:02d},{milliseconds:03d}"


def wrap_caption(text: str, width: int = 44) -> str:
    return "\n".join(textwrap.wrap(" ".join(text.split()), width=width, break_long_words=False))


def remove_level_heading(text: str) -> str:
    """Avoid repeating the heading already shown on a level title card."""
    return re.sub(
        r"^\s*level\s+(?:\d+|[a-z]+)\s*[,.:\-–—]\s*[^.!?]+[.!?]\s*",
        "", text, count=1, flags=re.IGNORECASE,
    ).strip()


def detect_heading_split(ffmpeg: str, audio: Path) -> tuple[float, float, float]:
    """Find the pause after the full level heading.

    The narrator often pauses after saying "Level one" before saying the
    rank name. Select the second substantial pause, which follows the full
    heading, and ignore short internal pauses between words in a rank name.
    """
    result = subprocess.run([
        ffmpeg, "-hide_banner", "-i", str(audio),
        "-af", "silencedetect=noise=-35dB:d=0.12", "-f", "null", "NUL",
    ], capture_output=True, text=True)
    log = result.stderr
    starts = [float(value) for value in re.findall(r"silence_start: ([0-9.]+)", log)]
    ends = [float(value) for value in re.findall(r"silence_end: ([0-9.]+)", log)]
    intervals = list(zip(starts, ends))
    # Skip initial encoder padding and ignore brief pauses inside multiword
    # rank names (for example, "camp prefect").
    initial_end = ends[0] if starts and starts[0] == 0 else 0.0
    candidates = [
        (start, end) for start, end in intervals
        if start >= 0.30 and 0.15 <= end - start <= 1.2 and end <= 3.5
    ]
    if len(candidates) < 2:
        raise RuntimeError(f"Could not find the pause after the complete level heading in {audio.name}.")
    heading_end, scene_start = candidates[1]
    if heading_end <= initial_end:
        raise RuntimeError(f"Could not find a usable level heading boundary in {audio.name}.")
    return initial_end, heading_end, scene_start


def trim_audio(ffmpeg: str, source: Path, destination: Path, start: float, end: float) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{start:.6f}", "-i", str(source), "-t", f"{end-start:.6f}",
        "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(destination),
    ], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1200:])


def escape_filter_path(path: Path) -> str:
    # FFmpeg filter syntax treats a Windows drive colon as a separator.
    return path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")


def get_level_titles(scenes: list[dict], script: dict) -> dict[int, tuple[str, str]]:
    """Read each level's name from its first voiceover line."""
    result: dict[int, tuple[str, str]] = {}
    explicit = script.get("level_names", {})
    for scene in scenes:
        level = scene.get("level")
        if not isinstance(level, int) or level in result:
            continue
        role = scene.get("level_name") or explicit.get(str(level)) or explicit.get(level)
        if not role:
            match = re.match(
                r"^\s*level\s+(?:\d+|[a-z]+)\s*[,.:\-–—]\s*([^.!?]+)",
                str(scene.get("voiceover", "")), re.IGNORECASE,
            )
            role = match.group(1).strip() if match else ""
        if not role:
            raise ValueError(f"Cannot determine the name for level {level} from the script.")
        role = re.sub(r"\s+", " ", str(role)).strip().upper()
        level_label = f"LEVEL {LEVEL_WORDS.get(level, str(level))}"
        result[level] = (level_label, role)
    return result


def make_level_card_png(path: Path, level_label: str, role: str) -> None:
    """Create a plain black card with only the level label and level name."""
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    font_file = Path("C:/Windows/Fonts/arialbd.ttf")
    if not font_file.exists():
        font_file = Path("C:/Windows/Fonts/arial.ttf")
    try:
        small = ImageFont.truetype(str(font_file), 54)
        large = ImageFont.truetype(str(font_file), 88)
    except OSError:
        small = large = ImageFont.load_default()

    first = draw.textbbox((0, 0), level_label, font=small)
    second = draw.textbbox((0, 0), role, font=large)
    first_h = first[3] - first[1]
    second_h = second[3] - second[1]
    gap = 28
    top = (HEIGHT - first_h - gap - second_h) // 2
    first_w = first[2] - first[0]
    draw.text(((WIDTH-first_w)//2, top-first[1]), level_label, fill=(255,255,255), font=small)
    second_w = second[2] - second[0]
    draw.text(((WIDTH-second_w)//2, top+first_h+gap-second[1]), role, fill=(255,255,255), font=large)
    image.save(path)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
    root = Path(__file__).resolve().parent
    pointer = root / "videos/current_video_folder.txt"
    if not pointer.is_file():
        print(f"ERROR: active video pointer is missing: {pointer}")
        return 1
    folder = Path(pointer.read_text(encoding="utf-8-sig").strip())
    if not folder.is_absolute():
        folder = root / folder
    folder = folder.resolve()
    script_path = folder / "current_script.json"
    if not script_path.is_file():
        print(f"ERROR: active script is missing: {script_path}")
        return 1
    data = json.loads(script_path.read_text(encoding="utf-8"))
    scenes = data["scenes"]
    total = len(scenes)
    from style_pipeline import verify_for_assembly
    try:
        verify_for_assembly(folder)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    try:
        level_titles = get_level_titles(scenes, data)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    missing_images = []
    missing_audio = []
    for scene in scenes:
        n = int(scene["scene_number"])
        if not (folder / "images/approved" / f"scene_{n:03d}.png").is_file():
            missing_images.append(n)
        if not (folder / "audio" / f"scene_{n:03d}.mp3").is_file():
            missing_audio.append(n)
    if missing_images or missing_audio:
        if missing_images:
            print(f"ERROR: missing approved images for scenes: {missing_images}")
        if missing_audio:
            print(f"ERROR: missing audio for scenes: {missing_audio}")
        return 1

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        print("ERROR: both ffmpeg and ffprobe must be available on PATH.")
        return 1

    clips = folder / "clips"
    output = folder / "final_output"
    clips.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    title_dir = clips / "title_cards"
    title_dir.mkdir(parents=True, exist_ok=True)
    level_openings: dict[int, dict[str, float | int | Path]] = {}
    first_scene_by_level: dict[int] = {}
    for scene in scenes:
        first_scene_by_level.setdefault(int(scene["level"]), scene)
    for level, scene in first_scene_by_level.items():
        n = int(scene["scene_number"])
        source_audio = folder / "audio" / f"scene_{n:03d}.mp3"
        try:
            speech_start, heading_end, scene_start = detect_heading_split(ffmpeg, source_audio)
            card_duration = max(
                CARD_DURATION,
                (int((scene_start - speech_start + 0.0999) * 10) / 10),
            )
            heading_audio = title_dir / f"level_{level:02d}_narration.mp3"
            scene_audio = title_dir / f"level_{level:02d}_scene_audio.mp3"
            trim_audio(ffmpeg, source_audio, heading_audio, speech_start, heading_end)
            trim_audio(ffmpeg, source_audio, scene_audio, scene_start, probe_duration(ffprobe, source_audio))
            level_openings[level] = {
                "scene_number": n, "speech_start": speech_start,
                "heading_end": heading_end, "scene_start": scene_start,
                "card_duration": card_duration, "heading_audio": heading_audio,
                "scene_audio": scene_audio,
            }
            print(
                f"[OK] Level {level} heading ends at {heading_end:.2f}s; "
                f"the card stays for {card_duration:.1f}s before the scene."
            )
        except Exception as exc:
            print(f"ERROR: Could not move level {level} narration onto its title card: {exc}")
            return 1
    render_started = time.time()
    failures: list[tuple[int, str]] = []
    elapsed_durations: dict[int, float] = {}

    print(f"Rendering {total} scenes at {WIDTH}x{HEIGHT}/{FPS}fps with gentle zoom and burned captions.")
    print("Captions: bold white text with a black outline, centered near the bottom.")

    with tempfile.TemporaryDirectory(prefix="pov-captions-") as caption_tmp:
        caption_dir = Path(caption_tmp)
        seen_levels: set[int] = set()
        for index, scene in enumerate(scenes, start=1):
            n = int(scene["scene_number"])
            level = int(scene["level"])
            image = folder / "images/approved" / f"scene_{n:03d}.png"
            audio = folder / "audio" / f"scene_{n:03d}.mp3"
            if level in level_openings and int(level_openings[level]["scene_number"]) == n:
                audio = Path(level_openings[level]["scene_audio"])
            clip = clips / f"scene_{n:03d}.mp4"
            marker = clips / f".scene_{n:03d}.render-profile"
            caption_file = caption_dir / f"scene_{n:03d}.srt"
            try:
                caption_text = str(scene["voiceover"])
                caption_profile = PROFILE
                if level not in seen_levels:
                    caption_text = remove_level_heading(caption_text) or caption_text
                    if caption_text != scene["voiceover"]:
                        caption_profile = f"{PROFILE}:complete-heading-on-title-card"
                    seen_levels.add(level)
                if (clip.is_file() and clip.stat().st_size > 4096 and marker.is_file()
                        and marker.read_text(encoding="utf-8").strip() == caption_profile):
                    try:
                        clip_duration = probe_duration(ffprobe, clip)
                        if clip_duration > 0:
                            elapsed_durations[n] = clip_duration
                            if index % 25 == 0 or index == total:
                                print(f"Progress: {index}/{total} clips (resumed existing render).")
                            continue
                    except (OSError, subprocess.SubprocessError, ValueError):
                        pass

                audio_duration = probe_duration(ffprobe, audio)
                caption_file.write_text(
                    f"1\n00:00:00,000 --> {srt_time(audio_duration)}\n{wrap_caption(caption_text)}\n",
                    encoding="utf-8",
                )
                caption_path = escape_filter_path(caption_file)
                graph = (
                    "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,"
                    "crop=1920:1080,"
                    "zoompan=z='min(zoom+0.0005,1.08)':"
                    "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                    "d=1:s=1920x1080:fps=30,"
                    f"subtitles=filename='{caption_path}':force_style='{CAPTION_STYLE}'[v]"
                )
                temp_clip = clips / f".tmp_scene_{n:03d}.mp4"
                command = [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-loop", "1", "-framerate", str(FPS), "-i", str(image),
                    "-i", str(audio), "-filter_complex", graph,
                    "-map", "[v]", "-map", "1:a:0", "-t", f"{audio_duration:.6f}",
                    "-r", str(FPS), "-fps_mode", "cfr",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(temp_clip),
                ]
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode:
                    temp_clip.unlink(missing_ok=True)
                    raise RuntimeError(result.stderr[-1200:])
                os.replace(temp_clip, clip)
                marker.write_text(caption_profile, encoding="utf-8")
                elapsed_durations[n] = probe_duration(ffprobe, clip)
                if index % 10 == 0 or index == total:
                    print(f"Progress: {index}/{total} scenes rendered.")
            except Exception as exc:
                failures.append((n, str(exc)))
                print(f"[FAIL] Scene {n}: {exc}")
                if len(failures) >= 3:
                    print("Stopping after three clip failures; fix the cause and rerun to resume.")
                    break

    if failures:
        print(f"Failed scene numbers: {[n for n, _ in failures]}")
        return 1

    # Add a plain black title card before the first scene of every level.
    title_card_paths: dict[int, Path] = {}
    title_card_durations: dict[int, float] = {}
    for level, (level_label, role_name) in level_titles.items():
        card_png = title_dir / f"level_{level:02d}.png"
        card_mp4 = title_dir / f"level_{level:02d}.mp4"
        card_marker = title_dir / f".level_{level:02d}.profile"
        title_card_paths[level] = card_mp4
        if (card_mp4.is_file() and card_mp4.stat().st_size > 4096 and card_marker.is_file()
                and card_marker.read_text(encoding="utf-8").strip() == CARD_PROFILE):
            try:
                card_video_duration, _ = probe_stream_durations(ffprobe, card_mp4)
                if card_video_duration > 0:
                    title_card_durations[level] = card_video_duration
                    continue
            except (OSError, subprocess.SubprocessError, ValueError):
                pass

        try:
            make_level_card_png(card_png, level_label, role_name)
            temp_card = title_dir / f".tmp_level_{level:02d}.mp4"
            narration = Path(level_openings[level]["heading_audio"])
            result = subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-loop", "1", "-framerate", str(FPS), "-i", str(card_png),
                "-i", str(narration), "-map", "0:v:0", "-map", "1:a:0",
                "-af", f"apad=pad_dur={float(level_openings[level]['card_duration']):.3f}",
                "-t", f"{float(level_openings[level]['card_duration']):.3f}",
                "-r", str(FPS), "-fps_mode", "cfr", "-vf", "setsar=1,format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(temp_card),
            ], capture_output=True, text=True)
            if result.returncode:
                temp_card.unlink(missing_ok=True)
                raise RuntimeError(result.stderr[-1200:])
            os.replace(temp_card, card_mp4)
            card_marker.write_text(CARD_PROFILE, encoding="utf-8")
            card_video_duration, _ = probe_stream_durations(ffprobe, card_mp4)
            title_card_durations[level] = card_video_duration or probe_duration(ffprobe, card_mp4)
            print(f"[OK] Title card: {level_label} — {role_name}")
        except Exception as exc:
            print(f"[FAIL] Level {level} title card: {exc}")
            return 1

    # The external SRT follows video clip timing, including spoken headings on
    # their black cards and the remaining opening narration on the scene image.
    srt_entries: list[str] = []
    cursor = 0.0
    previous_level = None
    srt_number = 1
    for scene in scenes:
        n = int(scene["scene_number"])
        level = int(scene["level"])
        if level != previous_level:
            card_start = cursor
            cursor += title_card_durations[level]
            previous_level = level
            opening = level_openings[level]
            heading = re.match(
                r"^\s*(level\s+(?:\d+|[a-z]+)\s*[,.:\-–—]\s*[^.!?]+[.!?])",
                str(scene["voiceover"]), re.IGNORECASE,
            )
            if not heading:
                print(f"ERROR: could not extract spoken heading for level {level}.")
                return 1
            heading_start = float(opening["speech_start"])
            heading_end = float(opening["heading_end"])
            srt_entries.extend([
                str(srt_number),
                f"{srt_time(card_start + heading_start)} --> {srt_time(card_start + heading_end)}",
                heading.group(1).strip(), "",
            ])
            srt_number += 1
        duration = elapsed_durations.get(n)
        if duration is None:
            print(f"ERROR: no duration available for scene {n}.")
            return 1
        caption_text = str(scene["voiceover"])
        if level in level_openings and int(level_openings[level]["scene_number"]) == n:
            caption_text = remove_level_heading(caption_text) or caption_text
        srt_entries.extend([str(srt_number), f"{srt_time(cursor)} --> {srt_time(cursor + duration)}", caption_text, ""])
        srt_number += 1
        cursor += duration
    srt_path = output / "subtitles.srt"
    srt_path.write_text("\n".join(srt_entries), encoding="utf-8")

    concat_list = clips / "concat_list.txt"
    with concat_list.open("w", encoding="utf-8", newline="\n") as handle:
        previous_level = None
        for scene in scenes:
            n = int(scene["scene_number"])
            level = int(scene["level"])
            if level != previous_level:
                card_path = title_card_paths[level].resolve().as_posix().replace("'", "'\\''")
                handle.write(f"file '{card_path}'\n")
                previous_level = level
            clip_path = (clips / f"scene_{n:03d}.mp4").resolve().as_posix().replace("'", "'\\''")
            handle.write(f"file '{clip_path}'\n")

    final_video = output / "final_video.mp4"
    temp_final = output / "final_video.part.mp4"
    result = subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy", "-movflags", "+faststart", str(temp_final),
    ], capture_output=True, text=True)
    if result.returncode:
        temp_final.unlink(missing_ok=True)
        print(f"ERROR: could not concatenate scene clips: {result.stderr[-2000:]}")
        return 1
    try:
        os.replace(temp_final, final_video)
    except PermissionError:
        # Windows may keep an existing MP4 locked in a player or preview pane.
        # Preserve that file and publish this complete render under a new name.
        final_video = output / "final_video_with_level_cards.mp4"
        os.replace(temp_final, final_video)
        print("NOTE: the previous final_video.mp4 was locked; wrote the new version as final_video_with_level_cards.mp4.")

    video_duration = probe_duration(ffprobe, final_video)
    video_stream_duration, audio_stream_duration = probe_stream_durations(ffprobe, final_video)
    skew = audio_stream_duration - video_stream_duration
    try:
        thumbnail_path = make_thumbnail(folder, root / "channel_config.txt")
        metadata_path = write_upload_metadata(folder)
    except Exception as exc:
        print(f"ERROR: video assembled, but final upload assets could not be generated: {exc}")
        return 1
    print("\nVideo assembly complete.")
    print(f"Video: {final_video}")
    print(f"Separate YouTube SRT: {srt_path}")
    print(f"Thumbnail: {thumbnail_path}")
    print(f"Upload metadata: {metadata_path}")
    print(f"Scenes: {total}; duration: {video_duration/60:.2f} min; A/V stream skew (audio - video): {skew:+.3f} s")
    if abs(skew) > 0.5:
        print("WARNING: A/V stream skew exceeds 0.5 seconds; inspect before uploading.")
    print("Visual treatment: gentle Ken Burns zoom on every scene; captions burned in.")
    print(f"Elapsed: {(time.time()-render_started)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
