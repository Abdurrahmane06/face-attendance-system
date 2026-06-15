"""Face recognition request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FaceUploadResponse(BaseModel):
    """Response after uploading and encoding a face.

    Attributes:
        user_id: Owner user UUID.
        encoding_id: Stored encoding UUID.
        face_detected: Whether a face was detected.
        confidence: Match confidence score.
    """

    user_id: str
    encoding_id: str
    face_detected: bool = True
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class FaceRecognizeResponse(BaseModel):
    """Response from face recognition attempt.

    Attributes:
        recognized: Whether the face was recognized.
        user_id: Matched user UUID (if recognized).
        user_name: Matched user name (if recognized).
        confidence: Match confidence score.
        threshold: Recognition threshold used.
        message: Human-readable result message.
    """

    recognized: bool
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    confidence: Optional[float] = None
    threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    message: str = "Visage non identifié"


class FaceEncodingResponse(BaseModel):
    """Face encoding response.

    Attributes:
        id: Encoding UUID.
        user_id: Owner user UUID.
        created_at: Creation timestamp.
    """

    id: str
    user_id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FaceEncodingListResponse(BaseModel):
    """List of face encodings for a user.

    Attributes:
        items: List of encoding responses.
        total: Total encoding count.
    """

    items: List[FaceEncodingResponse]
    total: int
