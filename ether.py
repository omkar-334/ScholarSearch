import random
from urllib.parse import quote

import aiohttp

from app import user_agents


### NOTE - IEEE and Scopus need Institute Ethernet for access
async def ieee(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = "https://ieeexplore.ieee.org/rest/search"
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Referer": "https://ieeexplore.ieee.org/search/searchresult.jsp",
        "Origin": "https://ieeexplore.ieee.org",
    }

    payload = {"newsearch": True, "queryText": f'("Authors":{quote(author)})', "highlight": True, "returnFacets": ["ALL"], "returnType": "SEARCH", "matchPubs": True}

    async with session.post(url, headers=headers, json=payload) as response:
        if response.status == 200:
            response = await response.read()
            # print(response)
            # results = list(chain.from_iterable([i["authors"] for i in response["records"]]))
            # results = list(set([i.get("id", 0) for i in results if (author in i["preferredName"] or fuzz.ratio(author, i["preferredName"]) >= 90)]))
            # results.remove(0)
            # return results
            with open("sample.txt", "wb") as f:
                f.write(response)
        return None
