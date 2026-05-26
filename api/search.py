import httpx
from typing import List, Dict, Any

async def search_torrents(query: str) -> List[Dict[str, Any]]:
    """
    Cerca torrent su The Pirate Bay usando l'API pubblica apibay.org
    """
    try:
        url = f"https://apibay.org/q.php?q={query}&cat=100"  # cat=100 è musica
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            data = response.json()
        
        torrents = []
        for item in data:
            if item.get("name"):
                torrents.append({
                    'name': item['name'],
                    'magnet': f"magnet:?xt=urn:btih:{item['info_hash']}&dn={item['name']}",
                    'seeders': int(item.get('seeders', 0)),
                    'leechers': int(item.get('leechers', 0)),
                    'size': item.get('size', '0'),
                    'info_hash': item['info_hash']
                })
        return torrents
    except Exception as e:
        print(f"[ERROR] ❌ Errore nella ricerca TPB: {e}")
        return []
