import os
from fastapi import FastAPI, HTTPException
from py1337x import AsyncPy1337x
from torbox_api import TorboxApi

app = FastAPI()

# Inizializza lo scraper specializzato all'avvio dell'applicazione
scraper = AsyncPy1337x()

async def get_streamable_link(magnet_link: str, api_token: str):
    """Invia il magnet link a TorBox e restituisce l'URL per lo streaming."""
    sdk = TorboxApi(access_token=api_token)
    try:
        # 1. Aggiunge il torrent a TorBox
        add_result = await sdk.torrents.create_torrent(request_body={"magnet": magnet_link})
        torrent_id = add_result.data["id"]
        # 2. Seleziona il primo file audio trovato (mp3, flac, wav...)
        files = add_result.data.get("files", [])
        audio_file = next((f for f in files if f["name"].lower().endswith(('.mp3', '.flac', '.m4a', '.wav'))), None)
        if not audio_file:
            return None
        # 3. Ottiene l'URL diretto per lo streaming
        stream_response = await sdk.torrents.request_download_link(
            torrent_id=torrent_id, file_id=audio_file["id"]
        )
        return stream_response.url
    except Exception:
        return None

@app.get("/search")
async def search_endpoint(q: str):
    api_token = os.environ.get("TORBOX_API_KEY")
    if not api_token:
        raise HTTPException(status_code=500, detail="TORBOX_API_KEY not configured")

    # 1. Cerca il torrent su 1337x nella categoria MUSICA
    # ⚠️ È fondamentale specificare la 'category' per evitare risultati vuoti
    search_results = await scraper.search(q, category="MUSIC")

    if not search_results or not search_results.get('items'):
        raise HTTPException(status_code=404, detail="Nessun torrent trovato")

    # Prende il risultato con più seeders (il più popolare)
    best_match = search_results['items'][0]
    # Ottiene i dettagli completi (incluso il magnet link) usando il torrent_id
    torrent_info = await scraper.info(torrent_id=best_match['torrent_id'])

    # 2. Ottiene l'URL di streaming da TorBox
    stream_url = await get_streamable_link(torrent_info['magnet'], api_token)
    if not stream_url:
        raise HTTPException(status_code=500, detail="Impossibile generare il link di streaming")

    return {
        "title": best_match['name'],
        "stream_url": stream_url,
    }

@app.get("/")
async def root():
    return {"status": "ok", "message": "API di ricerca torrent per Eclipse Music (con TorBox)"}
