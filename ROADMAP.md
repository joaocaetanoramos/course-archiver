# Roadmap

Features planned for future versions.

## 1. Chrome extension for cookie extraction
- Browser extension that extracts cookies (and localStorage tokens when needed, e.g. Kiwify/Hotmart) from the current domain.
- Direct integration with `course-archiver`: the extension exports a cookies file ready to use.
- Motivation: today the user has to export cookies manually via third-party extensions.

## 2. Download of supplementary materials
- Some lessons have attached files (PDFs, spreadsheets, audio, support material).
- Extend the adapters to, beyond the video, extract and download the attachments of each lesson into the same folder.
- Sources already mapped:
  - **Kiwify**: `lesson.files` in the lesson response.
  - **Hotmart**: non-video `medias` and `complementary-content`.
  - **Astron Members**: investigate the attachment field on the lesson page.

## 3. Curseduca — lesson discovery
- Domain detection (`*.curseduca.pro`) already works; lesson listing still pending (via `clas.curseduca.pro` `menus/current` + `contents/{id}` and `player.curseduca.com/videos/bulk`).
- The cookie provides `api_key` + `access_token` (JWT), which simplifies authentication.

## 4. More platform adapters
The architecture was designed to be extensible. Platform candidates:
- Udemy (domain-restricted player)
- Domestika
- School Maker / Hotmart Sparkle
- Membertoo / Kirvano / PerfectPay

## 5. Packaging
- `pyinstaller` to generate a standalone binary.
- Distribution via `pipx` or `pip install course-archiver`.
- Installation documentation for Windows / macOS / Linux.

---

# Roadmap (versão em Português)

Funcionalidades planejadas para versões futuras.

## 1. Extensão do Chrome para extração de cookies
- Extensão que extrai os cookies (e tokens de localStorage quando necessário, ex.: Kiwify/Hotmart) do domínio aberto no navegador.
- Integração direta com o `course-archiver`: a extensão exporta um arquivo de cookies pronto para uso.
- Motivação: hoje o usuário precisa exportar manualmente via extensões de terceiros.

## 2. Download de materiais complementares
- Algumas aulas possuem arquivos anexos (PDFs, planilhas, áudios, materiais de apoio).
- Estender os adaptadores para, além do vídeo, extrair e baixar os anexos de cada aula para a mesma pasta.
- Fontes já mapeadas:
  - **Kiwify**: `lesson.files` na resposta da aula.
  - **Hotmart**: `medias` (não-vídeo) e `complementary-content`.
  - **Astron Members**: investigar campo de anexos na página da aula.

## 3. Curseduca — descoberta de aulas
- A detecção (`*.curseduca.pro`) já existe; falta implementar a listagem de aulas via `clas.curseduca.pro` (`menus/current` + `contents/{id}`) e `player.curseduca.com/videos/bulk`.
- O cookie fornece `api_key` + `access_token` (JWT), o que facilita a autenticação.

## 4. Mais adaptadores de plataforma
A arquitetura foi projetada para ser extensível. Plataformas candidatas:
- Udemy (player restrito a domínios)
- Domestika
- School Maker / Hotmart Sparkle
- Membertoo / Kirvano / PerfectPay

## 5. Empacotamento
- `pyinstaller` para gerar binário standalone.
- Distribuição via `pipx` ou `pip install course-archiver`.
- Documentação de instalação para Windows / macOS / Linux.
