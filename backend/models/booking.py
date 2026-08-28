import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Date
from database import Base

class RoomBooking(Base):
    __tablename__ = 'room_booking'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hotel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel.id'))
    guest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('guest.id'))
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('session_context.id'))
    room_type: Mapped[str] = mapped_column(String(100))
    check_in_date = mapped_column(Date)
    check_out_date = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50))
    confirmation_id: Mapped[str] = mapped_column(String(50), nullable=True)