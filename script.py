import asyncio
import os
import random
import re
import time
from urllib.parse import quote

import aiohttp
import feedparser
from bs4 import BeautifulSoup
from bs4.element import Tag
from dotenv import load_dotenv
from fuzzywuzzy import fuzz

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

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


def random_headers():
    return {"User-Agent": random.choice(user_agents)}


def generate_variants(author: str) -> set[str]:
    author = author.replace(".", "").replace(",", "").lower()
    variants = {author}
    splitname = author.split()

    if len(splitname) == 2:
        first, last = splitname
        if len(first) > 1 and len(last) > 1:
            variants.add(f"{first[0]} {last}")
            variants.add(f"{first} {last[0]}")
    elif len(splitname) == 3:
        first, middle, last = splitname
        variants.update(
            {
                f"{first[0]} {middle} {last}",
                f"{first} {middle[0]} {last}",
                f"{first} {middle} {last[0]}",
                f"{first} {last}",
                f"{first[0]} {last}",
                f"{first} {last[0]}",
            }
        )
    return variants


def valid_name(variants, name):
    name = name.replace(".", "").replace(",", "").lower()
    for i in variants:
        if fuzz.token_sort_ratio(i, name) >= 90:
            return True
    return False


def valid_names(names: list[str], author: str):
    variants = generate_variants(author)
    for name in names:
        if valid_name(variants, name):
            return True
    return False


