import os
from fastapi import FastAPI, HTTPException, Header
from typing import Optional
from utils.torrent_scraper import search_torrents
from utils.torbox import get_streamable_link

app = FastAPI()

@app.get("/search")
async def search_torrents_endpoint(q: str):
    """
    Endpoint per cercare torrent e ottenere un link di streaming.
    Usa il token TorBox dalla variabile d'ambiente (uso personale).
    """
    # Leggi il token dalle variabili d'ambiente di Vercel
    api_token = os.environ.get("TORBOX_API_KEY")
    if not api_token:
        raise HTTPException(status_code=500, detail="TORBOX_API_KEY not configured on server")

    # 1. Cerca il torrent su 1337x
    torrents = search_torrents(q)
    if not torrents:
        raise HTTPException(status_code=404, detail="No torrents found")

    best_match = torrents[0]
    magnet_link = best_match.get("magnet")
    if not magnet_link:
        raise HTTPException(status_code=500, detail="Magnet link not available")

    # 2. Ottieni il link di streaming da TorBox
    stream_url = await get_streamable_link(magnet_link, api_token)
    if not stream_url:
        raise HTTPException(status_code=500, detail="Failed to generate stream URL")

    # 3. Risposta finale
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
