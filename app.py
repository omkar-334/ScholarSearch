from itertools import chain

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from script import main

app = FastAPI()


class QParams(BaseModel):
    author: str


@app.get("/status")
async def status():
    return {"status": "200 OK"}


@app.get("/query")
async def query(params=Depends(QParams)):
    author = params.author
    results = await main(author)
    results = chain.from_iterable(results)
    return results
