import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from models import HotelPackage
from services.ai_factory import get_dynamic_llm

async def get_upsell_recommendation(booking_data: dict, hotel_id: uuid.UUID, db: AsyncSession) -> str:
    """
    Evaluates the guest's booking details and uses the LLM to suggest the most relevant hotel package.
    """
    try:
        # 1. Fetch available packages from the database
        query = select(HotelPackage).where(HotelPackage.hotel_id == hotel_id)
        result = await db.execute(query)
        packages = result.scalars().all()
        
        if not packages:
            return "" 
            
        # 2. Format packages into a readable list for the AI
        packages_text = "\n".join(
            [f"- {p.name} (${p.price}): {p.description} (Best for: {p.target_audience})" for p in packages]
        )
        
        # 3. Use the LLM as a semantic recommendation engine
        llm = get_dynamic_llm(provider="groq", model_name="llama3-8b-8192")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a highly skilled luxury hotel concierge. 
            Your goal is to select the SINGLE best upsell package for a guest based on their booking details.
            
            Available Packages:
            {packages_text}
            
            Guest Booking Details:
            Room Type: {room_type}
            Number of Guests: {guests}
            Check-in: {check_in}
            Check-out: {check_out}
            
            Instructions:
            1. Analyze the party size and dates to pick the most logical package (e.g., romantic dining for 2 people, family spa for 3+ people).
            2. Write a short, natural, 1-2 sentence question offering this package to the guest.
            3. DO NOT say "Based on your booking" or "I recommend". 
            
            Example: "Since you are joining us for the weekend, would you like to add our Late Checkout package for $50?"
            """),
            ("user", "Please suggest a package.")
        ])
        
        chain = prompt | llm | StrOutputParser()
        
        suggestion = await chain.ainvoke({
            "packages_text": packages_text,
            "room_type": booking_data.get("room_type", "Standard"),
            "guests": booking_data.get("guests", 1),
            "check_in": booking_data.get("check_in_date", "Unknown"),
            "check_out": booking_data.get("check_out_date", "Unknown")
        })
        
        return suggestion.strip()
        
    except Exception as e:
        print(f"Recommendation Engine Error: {e}")
        return ""