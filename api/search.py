from fastapi import FastAPI, HTTPException, Header
from typing import Optional
from utils.torrent_scraper import search_torrents
from utils.torbox import get_streamable_link  # <-- Import aggiornato

app = FastAPI()

@app.get("/search")
async def search_torrents_endpoint(q: str, authorization: Optional[str] = Header(None)):
    """
    Endpoint per cercare torrent e ottenere un link di streaming.
    """
    # 1. Autenticazione
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Real-Debrid API token")
    api_token = authorization.replace("Bearer ", "")
    
    # 2. Ricerca torrent su 1337x
    torrents = search_torrents(q)
    if not torrents:
        raise HTTPException(status_code=404, detail="No torrents found")
    
    best_match = torrents[0]
    magnet_link = best_match.get("magnet")
    if not magnet_link:
        raise HTTPException(status_code=500, detail="Magnet link not available")
    
    # 3. Streaming con TorBox
    stream_url = await get_streamable_link(magnet_link, api_token)
    if not stream_url:
        raise HTTPException(status_code=500, detail="Failed to generate stream URL")
    
    # 4. Risposta finale
    return {
        "title": best_match["name"],
        "artist": "Unknown Artist",
        "stream_url": stream_url,
        "format": "audio/mpeg",
        "quality": "320kbps"
    }

@app.get("/")
async def root():
    return {"message": "Eclipse Torrent Addon with TorBox is running. Use /search?q=..."}
