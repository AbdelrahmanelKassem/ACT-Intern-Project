import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database import AsyncSessionLocal
from models import IntentLog, MessageLog, SessionContext

router = APIRouter(prefix="/analytics", tags=["Analytics"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/{hotel_id}/top-intents")
async def get_top_intents(hotel_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the most common questions guests are asking for a specific hotel."""
    try:
        hotel_uuid = uuid.UUID(hotel_id)
        
        # Join IntentLog -> MessageLog -> SessionContext to filter by hotel_id
        query = (
            select(IntentLog.detected_intent, func.count(IntentLog.id).label("count"))
            .join(MessageLog, IntentLog.message_id == MessageLog.id)
            .join(SessionContext, MessageLog.session_id == SessionContext.id)
            .where(SessionContext.hotel_id == hotel_uuid)
            .group_by(IntentLog.detected_intent)
            .order_by(desc("count"))
        )
        
        result = await db.execute(query)
        intents = result.all()
        
        return [{"intent": row.detected_intent, "count": row.count} for row in intents]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Hotel ID format")


@router.get("/{hotel_id}/message-volume")
async def get_message_volume(hotel_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the total number of messages handled by the bot."""
    try:
        hotel_uuid = uuid.UUID(hotel_id)
        
        query = (
            select(func.count(MessageLog.id))
            .join(SessionContext, MessageLog.session_id == SessionContext.id)
            .where(SessionContext.hotel_id == hotel_uuid)
            .where(MessageLog.sender == "user")
        )
        
        result = await db.execute(query)
        total_messages = result.scalar()
        
        return {"total_inbound_messages": total_messages}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Hotel ID format")