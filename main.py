import os
import time
from collections import defaultdict
from itertools import chain
from typing import List

# import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from script import multimain, validate_query

load_dotenv()

if not (API_KEY := os.getenv("API_KEY")):
    raise ValueError("API_KEY environment variable not set in build.")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root(request: Request):
    return {
        "message": "Welcome to ScholarSearch API!",
        "endpoints": {"status", "query"},
        "ip address": [request.client.host, request.headers.get("X-Forwarded-For", request.client.host)],
    }


@app.get("/status")
async def status():
    return {"status": "200 OK"}


last_request = defaultdict(int)
RATE_LIMIT_SECONDS = 10


def wait_till_request(ip: str):
    now = time.time()
    last_time = last_request[ip]

    time_since_last_request = now - last_time
    if time_since_last_request < RATE_LIMIT_SECONDS:
        return RATE_LIMIT_SECONDS - time_since_last_request

    last_request[ip] = now
    return 0


@app.get("/query")
async def query(request: Request, author: List[str] = Query(...), api_key: str = Query(...)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    wait_time = wait_till_request(request.headers.get("X-Forwarded-For", request.client.host))

    if wait_time > 0:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again in {int(wait_time)} seconds.")

    for idx in range(len(author)):
        author[idx] = " ".join(author[idx].split())

        if not validate_query(author[idx]):
            raise HTTPException(status_code=400, detail=f"Invalid or ambiguous author name: {author[idx]}")

    results = await multimain(author)
    results = list(chain.from_iterable(results))
    results = [lst for lst in results if lst]
    return {"data": results}


@app.exception_handler(RequestValidationError)
async def handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    for error in error_details:
        loc = error["loc"]
        if "api_key" in loc:
            return JSONResponse(
                status_code=400,
                content={"detail": "API key parameter is required."},
            )
        elif "author" in loc:
            return JSONResponse(
                status_code=400,
                content={"detail": "Atleast one author parameter is required."},
            )
    return JSONResponse(status_code=422, content={"detail": error_details})


# if __name__ == "__main__":
#     uvicorn.run(
#         app,
#         port=8080,
#         host="0.0.0.0",
#         timeout_keep_alive=60,
#     )
