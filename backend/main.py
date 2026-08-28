import logging
import traceback
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import httpx
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import models from your models package
from models import MessageLog, Document, ChunkingTable, SessionContext
from database import AsyncSessionLocal
from services.ai_factory import get_dynamic_embeddings
# --- Import the booking handler ---
from services.chat_flow import log_intent, search_knowledge, generate_reply, track_citation, handle_booking_flow
from routers import analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hotel Chatbot API",
    description="Multi-tenant hotel reservation and knowledge base AI API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

class DocumentUploadRequest(BaseModel):
    document_id: str
    source_url: str
    source_type: str = "url"

class ChatRequest(BaseModel):
    session_id: str
    message: str

class RatingRequest(BaseModel):
    session_id: str
    rating: int

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Hotel Chatbot Backend is running successfully!",
        "docs_url": "/docs"
    }

@app.post("/upload-document")
async def upload_document(request: DocumentUploadRequest, db: AsyncSession = Depends(get_db)):
    try:
        doc_uuid = uuid.UUID(request.document_id)
        result = await db.execute(select(Document).where(Document.id == doc_uuid))
        document = result.scalars().first()

        if not document:
            raise HTTPException(status_code=404, detail="Document ID not found in database.")

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

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = text_splitter.split_text(full_text)[:15]

        logger.info(f"Processing {len(chunks)} chunks. Generating embeddings...")

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

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    try:
        try:
            sess_uuid = uuid.UUID(request.session_id)
        except (ValueError, TypeError):
            sess_uuid = uuid.UUID("d93f3d75-2de5-43e4-831b-8df52d20fdc5")

        # --- 1. Find or Create the Session FIRST ---
        session_obj = await db.execute(select(SessionContext).where(SessionContext.id == sess_uuid))
        session_ctx = session_obj.scalar_one_or_none()
        
        if not session_ctx:
            # Generate a valid Guest UUID in Python
            new_guest_id = uuid.uuid4()
            
            # Insert the Guest via raw SQL
            await db.execute(text("""
                INSERT INTO guest (id, name, phone, email) 
                VALUES (:id, :name, :phone, :email)
            """), {
                "id": new_guest_id,
                "name": "Anonymous Guest",
                "phone": "N/A",
                "email": "N/A"
            })
            
            # Insert the Session with the valid Guest UUID via raw SQL
            await db.execute(text("""
                INSERT INTO session_context (id, hotel_id, guest_id, status, started_at) 
                VALUES (:id, :hotel_id, :guest_id, :status, :started_at)
            """), {
                "id": sess_uuid,
                "hotel_id": uuid.UUID("19a70845-1b5e-423a-b5c6-83a9851bbebe"),
                "guest_id": new_guest_id,
                "status": "active",
                "started_at": datetime.utcnow()
            })
            await db.flush()
            
            # Fetch it back so we have the ORM object for the rest of the flow
            session_obj = await db.execute(select(SessionContext).where(SessionContext.id == sess_uuid))
            session_ctx = session_obj.scalar_one_or_none()

        hotel_uuid = session_ctx.hotel_id

        # --- 2. NOW Save the user's message log ---
        user_msg = MessageLog(
            session_id=sess_uuid,
            sender="user",
            content=request.message
        )
        db.add(user_msg)
        await db.flush()

        # --- 3. Fetch Chat History for Memory ---
        history_query = select(MessageLog).where(MessageLog.session_id == sess_uuid)
        history_result = await db.execute(history_query)
        all_messages = history_result.scalars().all()
        
        recent_messages = all_messages[-6:] 
        chat_history = "\n".join([f"{msg.sender.capitalize()}: {msg.content}" for msg in recent_messages])

        # --- 4. Log intent ---
        detected_intent = await log_intent(user_msg.id, request.message, chat_history, db)

        # --- THE ROUTER ---
        if detected_intent == "room_booking":
            reply = await handle_booking_flow(request.message, chat_history, hotel_uuid, sess_uuid, db)
            chunk_ids = []
            similarity_scores = []
        else:
            search_results = await search_knowledge(request.message, top_k=3, db=db)

            retrieved_chunks = [row.content_text for row in search_results]
            chunk_ids = [row.id for row in search_results]
            similarity_scores = [1.0 - float(row.distance) for row in search_results]

            reply = await generate_reply(request.message, retrieved_chunks)

        # --- 5. Save the assistant's reply log ---
        assistant_msg = MessageLog(
            session_id=sess_uuid,
            sender="assistant",
            content=reply
        )
        db.add(assistant_msg)
        await db.flush()

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

# --- NEW: Rating Endpoint ---
@app.post("/rate-session")
async def rate_session(request: RatingRequest, db: AsyncSession = Depends(get_db)):
    try:
        sess_uuid = uuid.UUID(request.session_id)
        
        # 1. Find the session
        result = await db.execute(select(SessionContext).where(SessionContext.id == sess_uuid))
        session_ctx = result.scalar_one_or_none()
        
        # 2. If the user didn't send a message first, create the session using raw SQL!
        if not session_ctx:
            new_guest_id = uuid.uuid4()
            
            await db.execute(text("""
                INSERT INTO guest (id, name, phone, email) 
                VALUES (:id, :name, :phone, :email)
            """), {
                "id": new_guest_id,
                "name": "Anonymous Rater",
                "phone": "N/A",
                "email": "N/A"
            })
            
            await db.execute(text("""
                INSERT INTO session_context (id, hotel_id, guest_id, status, rating, started_at) 
                VALUES (:id, :hotel_id, :guest_id, :status, :rating, :started_at)
            """), {
                "id": sess_uuid,
                "hotel_id": uuid.UUID("19a70845-1b5e-423a-b5c6-83a9851bbebe"),
                "guest_id": new_guest_id,
                "status": "ended",
                "rating": request.rating,
                "started_at": datetime.utcnow()
            })
        else:
            # Otherwise, just update the existing session
            session_ctx.status = "ended"
            session_ctx.rating = request.rating
            
        await db.commit()
        
        return {"status": "success", "message": f"Session ended with a {request.rating}-star rating."}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Rating endpoint crashed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save rating")