from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.mcp_enrichment import MCPEnrichment
from app.schemas.enrichment import EnrichmentCreate, EnrichmentOut, EnrichmentListResponse

router = APIRouter(prefix="/enrichments", tags=["enrichments"])


@router.post("/", response_model=EnrichmentOut)
def create_enrichment(payload: EnrichmentCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(MCPEnrichment)
        .filter(
            MCPEnrichment.entity_type == payload.entity_type,
            MCPEnrichment.entity_id == payload.entity_id,
            MCPEnrichment.mcp_source == payload.mcp_source,
        )
        .first()
    )
    if existing:
        existing.query_prompt = payload.query_prompt
        existing.response_markdown = payload.response_markdown
        existing.response_summary = payload.response_summary
        existing.citations = payload.citations
        existing.stale_after = payload.stale_after
        existing.fetched_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    enrichment = MCPEnrichment(**payload.model_dump())
    db.add(enrichment)
    db.commit()
    db.refresh(enrichment)
    return enrichment


@router.get("/", response_model=EnrichmentListResponse)
def list_enrichments(
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    mcp_source: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(MCPEnrichment)
    if entity_type:
        query = query.filter(MCPEnrichment.entity_type == entity_type)
    if entity_id:
        query = query.filter(MCPEnrichment.entity_id == entity_id)
    if mcp_source:
        query = query.filter(MCPEnrichment.mcp_source == mcp_source)

    total = query.count()
    enrichments = query.order_by(MCPEnrichment.fetched_at.desc()).all()
    return EnrichmentListResponse(enrichments=enrichments, total=total)


@router.get("/company/{company_id}", response_model=EnrichmentListResponse)
def get_company_enrichments(company_id: str, db: Session = Depends(get_db)):
    enrichments = (
        db.query(MCPEnrichment)
        .filter(MCPEnrichment.entity_type == "company", MCPEnrichment.entity_id == company_id)
        .order_by(MCPEnrichment.fetched_at.desc())
        .all()
    )
    return EnrichmentListResponse(enrichments=enrichments, total=len(enrichments))


@router.delete("/{enrichment_id}")
def delete_enrichment(enrichment_id: str, db: Session = Depends(get_db)):
    enrichment = db.query(MCPEnrichment).filter(MCPEnrichment.id == enrichment_id).first()
    if not enrichment:
        raise HTTPException(status_code=404, detail="Enrichment not found")
    db.delete(enrichment)
    db.commit()
    return {"status": "deleted"}
