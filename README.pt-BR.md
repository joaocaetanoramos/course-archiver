<p align="center">
  <img src="course-archiver.png" alt="course-archiver" width="460">
</p>

<h3 align="center">
  Ferramenta CLI multi-plataforma para baixar vídeos de cursos online para assistir offline 🎬
  <br/>
  <sub>Remux lossless (-c copy) · Downloads paralelos · Adaptadores plugáveis</sub>
</h3>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square" alt="License: MIT"></a>
  &nbsp;
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  &nbsp;
  <a href="https://github.com/joaocaetanoramos/course-archiver/stargazers"><img src="https://img.shields.io/github/stars/joaocaetanoramos/course-archiver?style=flat-square&logo=github" alt="GitHub stars"></a>
  &nbsp;
  <a href="https://github.com/joaocaetanoramos/course-archiver/releases"><img src="https://img.shields.io/github/v/release/joaocaetanoramos/course-archiver?style=flat-square" alt="GitHub release"></a>
</p>

---

## Índice

- [Por quê?](#por-qu%C3%AA)
- [Funcionalidades](#funcionalidades)
- [Plataformas suportadas](#plataformas-suportadas)
- [Instalação](#instala%C3%A7%C3%A3o)
- [Como obter o cookie](#como-obter-o-cookie)
- [Uso](#uso)
  - [Início rápido](#in%C3%ADcio-r%C3%A1pido)
  - [Todos os argumentos](#todos-os-argumentos)
  - [Exemplos](#exemplos)
- [Estrutura de saída](#estrutura-de-sa%C3%ADda)
- [Arquitetura](#arquitetura)
  - [Mapa de módulos](#mapa-de-m%C3%B3dulos)
  - [Fluxo de requisições](#fluxo-de-requisi%C3%A7%C3%B5es)
  - [Adicionando uma nova plataforma](#adicionando-uma-nova-plataforma)
- [Ajuste de performance](#ajuste-de-performance)
- [Solução de problemas & FAQ](#solu%C3%A7%C3%A3o-de-problemas--faq)
- [Limitações conhecidas](#limita%C3%A7%C3%B5es-conhecidas)
- [Aviso legal](#aviso-legal)
- [Roadmap](#roadmap)
- [Licença](#licen%C3%A7a)

---

## Por quê?

Assistir cursos online exige conexão estável, e a maioria das plataformas não oferece uma opção nativa de "baixar para offline". Esta ferramenta preenche essa lacuna baixando vídeos **que você já tem acesso** (via seu cookie de sessão logado) para sua máquina local, organizados em pastas, com metadados, na qualidade máxima.

É o mesmo modelo do `yt-dlp --cookies-from-browser` ou `Streamlink`, mas com **descoberta automática** de cada curso/módulo/aula a partir do cookie, suporte multi-plataforma e organização embutida.

## Funcionalidades

- 🎓 **Descoberta automática de cursos** — aponte para um dashboard/curso e ela percorre a sidebar.
- 🌐 **Multi-plataforma** — adaptadores plugáveis para Astron Members, Hotmart Club, Kiwify, Curseduca, mais um fallback genérico.
- 🎥 **Suporte multi-host de vídeo** — Bunny Stream, PandaVideo, Scaleup (Smart Player), Hotmart AES-128 HLS, YouTube, m3u8 / mp4 diretos — todos pela mesma rota de download.
- ⚡ **Downloads paralelos** — segmentos em paralelo por vídeo (`--concurrent`) e aulas em paralelo (`--parallel`).
- 🔁 **Resiliente** — retry automático com backoff exponencial para erros de rede transitórios; auto-reduz `concurrent` quando o servidor reseta conexões; auto-regenera o arquivo de cookie no raro erro "Netscape format".
- 📁 **Saída organizada** — `downloads/<grupo>/<curso>/NN - Aula X.Y.mp4` com metadados título/curso/grupo embutidos.
- 🪶 **Lossless** — remux direto (`-c copy`) para MP4. Sem re-encoding, sem perda de qualidade.
- 💻 **CLI limpo** — barras de progresso com rich (sem sobreposição), linhas de status coloridas, headers por capítulo.

## Plataformas suportadas

| Plataforma | Descoberta auto | Download de vídeo | Observações |
|---|---|---|---|
| **Astron Members** (`*.astronmembers.com`) | ✅ | ✅ Bunny / PandaVideo / Scaleup / YouTube | Descoberta completa de curso/módulo/aula a partir da sidebar do dashboard. |
| **Hotmart Club** (`*.hotmart.com`) | ✅ | ✅ HLS master m3u8 | AES-128 + áudio separado mesclado automaticamente. Requer cookie de sessão recente. |
| **Kiwify** (`*.kiwify.com`) | ✅ | ✅ HLS stream / download direto | Pode exigir refresh token do localStorage. |
| **Curseduca** (`*.curseduca.pro`) | ⚠️ apenas detecção | — | Listagem de aulas pendente. |
| **URL genérica de vídeo** | — | ✅ via `yt-dlp` | Qualquer link m3u8 / mp4 / YouTube / Vimeo / Wistia. |

> Para solicitar uma nova plataforma, abra uma issue ou PR — veja [Adicionando uma nova plataforma](#adicionando-uma-nova-plataforma).

## Instalação

### Recomendado: instalar como CLI (rode `course-archiver` de qualquer lugar)

```bash
git clone https://github.com/joaocaetanoramos/course-archiver.git
cd course-archiver
pip install .
```

Isso instala o comando `course-archiver` no seu `PATH` (geralmente `~/.local/bin`), então você pode rodar de qualquer pasta:

```bash
course-archiver --cookies /caminho/cookie.txt "<URL_DO_CURSO>"
```

As dependências (pacotes Python + `ffmpeg`) são instaladas automaticamente.

### Alternativa: rodar direto da fonte sem instalar

```bash
git clone https://github.com/joaocaetanoramos/course-archiver.git
cd course-archiver
pip install -r requirements.txt
python extrator.py --cookies cookie.txt "<URL_DO_CURSO>"
```

### Requisitos

- **Python 3.10+**
- **ffmpeg** (`sudo dnf install ffmpeg` / `brew install ffmpeg` / `apt install ffmpeg` / `pip install static-ffmpeg`)
- **pycryptodomex** (instalado automaticamente via `pip install .` ou `pip install -r requirements.txt`) — usado para descriptografia nativa de HLS AES-128.

### Atualizando

Se você instalou via `pip install .` a partir de um clone local do repo:

```bash
cd /caminho/para/course-archiver
git pull
pip install --upgrade .
```

Se você instalou direto do GitHub (sem clone):

```bash
pip install --upgrade --force-reinstall "git+https://github.com/joaocaetanoramos/course-archiver.git"
```

Para verificar a versão instalada:

```bash
pip show course-archiver
```

Se você roda direto da fonte sem instalar:

```bash
cd /caminho/para/course-archiver
git pull
```

(Rode `pip install -r requirements.txt` novamente só se as dependências mudarem.)

## Como obter o cookie

A ferramenta **exige** o cookie da sua sessão logada. A autenticação é sua responsabilidade — a ferramenta nunca embute credenciais.

1. **Instale uma extensão de exportação de cookies no navegador:**
   - **Chrome / Edge / Brave:** [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbldhenkjhdlgphoegibknjl) ou [Cookie-Editor](https://cookie-editor.com/)
   - **Firefox:** [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
2. **Faça login** na plataforma do curso no navegador.
3. **Exporte os cookies** daquele domínio em formato **JSON** (Cookie-Editor) ou **Netscape**. A ferramenta detecta os dois automaticamente.
4. **Passe o arquivo** para a ferramenta:
   ```bash
   course-archiver --cookies ~/Downloads/cookies.json "<URL_DO_CURSO>"
   ```

A ferramenta também aceita uma string `Cookie:` crua (ex.: copiada do DevTools) no lugar do arquivo.

> **Segurança:** o arquivo de cookie contém sua sessão — trate como senha. Não compartilhe. O `.gitignore` deste repo já exclui `cookie*.txt`.

## Uso

### Início rápido

```bash
# Baixar um dashboard de cursos completo
course-archiver --cookies cookie.txt "<URL_DO_DASHBOARD>"

# Baixar um curso específico
course-archiver --cookies cookie.txt "<URL_DO_CURSO>"

# Apenas listar cursos/aulas sem baixar
course-archiver --cookies cookie.txt "<URL_DO_CURSO>" --dry-run
```

### Todos os argumentos

| Flag | Descrição | Padrão |
|---|---|---|
| `url` | URL do dashboard, curso ou aula (posicional, **obrigatório**) | — |
| `--cookies` `CAMINHO` | Arquivo de cookies (JSON / Netscape) ou string `Cookie:` crua (**obrigatório**) | — |
| `--output` `DIR` | Diretório de saída | `./downloads` |
| `--parallel` `N` | Número de aulas baixadas em paralelo | `1` |
| `--concurrent` `N` | Fragmentos HLS baixados em paralelo **por vídeo** | `8` |
| `--retries` `N` | Tentativas por aula em erros de rede transitórios | `3` |
| `--dry-run` | Apenas lista cursos/aulas sem baixar | `false` |
| `--course` `IDS` | Filtra por slug ou id de curso (separado por vírgula) | — |
| `--lesson` `IDS` | Filtra por id de aula (separado por vírgula) | — |
| `--ffmpeg` `CAMINHO` | Caminho do executável ffmpeg | auto-detecta |

### Exemplos

```bash
# Conservador: uma aula por vez, lento mas seguro
course-archiver --cookies cookie.txt "<URL>" --parallel 1

# Rápido: 4 aulas em paralelo, 8 segmentos por vídeo
course-archiver --cookies cookie.txt "<URL>" --parallel 4 --concurrent 8

# Agressivo (use só se a conexão e o servidor aguentarem)
course-archiver --cookies cookie.txt "<URL>" --parallel 8 --concurrent 16

# Rede instável: mais retries com backoff
course-archiver --cookies cookie.txt "<URL>" --retries 5

# Filtrar por um curso
course-archiver --cookies cookie.txt "<URL>" --course meu-slug-de-curso

# Filtrar por aulas específicas
course-archiver --cookies cookie.txt "<URL_DO_CURSO>" --lesson 123,456,789
```

## Estrutura de saída

Os arquivos são organizados por **grupo → curso → aula**:

```
downloads/
└── <Nome do Grupo>/
    └── <Nome do Curso>/
        ├── 01 - Aula 1.1 - Introdução.mp4
        ├── 02 - Aula 1.2 - Conceitos.mp4
        ├── 03 - Trilha: RESUMO (sem vídeo)        # pulado (divisores de trilha)
        └── 04 - Aula 1.3 - Aprofundamento.mp4
```

Cada `.mp4` tem metadados embutidos:

| Tag | Valor |
|---|---|
| `title` | Título da aula |
| `album` | Nome do curso (módulo) |
| `artist` | Nome do grupo |
| `comment` | URL original da aula |

Aulas marcadas como **"sem vídeo"** (`--dry-run` / execução real) são divisores de seção/trilha na sidebar da plataforma (sem vídeo de verdade) e são puladas automaticamente.

## Arquitetura

### Mapa de módulos

```
extrator.py          # Ponto de entrada CLI (argparse), orquestração
lib/
  cookies.py         # Carregamento de cookies: JSON / Netscape / header Cookie cru + TolerantSession (tolerância a redirect latin-1)
  platforms.py       # Adaptadores de plataforma plugáveis (detect / discover / list_lessons / extract_video)
  streams.py         # Resolve URL de embed do host de vídeo → master m3u8 (Bunny / PandaVideo / Scaleup / Hotmart / YouTube)
  downloader.py      # O download em si: yt-dlp nativo HLS, `concurrent_fragment_downloads`, remux `-c copy`, metadados
  progress.py        # Barras de progresso com Rich (uma por vídeo, empilhadas, sem sobreposição)
```

### Fluxo de requisições

```
+--------------------+
| 1. Parse URL & detecta plataforma (lib/platforms.py)
|    (Astron / Hotmart / Kiwify / Curseduca / genérica)
+----------+---------+
           |
           v
+--------------------+
| 2. Descobre cursos (platform.discover)
|    GET dashboard, parse sidebar <a href="curso/...">
+----------+---------+
           |
           v
+--------------------+
| 3. Lista aulas de cada curso (platform.list_lessons)
|    GET página do curso, parse <a> de módulos + aulas
+----------+---------+
           |
           v
+--------------------+
| 4. Extrai URL de embed do vídeo por aula (platform.extract_video)
|    GET página da aula, regex data-streaming-video / data-original-url
+----------+---------+
           |
           v
+--------------------+
| 5. Resolve embed → master m3u8 (lib/streams.py)
|    Bunny:  fetch embed → regex vz-*.b-cdn.net/playlist.m3u8
|    Panda:  monta b-{pullzone}.tv.pandavideo.com.br/{id}/playlist.m3u8
|    Scale:  fetch embed → meta hls-prefetch-url
|    Hotm:   fetch cf-embed → regex vod-akm.play.hotmart.com/.../master-pkg-*.m3u8
|    YT:     normaliza /embed/{id} → /watch?v={id}
+----------+---------+
           |
           v
+--------------------+
| 6. Download via yt-dlp nativo (lib/downloader.py)
|    - cookiefile (auto-regenerado se erro "Netscape format")
|    - concurrent_fragment_downloads (auto-dividido pela metade em ConnectionReset)
|    - retries=10, fragment_retries=10 (interno)
|    - AES-128 via pycryptodomex (nativo, paralelo)
|    - remux para MP4 via ffmpeg -c copy + metadados
+----------+---------+
           |
           v
+--------------------+
| 7. Salva em downloads/<grupo>/<curso>/<NN> - <título>.mp4
+--------------------+
```

### Adicionando uma nova plataforma

Para adicionar suporte a uma nova plataforma (ex.: Udemy), implemente um adaptador em `lib/platforms.py`:

```python
class UdemyPlatform(Platform):
    name = "udemy"

    def detect(self, url):
        return "udemy.com" in urlparse(url).netloc

    def discover(self, url, session):
        # Retorna lista de {"id", "title", "group", "slug", "url"}
        ...

    def list_lessons(self, course, session):
        # Retorna lista de {"id", "title", "url", "group", "chapter"}
        ...

    def extract_video(self, lesson, session):
        # Retorna a URL do embed (ex.: https://player.vimeo.com/... ou m3u8 direto)
        ...
```

Depois registre em `PLATFORMS`:

```python
PLATFORMS = [AstronPlatform(), HotmartPlatform(), KiwifyPlatform(), CurseducaPlatform(), UdemyPlatform()]
```

A camada de resolução de vídeo (`lib/streams.py`) é **compartilhada** — se sua plataforma usa um host conhecido (Bunny / PandaVideo / Scaleup / Hotmart / YouTube), o stream é resolvido automaticamente. Se usar um host custom, adicione uma função `resolve_seu_host` em `streams.py`.

## Ajuste de performance

Os dois controles de concorrência são independentes e servem propósitos diferentes:

| Controle | Escopo | Recomendação |
|---|---|---|
| `--concurrent N` | Fragmentos HLS baixados **por vídeo** em paralelo (via yt-dlp nativo) | `8` é um bom padrão. Maior = mais banda mas mais pressão no servidor. A ferramenta **auto-dividi pela metade** em erros de conexão. |
| `--parallel N` | Número de **aulas** baixadas em paralelo (thread pool) | `1` (sequencial) é o mais seguro. `2–4` é razoável. `6+` arrisca disparar rate-limits do Cloudflare. |

### Por que vídeos "muito grandes" disparam connection resets

Um vídeo de 30 min em 1080p pode ter **300+ segmentos HLS**. Com `concurrent_fragment_downloads: 8`, isso são 8 conexões HTTP paralelas por vídeo. Com `--parallel 6`, você pode atingir **48 conexões simultâneas** no mesmo host do CDN. Os limites de conexão por IP e os rate-limits do Cloudflare começam a ser atingidos, e ele passa a resetar conexões no meio do download.

Defesas da ferramenta:
- `--concurrent 8` como padrão (não mais alto).
- **Throttling adaptativo**: a cada `ConnectionResetError`, a ferramenta **divide `concurrent` pela metade** automaticamente e mostra um aviso. Vídeos seguintes usam o valor reduzido.
- **Retry com backoff exponencial + jitter** (2s, 4s, 8s, cap em 30s) — `ConnectionResetError`, `ReadTimeout`, etc. são capturados e retentados até `--retries` vezes.
- **yt-dlp retries internos**: `retries: 10`, `fragment_retries: 10` para que falhas individuais de segmento retentem dentro do yt-dlp antes de propagar.

### Configurações recomendadas por cenário

| Cenário | `--parallel` | `--concurrent` | `--retries` |
|---|---|---|---|
| Conexão estável e rápida | `4` | `8` | `3` |
| Instável / móvel | `2` | `4` | `5` |
| Servidor com rate-limit agressivo | `1` | `2` (deixe o auto-throttle agir) | `5` |
| Downloads grandes (>1 GB cada) | `2` | `4` | `5` |

## Solução de problemas & FAQ

### "ERROR: '/tmp/cookies_...txt' does not look like a Netscape format cookies file"

O arquivo de cookie estava válido no início mas ficou ilegível durante o run (raro glitch de filesystem). **A ferramenta detecta isso automaticamente e regenera o arquivo a partir do jar em memória, depois tenta de novo.** Se ainda falhar, seu cookie provavelmente expirou — re-exporte do navegador.

### Connection reset / timeout no meio do download

A ferramenta **retenta automaticamente** com backoff exponencial (2s → 4s → 8s, cap em 30s, mais jitter). Ela também **divide `concurrent` pela metade** após o primeiro reset, então vídeos seguintes usam menos conexões paralelas. Basta rodar de novo — aulas já concluídas são puladas (resume), só as que falharam retentam.

### Uma aula aparece como "sem vídeo" (no video)

A sidebar da plataforma pode ter divisores de seção ("Trilha: …", "Nota de atualização", etc.) que não têm vídeo. Esses são **pulados automaticamente**. Se uma aula real aparece como "sem vídeo", a página não retornou `data-streaming-video` — geralmente rate-limit transitório ou problema de autenticação.

### ffmpeg não encontrado

Instale: `sudo dnf install ffmpeg` / `brew install ffmpeg` / `apt install ffmpeg`. A ferramenta auto-detecta via `shutil.which('ffmpeg')`. Se estiver em um local não-padrão, passe `--ffmpeg /caminho/ffmpeg`.

### Download de aula está muito grande / lento

Para vídeos de 1h+ em 1080p, espere 1–3 GB. A velocidade é limitada por:
1. Banda da sua conexão.
2. Limite de velocidade por conexão do CDN (Cloudflare frequentemente limita por conexão).
3. Sua configuração `--concurrent` (mais segmentos = mais banda, até o limite).

Reduza `--concurrent` para 2 ou 4 se os downloads estão dando timeout em arquivos grandes.

### Resume

A ferramenta **pula** aulas cujo `.mp4` de saída já existe (verificado pelo caminho do arquivo). Se um run for interrompido (Ctrl+C), rode o mesmo comando de novo — aulas concluídas são puladas, as que falharam retentam.

### Aulas do Curseduca não aparecem

A listagem de aulas do Curseduca **não está implementada ainda** (veja [ROADMAP.md](ROADMAP.md)). A ferramenta detecta a plataforma mas exibe um erro claro. Workaround: extraia os IDs das aulas manualmente via `clas.curseduca.pro/contents/{id}`.

### Kiwify: "token de autenticação não encontrado"

A autenticação do Kiwify usa um JWT do Firebase (`id_token` / `access_token` / `refresh_token`) que fica no **localStorage**, não nos cookies. Exporte o arquivo de cookies *e* inclua esses tokens (Cookie-Editor pode exportá-los como cookies `__session`, ou extraia do DevTools → Application → Local Storage). Veja as notas da plataforma no `ROADMAP.md`.

## Limitações conhecidas

- **Extensão `.dts` em HLS (Bunny Stream)**: tratado nativamente pelo yt-dlp, sem problema.
- **Trilhas de áudio separadas (Scaleup, Hotmart)**: yt-dlp mescla automaticamente com `bestvideo+bestaudio`.
- **Conteúdo protegido por DRM**: não suportado (a ferramenta só trata as URLs de vídeo retornadas pelo player da plataforma, não streams com criptografia DRM).
- **Login obrigatório**: a ferramenta não burla autenticação. Um cookie válido da sua sessão logada é sempre necessário.
- **Curseduca**: listagem de aulas ainda não implementada (veja ROADMAP).
- **Live streams**: não testado; yt-dlp suporta, mas a ferramenta assume VOD (master playlist).

## Aviso legal

Use esta ferramenta apenas para baixar conteúdo que você comprou e tem direito de acessar, para uso pessoal offline (viagens, conexão ruim, acessibilidade).

- ❌ Não redistribua o material baixado.
- ❌ Não use para acessar conteúdo sem autorização.
- ❌ Não compartilhe seus cookies.

Você é o único responsável pelo uso que fizer da ferramenta. Os autores não se responsabilizam por uso indevido.

## Roadmap

Veja [ROADMAP.md](ROADMAP.md) para funcionalidades planejadas (extensão Chrome, materiais complementares, mais adaptadores, empacotamento).

## Licença

MIT — veja [LICENSE](LICENSE).

## Aviso

Esta ferramenta não é afiliada a nenhuma das plataformas suportadas. É um projeto independente de utilidade pessoal.

---

🇺🇸 **English version:** [README.md](README.md)