async def dblp(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    t = time.time()
    url = f"https://dblp.org/search/author/api?q={quote(author)}&format=json"
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            data = await response.json()
            hits = data.get("result", {}).get("hits", {}).get("hit", {})
            for i in hits:
                info = i["info"]
                if valid_name(generate_variants(author), info["author"]):
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
                        return list(zip(source, titles, years, authors, links, abstracts))
        return []


# 5.924
async def arxiv(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://export.arxiv.org/api/query?search_query=au:{quote(author)}"
    results = []
    async with session.get(url, headers=random_headers()) as response:
        if response.status == 200:
            content = await response.read()
            articles = feedparser.parse(content)["entries"]
            for i in articles:
                authors = [author["name"] for author in i["authors"]]
                if valid_names(authors, author):
                    title = i["title"]
                    year = extract_year(i["published"])
                    link = i["link"]
                    abstract = clean_abs(i["summary"])
                    results.append(("arxiv", title, year, authors, link, abstract))
    return results


async def scholar(session: aiohttp.ClientSession, author: str) -> list[tuple]:
    url = f"https://serpapi.com/search?engine=google_scholar&q=author:{quote(author)}&api_key={SERPAPI_KEY}"
    async with session.get(url, headers=random_headers()) as response:
        results, tasks = [], []
        if response.status == 200:
            response = await response.json()
            articles = response["organic_results"]
            for i in articles:
                authors = [author["name"] for author in i["publication_info"]["authors"]]
                if valid_names(authors, author):
                    title = i["title"]
                    year = extract_year(i["publication_info"]["summary"])
                    link = i["link"]
                    tasks.append(abstract(session, link))
                    results.append(("scholar", title, year, authors, link))

            abstracts = await asyncio.gather(*tasks)
            return [(a, b, c, d, e, f) for (a, b, c, d, e), f in zip(results, abstracts)]
        return None


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
                authors = i.find("span", {"class": "docsum-authors full-authors"}).text.split(",")
                if valid_names(authors, author):
                    title = i.find("a", {"class": "docsum-title"}).text.strip()
                    year = extract_year(i.find("span", {"class": "docsum-journal-citation short-journal-citation"}).text.strip())
                    link = baseurl + i.find("span", {"class": "citation-part"}).text.split()[-1]
                    tasks.append(abstract(session, link, "pubmed"))
                    results.append(("pubmed", title, year, authors, link))

            abstracts = await asyncio.gather(*tasks)
            return [(a, b, c, d, e, f) for (a, b, c, d, e), f in zip(results, abstracts)]
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
                authors = [j.text for j in i.find_all("span", {"class": "hlFld-ContribAuthor"})]
                if valid_names(authors, author):
                    title = i.find("span", {"class": "hlFld-Title"}).text.strip()
                    year = extract_year(i.find("div", {"class": "bookPubDate simple-tooltip__block--b"}).text)
                    link = "https://dl.acm.org" + i.find("span", {"class": "hlFld-Title"}).find("a").get("href")
                    abstract = clean_abs(i.find("div", {"class": "issue-item__abstract truncate-text"}).text.strip())
                    results.append(("acmdl", title, year, authors, link, abstract))
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
                authors = [i["full_name"] for i in metadata["authors"]]
                if valid_names(authors, author):
                    title = metadata["titles"][0]["title"]
                    year = metadata.get("publication_info", [{}])[0].get("year") or metadata.get("imprints", [{}])[0].get("date") or metadata.get("preprint_date")
                    link = url.replace("/api", "").replace("?format=json", "")
                    abstract = metadata["abstracts"][0]["value"]
                    return (source, title, extract_year(year), authors, link, clean_abs(abstract))

            elif source == "biorxiv":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                authors = [i.text.strip() for i in soup.find_all("span", {"class": "highwire-citation-author"})]
                if valid_names(authors, author):
                    title = soup.find("h1", {"class": "highwire-cite-title"}).text.strip()
                    year = soup.find("div", {"class": "panel-pane pane-custom pane-1"}).text
                    abstract = soup.find("div", {"class": "highwire-markup"}).text.strip()
                    return (source, title, extract_year(year), authors, url, clean_abs(abstract))

            elif source == "nature":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                authors = [i.text for i in soup.find_all("li", {"class": "c-article-author-list__item"})]
                if valid_names(authors, author):
                    year = soup.find("time").text
                    title = soup.find("h1", {"class": "c-article-title"}).text.strip()
                    abstract = soup.find("div", {"id": "Abs1-content", "class": "c-article-section__content"}).text.strip()
                    return (source, title, extract_year(year), authors, url, clean_abs(abstract))


def clean_abs(abstract: str):
    abstract = abstract.strip()
    if abstract[:8].lower() == "abstract":
        abstract = abstract[8:]
        if abstract[0] == ":":
            abstract = abstract[1:]
    return abstract


source_map = {
    "www.nature.com": "nature",
    "ieeexplore.ieee.org": "ieee",
    "arxiv.org": "arxiv",
    "proceedings.neurips.cc": "neurips",
    "openreview.net": "openreview",
    "jmlr.org": "jmlr",
    "dl.acm.org": "acmdl",
    "pubmed.ncbi.nlm.nih.gov": "pubmed",
    "inspirehep.net": "inspire",
    "www.biorxiv.org": "biorxiv",
    "www.mdpi.com": "mdpi",
    "www.frontiersin.org": "frontiers",
    "doi.org": "doi",
    # -----
    # Access blocked - JS needed
    # -----
    # "www.worldscientific.com": "world",
    # "www.sciencedirect.com": "sciencedirect",
    # "www.science.org": "science",
    # "linkinghub.elsevier.com" : "elsevier",
    # "link.springer.com" : "springer",
    # -----
    # Not Implemented
    # -----
    # "citeseerx.ist.psu.edu": "citeseerx",
    # "direct.mit.edu": "mit",
}


def extract_source(url: str):
    match = re.search(r"https*://([^/]+)", url)
    domain = match.group(1)
    source = source_map.get(domain, None)
    return source


async def abstract(session: aiohttp.ClientSession, url: str, source: str = None) -> str:
    """Extract abstract of the given paper based on the source publication.

    Args:
        session (aiohttp.ClientSession):
        url (str): URL of the required paper
        source (str): source publication

    Returns:
        str: Abstract text
    """
    if not source:
        if not (source := extract_source(url)):
            return None

    ### Too many redirects error
    if source == "openreview":
        return

    async with session.get(url, headers=random_headers()) as response:
        abstract = None

        if response.status == 200:
            # DOI reroutes websites, so checking URL of response is necessary.
            if source == "doi":
                url = str(response.url)
                if not (source := extract_source(url)):
                    return None

            if source == "pubmed":
                response = await response.text()
                soup = BeautifulSoup(response, "lxml")
                abstract = soup.find("div", id="abstract")

            elif source == "arxiv":
                response = await response.read()
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
                abstract = soup.find("div", {"class": "highwire-markup"})

            elif source == "nature":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                abstract = soup.find("div", {"id": "Abs1-content", "class": "c-article-section__content"})

            elif source == "openreview":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                abstract = soup.find("meta", {"name": "citation_abstract"}).get("content")

            elif source == "jmlr":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                abstract = soup.find("p", {"class": "abstract"})

            elif source == "neurips":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                text = soup.find("div", {"class": "col"}).text
                match = re.split(r"Abstract|abstract", text, maxsplit=1)
                abstract = match[1] if len(match) == 2 else None

            elif source == "mdpi":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                abstract = soup.find("section", {"class": "html-abstract"})

            elif source == "ieee":
                res = await response.text()
                soup = BeautifulSoup(res, "lxml")
                content = soup.select_one('meta[property="og:description"]')
                if content and "content" in content:
                    soup = BeautifulSoup(content["content"], "lxml")
                    abstract = soup.get_text(separator=" ", strip=True)

            elif source == "frontiers":
                res = await response.read()
                soup = BeautifulSoup(res, "lxml")
                soup = soup.find("div", {"class": "JournalFullText"})
                abstract = soup.find("div", {"class": "JournalAbstract"})

                if authors := abstract.find("div", {"class": "authors"}):
                    authors.decompose()
                if notes := abstract.find("ul", {"class": "notes"}):
                    notes.decompose()

            if abstract:
                if isinstance(abstract, Tag):
                    abstract = abstract.text
                abstract = clean_abs(abstract)
                return abstract


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


async def main(author, functions: list = None):
    async with aiohttp.ClientSession() as session:
        if not functions:
            functions = [arxiv, pubmed, inspire, acmdl, biorxiv, nature]
        tasks = [function(session, author) for function in functions]
        print(author)
        return await asyncio.gather(*tasks)


async def multimain(authors: list[str]):
    tasks = [main(author) for author in authors]
    results = await asyncio.gather(*tasks)

    results = [item for sublist in results for item in sublist]
    return results


def validate_query(author: str):
    author = author.strip()
    if not author or author == "":
        return False
    if len(author.split()) <= 1:
        return False
    if len(author) > 25:
        return False
    if not re.match(r"^[A-Za-z\s]+$", author):
        return False
    return True
