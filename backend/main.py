import json
import os
import time
from collections import defaultdict
from urllib.parse import unquote

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import AsyncGroq

# from google.cloud import firestore
# import uvicorn
from scraper import multimain, validate_query

load_dotenv()

if not (API_KEY := os.getenv("API_KEY")):
    raise ValueError("API_KEY environment variable not set in build.")

# db = firestore.Client.from_service_account_json("credentials.json", database="ss1614").collection("authors")
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# def background(response):
#     for author in response:
#         data = response["author"]
#         summary = generate_summary(data)
#         insert_record(author, data, summary)


# def record_exists(author: str):
#     authors = generate_variants(author)
#     record = db.where("name", "in", authors).limit(1).get()
#     if record:
#         record = record[0].to_dict()
#         return {record["name"]: record["response"]}


# def insert_record(author: str, data: dict, summary: str):
#     record = {"name": author.lower(), "data": data, "summary": summary}
#     db.add(record)


async def generate_summary(publications) -> str:
    prompt = (
        f"Here is a list of publications by an author:\n\n"
        f"{publications}\n\n"
        f"Please generate a summary of the author's research work based on these publications. Follow this template:\n"
        f"1. **Introduction:** Briefly introduce the author's research area.\n"
        f"2. **Key Contributions:** Highlight the major contributions or findings from the publications.\n"
        f"3. **Research Focus:** Describe the specific area or field of research the author is known for.\n"
        f"4. **Overall Impact:** Summarize the significance or impact of the author's work.\n"
        f"Provide the summary in a structured format following the above points."
    )

    chat_completion = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    print(chat_completion.choices[0].message.content)
    return chat_completion.choices[0].message.content


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
async def query(request: Request, background_tasks: BackgroundTasks, author: list[str] = Query(...), api_key: str = Query(...)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    wait_time = wait_till_request(request.headers.get("X-Forwarded-For", request.client.host))

    if wait_time > 0:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again in {int(wait_time)} seconds.")

    # fetched_results = []
    # for idx in range(len(author)):
    #     author[idx] = " ".join(author[idx].split())

    #     if record := record_exists(author[idx]):
    #         author.pop(idx)
    #         fetched_results.append(record)
    #     else:
    #         if not validate_query(author[idx]):
    #             raise HTTPException(status_code=400, detail=f"Invalid or ambiguous author name: {author[idx]}")
    for i in author:
        if not validate_query(i):
            raise HTTPException(status_code=400, detail=f"Invalid or ambiguous author name: {i}")
    results = await multimain(author)

    # background_tasks.add_task(background, response=results)
    return results


@app.get("/dummy")
async def dummy(request: Request, background_tasks: BackgroundTasks, author: list[str] = Query(...), api_key: str = Query(...)):
    with open("dummy.json", "r") as file:
        data = json.load(file)  # Load the JSON content
        return data


@app.get("/summary")
async def summary(request: Request, background_tasks: BackgroundTasks, response=Query(...), api_key: str = Query(...)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    wait_time = wait_till_request(request.headers.get("X-Forwarded-For", request.client.host))

    if wait_time > 0:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again in {int(wait_time)} seconds.")
    print(response)
    try:
        response = json.loads(unquote(response))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    response = dict(response).values()[0]
    response = [{"title": i["title"], "abstract": i["abstract"].strip()} for i in response if i["abstract"]]
    publications = "\n".join([f"Title: {i['title']}\nAbstract: {i['abstract']}\n" for i in response])
    result = await generate_summary(publications)

    # background_tasks.add_task(background, response=results)
    return result


# + fetched_results


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
        if "author" in loc:
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
