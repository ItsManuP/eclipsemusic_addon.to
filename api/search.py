import os
from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

TORBOX_API_URL = "https://api.torbox.app/v1/api"

async def search_apibay(query: str):
    url = f"https://apibay.org/q.php?q={query}&cat=100"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    results = []
    for item in data:
        if not item.get("name"):
            continue
        results.append({
            "name": item["name"],
            "magnet": f"magnet:?xt=urn:btih:{item['info_hash']}&dn={item['name']}",
            "seeders": int(item.get("seeders", 0))
        })
    results.sort(key=lambda x: x["seeders"], reverse=True)
    return results

async def add_torrent_to_torbox(magnet: str, api_token: str):
    """Aggiunge un torrent a TorBox tramite magnet link (usa form data)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        headers = {"Authorization": f"Bearer {api_token}"}
        # Importante: usare data= (form-urlencoded) non json=
        resp = await client.post(
            f"{TORBOX_API_URL}/torrents/createtorrent",
            data={"magnet": magnet},
            headers=headers
        )
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")
        result = resp.json()
        if not result.get("success"):
            raise Exception(f"TorBox error: {result.get('error')} - {result.get('detail')}")
        return str(result["data"]["id"])

async def get_torrent_status(torrent_id: str, api_token: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        headers = {"Authorization": f"Bearer {api_token}"}
        info_resp = await client.post(
            f"{TORBOX_API_URL}/torrents/controltorrent?torrent_id={torrent_id}&op=info",
            headers=headers
        )
        if info_resp.status_code != 200:
            return {"status": "error", "detail": "Torrent not found"}
        info = info_resp.json()
        if not info.get("success"):
            return {"status": "error", "detail": info.get("error")}
        data = info["data"]
        status = data["status"]
        if status not in ("downloaded", "cached"):
            return {"status": status}
        # Cerca file audio
        files = data.get("files", [])
        audio_file = next((f for f in files if f["name"].lower().endswith(('.mp3','.flac','.m4a','.wav'))), None)
        if not audio_file:
            return {"status": "error", "detail": "No audio file found"}
        # Ottieni link streaming (requestdl)
        stream_resp = await client.get(
            f"{TORBOX_API_URL}/torrents/requestdl?torrent_id={torrent_id}&file_id={audio_file['id']}",
            headers=headers,
            follow_redirects=True
        )
        return {"status": "completed", "stream_url": str(stream_resp.url), "filename": audio_file["name"]}

@app.get("/search")
async def search_endpoint(q: str):
    api_token = os.environ.get("TORBOX_API_KEY")
    if not api_token:
        raise HTTPException(500, "TORBOX_API_KEY not configured")
    if not q:
        raise HTTPException(400, "Missing 'q' parameter")
    torrents = await search_apibay(q)
    if not torrents:
        raise HTTPException(404, "No torrents found")
    best = torrents[0]
    try:
        torrent_id = await add_torrent_to_torbox(best["magnet"], api_token)
    except Exception as e:
        raise HTTPException(500, f"TorBox error: {str(e)}")
    return {
        "torrent_id": torrent_id,
        "title": best["name"],
        "status": "downloading",
        "message": "Use /status?torrent_id=... to get the stream URL when ready"
    }

@app.get("/status")
async def status_endpoint(torrent_id: str):
    api_token = os.environ.get("TORBOX_API_KEY")
    if not api_token:
        raise HTTPException(500, "TORBOX_API_KEY not configured")
    if not torrent_id:
        raise HTTPException(400, "Missing 'torrent_id' parameter")
    result = await get_torrent_status(torrent_id, api_token)
    if result["status"] == "completed":
        return {"status": "ready", "stream_url": result["stream_url"], "filename": result.get("filename")}
    elif result["status"] in ("downloading", "queued", "processing", "cached"):
        return {"status": "pending", "state": result["status"]}
    else:
        raise HTTPException(404, result.get("detail", "Torrent not ready or error"))

@app.get("/")
async def root():
    return {"status": "ok", "message": "Eclipse Torrent Addon (async TorBox with form-data)"}
