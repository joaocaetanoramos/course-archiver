# course-archiver

Ferramenta CLI em Python para baixar cursos online (vídeos) para assistir **offline**, usando o **próprio cookie de sessão** do usuário. Funciona como um "backup pessoal" do conteúdo que você já comprou e tem acesso autenticado.

> Suporta múltiplas plataformas via adaptadores. Arquitetura extensível.

## Plataformas suportadas

| Plataforma | Descoberta de cursos | Download de vídeo |
|---|---|---|
| Astron Members (astronmembers.com) | ✅ | ✅ Bunny, PandaVideo, Scaleup, YouTube |
| Hotmart Club | ✅ | ✅ via master m3u8 (AES-128 + áudio separado) |
| Kiwify | ✅ | ✅ stream m3u8 / download direto |
| Curseduca | ⚠️ detecção OK, listagem pendente | — |
| Qualquer URL de vídeo (genérico) | — | ✅ via yt-dlp |

## Como funciona

1. Você exporta o cookie da sua sessão logada (extensão do navegador).
2. Roda `course-archiver --cookies cookie.txt <URL_DO_CURSO>`.
3. A ferramenta descobre automaticamente módulos/aulas, resolve a URL do vídeo de cada aula, e baixa em paralelo.
4. Os arquivos são salvos em `downloads/<grupo>/<curso>/NN - Aula X.Y.mp4` com metadados (título/curso/grupo/URL).

**O vídeo é baixado em qualidade máxima** (1080p ou menor, o que estiver disponível) via **remux (`-c copy`)** — sem re-encode, **sem perda de qualidade**.

## Instalação

```bash
git clone https://github.com/joaocaetanoramos/course-archiver.git
cd course-archiver
pip install -r requirements.txt
```

Dependências externas:
- **Python 3.10+**
- **ffmpeg** (`sudo dnf install ffmpeg` ou `brew install ffmpeg`)
- **pycryptodomex** (instalado via `requirements.txt` — usado para descriptografar HLS AES-128 nativo)

## Como obter o cookie

A ferramenta **exige** o cookie da sua sessão logada. Você é quem decide autenticá-la (a ferramenta nunca usa credenciais embutidas).

1. Instale uma extensão de cookies no navegador:
   - Chrome/Edge: **"Get cookies.txt LOCALLY"** ou **"Cookie-Editor"**.
   - Firefox: **"cookies.txt"**.
2. Faça login na plataforma do curso no navegador.
3. Exporte os cookies em **formato JSON** (Cookie-Editor) ou **Netscape**. A ferramenta detecta ambos automaticamente.

> A ferramenta **não** cracka, **não** autentica sozinha e **não** baixa conteúdo que você não tem direito de acessar. É o mesmo modelo do `yt-dlp --cookies-from-browser`.

## Uso

```bash
# Baixar todo o dashboard de cursos
python extrator.py --cookies cookie.txt "https://marciomedeirosedu.astronmembers.com/dashboard"

# Baixar um curso específico
python extrator.py --cookies cookie.txt "https://.../curso/<slug>/<id>"

# Baixar uma aula específica
python extrator.py --cookies cookie.txt "https://.../curso/<slug>/<id>/<aula>"

# Dry-run (apenas lista, sem baixar)
python extrator.py --cookies cookie.txt <URL> --dry-run

# Opções de download
python extrator.py --cookies cookie.txt <URL> \
    --output ./meus-cursos \
    --parallel 4 \
    --concurrent 16
```

### Argumentos

| Flag | Descrição | Padrão |
|---|---|---|
| `url` | URL do dashboard, curso ou aula (posicional, obrigatório) | — |
| `--cookies` | Arquivo de cookies (Netscape/JSON) ou string `Cookie:` (obrigatório) | — |
| `--output` | Diretório de saída | `./downloads` |
| `--parallel` | Aulas baixadas em paralelo | `1` |
| `--concurrent` | Segmentos HLS baixados em paralelo por vídeo | `8` |
| `--dry-run` | Apenas lista cursos/aulas sem baixar | `false` |
| `--course` | Filtra por slug ou id de curso | — |
| `--lesson` | Filtra por id de aula | — |
| `--ffmpeg` | Caminho do executável ffmpeg | auto |

## Performance

- **Concorrência por vídeo:** `--concurrent N` baixa N segmentos HLS em paralelo (via yt-dlp nativo + pycryptodomex). Ganho típico de 3–8× sobre o download single-threaded.
- **Concorrência entre vídeos:** `--parallel N` baixa N vídeos simultaneamente.
- **Sem re-encode:** remux `-c copy` direto para MP4.

## Arquitetura

```
extrator.py          # CLI (argparse)
lib/
  cookies.py         # Carregamento de cookies (JSON / Netscape / header)
  platforms.py       # Adaptadores por plataforma (Astron, Hotmart, Kiwify, ...)
  streams.py         # Resolução do stream (Bunny, PandaVideo, Scaleup, Hotmart, YouTube)
  downloader.py      # Download via yt-dlp nativo + merge de áudio/vídeo
  progress.py        # Barras de progresso com rich
```

Adicionar uma nova plataforma = implementar um adaptador em `lib/platforms.py` com 3 métodos: `detect`, `discover`, `list_lessons`, `extract_video`.

## Aviso legal

**Use esta ferramenta apenas para baixar conteúdo que você comprou e tem direito de acessar**, para uso pessoal offline (viagens, conexão ruim, acessibilidade).

- ❌ **Não** redistribua o material baixado.
- ❌ **Não** use para acessar conteúdo sem autorização.
- ❌ **Não** compartilhe seus cookies.

Você é o único responsável pelo uso que fizer da ferramenta. Os autores não se responsabilizam por uso indevido.

## Roadmap

Veja [ROADMAP.md](ROADMAP.md).

## Licença

MIT — veja [LICENSE](LICENSE).

## Aviso

Esta ferramenta não é afiliada a nenhuma das plataformas suportadas. É um projeto independente de utilidade pessoal.
