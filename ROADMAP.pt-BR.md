# Roadmap

Este documento acompanha a evolução planejada do `course-archiver`, a justificativa de cada funcionalidade, o status atual e as diretrizes de contribuição.

> O idioma padrão é inglês. Veja [ROADMAP.md](ROADMAP.md) para a versão em inglês.

---

## Estado atual — v2.0.0

- ✅ Multi-plataforma: Astron Members, Hotmart Club, Kiwify, Curseduca (apenas detecção).
- ✅ Multi-host de vídeo: Bunny Stream (AES-128), PandaVideo, Scaleup (Smart Player), Hotmart HLS, YouTube, genérico.
- ✅ Descoberta automática de curso/módulo/aula a partir do cookie de sessão.
- ✅ Remux lossless (`-c copy`) para MP4 com metadados embutidos.
- ✅ Downloads paralelos: `--parallel` (aulas) e `--concurrent` (fragmentos HLS por vídeo).
- ✅ Camada de rede resiliente: retries internos do yt-dlp (10/10), retry externo com backoff exponencial + jitter (`--retries`), throttling adaptativo de `concurrent` em resets de conexão, auto-regeneração do arquivo de cookie em erros `Netscape format`.
- ✅ UI limpa com rich (barras sem sobreposição).
- ✅ Instalável como CLI global via `pip install .` → `course-archiver`.
- ✅ Documentação em inglês e português.

---

## Funcionalidades planejadas

Cada item tem: **Objetivo**, **Por quê**, **Status**, **Abordagem** (notas técnicas para contribuidores).

### 1. Extensão do Chrome para extração de cookies

- **Objetivo:** uma extensão de navegador que extrai cookies (e tokens do localStorage quando necessário, ex.: Kiwify/Hotmart) do domínio atual e salva no formato exato que o `course-archiver` espera.
- **Por quê:** hoje o usuário precisa exportar cookies manualmente via extensões de terceiros. A integração também cobriria o `localStorage` (que o Kiwify usa para seu JWT do Firebase) — algo que a maioria das extensões de cookie NÃO exporta.
- **Status:** planejado (v2.x).
- **Abordagem:**
  - Extensão para Chrome com Manifest V3.
  - Botão no popup "Export for course-archiver" → grava um `cookies.json` (esquema do Cookie-Editor) E um `localstorage.json` (chaves selecionadas, configuráveis).
  - Opcional: native messaging para invocar o `course-archiver` direto do popup da extensão com a URL da página atual.
  - O lado Python (`lib/cookies.py`) já auto-detecta JSON; a saída da extensão só precisa casar com o esquema existente (`[{name, value, domain, path, secure}, ...]`).
  - Para localStorage: adicionar uma nova branch em `load_cookies` que mescla tokens do Firebase como cookies sintéticos (ex.: `__session=<id_token>`) para que a autenticação do Kiwify funcione direto.

### 2. Download de materiais complementares

- **Objetivo:** estender os adaptadores para que, além do vídeo, a ferramenta também baixe quaisquer arquivos anexos (PDFs, planilhas, áudios, materiais de apoio) de cada aula na mesma pasta.
- **Por quê:** muitas aulas vêm com listas de leitura, templates ou exercícios. Baixar só o vídeo é incompleto.
- **Status:** planejado (v2.x).
- **Abordagem / fontes já mapeadas:**
  - **Kiwify:** `lesson.files` já está presente na resposta de `lesson/{id}` (`v1/viewer/courses/{cid}/lesson/{lid}`). O adaptador só precisa expor isso e passar para uma nova rota genérica de download de anexos.
  - **Hotmart:** `v2/web/lessons/{hash}` retorna `medias[]` (algumas entradas não são `VIDEO`, ex.: PDF). Também `v1/pages/{hash}/complementary-content`. Filtrar `medias` por `type != "VIDEO"` e baixar.
  - **Astron Members:** investigar o HTML da página da aula por `<a href="...">` de download (algumas plataformas expõem `.pdf`/`.zip` na descrição ou sidebar).
  - Comum: adicionar um campo `lesson["attachments"] = [...]`, obtido em `extract_video` ou em um novo passo `extract_attachments`; baixar com `requests` (não precisa de yt-dlp) para `downloads/<grupo>/<curso>/`.
  - Nomeação: `<NN> - <lesson_title> - <attachment_name>.<ext>`.

### 3. Curseduca — descoberta de aulas

- **Objetivo:** implementar o passo `list_lessons` para a plataforma Curseduca.
- **Por quê:** a `detect` e a autenticação via cookie já estão prontas; só falta a listagem de aulas.
- **Status:** planejado (v2.x).
- **Abordagem:**
  - Endpoints já mapeados via análise de HAR:
    - `GET https://clas.curseduca.pro/menus/current/{tenantUuid}` → navegação do curso (módulos + aulas).
    - `GET https://clas.curseduca.pro/contents/{id}` → info do conteúdo/curso.
    - `POST https://player.curseduca.com/videos/bulk` body `{"uuids": [...]}` → URLs de vídeo assinadas.
  - O cookie fornece `api_key` + `access_token` (JWT), o que simplifica a autenticação (já suportado por `load_cookies`).
  - Resolver o `tenant_uuid` a partir de `cookie.platform_url` / `cookie.tenant_uuid` (já extraído pelo esquema JSON do Cookie-Editor).

### 4. Mais adaptadores de plataforma

