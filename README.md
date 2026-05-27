# CloneHeroWebmDownloader Fuzzy v2

A Windows-friendly Python tool for building `video.webm` files for Clone Hero song folders using fuzzy YouTube matching and optional audio auto-alignment.

This project is designed for Clone Hero libraries where song folders already contain chart and audio files such as:

- `song.ini`
- `notes.chart` or `notes.mid`
- `song.ogg`, `song.opus`, `audio.ogg`, `guitar.ogg`, or `guitar.opus`

The script scans a root folder, builds a cleaned search query from folder metadata, scores multiple YouTube results, downloads the best candidate, converts it to `video.webm`, and can optionally align the downloaded video to the song audio already present in the folder.

---

## Features

- Recursively scans a root folder
- Processes folders in alphabetical order
- Uses `song.ini` artist and title when available
- Falls back to folder name when metadata is incomplete
- Strips chart noise such as `6 Fret`, `chart`, `clone hero`, and similar clutter from search text
- Searches multiple YouTube results instead of blindly taking the first one
- Scores candidates using fuzzy title and metadata matching
- Penalizes gameplay, FC, chart, tutorial, and obvious bad matches
- Downloads the best candidate and converts it to `video.webm`
- Optionally auto-aligns the downloaded video to the local song audio
- Skips existing `video.webm` files unless `--overwrite` is used

---

## Files in this repo

This repo only needs:

- `CloneHeroWebmDownloader_fuzzy_v2.py`
- `CloneHeroWebmDownloader_fuzzy_v2.bat`
- `README.md`

---

## What auto-align does

Auto-align does **not** change the song audio file.

When `--auto-align` is enabled, the script:

1. extracts audio from the downloaded video
2. extracts audio from a local reference file in the folder
3. builds simplified amplitude envelopes
4. estimates the offset between them
5. rewrites the downloaded `video.webm` so it lines up better with the local song audio

### Supported reference audio files

The script will use the first one it finds from this list:

- `song.ogg`
- `song.opus`
- `audio.ogg`
- `guitar.ogg`
- `guitar.opus`
- `song.mp3`
- `song.wav`

---

## What this tool does **not** do

- It does not guarantee the correct YouTube video every time
- It does not perfectly fix every sync problem
- It does not change the Clone Hero audio file
- It does not solve all age-restricted YouTube cases by itself
- It does not fully solve drift when the downloaded source is a different edit of the song

---

# Windows setup

On Windows, this is the quickest setup for the scripts:

