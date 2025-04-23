import asyncio
import os
import time
from itertools import chain
from urllib.parse import quote

import aiohttp
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from utils import (
    abstract,
    clean_abs,
    clean_author,
    extract_year,
    random_headers,
    to_dict,
    valid_affil,
    valid_names,
)

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")


async def linker(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://serpapi.com/search?engine=google_scholar&q=author:{quote(author)}&api_key={SERPAPI_KEY}"
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            response = await response.json()
            articles = response["organic_results"]
            linkmap = {i["title"]: i.get("link", "") for i in articles}
            return linkmap
    return {}


async def scholar(session: aiohttp.ClientSession, author: str, affiliation: str = None) -> list[tuple]:
    url = f"https://serpapi.com/search.json?engine=google_scholar_profiles&mauthors={quote(author)}&api_key={SERPAPI_KEY}"
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            response = await response.json()

            if affiliation:
                for profile in response["profiles"]:
                    if valid_names([profile["name"]], author, 80):
                        if valid_affil(affiliation, profile["affiliations"]):
                            author_id = profile["author_id"]
                            break
                else:
                    return []
            else:
                profile = response["profiles"][0]
                if valid_names([profile["name"]], author, 80):
                    author_id = profile["author_id"]
                else:
                    return []

            results, tasks = [], []
            url = f"https://serpapi.com/search.json?engine=google_scholar_author&author_id={author_id}&api_key={SERPAPI_KEY}"
            async with session.get(url, headers=random_headers()) as response:
                response = await response.json()
                table = response["cited_by"]["table"]
                info = response["author"] | {"graph": response["cited_by"]["graph"]} | table[0] | table[1] | table[2]

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
                return [results, info]

    return []


async def dblp(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    t = time.time()
    url = f"https://dblp.org/search/author/api?q={quote(author)}&format=json"
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            data = await response.json()
            hits = data.get("result", {}).get("hits", {}).get("hit", {})
            for i in hits:
                info = i["info"]
                tempauthor = clean_author(info["author"])
                if valid_names([tempauthor], author):
                    url = info.get("url") + ".xml"
                    print(url, time.time() - t)
                    async with session.get(url, headers=random_headers()) as response:
                        res = await response.read()
                        soup = BeautifulSoup(res, features="xml")
                        articles = soup.find_all("article")
                        source = ["dblp"] * len(articles)
                        titles = [i.find("title").text.strip() for i in articles]
                        years = [extract_year(i.find("year").text) for i in articles]
                        authors = [[author.text for author in i.find_all("author")] for i in articles]
                        links = [i.find("ee").text for i in articles]
                        tasks = [abstract(session, link) for link in links]
                        abstracts = await asyncio.gather(*tasks)
                        results = list(zip(source, titles, years, authors, links, abstracts))
                        return [to_dict(*i) for i in results if i]
        return []


async def arxiv(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://export.arxiv.org/api/query?search_query=au:{quote(author)}"
    results = []
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            content = await response.read()
            articles = feedparser.parse(content)["entries"]
            for i in articles:
                authors = [clean_author(author["name"]) for author in i["authors"]]
                if valid_names(authors, author):
                    title = i["title"]
                    year = extract_year(i["published"])
                    link = i["link"]
                    abstract = clean_abs(i["summary"])
                    results.append(to_dict("arxiv", title, year, authors, link, abstract))
    return results


async def pubmed(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://pubmed.ncbi.nlm.nih.gov/?term=%28{quote(author)}%5BAuthor%5D&sort="
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            results, tasks = [], []
            response = await response.text()

            soup = BeautifulSoup(response, "lxml")
            baseurl = "https://pubmed.ncbi.nlm.nih.gov/"
            articles = soup.find_all("article", {"class": "full-docsum"})
            for i in articles:
                authors = [clean_author(i) for i in i.find("span", {"class": "docsum-authors full-authors"}).text.split(",")]
                if valid_names(authors, author):
                    title = i.find("a", {"class": "docsum-title"}).text.strip()
                    year = extract_year(i.find("span", {"class": "docsum-journal-citation short-journal-citation"}).text.strip())
                    link = baseurl + i.find("span", {"class": "citation-part"}).text.split()[-1]
                    tasks.append(abstract(session, link, "pubmed"))
                    results.append(("pubmed", title, year, authors, link))

            abstracts = await asyncio.gather(*tasks)
            return [to_dict(a, b, c, d, e, f) for (a, b, c, d, e), f in zip(results, abstracts)]
        return []


async def inspire(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://inspirehep.net/api/literature?sort=mostrecent&size=50&page=1&q=a%3A{quote(author)}"
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            response = await response.json()
            links = [i["links"]["json"] for i in response["hits"]["hits"]]
            tasks = [worker(session, link, "inspire", author) for link in links]
            return await asyncio.gather(*tasks)
        return []


async def acmdl(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://dl.acm.org/action/doSearch?fillQuickSearch=false&target=advanced&expand=dl&field1=ContribAuthor&text1={quote(author)}"
    results = []
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            response = await response.read()
            soup = BeautifulSoup(response, "lxml")
            articles = soup.find_all("li", {"class": "search__item issue-item-container"})
            for i in articles:
                authors = [clean_author(j.text) for j in i.find_all("span", {"class": "hlFld-ContribAuthor"})]
                if valid_names(authors, author):
                    title = i.find("span", {"class": "hlFld-Title"}).text.strip()
                    year = extract_year(i.find("div", {"class": "bookPubDate simple-tooltip__block--b"}).text)
                    link = "https://dl.acm.org" + i.find("span", {"class": "hlFld-Title"}).find("a").get("href")
                    abstract = clean_abs(i.find("div", {"class": "issue-item__abstract truncate-text"}).text.strip())
                    results.append(to_dict("acmdl", title, year, authors, link, abstract))
    return results


async def biorxiv(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://www.biorxiv.org/search/%20author1%3A{quote(author)}%20jcode%3Abiorxiv%20numresults%3A75%20sort%3Arelevance-rank%20format_result%3Astandard"
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            response = await response.read()
            soup = BeautifulSoup(response, "lxml")
            baseurl = "https://www.biorxiv.org"
            links = [baseurl + i.get("href", None) for i in soup.find_all("a", {"class": "highwire-cite-linked-title"})]
            tasks = [worker(session, link, "biorxiv", author) for link in links]
            return await asyncio.gather(*tasks)
    return None


async def nature(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://www.nature.com/search?author={quote(author)}&order=relevance"
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            response = await response.read()
            soup = BeautifulSoup(response, "lxml")
            baseurl = "https://www.nature.com"
            links = [baseurl + i.get("href", None) for i in soup.find_all("a", {"class": "c-card__link u-link-inherit"})]
            tasks = [worker(session, link, "nature", author) for link in links]
            return await asyncio.gather(*tasks)
    return None


### NOTE - IEEE and Scopus need Institute Ethernet for access
async def ieee(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = "https://ieeexplore.ieee.org/rest/search"
    headers = random_headers() | {
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


async def worker(session: aiohttp.ClientSession, url: str, source: str, author: str) -> list[tuple]:
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
                authors = [clean_author(i["full_name"]) for i in metadata["authors"]]
                if valid_names(authors, author):
                    title = metadata["titles"][0]["title"]
                    year = metadata.get("publication_info", [{}])[0].get("year") or metadata.get("imprints", [{}])[0].get("date") or metadata.get("preprint_date")
                    link = url.replace("/api", "").replace("?format=json", "")
                    try:
                        abstract = metadata["abstracts"][0]["value"]
                    except:
                        abstract = None
                    return to_dict(source, title, extract_year(year), authors, link, clean_abs(abstract))

            elif source == "biorxiv":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                authors = [clean_author(i.text) for i in soup.find_all("span", {"class": "highwire-citation-author"})]
                if valid_names(authors, author):
                    title = soup.find("h1", {"class": "highwire-cite-title"}).text.strip()
                    year = soup.find("div", {"class": "panel-pane pane-custom pane-1"}).text
                    abstract = soup.find("div", {"class": "highwire-markup"})
                    return to_dict(source, title, extract_year(year), authors, url, clean_abs(abstract))

            elif source == "nature":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                authors = [clean_author(i.text) for i in soup.find_all("li", {"class": "c-article-author-list__item"})]
                if valid_names(authors, author):
                    year = soup.find("time").text
                    title = soup.find("h1", {"class": "c-article-title"}).text.strip()
                    abstract = soup.find("div", {"id": "Abs1-content", "class": "c-article-section__content"})
                    return to_dict(source, title, extract_year(year), authors, url, clean_abs(abstract))
    return None


async def main(author, affiliation=None, functions: list = None):
    async with aiohttp.ClientSession() as session:
        if not functions:
            functions = [arxiv, pubmed, acmdl, biorxiv, nature]
        tasks = [function(session, author) for function in functions]
        sres = await scholar(session, author, affiliation)
        results = await asyncio.gather(*tasks)
        results = [result for result in results if result is not None]
        return {"data": list(chain.from_iterable(results)) + sres[0], "info": sres[1]}


async def multimain(authors: list[str], affiliation=None):
    tasks = [main(author, affiliation) for author in authors]
    results = await asyncio.gather(*tasks)
    return dict(zip(authors, results))
