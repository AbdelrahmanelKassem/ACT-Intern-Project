import logging
import traceback
import uuid
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import models from your models package
from models import MessageLog, Document, ChunkingTable
from database import AsyncSessionLocal
from services.ai_factory import get_dynamic_embeddings
from services.chat_flow import log_intent, search_knowledge, generate_reply, track_citation
from routers import analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hotel Chatbot API",
    description="Multi-tenant hotel reservation and knowledge base AI API",
    version="1.0.0"
)

# --- CORS Middleware Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your Vite frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Modular Routers ---
app.include_router(analytics.router)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# --- Pydantic Request Schemas ---
class DocumentUploadRequest(BaseModel):
    document_id: str
    source_url: str
    source_type: str = "url"


class ChatRequest(BaseModel):
    session_id: str
    message: str


# --- Health Check Route ---
@app.get("/")
async def root():
    """Health check endpoint to verify backend status."""
    return {
        "status": "online",
        "message": "Hotel Chatbot Backend is running successfully!",
        "docs_url": "/docs"
    }


# --- Document Upload & Ingestion Endpoint ---
@app.post("/upload-document")
async def upload_document(request: DocumentUploadRequest, db: AsyncSession = Depends(get_db)):
    """
    POST /upload-document endpoint:
    1. Validates the document ID exists in the database.
    2. Fetches and scrapes text asynchronously using httpx and BeautifulSoup.
    3. Splits text into chunks and generates embeddings.
    4. Saves the chunks and vectors to Supabase.
    """
    try:
        doc_uuid = uuid.UUID(request.document_id)

        # A. Verify Document ID exists
        result = await db.execute(select(Document).where(Document.id == doc_uuid))
        document = result.scalars().first()

        if not document:
            raise HTTPException(status_code=404, detail="Document ID not found in database.")

        # B. Asynchronously fetch the webpage
        logger.info(f"Fetching URL: {request.source_url}")
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(request.source_url)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch URL, status code: {response.status_code}"
                )
            html_content = response.text

        soup = BeautifulSoup(html_content, "html.parser")
        for script in soup(["script", "style"]):
            script.decompose()
        full_text = soup.get_text(separator=" ")

        if not full_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract any text from the URL.")

        # C. Intelligent Text Chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = text_splitter.split_text(full_text)[:15]

        logger.info(f"Processing {len(chunks)} chunks. Generating embeddings...")

        # D. Generate Embeddings and Save to Database
        embeddings_model = get_dynamic_embeddings()
        new_chunks = []

        for chunk_text in chunks:
            cleaned_text = " ".join(chunk_text.split())
            if not cleaned_text:
                continue

            vector = embeddings_model.embed_query(cleaned_text)

            new_chunk = ChunkingTable(
                id=uuid.uuid4(),
                document_id=doc_uuid,
                content_text=cleaned_text,
                vector_embedding=vector
            )
            db.add(new_chunk)
            new_chunks.append(new_chunk)

        await db.commit()

        return {
            "status": "success",
            "message": f"Successfully scraped, chunked, and embedded {len(new_chunks)} blocks of text.",
            "chunks_processed": len(new_chunks)
        }

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Upload-document crashed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


# --- Chat Flow Endpoint ---
@app.post("/chat")
async def chat_endpoint(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    POST /chat endpoint:
    1. Logs the user message.
    2. Identifies user intent.
    3. Retrieves relevant RAG chunks via vector similarity.
    4. Generates an AI response.
    5. Logs the assistant reply and citations.
    """
    try:
        # Safely parse session_id; if invalid, fall back to default valid UUID
        try:
            sess_uuid = uuid.UUID(request.session_id)
        except (ValueError, TypeError):
            sess_uuid = uuid.UUID("d93f3d75-2de5-43e4-831b-8df52d20fdc5")

        # 1. Save the user's message log
        user_msg = MessageLog(
            session_id=sess_uuid,
            sender="user",
            content=request.message
        )
        db.add(user_msg)
        await db.flush()

        # 2. Log intent
        await log_intent(user_msg.id, request.message, db)

        # 3. Perform Semantic Search
        search_results = await search_knowledge(request.message, top_k=3, db=db)

        retrieved_chunks = [row.content_text for row in search_results]
        chunk_ids = [row.id for row in search_results]
        similarity_scores = [1.0 - float(row.distance) for row in search_results]

        # 4. Generate AI Reply
        reply = await generate_reply(request.message, retrieved_chunks)

        # 5. Save the assistant's reply log
        assistant_msg = MessageLog(
            session_id=sess_uuid,
            sender="assistant",
            content=reply
        )
        db.add(assistant_msg)
        await db.flush()

        # 6. Log citations
        if chunk_ids:
            await track_citation(assistant_msg.id, chunk_ids, similarity_scores, db)

        await db.commit()

        return {
            "reply": reply
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Chat endpoint crashed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")