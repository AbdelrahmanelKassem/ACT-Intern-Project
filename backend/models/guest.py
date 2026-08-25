import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from database import Base

class Guest(Base):
    __tablename__ = 'guest'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255))