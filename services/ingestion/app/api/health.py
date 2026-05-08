from fastapi import APIRouter, Depends
from app.core.database import get_db

router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check(db=Depends(get_db)):
    await db.fetchval("SELECT 1")
    return {"status": "healthy", "service": "ingestion", "version": "1.0.0"}