# Roadmap

This document tracks the planned evolution of `course-archiver`, the rationale behind each feature, the current status, and the contribution guidelines.

> English is the default language. See [ROADMAP.pt-BR.md](ROADMAP.pt-BR.md) for the Portuguese version.

---

## Current state — v2.0.0

- ✅ Multi-platform: Astron Members, Hotmart Club, Kiwify, Curseduca (detection only).
- ✅ Multi-host video: Bunny Stream (AES-128), PandaVideo, Scaleup (Smart Player), Hotmart HLS, YouTube, generic.
- ✅ Automatic course / module / lesson discovery from the cookie session.
- ✅ Lossless remux (`-c copy`) to MP4 with embedded metadata.
- ✅ Parallel downloads: `--parallel` (lessons) and `--concurrent` (HLS fragments per video).
- ✅ Resilient network layer: yt-dlp internal retries (10/10), outer retry with exponential backoff + jitter (`--retries`), adaptive `concurrent` throttling on connection resets, auto-regeneration of the cookie file on `Netscape format` errors.
- ✅ Clean rich-powered terminal UI (no overlapping bars).
- ✅ Installable as a global CLI via `pip install .` → `course-archiver`.
- ✅ English + Portuguese documentation.

---

## Planned features

Each item has: **Goal**, **Why**, **Status**, **Approach** (technical notes for contributors).

### 1. Chrome extension for cookie extraction

- **Goal:** a browser extension that extracts cookies (and localStorage tokens when needed, e.g. Kiwify/Hotmart) from the current domain and saves them in the exact format `course-archiver` expects.
- **Why:** today the user has to manually export cookies via third-party extensions. The integration would also cover `localStorage` (which Kiwify uses for its Firebase JWT) — something most cookie-export extensions do NOT export.
- **Status:** planned (v2.x).
- **Approach:**
  - Manifest V3 Chrome extension.
  - Popup button "Export for course-archiver" → writes a `cookies.json` (Cookie-Editor schema) AND a `localstorage.json` (selected keys, configurable).
  - Optional: native messaging to invoke `course-archiver` directly from the extension popup with the URL of the current page.
  - The Python side (`lib/cookies.py`) already auto-detects JSON; the extension output just needs to match the existing schema (`[{name, value, domain, path, secure}, ...]`).
  - For localStorage: add a new loader branch in `load_cookies` that merges Firebase tokens as synthetic cookies (e.g., `__session=<id_token>`) so Kiwify auth works out-of-the-box.

### 2. Download of supplementary materials

- **Goal:** extend the adapters so that, in addition to the video, the tool also downloads any attached files (PDFs, spreadsheets, audio, support material) for each lesson into the same folder.
- **Why:** many lessons come with reading lists, templates, or exercises. Downloading just the video is incomplete.
- **Status:** planned (v2.x).
- **Approach / already-mapped sources:**
  - **Kiwify:** `lesson.files` is already present in the `lesson/{id}` response (`v1/viewer/courses/{cid}/lesson/{lid}`). The adapter just needs to surface it and pass it to a new generic attachment-download path.
  - **Hotmart:** `v2/web/lessons/{hash}` returns `medias[]` (some entries are non-`VIDEO`, e.g. PDF). Also `v1/pages/{hash}/complementary-content`. Filter `medias` by `type != "VIDEO"` and download them.
  - **Astron Members:** investigate the lesson page HTML for `<a href="...">` download links (some platforms expose `.pdf` / `.zip` in the description or sidebar).
  - Common: add a `lesson["attachments"] = [...]` field, fetched in `extract_video` or in a new `extract_attachments` step; download them with `requests` (no yt-dlp needed) into `downloads/<group>/<course>/`.
  - File naming: `<NN> - <lesson_title> - <attachment_name>.<ext>`.

### 3. Curseduca — lesson discovery

- **Goal:** implement the `list_lessons` step for the Curseduca platform.
- **Why:** the `detect` and the cookie-based auth are already in place; only the lesson listing is missing.
- **Status:** planned (v2.x).
- **Approach:**
  - Endpoints already mapped from HAR analysis:
    - `GET https://clas.curseduca.pro/menus/current/{tenantUuid}` → course navigation (modules + lessons).
    - `GET https://clas.curseduca.pro/contents/{id}` → content / course info.
    - `POST https://player.curseduca.com/videos/bulk` body `{"uuids": [...]}` → signed video URLs.
  - The cookie provides `api_key` + `access_token` (JWT), which simplifies authentication (already supported by `load_cookies`).
  - Resolve the `tenant_uuid` from `cookie.platform_url` / `cookie.tenant_uuid` (already extracted by the Cookie-Editor JSON).

### 4. More platform adapters

