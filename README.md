# course-archiver

A Python CLI tool to download online course videos for **offline viewing**, using the **user's own session cookie**. Acts as a personal backup of content you have already purchased and are authenticated to access.

> Multi-platform support via pluggable adapters. Designed to be extensible.

## Supported platforms

| Platform | Course discovery | Video download |
|---|---|---|
| Astron Members (`*.astronmembers.com`) | ✅ | ✅ Bunny Stream, PandaVideo, Scaleup (Smart Player), YouTube |
| Hotmart Club (`*.hotmart.com`) | ✅ | ✅ HLS master m3u8 (AES-128 + separate audio merged via yt-dlp) |
| Kiwify (`*.kiwify.com`) | ✅ | ✅ HLS stream link / direct download link |
| Curseduca (`*.curseduca.pro`) | ⚠️ detection only, lesson listing pending | — |
| Any generic video URL | — | ✅ via yt-dlp |

## How it works

1. You export the cookie of your logged-in session (browser extension).
2. You run `course-archiver --cookies cookie.txt <COURSE_URL>`.
3. The tool automatically discovers modules/lessons, resolves the video URL for each lesson, and downloads them (optionally in parallel).
4. Files are saved to `downloads/<group>/<course>/NN - Lesson X.Y.mp4` with embedded metadata (title/course/group/source URL).

**Videos are downloaded at maximum quality** (up to 1080p, whatever is available) via **remux (`-c copy`)** — no re-encoding, **no quality loss**.

## Installation

```bash
git clone https://github.com/joaocaetanoramos/course-archiver.git
cd course-archiver
pip install -r requirements.txt
```

External requirements:
- **Python 3.10+**
- **ffmpeg** (`sudo dnf install ffmpeg` / `brew install ffmpeg` / etc.)
- **pycryptodomex** (installed via `requirements.txt` — used for native AES-128 HLS decryption)

## How to obtain the cookie

The tool **requires** the cookie of your logged-in session. Authentication is up to you — the tool never embeds credentials.

1. Install a cookie-export browser extension:
   - Chrome / Edge: **"Get cookies.txt LOCALLY"** or **"Cookie-Editor"**
   - Firefox: **"cookies.txt"**
2. Log in to the course platform in your browser.
3. Export the cookies in **JSON** (Cookie-Editor) or **Netscape** format. The tool auto-detects both.

> The tool does **not** crack accounts, does **not** authenticate on its own, and does **not** download content you don't have the right to access. It is the same model as `yt-dlp --cookies-from-browser`.

## Usage

```bash
# Download a dashboard of courses
python extrator.py --cookies cookie.txt "<DASHBOARD_URL>"

# Download a specific course
python extrator.py --cookies cookie.txt "<COURSE_URL>"

# Download a specific lesson
python extrator.py --cookies cookie.txt "<LESSON_URL>"

# Dry-run (just lists, doesn't download)
python extrator.py --cookies cookie.txt <URL> --dry-run

# Download options
python extrator.py --cookies cookie.txt <URL> \
    --output ./my-courses \
    --parallel 4 \
    --concurrent 16
```

### Arguments

| Flag | Description | Default |
|---|---|---|
| `url` | URL of the dashboard, course or lesson (positional, required) | — |
| `--cookies` | Cookie file (Netscape / JSON) or raw `Cookie:` header string (required) | — |
| `--output` | Output directory | `./downloads` |
| `--parallel` | Lessons downloaded in parallel | `1` |
| `--concurrent` | HLS fragments downloaded in parallel per video | `8` |
| `--dry-run` | Only list courses/lessons, don't download | `false` |
| `--course` | Filter by course slug or id | — |
| `--lesson` | Filter by lesson id | — |
| `--ffmpeg` | Path to the ffmpeg executable | auto-detect |

## Performance

- **Per-video concurrency:** `--concurrent N` downloads N HLS fragments in parallel (via yt-dlp native + pycryptodomex). Typical speedup of 3–8× over single-threaded sequential downloads.
- **Per-lesson concurrency:** `--parallel N` downloads N lessons simultaneously.
- **No re-encoding:** direct remux `-c copy` to MP4.

## Architecture

```
extrator.py          # CLI (argparse)
lib/
  cookies.py         # Cookie loading (JSON / Netscape / raw header)
  platforms.py       # Platform adapters (Astron, Hotmart, Kiwify, Curseduca, generic)
  streams.py         # Stream resolution (Bunny, PandaVideo, Scaleup, Hotmart, YouTube)
  downloader.py      # Download via yt-dlp native + audio/video merging
  progress.py        # Progress bars with rich
```

Adding a new platform = implement an adapter in `lib/platforms.py` with 4 methods: `detect`, `discover`, `list_lessons`, `extract_video`.

## Legal notice

