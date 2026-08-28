import uuid
import random
import string
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field

from models import SessionContext, IntentLog, ChunkingTable, RagCitation, Hotel, Guest, RoomBooking
# --- NEW: Import from your AI Factory and Recommender ---
from services.ai_factory import get_dynamic_llm, get_dynamic_embeddings
from services.recommender import get_upsell_recommendation

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


async def log_intent(message_id, message_content: str, chat_history: str, db: AsyncSession):
    llm = get_dynamic_llm(provider="groq", model_name="llama3-8b-8192")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert intent classifier for a luxury hotel. 
        Analyze the guest's LATEST message and categorize it into EXACTLY ONE of the following intents:
        - room_booking
        - late_checkout
        - amenities_inquiry
        - complaint
        - spa_reservation
        - general_inquiry
        
        CRITICAL CONTEXT: Use the Chat History to understand short replies. If the bot just asked for booking details (dates, guest count, names) and the user replies with a number, a "yes", or short data, the intent MUST remain 'room_booking'.
        
        Respond ONLY with the exact text string of the intent. Do not add any punctuation or extra words.
        
        Chat History:
        {chat_history}"""),
        ("user", "{message}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    try:
        detected = await chain.ainvoke({"message": message_content, "chat_history": chat_history})
        intent_label = detected.strip().lower()
    except Exception as e:
        print(f"Intent classification failed: {e}")
        intent_label = "general_inquiry" 
        
    confidence = 0.90 
    
    if isinstance(message_id, str):
        message_id = uuid.UUID(message_id)

    new_intent = IntentLog(
        message_id=message_id,
        detected_intent=intent_label,
        confidence_score=confidence
    )
    db.add(new_intent)
    
    return intent_label
    

async def search_knowledge(question: str, top_k: int, db: AsyncSession):
    embeddings_model = get_dynamic_embeddings()
    query_vector = await embeddings_model.aembed_query(question)
    
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
    llm = get_dynamic_llm(provider=provider, model_name=model_name)
    context = "\n---\n".join(retrieved_chunks) if retrieved_chunks else "No information available."
    
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
    
    chain = prompt | llm | StrOutputParser()
    response_text = await chain.ainvoke({"context": context, "question": question})
    
    print(f"\n--- AI RESPONSE DEBUG ---:\n'{response_text}'\n-------------------------\n")
    
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


# --- NEW: AGENTIC BOOKING FLOW ---

class BookingChecklist(BaseModel):
    is_complete: bool = Field(description="True ONLY if name, phone, email, room_type, guests, check_in_date, and check_out_date are ALL provided.")
    missing_fields: list[str] = Field(description="List of fields that are still missing.")
    extracted_data: dict = Field(description="Dictionary of data successfully extracted (name, phone, email, room_type, guests, check_in_date, check_out_date).")
    bot_reply: str = Field(description="If is_complete is false, politely ask for missing fields. If true, write 'Booking ready.'")


async def execute_fake_booking(booking_data: dict, hotel_id: uuid.UUID, session_id: uuid.UUID, db: AsyncSession):
    confirmation_code = "RES-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    new_guest = Guest(
        name=booking_data.get("name", "Unknown"),
        phone=booking_data.get("phone", "Unknown"),
        email=booking_data.get("email", "Unknown")
    )
    db.add(new_guest)
    await db.flush() 
    
    check_in = datetime.strptime(booking_data["check_in_date"], "%Y-%m-%d").date()
    check_out = datetime.strptime(booking_data["check_out_date"], "%Y-%m-%d").date()

    new_booking = RoomBooking(
        hotel_id=hotel_id,
        guest_id=new_guest.id,
        session_id=session_id,
        room_type=booking_data.get("room_type", "Standard"),
        check_in_date=check_in,
        check_out_date=check_out,
        status="confirmed",
        confirmation_id=confirmation_code
    )
    db.add(new_booking)
    return confirmation_code

from datetime import date
from sqlalchemy import or_, and_

async def handle_booking_flow(user_message: str, chat_history: str, hotel_id: uuid.UUID, session_id: uuid.UUID, db: AsyncSession):
    llm = get_dynamic_llm(provider="groq", model_name="llama3-8b-8192")
    parser = JsonOutputParser(pydantic_object=BookingChecklist)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a hotel booking agent. Extract booking details from the conversation.
        REQUIRED FIELDS: name, phone, email, room_type, guests (integer), check_in_date (YYYY-MM-DD), check_out_date (YYYY-MM-DD).
        
        Formatting Instructions:
        {format_instructions}
        
        Chat History:
        {chat_history}
        """),
        ("user", "{message}")
    ])
    
    chain = prompt | llm | parser
    
    try:
        state = await chain.ainvoke({
            "message": user_message, 
            "chat_history": chat_history,
            "format_instructions": parser.get_format_instructions()
        })
        
        if not state["is_complete"]:
            return state["bot_reply"]
            
        data = state["extracted_data"]
        
        # --- 1. Date Validation ---
        try:
            check_in = datetime.strptime(data["check_in_date"], "%Y-%m-%d").date()
            check_out = datetime.strptime(data["check_out_date"], "%Y-%m-%d").date()
            
            if check_in < date.today():
                return "I cannot book a room in the past. Please provide a valid future check-in date."
            if check_out <= check_in:
                return "Your check-out date must be after your check-in date. Let's adjust those dates."
            if (check_out - check_in).days > 30:
                return "For stays longer than 30 days, please contact our front desk directly for extended-stay rates."
        except ValueError:
            return "Please provide the dates in a standard format (YYYY-MM-DD)."

        # --- 2. Capacity Validation ---
        room_type = data.get("room_type", "Standard")
        guests = int(data.get("guests", 1))
        
        capacity_map = {"Standard": 2, "Deluxe": 3, "Suite": 4}
        max_pax = capacity_map.get(room_type, 2)
        
        if guests > max_pax:
            return f"A {room_type} room can only accommodate up to {max_pax} guests. Would you like to book a larger room or reserve multiple rooms?"

        # --- 3. Double-Booking Validation ---
        overlap_query = select(RoomBooking).where(
            and_(
                RoomBooking.room_type == room_type,
                RoomBooking.check_in_date < check_out,
                RoomBooking.check_out_date > check_in,
                RoomBooking.status == "confirmed"
            )
        )
        existing_booking = await db.execute(overlap_query)
        if existing_booking.first():
            return f"I apologize, but our {room_type} rooms are completely booked for those specific dates. Do your dates have any flexibility, or would you like to check a different room tier?"

        # --- 4. Execution ---
        conf_code = await execute_fake_booking(data, hotel_id, session_id, db)
        
        # --- 5. AI Recommendation (Upselling) ---
        upsell_message = await get_upsell_recommendation(data, hotel_id, db)
        
        base_reply = f"Fantastic! Your {room_type} is booked for {guests} guests starting on {check_in}. Your confirmation number is **{conf_code}**. We look forward to your stay!"
        
        if upsell_message:
            return f"{base_reply}\n\n{upsell_message}"
        return base_reply
        
    except Exception as e:
        print(f"Booking flow error: {e}")
        return "I encountered a slight issue processing those details. Could you please confirm your dates and party size once more?"