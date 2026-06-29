#!/usr/bin/env python3
"""CLI script to create the first admin account.

Usage (inside the backend container):
    docker exec -it faceattend-backend python scripts/create_admin.py

Usage (local dev, run from backend/):
    python scripts/create_admin.py

The script fails gracefully if an admin already exists.
"""

import asyncio
import getpass
import sys
from pathlib import Path

# Allow running from project root or from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.security import get_password_hash
from app.database import async_session_factory
from app.models.user import User


async def main() -> None:
    print("=== FaceAttend — Create First Admin ===\n")

    async with async_session_factory() as db:
        # Guard: refuse if an active admin already exists
        result = await db.execute(
            select(User).where(User.role == "ADMIN", User.deleted_at.is_(None))
        )
        if result.scalar_one_or_none():
            print(
                "ERROR: An admin account already exists.\n"
                "Log in and use POST /api/v1/users to create additional admins."
            )
            sys.exit(1)

        # Collect credentials interactively
        default_email = "admin@faceattend.local"
        email = input(f"Email [{default_email}]: ").strip() or default_email

        default_name = "Administrateur"
        full_name = input(f"Full name [{default_name}]: ").strip() or default_name

        while True:
            password = getpass.getpass("Password (min 8 chars): ")
            if len(password) >= 8:
                break
            print("  Password must be at least 8 characters.")

        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("ERROR: Passwords do not match.")
            sys.exit(1)

        # Create admin
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role="ADMIN",
        )
        db.add(user)
        await db.commit()

    print(f"\nAdmin created successfully: {email}")
    print("You can now log in at POST /api/v1/auth/login")


if __name__ == "__main__":
    asyncio.run(main())
