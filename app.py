from itertools import chain

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from script import main

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QParams(BaseModel):
    author: str


@app.get("/status")
async def status():
    return {"status": "200 OK"}


@app.get("/query")
async def query(params=Depends(QParams)):
    author = params.author
    results = await main(author)
    results = list(chain.from_iterable(results))
    return {"data": results}
