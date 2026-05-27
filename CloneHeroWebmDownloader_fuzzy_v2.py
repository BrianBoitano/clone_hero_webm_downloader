import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import correlate


def check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def sanitize_query(name: str) -> str:
    cleaned = re.sub(r"\[[^\]]*\]", " ", name)
    cleaned = re.sub(r"\([^\)]*\)", " ", cleaned)
    cleaned = re.sub(r"[_\.]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\([^\)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_song_ini(song_ini: Path):
    try:
        raw = song_ini.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = song_ini.read_text(encoding="latin-1", errors="replace")

    in_song_section = False
    values = {}

    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(";") or line.startswith("#") or line.startswith("//"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_song_section = (line.lower() == "[song]")
            continue
        if not in_song_section:
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip().lower()] = value.strip()

    return values


def looks_like_song_folder(folder: Path) -> bool:
    markers = [
        folder / "song.ini",
        folder / "notes.chart",
        folder / "notes.mid",
        folder / "video.mp4",
        folder / "video.webm",
        folder / "song.ogg",
        folder / "guitar.ogg",
    ]
    return any(p.exists() for p in markers)


def iter_target_folders(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort(key=lambda x: x.lower())
        folder = Path(dirpath)
        if looks_like_song_folder(folder):
            yield folder


def has_video(folder: Path, overwrite: bool) -> bool:
    target = folder / "video.webm"
    if overwrite:
        return False
    return target.exists()


def strip_chart_noise(text: str) -> str:
    text = text or ""
    patterns = [
        r"\b6\s*fret\b",
        r"\bchart\b",
        r"\boverchart\b",
        r"\bphase shift\b",
        r"\bmiscellany\b",
        r"\bfull album\b",
        r"\brandom\b",
        r"\bghwor\b",
        r"\bclone hero\b",
    ]
    out = text
    for pat in patterns:
        out = re.sub(pat, " ", out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip(" -")
    return out


def build_folder_metadata(folder: Path):
    meta = {
        "artist": "",
        "title": "",
        "album": "",
        "folder_name": folder.name,
    }

    song_ini = folder / "song.ini"
    if song_ini.exists():
        parsed = parse_song_ini(song_ini)
        meta["artist"] = parsed.get("artist", "").strip()
        meta["title"] = parsed.get("name", "").strip()
        meta["album"] = parsed.get("album", "").strip()

    meta["artist"] = strip_chart_noise(meta["artist"])
    meta["title"] = strip_chart_noise(meta["title"])

    if not meta["artist"] or not meta["title"]:
        fallback = sanitize_query(folder.name)
        if " - " in fallback:
            left, right = fallback.split(" - ", 1)
            if not meta["artist"]:
                meta["artist"] = strip_chart_noise(left.strip())
            if not meta["title"]:
                meta["title"] = strip_chart_noise(right.strip())
        else:
            if not meta["title"]:
                meta["title"] = strip_chart_noise(fallback)

    return meta


def build_search_query(folder: Path, suffix: str) -> str:
    meta = build_folder_metadata(folder)
    parts = []
    if meta["artist"]:
        parts.append(meta["artist"])
    if meta["title"]:
        parts.append(meta["title"])
    if not parts:
        parts.append(strip_chart_noise(sanitize_query(folder.name)))
    if suffix and suffix.strip():
        parts.append(suffix.strip())
    return " ".join(p for p in parts if p).strip()


def run_cmd(cmd, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd)
    return proc.returncode


def run_cmd_capture(cmd, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def find_reference_audio(folder: Path):
    for name in ["song.ogg", "song.opus", "audio.ogg", "guitar.ogg", "guitar.opus", "song.mp3", "song.wav"]:
        p = folder / name
        if p.exists():
            return p
    return None


def ffprobe_value(path: Path, entries: str) -> str:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", entries,
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return out


def extract_wav(input_path: Path, output_wav: Path, sample_rate: int = 2000):
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        str(output_wav),
    ]
    return run_cmd(cmd) == 0


def load_envelope(wav_path: Path):
    sr, data = wavfile.read(str(wav_path))
    if data.ndim > 1:
        data = data.mean(axis=1)
    data = data.astype(np.float32)
    if data.size == 0:
        raise ValueError(f"No audio samples in {wav_path}")
    data /= max(np.max(np.abs(data)), 1.0)
    env = np.abs(data)
    win = max(int(sr * 0.10), 1)
    kernel = np.ones(win, dtype=np.float32) / win
    env = np.convolve(env, kernel, mode="same")
    env -= np.mean(env)
    std = np.std(env)
    if std > 1e-8:
        env /= std
    return sr, env


def detect_offset_seconds(video_file: Path, ref_audio_file: Path):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        video_wav = td / "video.wav"
        ref_wav = td / "ref.wav"
        if not extract_wav(video_file, video_wav):
            raise RuntimeError(f"Failed to extract audio from {video_file}")
        if not extract_wav(ref_audio_file, ref_wav):
            raise RuntimeError(f"Failed to extract audio from {ref_audio_file}")

        sr_v, env_v = load_envelope(video_wav)
        sr_r, env_r = load_envelope(ref_wav)
        if sr_v != sr_r:
            raise RuntimeError("Sample rates do not match after extraction")

        corr = correlate(env_v, env_r, mode="full", method="fft")
        lag_samples = int(np.argmax(corr) - (len(env_r) - 1))
        return lag_samples / float(sr_v)


def shift_and_encode(input_video: Path, output_video: Path, fps: str, shift_seconds: float):
    if abs(shift_seconds) < 0.02:
        shift_seconds = 0.0

    if shift_seconds > 0:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
            "-ss", f"{shift_seconds:.3f}",
            "-i", str(input_video),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-c:v", "libvpx", "-crf", "10", "-b:v", "1M",
            "-deadline", "good", "-cpu-used", "2",
            "-pix_fmt", "yuv420p", "-r", fps, "-vsync", "cfr",
            "-c:a", "libvorbis", "-q:a", "4",
            "-sn", "-dn", "-map_metadata", "-1",
            str(output_video),
        ]
        return run_cmd(cmd) == 0

    pad_seconds = abs(shift_seconds)
    delay_ms = int(round(pad_seconds * 1000))
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
        "-i", str(input_video),
        "-vf", f"tpad=start_duration={pad_seconds:.3f}:start_mode=add:color=black",
        "-af", f"adelay={delay_ms}|{delay_ms}",
        "-map", "0:v:0", "-map", "0:a:0?",
        "-c:v", "libvpx", "-crf", "10", "-b:v", "1M",
        "-deadline", "good", "-cpu-used", "2",
        "-pix_fmt", "yuv420p", "-r", fps, "-vsync", "cfr",
        "-c:a", "libvorbis", "-q:a", "4",
        "-sn", "-dn", "-map_metadata", "-1",
        str(output_video),
    ]
    return run_cmd(cmd) == 0


def simple_encode(input_video: Path, output_video: Path, fps: str):
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
        "-i", str(input_video),
        "-map", "0:v:0", "-map", "0:a:0?",
        "-c:v", "libvpx", "-crf", "10", "-b:v", "1M",
        "-deadline", "good", "-cpu-used", "2",
        "-pix_fmt", "yuv420p", "-r", fps, "-vsync", "cfr",
        "-c:a", "libvorbis", "-q:a", "4",
        "-sn", "-dn", "-map_metadata", "-1",
        str(output_video),
    ]
    return run_cmd(cmd) == 0


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def score_candidate(entry: dict, meta: dict):
    title = entry.get("title", "") or ""
    channel = entry.get("channel", "") or entry.get("uploader", "") or ""
    desc = entry.get("description", "") or ""
    combined = f"{title} {channel} {desc}"
    combined_norm = normalize_text(combined)

    artist = normalize_text(meta.get("artist", ""))
    song = normalize_text(meta.get("title", ""))
    expected = normalize_text(f"{meta.get('artist', '')} {meta.get('title', '')}".strip())
    title_norm = normalize_text(title)
    channel_norm = normalize_text(channel)

    score = 0.0

    if expected:
        score += 70 * title_similarity(title, expected)

    if artist and artist in title_norm:
        score += 35
    if song and song in title_norm:
        score += 45

    if artist and artist in combined_norm:
        score += 10
    if song and song in combined_norm:
        score += 15

    if artist and song and (artist in title_norm and song in title_norm):
        score += 30

    if artist and ("vevo" in channel_norm or "topic" in channel_norm or artist in channel_norm):
        score += 12

    penalties = [
        "cover by", "guitar cover", "drum cover", "bass cover",
        "nightcore", "slowed", "sped up", "reaction",
        "tutorial", "lesson", "fan made",
        "100 fc", "100% fc", "fc!!!!", "full combo",
        "clone hero", "gh", "rock band", "osu", "chart",
    ]
    for p in penalties:
        if p in combined_norm:
            score -= 25

    # Strongly penalize fret / gameplay variants unless the underlying song title genuinely needs them
    chart_noise = ["6 fret", "6fret", "gameplay", "expert", "pro drums"]
    for p in chart_noise:
        if p in combined_norm:
            score -= 18

    bonuses = [
        "official music video", "official video", "official audio",
        "provided to youtube", "vevo", "topic"
    ]
    for b in bonuses:
        if b in combined_norm:
            score += 10

    duration = entry.get("duration")
    if isinstance(duration, (int, float)):
        if 120 <= duration <= 420:
            score += 10
        elif duration < 60:
            score -= 20

    return score


