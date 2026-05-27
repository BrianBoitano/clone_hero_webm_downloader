# clone_hero_webm_downloader
# CloneHeroWebmDownloader Fuzzy v2

A Windows-friendly Python tool for building `video.webm` files for Clone Hero song folders using fuzzy YouTube matching and optional audio auto-alignment.

This project is designed for Clone Hero libraries where song folders already contain chart and audio files such as:

- `song.ini`
- `notes.chart` or `notes.mid`
- `song.ogg`, `song.opus`, `audio.ogg`, `guitar.ogg`, or `guitar.opus`

The script scans a root folder, builds a cleaned search query from folder metadata, scores multiple YouTube results, downloads the best candidate, converts it to `video.webm`, and can optionally align the downloaded video to the song audio already present in the folder.

---

## Features

- Recursively scans a root songs folder
- Processes folders in alphabetical order
- Uses `song.ini` artist and title when available
- Falls back to folder name when metadata is incomplete
- Strips chart noise such as `6 Fret`, `chart`, `clone hero`, and similar clutter from search text
- Searches multiple YouTube results instead of blindly taking the first one
- Scores candidates using fuzzy title and metadata matching
- Penalizes gameplay, FC, chart, tutorial, and obvious bad matches
- Downloads the best candidate and converts it to `video.webm`
- Optionally auto-aligns the downloaded video to the local song audio
- Supports existing `video.webm` skip behavior unless `--overwrite` is used

---

## What auto-align does

Auto-align does **not** modify the song audio file.

When `--auto-align` is enabled, the script:

1. extracts audio from the downloaded video
2. extracts audio from a local reference file in the folder
3. builds simplified amplitude envelopes
4. estimates the offset between the two
5. rewrites the downloaded `video.webm` so the video lines up better with the local song audio

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
- It does not fix every sync problem perfectly
- It does not change the Clone Hero song audio
- It does not handle all age-restricted YouTube cases by itself
- It does not fully solve drift when the downloaded source is a different edit of the song

---

