import random
import re

import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag
from fuzzywuzzy import fuzz

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


def to_dict(source, title, year, authors, link, abstract):
    return {"source": source, "title": title, "year": year, "authors": authors, "link": link, "abstract": abstract}


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
        variants.update({
            f"{first[0]} {middle} {last}",
            f"{first} {middle[0]} {last}",
            f"{first} {middle} {last[0]}",
            f"{first[0]} {middle[0]} {last[0]}",
            f"{middle[0]} {first[0]} {last[0]}",
            # f"{first} {last}",
            # f"{first[0]} {last}",
            # f"{first} {last[0]}",
        })
    return variants


def valid_name(variants, name, ratio=None):
    if not ratio:
        ratio = 90
    name = name.replace(".", "").replace(",", "").lower()
    return any(fuzz.token_sort_ratio(i, name) >= ratio for i in variants)


def valid_names(names: list[str], author: str, ratio=None):
    variants = generate_variants(author)
    return any(valid_name(variants, name, ratio) for name in names)


def valid_affil(query, result):
    if query in result or result in query:
        return True
    return fuzz.token_sort_ratio(result, query) >= 80


def clean_abs(abstract: str):
    if isinstance(abstract, Tag):
        abstract = abstract.text
    if not abstract:
        return None
    abstract = abstract.strip().replace("\n", "").replace("\t", "").replace("\xa0", " ")
    if abstract[:8].lower() == "abstract":
        abstract = abstract[8:]
        if abstract[0] == ":":
            abstract = abstract[1:]
    abstract = abstract.strip().replace("\n", "").replace("\t", "").replace("\xa0", " ")
    return abstract


def clean_author(author):
    author = re.sub(r"\d+\s*na\d*,\s*|&\s*|,", "", author)
    author = re.sub(r"\s+", " ", author.strip())
    return author


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
    # "doi.org": "doi",
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
    source = source_map.get(domain)
    return source


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


def validate_query(author: str):
    author = author.strip()
    if not author:
        return False
    if len(author.split()) <= 1:
        return False
    if len(author) > 25:
        return False
    return re.match(r"^[A-Za-z\s]+$", author)


async def abstract(session: aiohttp.ClientSession, url: str, source: str = None) -> str:
    """Extract abstract of the given paper based on the source publication.

    Args:
        session (aiohttp.ClientSession):
        url (str): URL of the required paper
        source (str): source publication

    Returns:
        str: Abstract text
    """
    if not source and not (source := extract_source(url)):
        return None

    # Too many redirects error
    if source == "openreview":
        return None

    async with session.get(url, headers=random_headers()) as response:
        abstract = None

        if response.status == 200:
            # DOI redirects websites, so checking URL of response is necessary.
            if source == "doi":
                url = str(response.url)
                if not (source := extract_source(url)):
                    return None

            elif source == "scholar":
                response = await response.read()
                soup = BeautifulSoup(response, "html.parser")
                abstract = soup.find("div", {"class": "gsh_small"})

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
                return clean_abs(abstract)
    return None