def pick_best_candidate(search_json: str, meta: dict):
    best = None
    best_score = None

    for raw in search_json.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        score = score_candidate(entry, meta)
        entry["_score"] = score
        if best is None or score > best_score:
            best = entry
            best_score = score

    return best


def download_candidate(url: str, out_tmp: Path, max_height: int):
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--ignore-errors",
        "--no-warnings",
        "--newline",
        "--geo-bypass",
        "--format", f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best",
        "--merge-output-format", "webm",
        "--recode-video", "webm",
        "--postprocessor-args", "ffmpeg:-c:v libvpx -pix_fmt yuv420p -c:a libvorbis -q:a 4",
        "--output", str(out_tmp),
        url,
    ]
    return run_cmd(cmd)


def download_and_convert(folder: Path, query_suffix: str, max_height: int, overwrite: bool, dry_run: bool, auto_align: bool, search_count: int):
    meta = build_folder_metadata(folder)
    query = build_search_query(folder, query_suffix)
    out_tmp = folder / "video.download.tmp.webm"
    out_final = folder / "video.webm"
    out_aligned = folder / "video.aligned.tmp.webm"

    if out_tmp.exists():
        out_tmp.unlink()
    if out_aligned.exists():
        out_aligned.unlink()

    if out_final.exists() and overwrite:
        out_final.unlink()

    print("\n" + "=" * 70)
    print(f"Folder : {folder}")
    print(f"Artist : {meta.get('artist','')}")
    print(f"Title  : {meta.get('title','')}")
    print(f"Search : {query}")
    print(f"Output : {out_final}")

    search_cmd = [
        "yt-dlp",
        f"ytsearch{search_count}:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--ignore-errors",
    ]

    if dry_run:
        print("DRY RUN SEARCH:")
        print(" ".join(search_cmd))
        return True

    rc, stdout, stderr = run_cmd_capture(search_cmd)
    if rc != 0 and not stdout.strip():
        print(f"ERROR: search failed for {folder}")
        return False

    best = pick_best_candidate(stdout, meta)
    if not best:
        print(f"ERROR: no search results found for {folder}")
        return False

    url = best.get("url") or best.get("webpage_url")
    if url and not str(url).startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"

    if not url:
        print(f"ERROR: could not determine URL for best candidate in {folder}")
        return False

    print(f"Chosen: {best.get('title','<unknown title>')} | channel={best.get('channel') or best.get('uploader') or ''} | score={best.get('_score', 0):.1f}")

    rc = download_candidate(url, out_tmp, max_height)
    if rc != 0:
        print(f"ERROR: yt-dlp download failed for {folder}")
        if out_tmp.exists():
            out_tmp.unlink(missing_ok=True)
        return False

    candidates = [
        out_tmp,
        folder / "video.download.tmp.mkv",
        folder / "video.download.tmp.mp4",
        folder / "video.download.tmp.webm.webm",
    ]
    produced = next((p for p in candidates if p.exists()), None)
    if produced is None:
        print(f"ERROR: download completed but no expected output file was found in {folder}")
        return False

    fps = ffprobe_value(produced, "stream=avg_frame_rate").strip()

    if auto_align:
        ref_audio = find_reference_audio(folder)
        if ref_audio is not None:
            try:
                offset_sec = detect_offset_seconds(produced, ref_audio)
                print(f"Detected offset vs {ref_audio.name}: {offset_sec:+.3f} sec")
                ok = shift_and_encode(produced, out_aligned, fps, offset_sec)
                if not ok:
                    print("WARNING: auto-align encode failed. Falling back to simple encode.")
                    ok = simple_encode(produced, out_aligned, fps)
            except Exception as ex:
                print(f"WARNING: auto-align failed ({ex}). Falling back to simple encode.")
                ok = simple_encode(produced, out_aligned, fps)
        else:
            print("No reference song audio found. Using simple encode.")
            ok = simple_encode(produced, out_aligned, fps)
    else:
        ok = simple_encode(produced, out_aligned, fps)

    produced.unlink(missing_ok=True)

    if not ok or not out_aligned.exists():
        print(f"ERROR: final encode failed for {folder}")
        out_aligned.unlink(missing_ok=True)
        return False

    out_aligned.replace(out_final)
    print("Done")
    return True


