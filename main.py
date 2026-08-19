from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

# Import your database session and rag_engine functions
from app.db.database import AsyncSessionLocal
from rag_engine import process_document, embed_vectors, DocumentProcessingError

app = FastAPI(title="Hotel Chatbot API")

# Dependency to get the database session safely
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Pydantic schema for incoming payload validation
class DocumentUploadRequest(BaseModel):
    document_id: str
    source_url: str
    source_type: str = "url"  # Default to url if not specified (options: url, pdf, docx, txt, database)


@app.post("/upload-document")
async def upload_document(request: DocumentUploadRequest, db: AsyncSession = Depends(get_db)):
    """
    POST /upload-document endpoint:
    1. Ingests and extracts raw text from a source (URL, PDF, etc.).
    2. Splits the raw text into smaller chunks.
    3. Generates vector embeddings via Gemini and stores them in the database.
    """
    try:
        # Step 1: Process and extract text from the source URL/document
        raw_text = await process_document(request.source_url, request.source_type)
        
        if not raw_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from the source.")

        # Step 2: Create chunks (splitting text by paragraphs or length constraints)
        # Simple paragraph-based splitting for now
        chunks = [chunk.strip() for chunk in raw_text.split("\n\n") if chunk.strip()]
        
        if not chunks:
            # Fallback split by lines if no double-newlines exist
            chunks = [line.strip() for line in raw_text.split("\n") if line.strip()]

        # Step 3: Pass chunks to your embed_vectors function to vectorize and save to DB
        await embed_vectors(chunks=chunks, document_id=request.document_id, db=db)

        return {
            "status": "success",
            "message": f"Successfully processed and embedded document {request.document_id}.",
            "total_chunks_saved": len(chunks)
        }

    except DocumentProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")