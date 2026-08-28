import uuid
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database import AsyncSessionLocal
from models import IntentLog, MessageLog, SessionContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/{hotel_id}/top-intents")
async def get_top_intents(hotel_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the most common questions guests are asking for a specific hotel."""
    try:
        hotel_uuid = uuid.UUID(hotel_id)
        
        # CHANGED: Use "intent_count" instead of "count" to prevent Python tuple conflicts
        query = (
            select(IntentLog.detected_intent, func.count(IntentLog.id).label("intent_count"))
            .join(MessageLog, IntentLog.message_id == MessageLog.id)
            .join(SessionContext, MessageLog.session_id == SessionContext.id)
            .where(SessionContext.hotel_id == hotel_uuid)
            .group_by(IntentLog.detected_intent)
            .order_by(desc("intent_count"))
        )
        
        result = await db.execute(query)
        intents = result.all()
        
        # CHANGED: Access row.intent_count
        return [{"intent": row.detected_intent, "count": row.intent_count} for row in intents]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Hotel ID format")
    except Exception as e:
        logger.error("Error in top-intents:")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Database error occurred. Check terminal logs.")


@router.get("/{hotel_id}/message-volume")
async def get_message_volume(hotel_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the total number of messages handled by the bot."""
    try:
        hotel_uuid = uuid.UUID(hotel_id)
        
        # CHANGED: Added fallback to 0 if the table is completely empty
        query = (
            select(func.count(MessageLog.id))
            .join(SessionContext, MessageLog.session_id == SessionContext.id)
            .where(SessionContext.hotel_id == hotel_uuid)
            .where(MessageLog.sender == "user")
        )
        
        result = await db.execute(query)
        total_messages = result.scalar() or 0
        
        return {"total_inbound_messages": total_messages}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Hotel ID format")
    except Exception as e:
        logger.error("Error in message-volume:")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Database error occurred. Check terminal logs.")


# --- NEW: Average Rating Endpoint ---
@router.get("/{hotel_id}/average-rating")
async def get_average_rating(hotel_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the average customer satisfaction (CSAT) rating for the hotel."""
    try:
        h_uuid = uuid.UUID(hotel_id)
        
        # Calculate the average rating, ignoring sessions where rating is null
        query = select(func.avg(SessionContext.rating)).where(
            SessionContext.hotel_id == h_uuid,
            SessionContext.rating.isnot(None)
        )
        
        result = await db.execute(query)
        avg_rating = result.scalar()
        
        return {"average_rating": round(avg_rating, 1) if avg_rating else 0.0}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Hotel ID format")
    except Exception as e:
        logger.error(f"Failed to fetch average rating: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Database error occurred. Check terminal logs.")