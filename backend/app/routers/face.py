"""Face recognition router.

/upload          — current user uploads their own face encoding.
/upload/{uid}    — admin uploads a face encoding for another user.
/recognize       — match a captured frame against stored encodings.
/encodings/{uid} — list active encodings for a user.
DELETE /encodings/{id} — soft-delete an encoding.
"""

import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, require_admin
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _read_and_validate_image(file: UploadFile) -> bytes:
    """Read upload, enforce MIME type and size limits."""
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG images are accepted",
        )
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds the {settings.max_upload_size_mb} MB limit",
        )
    return content


def _save_image(content: bytes, filename: str) -> str:
    """Write image bytes to the uploads directory, return the file path."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    filepath = os.path.join(settings.upload_dir, filename)
    with open(filepath, "wb") as fh:
        fh.write(content)
    return filepath


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=FaceUploadResponse, status_code=201,
             summary="Upload own face encoding")
async def upload_own_face(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FaceUploadResponse:
    """Detect exactly one face in the uploaded image and store its 128-D encoding.

    Returns a clear error if zero or more than one face is found.
    """
    content = await _read_and_validate_image(file)
    encoding = await face_service.extract_encoding(content)

    ext = (file.filename or "face.jpg").rsplit(".", 1)[-1]
    filepath = _save_image(content, f"face_{uuid.uuid4()}.{ext}")
    face_enc = await face_service.save_encoding(db, current_user.id, encoding, filepath)

    return FaceUploadResponse(
        user_id=current_user.id,
        encoding_id=face_enc.id,
        face_detected=True,
        confidence=1.0,
    )


@router.post("/upload/{target_user_id}", response_model=FaceUploadResponse, status_code=201,
             summary="Admin: upload face encoding for another user")
async def upload_face_for_user(
    target_user_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> FaceUploadResponse:
    """Admin-only: register a face encoding on behalf of any user."""
    from sqlalchemy import select
    from app.models.user import User as UserModel

    result = await db.execute(
        select(UserModel).where(UserModel.id == target_user_id, UserModel.deleted_at.is_(None))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    content = await _read_and_validate_image(file)
    encoding = await face_service.extract_encoding(content)

    ext = (file.filename or "face.jpg").rsplit(".", 1)[-1]
    filepath = _save_image(content, f"face_{uuid.uuid4()}.{ext}")
    face_enc = await face_service.save_encoding(db, target_user_id, encoding, filepath)

    return FaceUploadResponse(
        user_id=target_user_id,
        encoding_id=face_enc.id,
        face_detected=True,
        confidence=1.0,
    )


@router.post("/recognize", response_model=FaceRecognizeResponse,
             summary="Recognize a face against stored encodings")
async def recognize_face(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FaceRecognizeResponse:
    """Compare the uploaded frame against all stored encodings.

    Returns the best match (confidence = 1 - euclidean_distance) if distance ≤ FACE_TOLERANCE.
    """
    content = await _read_and_validate_image(file)
    return await face_service.recognize_face(db, content, settings.face_tolerance)


@router.get("/encodings/{user_id}", response_model=FaceEncodingListResponse,
            summary="List active face encodings for a user")
async def get_user_encodings(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FaceEncodingListResponse:
    """Return all non-deleted face encodings for the given user."""
    return await face_service.get_user_encodings(db, user_id)


@router.delete("/encodings/{encoding_id}", status_code=204,
               summary="Soft-delete a face encoding")
async def delete_face_encoding(
    encoding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-delete a face encoding (sets deleted_at, keeps the row for audit)."""
    await face_service.delete_encoding(db, encoding_id)
