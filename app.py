import asyncio
import random
import re
from itertools import chain
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


async def dblp(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://dblp.org/search/author/api?q={quote(author)}&format=json"
    headers = {"User-Agent": random.choice(user_agents)}
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            hits = data.get("result", {}).get("hits", {})
            articles = []
            for name in hits:
                if valid_name(author, name):
                    url = name.get("info", {}).get("url") + ".xml"
                    soup = BeautifulSoup(requests.get(url).content, features="xml")
                    articles = soup.find_all("article")
                    source = ["dblp"] * len(articles)
                    titles = [i.find("title").text.strip() for i in articles]
                    years = [i.find("year") for i in articles]
                    authors = [[author.text for author in i.find_all("author")] for i in articles]
                    links = [i.find("ee").text for i in articles]
                    abstracts = [None] * len(articles)
                    return (source, titles, years, authors, links, abstracts)
        return []


async def arxiv(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://export.arxiv.org/api/query?search_query=au:{quote(author)}"
    headers = {"User-Agent": random.choice(user_agents)}
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            content = await response.read()
            results = feedparser.parse(content)["entries"]
            source = ["arxiv"] * len(results)
            titles = [i["title"] for i in results]
            years = [extract_year(i["published"]) for i in results]
            authors = [[author["name"] for author in i["authors"]] for i in results]
            links = [i["link"] for i in results]
            abstracts = [i["summary"] for i in results]
            return list(zip(source, titles, years, authors, links, abstracts))
        return None


async def scholar(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://serpapi.com/search?engine=google_scholar&q=author:{quote(author)}&api_key={apidict['SERPAPI_KEY']}"
    async with session.get(url) as response:
        if response.status == 200:
            response = await response.json()
            articles = response["organic_results"]
            source = ["scholar"] * len(articles)
            titles = [i["title"] for i in articles]
            years = [extract_year(i["publication_info"]["summary"]) for i in articles]
            authors = [[author["name"] for author in i["publication_info"]["authors"]] for i in articles]
            links = [i["link"] for i in articles]
            abstracts = [None] * len(articles)
            return list(zip(source, titles, years, authors, links, abstracts))
        return None


async def pubmed(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://pubmed.ncbi.nlm.nih.gov/?term=%28{quote(author)}%5BAuthor%5D&sort="
    async with session.get(url) as response:
        if response.status == 200:
            response = await response.text()

            soup = BeautifulSoup(response, "lxml")
            baseurl = "https://pubmed.ncbi.nlm.nih.gov/"
            articles = soup.find_all("article", {"class": "full-docsum"})
            source = ["pubmed"] * len(articles)
            titles = [i.find("a", {"class": "docsum-title"}).text.strip() for i in articles]
            years = [extract_year(i.find("span", {"class": "docsum-journal-citation short-journal-citation"}).text.strip()) for i in articles]
            authors = [i.find("span", {"class": "docsum-authors full-authors"}).text.split(",") for i in articles]
            links = [baseurl + i.find("span", {"class": "citation-part"}).text.split()[-1] for i in articles]

            abstract_tasks = [abstract(session, link, "pubmed") for link in links]
            abstracts = await asyncio.gather(*abstract_tasks)
            return list(zip(source, titles, years, authors, links, abstracts))
        return []


async def inspire(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://inspirehep.net/api/literature?sort=mostrecent&size=50&page=1&q=a%3A{quote(author)}"
    async with session.get(url) as response:
        if response.status == 200:
            response = await response.json()
            links = [i["links"]["json"] for i in response["hits"]["hits"]]
            tasks = [worker(session, link, "inspire") for link in links]
            return await asyncio.gather(*tasks)
        return []


async def acmdl(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://dl.acm.org/action/doSearch?fillQuickSearch=false&target=advanced&expand=dl&field1=ContribAuthor&text1={quote(author)}"
    async with session.get(url) as response:
        if response.status == 200:
            response = await response.read()
            soup = BeautifulSoup(response, "lxml")
            articles = soup.find_all("li", {"class": "search__item issue-item-container"})
            source = ["acmdl"] * len(articles)
            titles = [i.find("span", {"class": "hlFld-Title"}).text for i in articles]
            years = [extract_year(i.find("div", {"class": "bookPubDate simple-tooltip__block--b"}).text) for i in articles]
            authors = [[j.text for j in i.find_all("span", {"class": "hlFld-ContribAuthor"})] for i in articles]
            baseurl = "https://dl.acm.org"
            links = [baseurl + i.find("span", {"class": "hlFld-Title"}).find("a").get("href") for i in articles]
            abstracts = [i.find("div", {"class": "issue-item__abstract truncate-text"}).text.strip() for i in articles]

            # abstract_tasks = [abstract(session, link, "acmdl") for link in links]
            # abstracts = await asyncio.gather(*abstract_tasks)
            return list(zip(source, titles, years, authors, links, abstracts))
        return []


async def biorxiv(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://www.biorxiv.org/search/%20author1%3A{quote(author)}%20jcode%3Abiorxiv%20numresults%3A75%20sort%3Arelevance-rank%20format_result%3Astandard"
    async with session.get(url) as response:
        if response.status == 200:
            response = await response.read()
            soup = BeautifulSoup(response, "lxml")
            baseurl = "https://www.biorxiv.org"
            links = [baseurl + i.get("href", None) for i in soup.find_all("a", {"class": "highwire-cite-linked-title"})]
            tasks = [worker(session, link, "biorxiv") for link in links]
            return await asyncio.gather(*tasks)


async def nature(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://www.nature.com/search?author={quote(author)}&order=relevance"
    async with session.get(url) as response:
        if response.status == 200:
            response = await response.read()
            soup = BeautifulSoup(response, "lxml")
            baseurl = "https://www.nature.com"
            links = [baseurl + i.get("href", None) for i in soup.find_all("a", {"class": "c-card__link u-link-inherit"})]
            tasks = [worker(session, link, "nature") for link in links]
            return await asyncio.gather(*tasks)


async def worker(session: aiohttp.ClientSession, url: str, source: str) -> list[tuple]:
    """Worker for a secondary event loop.

    Args:
        session (aiohttp.ClientSession):
        url (str): URL of the required paper
        source (str): source publication

    Returns:
        list[tuple]: list of features.
    """
    async with session.get(url) as response:
        if response.status == 200:
            if source == "inspire":
                res = await response.json()
                metadata = res["metadata"]
                title = metadata["titles"][0]["title"]
                year = metadata.get("publication_info", [{}])[0].get("year") or metadata.get("imprints", [{}])[0].get("date") or metadata.get("preprint_date")
                authors = [i["full_name"] for i in metadata["authors"]]
                link = url.replace("/api", "").replace("?format=json", "")
                abstract = metadata["abstracts"][0]["value"]
                return (source, title, extract_year(year), authors, link, abstract)

            elif source == "biorxiv":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                title = soup.find("h1", {"class": "highwire-cite-title"}).text.strip()
                year = extract_year(soup.find("div", {"class": "panel-pane pane-custom pane-1"}).text)
                authors = [i.text.strip() for i in soup.find_all("span", {"class": "highwire-citation-author"})]
                abstract = soup.find("div", {"class": "highwire-markup"}).text.strip()
                return (source, title, year, authors, url, abstract)

            elif source == "nature":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                year = extract_year(soup.find("time").text)
                title = soup.find("h1", {"class": "c-article-title"}).text.strip()
                authors = [i.text for i in soup.find_all("li", {"class": "c-article-author-list__item"})]
                abstract = soup.find("div", {"id": "Abs1-content", "class": "c-article-section__content"}).text.strip()
                return (source, title, year, authors, url, abstract)


def clean_abs(abstract: str):
    if abstract[:8].lower() == "abstract":
        abstract = abstract[8:]
        if abstract[0] == ":":
            abstract = abstract[1:]
    return abstract


async def abstract(session: aiohttp.ClientSession, url: str, source: str = None) -> str:
    """Extract abstract of the given paper based on the source publication.

    Args:
        session (aiohttp.ClientSession):
        url (str): URL of the required paper
        source (str): source publication

    Returns:
        str: Abstract text
    """
    async with session.get(url) as response:
        if response.status == 200:
            if source == "pubmed":
                response = await response.text()
                soup = BeautifulSoup(response, "lxml")
                abstract = soup.find("div", id="abstract")

            elif source == "arxiv":
                response = await response.text()
                soup = BeautifulSoup(response, features="xml")
                abstract = soup.find("blockquote", {"class": "abstract mathjax"})

            elif source == "acmdl":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                abstract = soup.find("section", id="abstract")

            elif source == "inspire":
                res = await response.json()
                abstract = res["metadata"]["abstracts"][0]["value"]

            elif source == "biorxiv":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                abstract = soup.find("div", {"class": "highwire-markup"}).text.strip()

            elif source == "nature":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                abstract = soup.find("div", {"id": "Abs1-content", "class": "c-article-section__content"}).text.strip()

            return clean_abs(abstract.text.strip()) if abstract else None


def extract_year(date):
    match = re.search(r"\b(\d{4})\b", str(date))
    if match:
        return int(match.group(1))
    return None


def extract_years(data):
    years = []
    for item in data:
        match = re.search(r"\b(\d{4})\b", str(item))
        if match:
            years.append(int(match.group(1)))
    return years


async def main(author):
    async with aiohttp.ClientSession() as session:
        # functions = [ieee, dblp, arxiv, scholar, pubmed, inspire]
        functions = [inspire]
        tasks = [function(session, author) for function in functions]
        return await asyncio.gather(*tasks)


if __name__ == "__main__":
    author = "Yann LeCun"

    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(main(author))

    results = chain.from_iterable(results)
    df = pd.DataFrame(results)
    df.to_excel("df.xlsx")
