from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.bootstrap import initialize_database, load_clip_model
from app.services.embedding_service import get_text_embedding
from app.services.search_pipeline import EmbeddingSearchPipeline
from app.web_search import SearchMatch, load_search_documents, search_documents


class SearchResponse(BaseModel):
    id: int
    title: str | None
    artist: str | None
    date: str | None
    thumbnail_url: str | None
    met_page_url: str | None
    credit_line: str | None
    object_name: str | None
    museum: str | None
    medium: str | None
    dimensions: str | None
    height: str | None
    width: str | None
    department: str | None
    classification: str | None
    culture: str | None
    period: str | None
    dynasty: str | None
    reign: str | None
    country: str | None
    accession_number: str | None
    is_public_domain: bool | None
    score: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    model, processor = load_clip_model()
    app.state.model = model
    app.state.processor = processor
    documents = load_search_documents()
    app.state.search_pipeline = EmbeddingSearchPipeline(
        encoder=lambda text: get_text_embedding(model, processor, text)[0].tolist(),
        searcher=lambda embedding, top_k: search_documents(
            embedding, documents, top_k
        ),
    )
    yield


app = FastAPI(title="Semantic Reference Image Search", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(Path(__file__).with_name("index.html"), media_type="text/html")


@app.get("/search", response_model=list[SearchResponse])
def search(
    request: Request,
    q: Annotated[str, Query(min_length=1)],
    k: Annotated[int, Query(ge=1, le=100)] = 24,
) -> list[SearchResponse]:
    if not q.strip():
        raise HTTPException(status_code=400, detail="q cannot be empty")

    matches = request.app.state.search_pipeline.search(q, k)
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
        museum=match.museum,
        object_name=match.object_name,
        medium=match.medium,
        dimensions=match.dimensions,
        height=match.height,
        width=match.width,
        department=match.department,
        classification=match.classification,
        culture=match.culture,
        period=match.period,
        dynasty=match.dynasty,
        reign=match.reign,
        country=match.country,
        accession_number=match.accession_number,
        is_public_domain=match.is_public_domain,
        score=match.score,
    )