**Use this tool only to download content you have purchased and have the right to access**, for personal offline use (travel, poor connection, accessibility).

- ❌ Do **not** redistribute the downloaded material.
- ❌ Do **not** use it to access unauthorized content.
- ❌ Do **not** share your cookies.

You are solely responsible for the use you make of the tool. The authors are not responsible for misuse.

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This tool is not affiliated with any of the supported platforms. It is an independent personal-utility project.

---

# Versão em Português (Brasil)

## O que faz

Ferramenta CLI em Python para baixar cursos online (vídeos) para assistir **offline**, usando o **próprio cookie de sessão** do usuário. Funciona como um "backup pessoal" do conteúdo que você já comprou e tem acesso autenticado.

> Suporta múltiplas plataformas via adaptadores plugáveis.

## Plataformas suportadas

| Plataforma | Descoberta de cursos | Download de vídeo |
|---|---|---|
| Astron Members (`*.astronmembers.com`) | ✅ | ✅ Bunny, PandaVideo, Scaleup, YouTube |
| Hotmart Club (`*.hotmart.com`) | ✅ | ✅ master m3u8 (AES-128 + áudio separado) |
| Kiwify (`*.kiwify.com`) | ✅ | ✅ stream m3u8 / download direto |
| Curseduca (`*.curseduca.pro`) | ⚠️ detecção OK, listagem pendente | — |
| Qualquer URL genérica | — | ✅ via yt-dlp |

## Instalação

```bash
git clone https://github.com/joaocaetanoramos/course-archiver.git
cd course-archiver
pip install -r requirements.txt
```

Requisitos externos:
- **Python 3.10+**
- **ffmpeg** (`sudo dnf install ffmpeg` / `brew install ffmpeg`)
- **pycryptodomex** (instalado via `requirements.txt` — descriptografia HLS AES-128 nativa)

## Como obter o cookie

A ferramenta **exige** o cookie da sua sessão logada.

1. Instale uma extensão de cookies no navegador (ex.: **"Get cookies.txt LOCALLY"** ou **"Cookie-Editor"**).
2. Faça login na plataforma do curso.
3. Exporte os cookies em **JSON** ou **Netscape**. A ferramenta detecta os dois.

> A ferramenta **não** cracka autenticação, **não** baixa conteúdo sem autorização. É o mesmo modelo do `yt-dlp --cookies-from-browser`.

## Uso

```bash
# Baixar dashboard de cursos
python extrator.py --cookies cookie.txt "<URL_DO_DASHBOARD>"

# Baixar um curso específico
python extrator.py --cookies cookie.txt "<URL_DO_CURSO>"

# Baixar uma aula específica
python extrator.py --cookies cookie.txt "<URL_DA_AULA>"

# Dry-run
python extrator.py --cookies cookie.txt <URL> --dry-run

# Opções
python extrator.py --cookies cookie.txt <URL> \
    --output ./meus-cursos \
    --parallel 4 \
    --concurrent 16
```

### Argumentos

| Flag | Descrição | Padrão |
|---|---|---|
| `url` | URL do dashboard, curso ou aula (posicional, obrigatório) | — |
| `--cookies` | Arquivo de cookies (Netscape/JSON) ou string `Cookie:` crua (obrigatório) | — |
| `--output` | Diretório de saída | `./downloads` |
| `--parallel` | Aulas baixadas em paralelo | `1` |
| `--concurrent` | Segmentos HLS em paralelo por vídeo | `8` |
| `--dry-run` | Apenas lista, sem baixar | `false` |
| `--course` | Filtra por slug/id de curso | — |
| `--lesson` | Filtra por id de aula | — |
| `--ffmpeg` | Caminho do ffmpeg | auto |

## Performance

- **Concorrência por vídeo:** `--concurrent N` baixa N segmentos HLS em paralelo (via yt-dlp nativo + pycryptodomex). Ganho típico de 3–8× sobre single-threaded.
- **Concorrência entre vídeos:** `--parallel N` baixa N vídeos simultaneamente.
- **Sem re-encoding:** remux `-c copy` para MP4.

## Arquitetura

```
extrator.py          # CLI (argparse)
lib/
  cookies.py
  platforms.py
  streams.py
  downloader.py
  progress.py
```

Adicionar plataforma = implementar adaptador em `lib/platforms.py` com 4 métodos: `detect`, `discover`, `list_lessons`, `extract_video`.

## Aviso legal

Use apenas para baixar conteúdo que você comprou e tem direito de acessar, para uso pessoal offline.

- ❌ Não redistribua o material.
- ❌ Não use para acessar conteúdo sem autorização.
- ❌ Não compartilhe seus cookies.

Você é o único responsável pelo uso. Os autores não se responsabilizam por uso indevido.

## Licença

MIT — veja [LICENSE](LICENSE).
