#!/usr/bin/env python3
"""
spotify_dl.py - Baixa músicas de playlists do Spotify via YouTube

Extrai todas as faixas de uma playlist do Spotify (sem precisar de API key)
e baixa em MP3/FLAC usando yt-dlp.

Uso:
    python3 spotify_dl.py <URL_DA_PLAYLIST> [--output PASTA] [--format mp3|flac|opus]
    python3 spotify_dl.py <URL_DA_PLAYLIST> --list-only
    python3 spotify_dl.py <URL_DA_PLAYLIST> --batch-only

Requisitos:
    pip install yt-dlp   (ou pipx install yt-dlp)
    sudo apt install ffmpeg nodejs
"""

import argparse
import json
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_url(url, headers=None, ctx=None):
    if ctx is None:
        ctx = get_ssl_context()
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    resp = urllib.request.urlopen(req, context=ctx, timeout=20)
    return resp.read()


def get_embed_token_and_first_100(playlist_id):
    """Busca o token de acesso e as primeiras 100 faixas do embed do Spotify."""
    print("[1/3] Buscando dados do embed do Spotify...")
    url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
    html = fetch_url(url).decode("utf-8", errors="ignore")

    token_match = re.search(r'accessToken":"([^"]+)"', html)
    if not token_match:
        print("ERRO: Nao foi possivel obter token do Spotify.")
        sys.exit(1)
    token = token_match.group(1)

    nd = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not nd:
        print("ERRO: Nao foi possivel extrair dados da playlist.")
        sys.exit(1)

    data = json.loads(nd.group(1))
    entity = data["props"]["pageProps"]["state"]["data"]["entity"]
    playlist_name = entity.get("name", "playlist")
    track_list = entity.get("trackList", [])

    first_100 = []
    for t in track_list:
        subtitle = t.get("subtitle", "").replace("\xa0", " ")
        title = t.get("title", "")
        uri = t.get("uri", "")
        first_100.append({"artist": subtitle, "title": title, "uri": uri})

    print(f"   Playlist: {playlist_name}")
    print(f"   Faixas no embed: {len(first_100)}")
    return token, playlist_name, first_100


def get_all_track_uris(playlist_id, token):
    """Usa o spclient para obter TODOS os URIs da playlist (sem limite de 100)."""
    print("[2/3] Buscando lista completa de faixas via spclient...")
    url = f"https://spclient.wg.spotify.com/playlist/v2/playlist/{playlist_id}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    try:
        raw = fetch_url(url, headers=headers)
        data = json.loads(raw.decode("utf-8"))
        items = data.get("contents", {}).get("items", [])
        uris = [item["uri"] for item in items]
        print(f"   Total de faixas na playlist: {len(uris)}")
        return uris
    except Exception as e:
        print(f"   spclient falhou ({e}), usando apenas as faixas do embed.")
        return None


def resolve_tracks_via_embed(track_ids, start_index=101):
    """Resolve nomes das faixas acessando o embed individual de cada track."""
    print(f"   Resolvendo nomes de {len(track_ids)} faixas via embed individual...")
    results = []
    for idx, tid in enumerate(track_ids):
        try:
            url = f"https://open.spotify.com/embed/track/{tid}"
            html = fetch_url(url).decode("utf-8", errors="ignore")

            nd = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
            )
            if nd:
                data = json.loads(nd.group(1))
                entity = data["props"]["pageProps"]["state"]["data"]["entity"]
                title = entity.get("title", "Unknown")
                subtitle = entity.get("subtitle", "").replace("\xa0", " ")
                results.append({"artist": subtitle, "title": title, "uri": f"spotify:track:{tid}"})
                num = start_index + idx
                artist_display = subtitle if subtitle else "?"
                print(f"   {num}. {artist_display} - {title}")
            else:
                results.append({"artist": "", "title": f"Unknown_{tid}", "uri": f"spotify:track:{tid}"})

            if (idx + 1) % 10 == 0:
                time.sleep(0.5)
        except Exception as e:
            results.append({"artist": "", "title": f"Error_{tid}", "uri": f"spotify:track:{tid}"})
            print(f"   {start_index + idx}. ERRO: {e}")
            time.sleep(1)

    return results


def get_playlist_tracks(playlist_id):
    """Pipeline completo: pega todas as faixas da playlist."""
    token, playlist_name, first_100 = get_embed_token_and_first_100(playlist_id)

    all_uris = get_all_track_uris(playlist_id, token)

    if all_uris and len(all_uris) > len(first_100):
        extra_ids = [uri.split(":")[-1] for uri in all_uris[len(first_100):]]
        print(f"[3/3] Resolvendo {len(extra_ids)} faixas extras...")
        extra_tracks = resolve_tracks_via_embed(extra_ids, start_index=len(first_100) + 1)
        all_tracks = first_100 + extra_tracks
    else:
        print("[3/3] Todas as faixas ja foram obtidas do embed.")
        all_tracks = first_100

    return playlist_name, all_tracks


def extract_playlist_id(url):
    """Extrai o ID da playlist de uma URL do Spotify."""
    match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
    if not match:
        print(f"ERRO: URL invalida: {url}")
        print("Use uma URL como: https://open.spotify.com/playlist/XXXXX")
        sys.exit(1)
    return match.group(1)


