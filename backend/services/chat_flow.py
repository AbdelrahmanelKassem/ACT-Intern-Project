import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from models import SessionContext, IntentLog, ChunkingTable, RagCitation, Hotel
# --- NEW: Import from your AI Factory ---
from services.ai_factory import get_dynamic_llm, get_dynamic_embeddings

async def start_session(widget_api_key: str, guest_id: str, db: AsyncSession):
    result = await db.execute(select(Hotel).where(Hotel.widget_api_key == widget_api_key))
    hotel = result.scalar_one_or_none()
    
    if not hotel:
        raise ValueError("Invalid Widget API Key")
    
    new_session = SessionContext(
        hotel_id=hotel.id,
        guest_id=guest_id,
        status="active",
        started_at=datetime.utcnow()           
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session

async def log_intent(message_id, message_content: str, db: AsyncSession):
    intent_label = "general_inquiry"  # Placeholder for MVP
    confidence = 0.95
    
    # Ensure message_id is a UUID object if it's passed as a string
    if isinstance(message_id, str):
        message_id = uuid.UUID(message_id)

    new_intent = IntentLog(
        message_id=message_id,
        detected_intent=intent_label,
        confidence_score=confidence
    )
    db.add(new_intent)
    # Remove await db.commit() here so it partakes in the main transaction block!

async def search_knowledge(question: str, top_k: int, db: AsyncSession):
    """
    Semantic Search using Factory Embeddings.
    """
    # 1. Use the factory to get the embedding model (Defaults to Gemini)
    embeddings_model = get_dynamic_embeddings()
    
    # 2. Generate the vector for the user's question
    query_vector = await embeddings_model.aembed_query(question)
    
    # 3. Search using pgvector cosine distance
    query = (
        select(
            ChunkingTable.id, 
            ChunkingTable.content_text, 
            ChunkingTable.vector_embedding.cosine_distance(query_vector).label('distance')
        )
        .order_by('distance')
        .limit(top_k)
    )
    
    result = await db.execute(query)
    return result.all()

async def generate_reply(question: str, retrieved_chunks: list[str], provider: str = "groq", model_name: str = "llama3-8b-8192"):
    """
    Generates a reply using the dynamic LLM Factory. (Defaults to Groq for speed).
    """
    # 1. Use the factory to get the text generation model
    llm = get_dynamic_llm(provider=provider, model_name=model_name)
    
    # 2. Safely handle empty context to prevent LLaMA-3 from freezing
    context = "\n---\n".join(retrieved_chunks) if retrieved_chunks else "No information available."
    
    # --- UPDATED MULTILINGUAL PROMPT ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful and polite hotel assistant. 
        Answer the guest's question strictly using the Context provided below. 
        If the answer is not in the Context, politely inform them that you will connect them with hotel staff.
        
        CRITICAL INSTRUCTION: You must detect the language of the user's question and write your final reply in that EXACT same language. 
        For example, if the user asks in Arabic, you must reply in Arabic. If they ask in Spanish, reply in Spanish.
        
        Context:
        {context}"""),
        ("user", "{question}")
    ])
    
    # 3. Add StrOutputParser() to guarantee LangChain extracts the text properly
    chain = prompt | llm | StrOutputParser()
    
    # 4. Invoke the chain (it will now return a string directly)
    response_text = await chain.ainvoke({"context": context, "question": question})
    
    # 5. Debug print so you can see exactly what the AI generates in your terminal!
    print(f"\n--- AI RESPONSE DEBUG ---:\n'{response_text}'\n-------------------------\n")
    
    # 6. Safety fallback: If Groq ever returns an empty string, send a default message
    if not response_text or not response_text.strip():
        response_text = "I apologize, but I am having a little trouble connecting to my knowledge base. Let me get a staff member to assist you."

    return response_text

async def track_citation(message_id: str, chunk_ids: list[str], similarity_scores: list[float], db: AsyncSession):
    for chunk_id, score in zip(chunk_ids, similarity_scores):
        citation = RagCitation(
            message_id=message_id,
            chunk_id=chunk_id,
            similarity_score=score
        )
        db.add(citation)