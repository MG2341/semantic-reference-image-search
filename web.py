from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from app.bootstrap import initialize_database, load_clip_model
from app.services.embedding_service import get_text_embedding
from app.web_search import SearchMatch, load_search_documents, search_documents


class SearchResponse(BaseModel):
    id: int
    title: str | None
    artist: str | None
    date: str | None
    thumbnail_url: str | None
    met_page_url: str | None
    credit_line: str | None
    score: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    model, processor = load_clip_model()
    app.state.model = model
    app.state.processor = processor
    app.state.documents = load_search_documents()
    yield


app = FastAPI(title="Semantic Reference Image Search", lifespan=lifespan)


@app.get("/search", response_model=list[SearchResponse])
def search(
    request: Request,
    q: Annotated[str, Query(min_length=1)],
    k: Annotated[int, Query(ge=1, le=100)] = 24,
) -> list[SearchResponse]:
    if not q.strip():
        raise HTTPException(status_code=400, detail="q cannot be empty")

    query_embedding = get_text_embedding(
        request.app.state.model,
        request.app.state.processor,
        q,
    )[0].tolist()
    matches = search_documents(query_embedding, request.app.state.documents, k)
    return [_to_response(match) for match in matches]


def _to_response(match: SearchMatch) -> SearchResponse:
    return SearchResponse(
        id=match.id,
        title=match.title,
        artist=match.artist,
        date=match.date,
        thumbnail_url=match.thumbnail_url,
        met_page_url=match.met_page_url,
        credit_line=match.credit_line,
        score=match.score,
    )