- **Goal:** expand coverage to other course platforms popular in Brazil and globally.
- **Why:** the architecture is designed to be extensible; each new adapter is ~150 lines.
- **Status:** ongoing.
- **Candidates:**
  - **Udemy** (player restricted to `*.udemy.com` — needs careful handling).
  - **Domestika** (`*.domestika.com`).
  - **School Maker / Hotmart Sparkle** (separate from Hotmart Club).
  - **Membertoo / Kirvano / PerfectPay** (Brazilian checkout platforms with their own membership areas).
  - **Teachable / Thinkific** (global, used by independent creators).
- **Approach:** for each, implement `class XxxPlatform(Platform)` in `lib/platforms.py`, plus a `resolve_xxxhost` in `lib/streams.py` if the video host is novel. Add tests (offline parsing against captured HAR fixtures).

### 5. Packaging & distribution

- **Goal:** make installation frictionless across OSes.
- **Why:** today `pip install .` works on Linux/macOS; Windows + standalone binary would widen the audience.
- **Status:** partial.
- **Planned:**
  - **Standalone binary** via `pyinstaller` (single-file `.exe` / ELF / `.app`).
  - **Homebrew formula** for macOS.
  - **Scoop / WinGet** manifest for Windows.
  - **AUR package** for Arch.
  - Document the install for each.

### 6. Quality-of-life

- **Interactive TUI** (optional `--tui` flag): an `interactive` mode that asks the user to pick specific courses from a list before downloading (currently `--course` only accepts ids/slugs as flags).
- **Resume manifest** (`.course-archiver.json` in the output dir) recording which lessons were downloaded and which failed, for easy re-run.
- **`--no-m3u8`** flag: bypass the `m3u8` heuristic and always use `yt-dlp`'s extractor (useful when a platform changes its player).
- **Per-lesson timeout** (`--timeout N`): hard cap on a single lesson's wall-clock time, beyond which it's marked as `erro` and the tool moves on.
- **Color-free output** (`--no-color`) for CI / log files.

### 7. Testing & CI

- **Goal:** a regression test suite so future refactors don't silently break a platform.
- **Why:** the tool has implicit contracts with each platform's HTML / API structure; a refactor that breaks one of them is hard to spot without tests.
- **Status:** planned.
- **Approach:**
  - Capture HAR / JSON fixtures (anonymized, no auth) for each platform's `dashboard`, `course`, `lesson`, `embed`, `master m3u8`.
  - Unit tests that parse these fixtures with the adapter and assert the expected list of lessons / video URLs.
  - GitHub Actions CI on push / PR.
  - These fixtures and tests live under a new `tests/` directory in the repo.

### 8. Performance — smarter scheduling

- **Goal:** go beyond the current binary `--parallel` / `--concurrent` and adapt to per-server characteristics automatically.
- **Why:** different CDNs have different rate-limit profiles; one size doesn't fit all.
- **Status:** research.
- **Approach:**
  - Probe the first lesson of a run with `--concurrent 1` and measure throughput. Then ramp up to the user-requested value.
  - Track recent `ConnectionResetError` / `429` rate and back off proactively (not just reactively).
  - Optional: integrate `pyrate-limiter` for explicit token-bucket rate limiting per host.

---

## Out of scope (will NOT be implemented)

To stay focused and to keep the project's legal position clean, the following are explicitly **out of scope**:

- ❌ **Bypassing authentication** (no credential stuffing, no captcha solving).
- ❌ **Decrypting DRM-protected content** (Widevine / FairPlay / PlayReady).
- ❌ **Mass-downloading entire catalogs** ("give me everything ever published") — the tool downloads only what the authenticated session exposes.
- ❌ **Redistributing downloaded content** — the legal notice in the README is explicit.

---

## How to contribute

1. **Pick an item** from the list above (or open an issue to propose one).
2. **Fork** the repo.
3. **Implement** following the architecture:
   - New platform → new class in `lib/platforms.py` + `lib/streams.py` if it uses a novel video host.
   - Bug fix → reproduce with a minimal fixture (a saved HTML/JSON response, anonymized).
4. **Add tests** under `tests/` (once the test suite exists — see item 7).
5. **Open a Pull Request** with:
   - Description of the change.
   - The fixture used (no real cookies / tokens).
   - Manual verification steps.
6. **Code style:** Python 3.10+, no third-party deps unless justified, follow the existing module layout.

---

## Versioning

- **v2.x:** current stable line (multi-platform, resilient network, rich UI).
- **v3.0 (planned):** supplementary materials, Chrome extension, Curseduca discovery — i.e. items 1–3 above.

Versions follow [Semantic Versioning](https://semver.org/).

---

🇧🇷 **Versão em português:** [ROADMAP.pt-BR.md](ROADMAP.pt-BR.md)
