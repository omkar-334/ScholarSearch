import asyncio
import os
from urllib.parse import quote

import aiohttp
from dotenv import load_dotenv

from utils import (
    abstract,
    clean_author,
    extract_year,
    random_headers,
    to_dict,
    valid_names,
)

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")


async def google_scholar(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://serpapi.com/search?engine=google_scholar&q=author:{quote(author)}&api_key={SERPAPI_KEY}"
    async with session.get(url, headers=random_headers()) as response:
        results, tasks = [], []
        if response.status == 200:
            response = await response.json()
            articles = response["organic_results"]
            for i in articles:
                print(i["publication_info"])
                authors = [clean_author(author["name"]) for author in i["publication_info"]["authors"]]
                if valid_names(authors, author):
                    title = i["title"]
                    year = extract_year(i["publication_info"]["summary"])
                    link = i["link"]
                    tasks.append(abstract(session, link))
                    results.append(("scholar", title, year, authors, link))

            abstracts = await asyncio.gather(*tasks)
            return [to_dict(a, b, c, d, e, f) for (a, b, c, d, e), f in zip(results, abstracts)]
        return None


async def scholar(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://serpapi.com/search.json?engine=google_scholar_profiles&mauthors={quote(author)}&api_key={SERPAPI_KEY}"
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            response = await response.json()
            try:
                author_id = response["profiles"][0]["author_id"]
                tempauthor = None
                if not valid_names([tempauthor], author):
                    return []
            except:
                return []
            results, tasks = [], []
            url = f"https://serpapi.com/search.json?engine=google_scholar_author&author_id={author_id}&api_key={SERPAPI_KEY}"
            async with session.get(url, headers=random_headers()) as response:
                response = await response.json()
                table = response["cited_by"]["table"]
                info = response["author"] | {"graph": response["cited_by"]["graph"]} | table[0] | table[1] | table[2]
                info.pop("interests")

                articles = response["articles"]
                for i in articles:
                    authors = [clean_author(author) for author in i["authors"].split(",")]
                    title = i["title"]
                    year = extract_year(i["year"])
                    link = i["link"]
                    tasks.append(abstract(session, link, "scholar"))
                    results.append(("scholar", title, year, authors, link))
            abstracts = await asyncio.gather(*tasks)
            results = [to_dict(a, b, c, d, e, f) for (a, b, c, d, e), f in zip(results, abstracts)]
            return {"results": results, "info": info}
            return results
