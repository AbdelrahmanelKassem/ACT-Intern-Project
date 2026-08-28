import uuid
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

# Adjust this import depending on where your SQLAlchemy Base is defined
from database import Base 

class HotelPackage(Base):
    __tablename__ = 'hotel_package'
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hotel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('hotel.id'))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    target_audience: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Float, nullable=True)