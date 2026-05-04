# Spotify Playlist Downloader

Baixa todas as músicas de uma playlist do Spotify em MP3/FLAC via YouTube — **sem precisar de API key ou conta do Spotify**.

## Como funciona

1. Acessa o embed da playlist no Spotify e extrai as primeiras 100 faixas
2. Usa o endpoint interno `spclient` para obter a lista completa (playlists com 100+ faixas)
3. Resolve os nomes das faixas extras via embed individual de cada track
4. Gera um arquivo batch e baixa tudo via `yt-dlp` buscando no YouTube

## Instalação

### Linux (Ubuntu/Debian)
```bash
sudo apt install yt-dlp ffmpeg
# ou via pip:
pip install yt-dlp
```

### Linux (Arch)
```bash
sudo pacman -S yt-dlp ffmpeg
```

### macOS
```bash
brew install yt-dlp ffmpeg
```

### Windows
```powershell
pip install yt-dlp
winget install Gyan.FFmpeg
```

## Uso

### Baixar playlist inteira em MP3
```bash
python spotify_dl.py "https://open.spotify.com/playlist/75sdPSQ4mlwKZeZluhIdiP"
```

### Escolher formato (FLAC, OPUS, etc)
```bash
python spotify_dl.py "https://open.spotify.com/playlist/XXXXX" --format flac
```

### Escolher pasta de saída
```bash
python spotify_dl.py "https://open.spotify.com/playlist/XXXXX" --output /mnt/hd/musicas
```

### Apenas listar as músicas (sem baixar)
```bash
python spotify_dl.py "https://open.spotify.com/playlist/XXXXX" --list-only
```

### Apenas gerar o arquivo batch (pra baixar depois/em outro PC)
```bash
python spotify_dl.py "https://open.spotify.com/playlist/XXXXX" --batch-only
```

Depois baixa manualmente com:
```bash
yt-dlp --batch-file download_all.txt -x --audio-format mp3 --audio-quality 0 -o '%(title)s.%(ext)s'
```

## Exemplos

```bash
# Baixar playlist em MP3 320kbps pro HD externo
python spotify_dl.py "https://open.spotify.com/playlist/XXXXX" -o /mnt/hd/musicas -f mp3

# Baixar em FLAC (sem perda de qualidade)
python spotify_dl.py "https://open.spotify.com/playlist/XXXXX" -f flac

# Só ver o que tem na playlist
python spotify_dl.py "https://open.spotify.com/playlist/XXXXX" -l
```

## Arquivos gerados

| Arquivo | Descrição |
|---|---|
| `tracklist.txt` | Lista numerada das músicas (artista - título) |
| `download_all.txt` | Arquivo batch para o yt-dlp |
| `*.mp3` / `*.flac` | As músicas baixadas |

## Limitações

- O embed do Spotify retorna no máximo 100 faixas por vez. Para playlists maiores, o script usa o `spclient` para obter os URIs restantes e resolve os nomes individualmente.
- O Spotify pode aplicar rate limit temporário. Se acontecer, espere uns minutos e tente novamente.
- A qualidade do áudio depende do que está disponível no YouTube. MP3 com `--audio-quality 0` resulta em ~245kbps VBR (equivalente a 320kbps CBR).
- Faixas muito obscuras ou remixes específicos do Spotify podem não ter match exato no YouTube.

## Licença

MIT
