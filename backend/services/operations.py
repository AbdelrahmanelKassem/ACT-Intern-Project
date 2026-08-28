import string
import secrets
import logging
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import RoomBooking

logger = logging.getLogger(__name__)

def generate_confirmation_code(length=8):
    """
    Generates a random numeric confirmation code.
    This will be replaced by the actual Opera PMS confirmation code later.
    """
    alphabet = string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Placeholder for the PMS integration layer
async def sync_with_opera_pms(booking: RoomBooking, action: str):
    """
    Pushes booking updates to Opera PMS.
    To be implemented in the PMS integration module.
    """
    logger.info(f"Syncing booking {booking.confirmation_id} to Opera PMS (Action: {action})")
    # Example: await opera_client.update_reservation(booking.model_dump())
    pass

async def manage_reservation(session_id: str, hotel_id: str, guest_id: str, room_type: str, check_in: date, check_out: date, db: AsyncSession, action: str = "update_pending"):
    # Updated to async execution
    result = await db.execute(
        select(RoomBooking).where(
            RoomBooking.session_id == session_id,
            RoomBooking.status == 'pending'
        )
    )
    existing_booking = result.scalar_one_or_none()

    if action == "confirm_booking" and existing_booking:
        existing_booking.status = 'confirmed'
        existing_booking.confirmation_id = generate_confirmation_code()
        await db.commit()
        await db.refresh(existing_booking)
        
        # Sync the confirmed booking with Opera PMS
        await sync_with_opera_pms(existing_booking, action="create")
        return existing_booking

    if existing_booking:
        existing_booking.room_type = room_type
        existing_booking.check_in_date = check_in
        existing_booking.check_out_date = check_out
        await db.commit()
        await db.refresh(existing_booking)
        return existing_booking
    else:
        new_booking = RoomBooking(
            hotel_id=hotel_id,
            guest_id=guest_id,
            session_id=session_id,
            room_type=room_type,
            check_in_date=check_in,
            check_out_date=check_out,
            status='pending'
        )
        db.add(new_booking)
        await db.commit()
        await db.refresh(new_booking)
        return new_booking

async def lookup_reservation(confirmation_id: str, db: AsyncSession):
    clean_id = confirmation_id.strip()
    
    result = await db.execute(
        select(RoomBooking).where(RoomBooking.confirmation_id == clean_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        return {"error": "No reservation found with that ID."}
    
    return {
        "status": "success",
        "room_type": booking.room_type,
        "check_in": booking.check_in_date.strftime("%Y-%m-%d"),
        "check_out": booking.check_out_date.strftime("%Y-%m-%d"),
        "booking_status": booking.status
    }

async def edit_existing_reservation(confirmation_id: str, new_check_in: date, new_check_out: date, new_room_type: str, db: AsyncSession):
    clean_id = confirmation_id.strip()
    
    result = await db.execute(
        select(RoomBooking).where(RoomBooking.confirmation_id == clean_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise ValueError("Reservation not found.")
        
    if new_check_in:
        booking.check_in_date = new_check_in
    if new_check_out:
        booking.check_out_date = new_check_out
    if new_room_type:
        booking.room_type = new_room_type
        
    await db.commit()
    await db.refresh(booking)
    
    # Sync the modified booking with Opera PMS
    await sync_with_opera_pms(booking, action="modify")
    
    return booking