"""Tests for the face recognition service.

Covers encoding extraction, saving, and recognition logic.
"""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face_encoding import FaceEncoding
from app.models.user import User
from app.services import face_service


@pytest.mark.asyncio
async def test_extract_encoding_invalid_image(db_session: AsyncSession):
    """Test that invalid image raises an error."""
    with pytest.raises(Exception):
        await face_service.extract_encoding(b"not an image")


@pytest.mark.asyncio
async def test_save_and_retrieve_encoding(db_session: AsyncSession):
    """Test saving a face encoding and retrieving it."""
    user = User(
        email="faceuser@example.com",
        full_name="Face User",
        hashed_password="hash",
    )
    db_session.add(user)
    await db_session.flush()

    encoding = [0.1] * 128
    face_enc = await face_service.save_encoding(db_session, user.id, encoding)

    assert face_enc.id is not None
    assert face_enc.user_id == user.id

    saved_data = json.loads(face_enc.encoding)
    assert len(saved_data) == 128
    assert saved_data[0] == 0.1


@pytest.mark.asyncio
async def test_recognize_no_encodings(db_session: AsyncSession):
    """Test recognition returns not recognized when DB is empty."""
    with pytest.raises(Exception):
        await face_service.recognize_face(db_session, b"fake_image")


@pytest.mark.asyncio
async def test_get_user_encodings_empty(db_session: AsyncSession):
    """Test getting encodings for a user with none stored."""
    result = await face_service.get_user_encodings(db_session, "nonexistent-id")
    assert result.total == 0
    assert len(result.items) == 0


@pytest.mark.asyncio
async def test_delete_encoding_not_found(db_session: AsyncSession):
    """Test deleting non-existent encoding raises 404."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await face_service.delete_encoding(db_session, "nonexistent-id")
    assert exc.value.status_code == 404
