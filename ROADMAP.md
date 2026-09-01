# Roadmap

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
- O cookie fornecido já contém `api_key` + `access_token` (JWT), o que facilita a autenticação.

## 4. Mais adaptadores de plataforma
A arquitetura foi desenhada para ser extensível. Plataformas candidatas:
- Udemy (player restrito a domínios)
- Domestika
- School Maker / Hotmart Sparkle
- Membertoo / Kirvano / PerfectPay

## 5. Empacotamento
- `pyinstaller` para gerar binário standalone.
- Distribuição via `pipx` ou `pip install course-archiver`.
- Documentação de instalação para Windows/macOS/Linux.
