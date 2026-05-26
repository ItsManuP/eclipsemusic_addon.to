from fastapi import FastAPI, HTTPException
import httpx
import traceback

app = FastAPI()

async def search_torrents(query: str):
    url = f"https://apibay.org/q.php?q={query}&cat=100"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
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

@app.get("/search")
async def search_endpoint(q: str):
    try:
        torrents = await search_torrents(q)
        if not torrents:
            raise HTTPException(404, "Nessun torrent trovato")
        return {
            "title": torrents[0]["name"],
            "magnet": torrents[0]["magnet"],
            "seeders": torrents[0]["seeders"]
        }
    except httpx.TimeoutException:
        raise HTTPException(500, "Timeout nella richiesta a apibay.org")
    except Exception as e:
        # Restituisci l'errore completo per il debug
        raise HTTPException(500, f"Errore: {str(e)}\n{traceback.format_exc()}")

@app.get("/query")
async def query_alias(q: str):
    return await search_endpoint(q)

@app.get("/")
async def root():
    return {"status": "ok"}
