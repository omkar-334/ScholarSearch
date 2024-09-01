import asyncio
import random
from itertools import chain
from operator import itemgetter as ig
from typing import Literal
from urllib.parse import quote

import aiohttp
import feedparser
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import dotenv_values
from fuzzywuzzy import fuzz

apidict = dotenv_values()
user_agents = [
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
    "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
    "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
]


def valid_name(author: str, name: str) -> bool:
    """Checks if the result author names match the queried author.

    Args:
        author (str): Queried author name
        name (str): Name to be checked

    Returns:
        bool: Returns True if name is valid.
    """
    name.replace(".", "").replace(",", "")
    names = [name]
    splitname = name.split()

    if len(splitname) == 2:
        first, last = splitname
        if len(first) != 1 and len(last) != 1:
            names.append(f"{first[0]} {last}")
            names.append(f"{first} {last[0]}")
    elif len(splitname) == 3:
        first, middle, last = splitname
        names.append(f"{first[0]} {middle} {last}")
        names.append(f"{first} {middle[0]} {last}")
        names.append(f"{first} {middle} {last[0]}")
        names.append(f"{first} {last}")
        names.append(f"{first[0]} {last}")
        names.append(f"{first} {last[0]}")

    for i in names:
        if fuzz.token_sort_ratio(author, i) >= 90:
            return True
    return False


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


async def abstract(session: aiohttp.ClientSession, url: str, website: Literal["pubmed", "arxiv", "inspire"]) -> str:
    """Extract abstract of the given publication.
    Also functions as a secondary event loop.

    Args:
        session (aiohttp.ClientSession):
        url (str): URL of the required publication
        website (Literal[&quot;pubmed&quot;, &quot;arxiv&quot;]): source website

    Returns:
        str: Abstract text
    """
    async with session.get(url) as response:
        if response.status == 200:
            if website == "pubmed":
                response = await response.text()
                soup = BeautifulSoup(response, "lxml")
                abstract = soup.find("div", id="abstract").text
                return abstract.strip() if abstract else None

            elif website == "arxiv":
                response = await response.text()
                soup = BeautifulSoup(response, features="xml")
                abstract = soup.find("blockquote", {"class": "abstract mathjax"}).text
                return abstract.strip() if abstract else None

            elif website == "inspire":
                res = await response.json()
                title = res["metadata"]["titles"][0]["title"]
                authors = [i["full_name"] for i in res["metadata"]["authors"]]
                abstract = res["metadata"]["abstracts"][0]["value"]
                link = url.replace("/api", "").replace("?format=json", "")
                return (title, link, abstract, authors)


async def main(author):
    async with aiohttp.ClientSession() as session:
        # functions = [ieee, dblp, arxiv, scholar, pubmed, inspire]
        functions = [ieee]
        tasks = [function(session, author) for function in functions]
        return await asyncio.gather(*tasks)


if __name__ == "__main__":
    author = "Yann LeCun"

    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(main(author))

    results = chain.from_iterable(results)
    df = pd.DataFrame(results)
    df.to_excel("df.xlsx")
