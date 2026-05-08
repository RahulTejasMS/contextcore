# ============================================================
# documents.py — File upload and document management endpoints
#
# POST /documents/upload  → upload a file
# GET  /documents         → list all documents for this tenant
# GET  /documents/{id}    → get status of one document
# ============================================================
import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.database import get_db
from app.core.security import verify_token
from app.core.storage import upload_file_to_s3, ensure_bucket_exists
from app.core.kafka_producer import publish

router = APIRouter()
bearer_scheme = HTTPBearer()

# Allowed file types
ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/markdown": "md",
    "text/plain": "txt",
    "text/html": "html",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/documents/upload", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_db),
):
    """
    Uploads a document for processing.
    Returns 202 Accepted — processing happens asynchronously.

    Flow:
    1. Verify JWT → get tenant_id
    2. Validate file type and size
    3. Compute SHA-256 hash (for deduplication)
    4. Upload to MinIO/S3
    5. Insert record into PostgreSQL (status: "uploaded")
    6. Publish to Kafka topic "doc.uploaded"
    7. Return document_id to client for status polling
    """
    # Step 1: Verify auth
    payload = verify_token(credentials.credentials)
    tenant_id = payload["sub"]

    # Step 2: Validate file type
    content_type = file.content_type
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{content_type}' not supported. "
                   f"Allowed: {list(ALLOWED_TYPES.values())}"
        )

    # Step 3: Read file and check size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is 50MB."
        )

    # Step 4: Compute SHA-256 hash for deduplication
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    # Check if this exact file was already uploaded by this tenant
    existing = await db.fetchrow(
        "SELECT id, status FROM documents WHERE tenant_id = $1 AND content_hash = $2",
        tenant_id, content_hash
    )
    if existing:
        return {
            "document_id": str(existing["id"]),
            "status": existing["status"],
            "message": "Document already exists (duplicate detected)",
            "duplicate": True,
        }

    # Step 5: Upload to MinIO/S3
    file_ext = ALLOWED_TYPES[content_type]
    document_id = str(uuid.uuid4())
    s3_key = f"tenants/{tenant_id}/{document_id}.{file_ext}"

    ensure_bucket_exists()
    upload_file_to_s3(file_bytes, s3_key, content_type)

    # Step 6: Insert into PostgreSQL
    await db.execute(
        """
        INSERT INTO documents
            (id, tenant_id, filename, file_type, s3_key,
             file_size_bytes, content_hash, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, 'uploaded')
        """,
        document_id,
        tenant_id,
        file.filename,
        file_ext,
        s3_key,
        len(file_bytes),
        content_hash,
    )

    # Step 7: Publish Kafka event
    await publish("doc.uploaded", {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "s3_key": s3_key,
        "file_type": file_ext,
        "filename": file.filename,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "document_id": document_id,
        "status": "uploaded",
        "message": "Document uploaded successfully. Processing started.",
        "filename": file.filename,
        "size_bytes": len(file_bytes),
        "duplicate": False,
    }


@router.get("/documents")
async def list_documents(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_db),
):
    """Returns all documents for the authenticated tenant."""
    payload = verify_token(credentials.credentials)
    tenant_id = payload["sub"]

    # Set RLS context
    await db.execute(f"SET app.tenant_id = '{tenant_id}'")

    rows = await db.fetch(
        """
        SELECT id, filename, file_type, file_size_bytes,
               status, error_message, created_at, updated_at
        FROM documents
        WHERE tenant_id = $1
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return [dict(row) for row in rows]


@router.get("/documents/{document_id}")
async def get_document_status(
    document_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db=Depends(get_db),
):
    """
    Returns the current status of a document.
    Clients poll this endpoint to know when processing is done.
    Status flow: uploaded → parsing → chunking → embedding → ready | failed
    """
    payload = verify_token(credentials.credentials)
    tenant_id = payload["sub"]

    row = await db.fetchrow(
        """
        SELECT id, filename, file_type, file_size_bytes,
               status, error_message, created_at, updated_at
        FROM documents
        WHERE id = $1 AND tenant_id = $2
        """,
        document_id, tenant_id,
    )

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    # Count how many chunks were created (0 until processing starts)
    chunk_count = await db.fetchval(
        "SELECT COUNT(*) FROM chunks WHERE document_id = $1",
        document_id,
    )

    return {
        **dict(row),
        "chunk_count": chunk_count,
    }