def build_search_query(track):
    """Monta a query de busca pro yt-dlp."""
    artist = track["artist"]
    title = track["title"]
    if artist:
        return f"ytsearch1:{artist} - {title}"
    return f"ytsearch1:{title}"


def save_batch_file(tracks, output_path):
    """Salva o arquivo batch para o yt-dlp."""
    with open(output_path, "w", encoding="utf-8") as f:
        for t in tracks:
            query = build_search_query(t)
            f.write(query + "\n")
    return output_path


def save_tracklist(tracks, output_path):
    """Salva a lista de faixas legivel."""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, t in enumerate(tracks, 1):
            artist = t["artist"] if t["artist"] else "?"
            f.write(f"{i}. {artist} - {t['title']}\n")


def find_yt_dlp():
    """Encontra o yt-dlp no sistema (pode estar em ~/.local/bin via pipx)."""
    yt_dlp = shutil.which("yt-dlp")
    if yt_dlp:
        return yt_dlp

    # Checar paths comuns do pipx
    candidates = [
        Path.home() / ".local" / "bin" / "yt-dlp",
        Path.home() / ".local" / "share" / "pipx" / "venvs" / "yt-dlp" / "bin" / "yt-dlp",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    return None


def check_dependencies():
    """Verifica se yt-dlp, ffmpeg e nodejs estao instalados."""
    yt_dlp = find_yt_dlp()
    if not yt_dlp:
        print("ERRO: yt-dlp nao encontrado!")
        print("Instale com: pipx install yt-dlp")
        print("         ou: pip install yt-dlp --break-system-packages")
        sys.exit(1)

    if not shutil.which("ffmpeg"):
        print("ERRO: ffmpeg nao encontrado!")
        print("Instale com: sudo apt install ffmpeg")
        sys.exit(1)

    if not shutil.which("node"):
        print("AVISO: nodejs nao encontrado. O download pode falhar.")
        print("Instale com: sudo apt install nodejs")

    return yt_dlp


def download_tracks(batch_file, output_dir, audio_format="mp3"):
    """Executa o yt-dlp para baixar todas as faixas."""
    yt_dlp = find_yt_dlp()

    cmd = [
        yt_dlp,
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "--batch-file", str(batch_file),
        "--extract-audio",
        "--audio-format", audio_format,
        "--audio-quality", "0",
        "--embed-thumbnail",
        "--add-metadata",
        "--no-playlist",
        "--concurrent-fragments", "4",
        "--ignore-errors",
        "--no-overwrites",
        "-o", str(output_dir / "%(title)s.%(ext)s"),
    ]

    print(f"\nBaixando {audio_format.upper()} para: {output_dir}")
    print(f"Comando: {' '.join(cmd)}\n")
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="Baixa musicas de playlists do Spotify via YouTube",
        epilog="Exemplo: python3 spotify_dl.py https://open.spotify.com/playlist/XXXXX",
    )
    parser.add_argument("url", help="URL da playlist do Spotify")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Pasta de saida (padrao: nome da playlist)",
    )
    parser.add_argument(
        "--format", "-f",
        default="mp3",
        choices=["mp3", "flac", "opus", "m4a", "wav"],
        help="Formato do audio (padrao: mp3)",
    )
    parser.add_argument(
        "--list-only", "-l",
        action="store_true",
        help="Apenas lista as faixas, nao baixa",
    )
    parser.add_argument(
        "--batch-only", "-b",
        action="store_true",
        help="Apenas gera o arquivo batch (download_all.txt), nao baixa",
    )

    args = parser.parse_args()

    playlist_id = extract_playlist_id(args.url)
    print(f"Playlist ID: {playlist_id}\n")

    playlist_name, tracks = get_playlist_tracks(playlist_id)

    safe_name = re.sub(r'[<>:"/\\|?*]', '', playlist_name).strip()
    output_dir = Path(args.output) if args.output else Path(safe_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    tracklist_path = output_dir / "tracklist.txt"
    save_tracklist(tracks, tracklist_path)
    print(f"\nTracklist salva em: {tracklist_path}")

    batch_path = output_dir / "download_all.txt"
    save_batch_file(tracks, batch_path)
    print(f"Batch file salvo em: {batch_path}")

    print(f"\nTotal: {len(tracks)} faixas")

    if args.list_only:
        print("\n--- Lista completa ---")
        for i, t in enumerate(tracks, 1):
            artist = t["artist"] if t["artist"] else "?"
            print(f"{i}. {artist} - {t['title']}")
        return

    if args.batch_only:
        print("\nArquivo batch gerado. Para baixar manualmente:")
        print(f"  yt-dlp --js-runtimes node --remote-components ejs:github \\")
        print(f"    --batch-file {batch_path} -x --audio-format mp3 --audio-quality 0 \\")
        print(f"    --ignore-errors --no-overwrites -o '%(title)s.%(ext)s'")
        return

    check_dependencies()
    download_tracks(batch_path, output_dir, args.format)

    count = len(list(output_dir.glob(f"*.{args.format}")))
    print(f"\nConcluido! {count} arquivos baixados em: {output_dir}")


if __name__ == "__main__":
    main()