```powershell
winget install -e --id Python.Python.3.9
winget install -e --id Gyan.FFmpeg
winget install -e --id yt-dlp.yt-dlp
py -m pip install --upgrade pip
py -m pip install numpy scipy
````

Then close PowerShell, open a **new** PowerShell window, and verify:

```powershell
python --version
ffmpeg -version
ffprobe -version
yt-dlp --version
py -c "import numpy, scipy; print('numpy/scipy ok')"
```


## Setup notes

* `ffprobe` comes with FFmpeg, so installing FFmpeg should give you both `ffmpeg` and `ffprobe`
* If `py` is not recognized after install, reboot once or reinstall Python and make sure the Python launcher and PATH options are enabled
* If `python` is not recognized after install, reopen PowerShell or reboot Windows
* If a new shell still does not see the tools, sign out and back in or restart the PC

---

# How the script finds song folders

A folder is treated as a candidate when it contains one or more of the following:

* `song.ini`
* `notes.chart`
* `notes.mid`
* `video.mp4`
* `video.webm`
* `song.ogg`
* `guitar.ogg`

The script prefers `song.ini` metadata when available.

---

# How the search query is built

The query is built from:

1. artist from `song.ini`
2. title from `song.ini`
3. fallback to folder name if needed

It also strips common clutter such as:

* `6 Fret`
* `chart`
* `overchart`
* `phase shift`
* `clone hero`

By default, the search suffix is **empty** in v2.

That means a folder like:

```text
Buckethead - Jordan (6 Fret)
```

is cleaned toward a query like:

```text
Buckethead Jordan
```

instead of keeping chart junk that hurts search quality.

---

# Fuzzy result scoring

Instead of using the first YouTube result, the script searches multiple results and scores them.

### Signals that improve score

* artist appears in title
* song title appears in title
* artist and song both appear together
* official video style wording
* VEVO / Topic / artist channel clues
* normal song-length durations

### Signals that reduce score

* cover videos
* gameplay and FC videos
* chart/tutorial content
* slowed/sped-up/nightcore/reaction style results

This is why the script performs better than a simple `ytsearch1:` flow.

---

# BAT file usage

You can double-click:

```text
CloneHeroWebmDownloader_fuzzy_v2.bat
```

A BAT launcher is provided for those who do not want to run Python from the command line directly. I recommend running this script from the BAT launcher :)


---

# Command line usage

## Basic run

```powershell
python CloneHeroWebmDownloader_fuzzy_v2.py "\\10.0.0.115\Vault\Clone Hero\01_songs"
```

## Overwrite existing videos and align

```powershell
python CloneHeroWebmDownloader_fuzzy_v2.py "\\10.0.0.115\Vault\Clone Hero\01_songs" --overwrite --auto-align
```

## Increase the number of scored YouTube candidates

```powershell
python CloneHeroWebmDownloader_fuzzy_v2.py "\\10.0.0.115\Vault\Clone Hero\01_songs" --search-count 8 --overwrite --auto-align
```

## Use a suffix to bias results

```powershell
python CloneHeroWebmDownloader_fuzzy_v2.py "\\10.0.0.115\Vault\Clone Hero\01_songs" --suffix "official music video" --search-count 8 --overwrite --auto-align
```

## Dry run

```powershell
python CloneHeroWebmDownloader_fuzzy_v2.py "\\10.0.0.115\Vault\Clone Hero\01_songs" --dry-run
```

---

# Command reference

## Positional argument

### `root`

Root folder to scan.

---

## Flags

### `--suffix`

Optional extra words appended to the search query.

Default in v2:

* none

Examples:

* `official music video`
* `official video`
* `live performance`

### `--max-height`

Maximum video height to request.

Default:

* `1080`

### `--overwrite`

Overwrite existing `video.webm` files.

If omitted, folders that already contain `video.webm` are skipped.

### `--dry-run`

Show what would happen without downloading.

### `--auto-align`

Try to align the downloaded video to local song audio.

### `--search-count`

How many YouTube results to score before picking the best one.

Default:

* `5`

---

# Recommended workflows

## Workflow 1: First library pass

Use:

```powershell
python CloneHeroWebmDownloader_fuzzy_v2.py "\\10.0.0.115\Vault\Clone Hero\01_songs" --search-count 5
```

This skips folders that already have `video.webm`.

## Workflow 2: Better quality pass

Use:

```powershell
python CloneHeroWebmDownloader_fuzzy_v2.py "\\10.0.0.115\Vault\Clone Hero\01_songs" --search-count 8 --auto-align
```

This gives the scorer more options and also aligns results when possible.

## Workflow 3: Full rebuild pass

Use:

```powershell
python CloneHeroWebmDownloader_fuzzy_v2.py "\\10.0.0.115\Vault\Clone Hero\01_songs" --overwrite --search-count 8 --auto-align
```

Use this when rebuilding an existing library.

## Workflow 4: Hard songs with bad matches

If fuzzy matching still picks bad results:

* rename the folder more clearly
* verify `song.ini` artist/title are accurate
* try `--search-count 10`
* try a suffix like `official video`
* use a manual URL tool for edge cases

---

# Example: does this script align songs?

Yes, but **only if you run it with `--auto-align`**.

Without `--auto-align`, it still downloads and converts the selected YouTube result into `video.webm`, but it does **not** try to sync that video to the local song audio.

So:

* `--auto-align` enabled = tries to sync
* `--auto-align` omitted = no sync, normal encode only

---

# Troubleshooting

## `python` is not recognized

Python is not installed correctly or not added to PATH.

Fix:

* reinstall Python
* ensure PATH is enabled
* reopen PowerShell
* reboot if needed

## `py` is not recognized

The Python launcher is missing or shell PATH is stale.

Fix:

* reboot
* reinstall Python with launcher enabled
* verify from a new shell

## `ffmpeg` is not recognized

FFmpeg is not installed or PATH is stale.

Fix:

* rerun:

  ```powershell
  winget install -e --id Gyan.FFmpeg
  ```
* reopen terminal
* verify:

  ```powershell
  ffmpeg -version
  ffprobe -version
  ```

## `yt-dlp` is not recognized

Fix:

```powershell
winget install -e --id yt-dlp.yt-dlp
```

Then open a new terminal and run:

```powershell
yt-dlp --version
```

## `numpy` or `scipy` import errors

Fix:

```powershell
py -m pip install --upgrade pip
py -m pip install numpy scipy
```

## The script is not aligning anything

Alignment only happens when `--auto-align` is enabled.

Also make sure the folder contains one of the supported reference files:

* `song.ogg`
* `song.opus`
* `audio.ogg`
* `guitar.ogg`
* `guitar.opus`
* `song.mp3`
* `song.wav`

## The wrong YouTube video keeps getting picked

Try:

* increasing `--search-count`
* improving the folder name
* correcting `song.ini`
* using a suffix such as `official music video`
* using a manual URL workflow for that folder

## The script skips my folders

It skips folders with existing `video.webm` unless `--overwrite` is set.

## The video is close but still not perfectly synced

That usually means:

* the downloaded video is a different cut
* there is intro/outro material
* the audio mix is too different from the local chart audio
* the source drifts over time

Fix:

* use a better source video
* use a manual URL + auto-align workflow
* manually adjust edge cases if needed

## Age-restricted YouTube videos fail

This fuzzy v2 script does not include cookies support by default.

For age-restricted cases:

* use a manual workflow with cookies
* or extend the script to pass a `cookies.txt` file

## UNC path or network share issues

If a BAT file is launched from a UNC path, `cmd.exe` can behave strangely.

Fixes:

* run the Python file directly
* copy the tools to a local folder
* or use a BAT that wraps execution with `pushd`

## Antivirus or SmartScreen warnings

Downloaded tools like `yt-dlp.exe` or fresh Python scripts can sometimes trigger caution prompts.

Fix:

* verify the source
* allow the tool if appropriate
* keep your scripts in a trusted local folder

---

# Quick start summary

## Install tools

```powershell
winget install -e --id Python.Python.3.9
winget install -e --id Gyan.FFmpeg
winget install -e --id yt-dlp.yt-dlp
py -m pip install --upgrade pip
py -m pip install numpy scipy
```

## Verify

```powershell
python --version
ffmpeg -version
ffprobe -version
yt-dlp --version
py -c "import numpy, scipy; print('numpy/scipy ok')"
```

## Run

```powershell
python CloneHeroWebmDownloader_fuzzy_v2.py "\\10.0.0.115\Vault\Clone Hero\01_songs" --search-count 5 --overwrite --auto-align
```
Or double click the BAT file and follow the onscreen prompts. Easy Peasy. 

---

# License / disclaimer
Use this tool responsibly. Always review outputs, especially for matching accuracy and alignment quality, before applying results across a large Clone Hero library.

