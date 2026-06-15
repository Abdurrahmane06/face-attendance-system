"""FaceEncoding ORM model for FaceAttend.

Stores 128-dimensional face encodings extracted from uploaded images,
linked to the user they belong to.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FaceEncoding(Base):
    """Face encoding storage model.

    Attributes:
        id: Primary UUID.
        user_id: Foreign key to users table.
        encoding: JSON array of 128 float values.
        image_path: Optional path to source image.
        created_at: Creation timestamp.
    """

    __tablename__ = "face_encodings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    encoding: Mapped[str] = mapped_column(Text, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", back_populates="face_encodings")
