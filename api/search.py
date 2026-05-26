import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

BASE_URL = "https://www.1377x.to"

async def search_torrents(query: str) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = f"{BASE_URL}/search/music/{query}/1/"
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table.table-list tbody tr")
        torrents = []
        for row in rows:
            link_tag = row.select_one("td.coll-1 a[href*='/torrent/']")
            if not link_tag:
                continue
            torrent_url = BASE_URL + link_tag.get("href")
            title = link_tag.get_text(strip=True)
            seeders = int(row.select_one("td.coll-2").get_text(strip=True) or 0)
            torrents.append({
                "name": title,
                "seeders": seeders,
                "torrent_url": torrent_url
            })
        torrents.sort(key=lambda x: x["seeders"], reverse=True)
        # Poi per il miglior risultato, ottieni il magnet (chiamata separata)
        if torrents:
            magnet = await _get_magnet(torrents[0]["torrent_url"], client)
            torrents[0]["magnet"] = magnet
        return torrents