def main():
    parser = argparse.ArgumentParser(description="Search YouTube and download Clone Hero background videos as video.webm.")
    parser.add_argument("root", nargs="?", default=r"\\10.0.0.115\Vault\Clone Hero\Movies", help="Root folder to scan")
    parser.add_argument("--suffix", default="", help="Extra search terms appended to each folder name")
    parser.add_argument("--max-height", type=int, default=1080, help="Maximum download height")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing video.webm files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without downloading")
    parser.add_argument("--auto-align", action="store_true", help="Try to auto-align downloaded video audio to song.ogg/audio.ogg/guitar.ogg in the same folder")
    parser.add_argument("--search-count", type=int, default=5, help="How many YouTube search results to score before picking the best one")
    args = parser.parse_args()

    if not check_tool("yt-dlp"):
        print("ERROR: yt-dlp is not installed or not in PATH.")
        sys.exit(1)
    if not check_tool("ffmpeg"):
        print("ERROR: ffmpeg is not installed or not in PATH.")
        sys.exit(1)
    if not check_tool("ffprobe"):
        print("ERROR: ffprobe is not installed or not in PATH.")
        sys.exit(1)

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: Root folder does not exist: {root}")
        sys.exit(1)

    folders = sorted(iter_target_folders(root), key=lambda p: str(p).lower())
    if not folders:
        print("No candidate folders found.")
        sys.exit(0)

    total = 0
    success = 0
    skipped = 0

    for folder in folders:
        if has_video(folder, args.overwrite):
            print(f"Skipping existing video.webm: {folder}")
            skipped += 1
            continue
        total += 1
        if download_and_convert(folder, args.suffix, args.max_height, args.overwrite, args.dry_run, args.auto_align, args.search_count):
            success += 1

    print("\n" + "-" * 70)
    print(f"Processed : {total}")
    print(f"Succeeded : {success}")
    print(f"Skipped   : {skipped}")


if __name__ == "__main__":
    main()
