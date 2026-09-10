# Changelog

All notable changes to **course-archiver** are documented here.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- **Downloads over unstable networks** — each retry now re-extracts the video and re-resolves the stream with a fresh URL/token, instead of retrying the same (already-expired) HLS URL that caused `ConnectionResetError` on long downloads.
- **Console output races** — writes are serialized with a reentrant lock (a nested acquisition previously dead-locked the very first progress bar), and progress bars are `transient` so they no longer overwrite/erase chapter-summary lines while other threads print.
- **Live errors that look like "config Vimeo"** — the Vimeo config endpoint now distinguishes HTTP failures and invalid JSON from a missing player config, with a message explaining the lesson may have been removed or restricted (HTTP 404 source).
- **ffmpeg metadata step** — capped at 900 s with an explicit timeout error instead of hanging forever (which froze the chapter list while the UI showed chapters splitting).

### Added
- **Partial resume** — a failed download keeps its `.part`/`.dl` files (per-attempt, and after the final retry) so a re-run resumes instead of starting over; successful downloads still clean up.

## [2.2.0] — 2026-09-10

### Added
- **Localized UI (i18n)** — the interface follows the system language: English by default, Portuguese when the system locale is `pt`. New `--lang {auto,en,pt}` flag overrides detection (`LC_ALL` / `LC_MESSAGES` / `LANG`, then `locale.getlocale()`, else English).
  - All console messages centralized in `lib/i18n.py`; plural-aware `nt()` and decimal-separator localization (PT uses `,`).
  - Adding a language = one new dict in `MESSAGES` + entries in `LANGUAGES` and `PLURAL_FORM_COUNT`; missing keys fall back to English.

### Changed
- New logo in the READMEs (`course-archiver.png`).

## [2.1.0] — 2026-09-10

### Added
- **Per-lesson attachments** — downloads each lesson's supplementary files into an `Anexos/` folder inside the chapter, with name+size dedup; complementary links become `.url` shortcuts.
  - Hotmart: `v1/pages/{hash}/complementary-content` (Bearer); DRM-protected (lambda) files resolved automatically.
  - Memberkit: best-effort scan of the lesson page (reuses the extract-video HTML cache, no extra request).
- `--ls` estimates now include attachments (`+N anexo(s) · X`) in lesson lines, chapter/course and grand totals.

### Changed
- Hotmart gateway is now authenticated with the **raw** (URL-encoded, undecoded) `hmVlcIntegration` cookie value — decoding corrupted the token.

## [2.0.0] — Initial `v2` (first stable line)

Baseline commit `2bfb9d8` ("Initial commit: course-archiver v2"). Since then:

### Added
- **`--ls` CLI** (`courses` / `chapters` / `lessons`, bare `--ls` lists everything) replacing `--dry-run`; `--course` / `--lesson` filters.
- **Size & duration estimates** — every `--ls` shows per-lesson size/duration plus per-chapter, per-course and grand totals; the download bar shows total size, speed, elapsed and ETA (generic: HLS bandwidth × `EXTINF`, or `Content-Range` for direct URLs; unknown values print `n/d`).
- **Throttle-aware networking** — per-host request pacing, `429` cooldown + one retry; after three consecutive `429`s the probe degrades to `n/d` for the rest of that course. Large listings just get slower instead of failing.
- **Memberkit adapter** (HLS via Vimeo player config).
- Transient "Listando…" progress bar while probing sizes/durations.

### Changed
- Hotmart Club: gateway authenticated with `Authorization: Bearer <hmVlcIntegration>`; updated `x-app-name`.
- Retry/backoff for transient network errors + adaptive fragment concurrency (auto-halved on reset).
- Cookie file auto-regenerated on "Netscape format" error.
- Docs split into English (default) + Portuguese with expanded content and module map.

[2.1.0]: https://github.com/joaocaetanoramos/course-archiver/releases/tag/v2.1.0