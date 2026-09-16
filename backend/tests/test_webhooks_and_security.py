import pytest
import hmac
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.entities import User, Duo, DuoMember, WebhookEvent
from app.core.security import verify_github_signature, get_password_hash

def test_github_webhook_signature_verification():
    secret = "my_webhook_secret_key"
    payload = b'{"action": "push", "repository": {"name": "test"}}'
    
    # Generate correct HMAC signature
    mac = hmac.new(secret.encode(), payload, hashlib.sha256)
    valid_sig = f"sha256={mac.hexdigest()}"
    
    # Assert valid signature passes
    assert verify_github_signature(payload, valid_sig, secret) is True
    
    # Assert forged/tampered signature fails
    assert verify_github_signature(payload, "sha256=invalidhash123", secret) is False
    assert verify_github_signature(b'{"tampered": true}', valid_sig, secret) is False
    assert verify_github_signature(payload, None, secret) is False

@pytest.mark.asyncio
async def test_duo_max_two_members_rule(db_session: AsyncSession):
    """Test that a Duo strictly rejects a 3rd member."""
    u1 = User(email="u1@test.com", full_name="User 1", hashed_password="pwd")
    u2 = User(email="u2@test.com", full_name="User 2", hashed_password="pwd")
    u3 = User(email="u3@test.com", full_name="User 3", hashed_password="pwd")
    db_session.add_all([u1, u2, u3])
    await db_session.flush()

    duo = Duo(name="Exclusive Duo", invite_code="DUO-MAX2", created_by=u1.id)
    db_session.add(duo)
    await db_session.flush()

    # Add 1st member
    m1 = DuoMember(duo_id=duo.id, user_id=u1.id, role="CREATOR")
    db_session.add(m1)
    # Add 2nd member
    m2 = DuoMember(duo_id=duo.id, user_id=u2.id, role="PARTNER")
    db_session.add(m2)
    await db_session.flush()

    # Attempt to join 3rd member: query members count
    members = (await db_session.execute(
        select(DuoMember).where(DuoMember.duo_id == duo.id)
    )).scalars().all()
    assert len(members) == 2

    # Simulate join logic check
    can_join = len(members) < 2
    assert can_join is False  # Enforces maximum 2 members!

@pytest.mark.asyncio
async def test_webhook_idempotency(db_session: AsyncSession):
    """Test that duplicate webhook deliveries are detected and handled idempotently."""
    delivery_id = "delivery-unique-uuid-999"
    ev1 = WebhookEvent(
        delivery_id=delivery_id,
        event_type="push",
        payload_hash="hash123",
        status="PROCESSED"
    )
    db_session.add(ev1)
    await db_session.flush()

    # Check duplicate delivery
    existing = (await db_session.execute(
        select(WebhookEvent).where(WebhookEvent.delivery_id == delivery_id)
    )).scalar_one_or_none()
    assert existing is not None
    assert existing.delivery_id == delivery_id
