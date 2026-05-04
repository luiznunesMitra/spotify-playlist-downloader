# Spotify Playlist Downloader

Baixa todas as músicas de uma playlist do Spotify em MP3/FLAC via YouTube.
**Não precisa de API key, conta do Spotify, nem login.**

## Como funciona

```
URL do Spotify → extrai nomes das músicas → busca no YouTube → baixa em MP3/FLAC
```

1. Acessa o embed da playlist e pega as primeiras 100 faixas
2. Para playlists com 100+ faixas, usa o endpoint `spclient` pra pegar o resto
3. Gera um arquivo batch e baixa tudo via `yt-dlp`

---

## Instalação (Linux - Ubuntu/Debian)

```bash
# 1. Clonar o repositório
git clone https://github.com/luiznunesMitra/spotify-playlist-downloader.git
cd spotify-playlist-downloader

# 2. Instalar dependências
sudo apt install ffmpeg nodejs

# 3. Instalar yt-dlp (versão mais recente via pipx)
sudo apt install pipx
pipx install yt-dlp

# 4. Garantir que ~/.local/bin está no PATH
# (adicionar no ~/.bashrc se não estiver)
export PATH="$HOME/.local/bin:$PATH"
```

### Outros sistemas

**Arch Linux:**
```bash
sudo pacman -S yt-dlp ffmpeg nodejs
```

**macOS:**
```bash
brew install yt-dlp ffmpeg node
```

**Windows (PowerShell):**
```powershell
pip install yt-dlp
winget install Gyan.FFmpeg
winget install OpenJS.NodeJS
```

---

## Uso

### Baixar uma playlist inteira em MP3

```bash
python3 spotify_dl.py "https://open.spotify.com/playlist/LINK_AQUI"
```

As músicas são salvas numa pasta com o nome da playlist.

### Escolher onde salvar

```bash
python3 spotify_dl.py "https://open.spotify.com/playlist/LINK" -o /mnt/hd/musicas
```

### Escolher formato

```bash
# FLAC (sem perda de qualidade, arquivos maiores)
python3 spotify_dl.py "https://open.spotify.com/playlist/LINK" -f flac

# OPUS (boa qualidade, arquivos menores)
python3 spotify_dl.py "https://open.spotify.com/playlist/LINK" -f opus
```

### Apenas listar as músicas (sem baixar)

```bash
python3 spotify_dl.py "https://open.spotify.com/playlist/LINK" -l
```

### Apenas gerar o arquivo batch (pra baixar depois)

```bash
python3 spotify_dl.py "https://open.spotify.com/playlist/LINK" -b
```

Isso cria o `download_all.txt`. Depois você baixa quando quiser com:

```bash
yt-dlp --js-runtimes node --remote-components ejs:github \
  --batch-file download_all.txt \
  -x --audio-format mp3 --audio-quality 0 \
  --embed-thumbnail --add-metadata \
  --ignore-errors --no-overwrites --no-playlist \
  -o '%(title)s.%(ext)s'
```

---

## Exemplo completo

```bash
# Clonar
git clone https://github.com/luiznunesMitra/spotify-playlist-downloader.git
cd spotify-playlist-downloader

# Baixar playlist pro HD externo
python3 spotify_dl.py "https://open.spotify.com/playlist/75sdPSQ4mlwKZeZluhIdiP" -o /media/seu_usuario/HD/Musicas
```

---

## Troubleshooting

### `Signature solving failed` / `n challenge solving failed`

O yt-dlp precisa do Node.js pra resolver desafios do YouTube. Instale:
```bash
sudo apt install nodejs
```

O script já usa `--js-runtimes node` e `--remote-components ejs:github` automaticamente.

### `externally-managed-environment` ao instalar yt-dlp

Use pipx em vez de pip:
```bash
sudo apt install pipx
pipx install yt-dlp
```

Ou force com:
```bash
pip install yt-dlp --break-system-packages
```

### `yt-dlp: command not found`

Se instalou via pipx, o binário fica em `~/.local/bin/`. Adicione ao PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

O script também procura automaticamente em `~/.local/bin/yt-dlp`.

### Atualizar o yt-dlp

```bash
pipx upgrade yt-dlp
```

---

## Arquivos gerados

| Arquivo | Descrição |
|---|---|
| `tracklist.txt` | Lista numerada (artista - título) |
| `download_all.txt` | Arquivo batch pro yt-dlp |
| `*.mp3` / `*.flac` | Músicas baixadas com capa e metadados |

## Limitações

- O embed do Spotify retorna no máximo 100 faixas. Para playlists maiores, o script usa o `spclient` + embeds individuais (pode demorar um pouco).
- O Spotify pode aplicar rate limit temporário. Se acontecer, espere uns minutos e tente novamente.
- Faixas muito obscuras podem não ter match exato no YouTube.

## Licença

MIT