- **Objetivo:** expandir a cobertura para outras plataformas de curso populares no Brasil e no mundo.
- **Por quê:** a arquitetura foi projetada para ser extensível; cada novo adaptador tem ~150 linhas.
- **Status:** contínuo.
- **Candidatos:**
  - **Udemy** (player restrito a `*.udemy.com` — precisa de tratamento cuidadoso).
  - **Domestika** (`*.domestika.com`).
  - **School Maker / Hotmart Sparkle** (separado do Hotmart Club).
  - **Membertoo / Kirvano / PerfectPay** (plataformas brasileiras de checkout com suas próprias áreas de membros).
  - **Teachable / Thinkific** (global, usado por criadores independentes).
- **Abordagem:** para cada um, implementar `class XxxPlatform(Platform)` em `lib/platforms.py`, mais um `resolve_xxxhost` em `lib/streams.py` se o host de vídeo for novo. Adicionar testes (parsing offline contra fixtures HAR capturados).

### 5. Empacotamento e distribuição

- **Objetivo:** tornar a instalação sem atrito em todos os sistemas operacionais.
- **Por quê:** hoje `pip install .` funciona em Linux/macOS; Windows + binário standalone ampliariam o público.
- **Status:** parcial.
- **Planejado:**
  - **Binário standalone** via `pyinstaller` (`.exe` / ELF / `.app` de arquivo único).
  - **Fórmula Homebrew** para macOS.
  - **Scoop / WinGet** manifest para Windows.
  - **Pacote AUR** para Arch.
  - Documentar a instalação para cada um.

### 6. Qualidade de vida

- **TUI interativo** (flag opcional `--tui`): um modo `interactive` que pede ao usuário para escolher cursos específicos de uma lista antes de baixar (atualmente `--course` só aceita ids/slugs como flags).
- **Manifest de resume** (`.course-archiver.json` no diretório de saída) registrando quais aulas foram baixadas e quais falharam, para fácil re-run.
- **Flag `--no-m3u8`**: contorna a heurística de `m3u8` e sempre usa o extractor do `yt-dlp` (útil quando uma plataforma troca o player).
- **Timeout por aula** (`--timeout N`): teto rígido de wall-clock por aula, após o qual é marcada como `erro` e a ferramenta segue em frente.
- **Saída sem cor** (`--no-color`) para CI / arquivos de log.

### 7. Testes & CI

- **Objetivo:** uma suíte de testes de regressão para que refactors futuros não quebrem silenciosamente uma plataforma.
- **Por quê:** a ferramenta tem contratos implícitos com a estrutura HTML/API de cada plataforma; um refactor que quebre um deles é difícil de notar sem testes.
- **Status:** planejado.
- **Abordagem:**
  - Capturar fixtures HAR / JSON (anonimizados, sem auth) para `dashboard`, `course`, `lesson`, `embed`, `master m3u8` de cada plataforma.
  - Testes unitários que parseiam essas fixtures com o adaptador e verificam a lista esperada de aulas / URLs de vídeo.
  - GitHub Actions CI em push / PR.
  - Essas fixtures e testes ficam num novo diretório `tests/` no repo.

### 8. Performance — agendamento mais inteligente

- **Objetivo:** ir além do binário `--parallel` / `--concurrent` atual e se adaptar automaticamente a características por servidor.
- **Por quê:** CDNs diferentes têm perfis diferentes de rate-limit; um tamanho único não serve para todos.
- **Status:** pesquisa.
- **Abordagem:**
  - Sondar a primeira aula de um run com `--concurrent 1` e medir a vazão. Depois subir até o valor pedido pelo usuário.
  - Acompanhar a taxa recente de `ConnectionResetError` / `429` e reduzir preventivamente (não só reativamente).
  - Opcional: integrar `pyrate-limiter` para rate limiting explícito por host com token-bucket.

---

## Fora do escopo (NÃO será implementado)

Para manter o foco e preservar a posição legal do projeto, os itens a seguir estão explicitamente **fora do escopo**:

- ❌ **Burla de autenticação** (nada de credential stuffing, captcha solving).
- ❌ **Descriptografar conteúdo protegido por DRM** (Widevine / FairPlay / PlayReady).
- ❌ **Download em massa de catálogos inteiros** ("me dá tudo que já foi publicado") — a ferramenta baixa apenas o que a sessão autenticada expõe.
- ❌ **Redistribuir o conteúdo baixado** — o aviso legal no README é explícito.

---

## Como contribuir

1. **Escolha um item** da lista acima (ou abra uma issue para propor um).
2. **Faça fork** do repo.
3. **Implemente** seguindo a arquitetura:
   - Nova plataforma → nova classe em `lib/platforms.py` + `lib/streams.py` se usar um host de vídeo novo.
   - Correção de bug → reproduza com uma fixture mínima (uma resposta HTML/JSON salva, anonimizada).
4. **Adicione testes** em `tests/` (quando a suíte existir — veja item 7).
5. **Abra um Pull Request** com:
   - Descrição da mudança.
   - A fixture usada (sem cookies/tokens reais).
   - Passos de verificação manual.
6. **Estilo de código:** Python 3.10+, sem dependências de terceiros sem justificativa, siga o layout dos módulos existentes.

---

## Versionamento

- **v2.x:** linha estável atual (multi-plataforma, rede resiliente, UI rica).
- **v3.0 (planejado):** materiais complementares, extensão Chrome, descoberta Curseduca — ou seja, itens 1–3 acima.

Versões seguem [Semantic Versioning](https://semver.org/).

---

🇺🇸 **English version:** [ROADMAP.md](ROADMAP.md)
