import asyncio
import httpx
from typing import Optional, Dict, Any

REAL_DEBRID_API = "https://api.real-debrid.com/rest/1.0"

async def get_streamable_link(magnet_link: str, api_token: str) -> Optional[str]:
    """
    Prende un magnet link, lo aggiunge a Real-Debrid e restituisce un link per lo streaming.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {api_token}"}
        try:
            # 1. Aggiungi il magnet link a Real-Debrid
            add_response = await client.post(
                f"{REAL_DEBRID_API}/torrents/addMagnet",
                data={"magnet": magnet_link},
                headers=headers
            )
            add_response.raise_for_status()
            torrent_id = add_response.json().get("id")
            if not torrent_id:
                return None
            # 2. Seleziona tutti i file audio (mp3, flac, ecc.)
            info_response = await client.get(
                f"{REAL_DEBRID_API}/torrents/info/{torrent_id}",
                headers=headers
            )
            info_response.raise_for_status()
            files = info_response.json().get("files", [])
            audio_file_ids = [
                str(f["id"]) for f in files
                if f.get("path", "").lower().endswith(('.mp3', '.flac', '.m4a', '.wav'))
            ]
            if audio_file_ids:
                await client.post(
                    f"{REAL_DEBRID_API}/torrents/selectFiles/{torrent_id}",
                    data={"files": ",".join(audio_file_ids)},
                    headers=headers
                )
            # 3. Attendi che il download sia completato (polling)
            while True:
                status_response = await client.get(
                    f"{REAL_DEBRID_API}/torrents/info/{torrent_id}",
                    headers=headers
                )
                status_response.raise_for_status()
                torrent_info = status_response.json()
                status = torrent_info.get("status")
                if status == "downloaded":
                    break
                elif status == "error":
                    return None
                await asyncio.sleep(2)
            # 4. Ottieni i link "unrestricted"
            links = torrent_info.get("links", [])
            if not links:
                return None
            unrestricted_response = await client.post(
                f"{REAL_DEBRID_API}/unrestrict/link",
                data={"link": links[0]},
                headers=headers
            )
            unrestricted_response.raise_for_status()
            return unrestricted_response.json().get("download")
        except Exception as e:
            print(f"[ERROR] ❌ Errore con Real-Debrid: {e}")
            return None
