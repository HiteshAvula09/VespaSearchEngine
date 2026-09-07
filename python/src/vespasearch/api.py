from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .config import get_settings
from .vespa_client import VespaClient
from .llm import grounded_answer


settings = get_settings()
app = FastAPI(title="VespaSearch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    mode: Literal["bm25", "semantic", "hybrid"] = "hybrid"
    source: Literal["slack", "google_drive", "github"] | None = None
    hits: int = Field(default=5, ge=1, le=20)
    generate: bool = True


@app.get("/health")
def health():
    return {"status": "ok", "service": "VespaSearch API"}


@app.post("/search")
def search(request: SearchRequest):
    try:
        results = VespaClient().search(
            request.query,
            request.mode,
            request.source,
            request.hits,
        )
        answer = grounded_answer(request.query, results) if request.generate else None

        return {
            "query": request.query,
            "mode": request.mode,
            "source_filter": request.source,
            "answer": answer,
            "results": results,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
