import asyncio
from torbox_api import TorboxApi
from typing import Optional

# Costanti per l'API
TORBOX_API_URL = "https://api.torbox.app/v1/api"

async def get_streamable_link(magnet_link: str, api_token: str) -> Optional[str]:
    """
    Prende un magnet link, lo aggiunge a TorBox e restituisce un link per lo streaming.
    """
    # 1. Inizializza il client TorBox con il token dell'utente
    client = TorboxApi(access_token=api_token, base_url=TORBOX_API_URL)

    try:
        # 2. Aggiunge il torrent a TorBox (endpoint: POST /torrents/createtorrent)
        add_response = await client.torrents.create_torrent(
            request_body={"magnet": magnet_link}
        )
        
        # 3. Verifica che la risposta sia valida
        if not add_response or not add_response.data:
            print("[ERROR] ❌ Impossibile aggiungere il torrent a TorBox.")
            return None

        torrent_id = add_response.data.get("id")
        print(f"[LOG] ✅ Torrent aggiunto con ID: {torrent_id}")

        # 4. Attesa del completamento del download
        is_cached = await wait_for_download(client, torrent_id)
        if not is_cached:
            print("[ERROR] ❌ Timeout o errore durante il download su TorBox.")
            return None

        # 5. Seleziona il primo file audio disponibile (puoi migliorare la logica)
        files = add_response.data.get("files", [])
        audio_file_id = None
        for file in files:
            if file.get("name", "").lower().endswith(('.mp3', '.flac', '.m4a', '.wav')):
                audio_file_id = file.get("id")
                break
        
        if not audio_file_id:
            print("[ERROR] ❌ Nessun file audio trovato nel torrent.")
            return None

        # 6. Genera il link di streaming (endpoint: GET /torrents/requestdl)
        stream_response = await client.torrents.request_download_link(
            torrent_id=torrent_id, file_id=audio_file_id
        )
        # Nota: questo endpoint restituisce direttamente l'URL (spesso un redirect)

        # 7. Restituisce l'URL per lo streaming
        if stream_response and hasattr(stream_response, 'url'): # Adatta in base alla risposta effettiva
            print("[LOG] 🔗 Link di streaming generato.")
            return stream_response.url
        else:
            return None

    except Exception as e:
        print(f"[ERROR] ❌ Eccezione in TorBox: {e}")
        return None


async def wait_for_download(client, torrent_id: str, timeout: int = 30) -> bool:
    """
    Esegue il polling dello stato del torrent fino al completamento o al timeout.
    """
    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        # Endpoint per ottenere informazioni: POST /torrents/controltorrent?op=info
        status_response = await client.torrents.control_torrent(
            torrent_id=torrent_id, operation="info"
        )
        
        if status_response and status_response.data:
            status = status_response.data.get("status")
            # Gli stati "downloaded" o "cached" indicano che il file è pronto
            if status in ("downloaded", "cached"):
                print(f"[LOG] ✅ Torrent pronto dopo {asyncio.get_event_loop().time() - start_time:.2f} secondi.")
                return True
            elif status == "error":
                print("[ERROR] ❌ Stato 'error' dal torrent.")
                return False
        await asyncio.sleep(3)
    return False
