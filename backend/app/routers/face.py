"""Face recognition router: upload encodings, recognize faces, manage encodings.

All endpoints require authentication.
"""

import logging
import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.face import (
    FaceEncodingListResponse,
    FaceEncodingResponse,
    FaceRecognizeResponse,
    FaceUploadResponse,
)
from app.services import face_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=FaceUploadResponse, status_code=201)
async def upload_face(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FaceUploadResponse:
    """Upload a photo, extract face encoding, and store it.

    Args:
        file: Image file (JPEG/PNG, max 10MB, exactly one face).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        FaceUploadResponse with encoding ID and confidence.
    """
    if file.content_type not in ("image/jpeg", "image/png"):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG files are allowed",
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum of {settings.max_upload_size_mb}MB",
        )

    encoding = await face_service.extract_encoding(content)

    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"face_{uuid.uuid4()}.{ext}"
    filepath = os.path.join(settings.upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    face_enc = await face_service.save_encoding(db, current_user.id, encoding, filepath)

    return FaceUploadResponse(
        user_id=current_user.id,
        encoding_id=face_enc.id,
        face_detected=True,
        confidence=1.0,
    )


@router.post("/recognize", response_model=FaceRecognizeResponse)
async def recognize_face(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FaceRecognizeResponse:
    """Recognize a face from an uploaded image.

    Args:
        file: Image file (JPEG/PNG).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        FaceRecognizeResponse with recognition result.
    """
    if file.content_type not in ("image/jpeg", "image/png"):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG files are allowed",
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum of {settings.max_upload_size_mb}MB",
        )

    return await face_service.recognize_face(db, content, settings.face_tolerance)


@router.get("/encodings/{user_id}", response_model=FaceEncodingListResponse)
async def get_user_encodings(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FaceEncodingListResponse:
    """Get all face encodings for a user.

    Args:
        user_id: User UUID.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        FaceEncodingListResponse.
    """
    return await face_service.get_user_encodings(db, user_id)


@router.delete("/encodings/{encoding_id}", status_code=204)
async def delete_face_encoding(
    encoding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a face encoding by ID.

    Args:
        encoding_id: Encoding UUID.
        db: Database session.
        current_user: Authenticated user.
    """
    await face_service.delete_encoding(db, encoding_id)
