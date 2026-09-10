# Changelog

All notable changes to **course-archiver** are documented here.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [Semantic Versioning](https://semver.org/).

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