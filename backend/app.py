import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from db import SessionLocal, init_db, User, ServiceBundle, Bid
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user_token,
)
from websocket_manager import ConnectionManager
from llm import chat_completion

load_dotenv()

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="BidBundle")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()


class AuthPayload(BaseModel):
    username: str
    password: str
    role: str = "homeowner"

class ChatPayload(BaseModel): 
    message: str



class BundlePayload(BaseModel):
    title: str
    service_type: str
    neighborhood: str
    homes_count: int
    target_date: str
    description: str
    budget_notes: str | None = None


class BidPayload(BaseModel):
    amount: float
    timeline_days: int
    proposal: str


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def get_user_by_username(session: AsyncSession, username: str) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user


def serialize_bundle(bundle: ServiceBundle, creator: User, stats: dict, winning_bid: dict | None):
    return {
        "id": bundle.id,
        "title": bundle.title,
        "service_type": bundle.service_type,
        "neighborhood": bundle.neighborhood,
        "homes_count": bundle.homes_count,
        "target_date": bundle.target_date,
        "description": bundle.description,
        "budget_notes": bundle.budget_notes,
        "status": bundle.status,
        "created_at": str(bundle.created_at),
        "created_by": creator.username,
        "creator_role": creator.role,
        "bid_count": stats["bid_count"],
        "lowest_bid": stats["lowest_bid"],
        "winning_bid": winning_bid,
    }


async def get_bundle_stats(session: AsyncSession, bundle_id: int):
    stats_result = await session.execute(
        select(func.count(Bid.id), func.min(Bid.amount)).where(Bid.bundle_id == bundle_id)
    )
    bid_count, lowest_bid = stats_result.one()

    winning_bid_result = await session.execute(
        select(Bid, User)
        .join(User, User.id == Bid.vendor_id)
        .where(Bid.bundle_id == bundle_id, Bid.status == "winning")
    )
    winning = winning_bid_result.first()
    winning_bid = None
    if winning:
        bid, vendor = winning
        winning_bid = {
            "id": bid.id,
            "vendor": vendor.username,
            "amount": bid.amount,
            "timeline_days": bid.timeline_days,
        }

    return {
        "bid_count": bid_count or 0,
        "lowest_bid": lowest_bid,
    }, winning_bid


async def broadcast_event(event_type: str, payload: dict):
    await manager.broadcast({"type": event_type, "payload": payload})


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
async def healthcheck():
    return {"ok": True, "app": "BidBundle"}


@app.post("/api/signup")
async def signup(payload: AuthPayload, session: AsyncSession = Depends(get_db)):
    print("username:", repr(payload.username))
    print("password:", repr(payload.password))
    print("password type:", type(payload.password))
    print("password len:", len(payload.password))
    print("role:", repr(payload.role))

    if payload.role not in {"homeowner", "vendor", "manager"}:
        raise HTTPException(status_code=400, detail="Role must be homeowner, vendor, or manager")
    if not payload.username.strip() or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    existing = await session.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=payload.username.strip(),
        password_hash=get_password_hash(payload.password),
        role=payload.role,
    )
    session.add(user)
    await session.commit()
    token = create_access_token({"sub": user.username})
    return {"ok": True, "token": token, "user": {"username": user.username, "role": user.role}}



@app.post("/api/login")
async def login(payload: AuthPayload, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"ok": True, "token": token, "user": {"username": user.username, "role": user.role}}


@app.get("/api/me")
async def me(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(session, username)
    return {"username": user.username, "role": user.role}


@app.get("/api/test-hash")
async def test_hash():
    return {"hash": get_password_hash("testpassword")}


@app.get("/api/bundles")
async def get_bundles(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(ServiceBundle).order_by(desc(ServiceBundle.created_at)))
    bundles = result.scalars().all()

    response = []
    for bundle in bundles:
        creator = await session.get(User, bundle.created_by)
        stats, winning_bid = await get_bundle_stats(session, bundle.id)
        response.append(serialize_bundle(bundle, creator, stats, winning_bid))

    return {"bundles": response}


@app.post("/api/bundles")
async def create_bundle(
    payload: BundlePayload,
    username: str = Depends(get_current_user_token),
    session: AsyncSession = Depends(get_db),
):
    user = await get_user_by_username(session, username)
    if user.role not in {"homeowner", "manager"}:
        raise HTTPException(status_code=403, detail="Only homeowners or managers can create bundles")
    if payload.homes_count < 1:
        raise HTTPException(status_code=400, detail="Homes count must be at least 1")

    bundle = ServiceBundle(
        title=payload.title.strip(),
        service_type=payload.service_type.strip(),
        neighborhood=payload.neighborhood.strip(),
        homes_count=payload.homes_count,
        target_date=payload.target_date.strip(),
        description=payload.description.strip(),
        budget_notes=(payload.budget_notes or "").strip() or None,
        created_by=user.id,
    )
    session.add(bundle)
    await session.commit()
    await session.refresh(bundle)

    stats, winning_bid = await get_bundle_stats(session, bundle.id)
    serialized = serialize_bundle(bundle, user, stats, winning_bid)
    await broadcast_event("bundle_created", serialized)
    return {"ok": True, "bundle": serialized}


@app.get("/api/bundles/{bundle_id}/bids")
async def get_bundle_bids(
    bundle_id: int,
    username: str = Depends(get_current_user_token),
    session: AsyncSession = Depends(get_db),
):
    user = await get_user_by_username(session, username)
    bundle = await session.get(ServiceBundle, bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    result = await session.execute(
        select(Bid, User)
        .join(User, User.id == Bid.vendor_id)
        .where(Bid.bundle_id == bundle_id)
        .order_by(Bid.amount.asc(), Bid.created_at.asc())
    )

    creator = await session.get(User, bundle.created_by)
    bids = []
    for bid, vendor in result.all():
        bids.append(
            {
                "id": bid.id,
                "vendor": vendor.username,
                "amount": bid.amount,
                "timeline_days": bid.timeline_days,
                "proposal": bid.proposal,
                "status": bid.status,
                "created_at": str(bid.created_at),
                "is_mine": vendor.id == user.id,
            }
        )

    return {
        "bundle_id": bundle_id,
        "bundle_title": bundle.title,
        "can_award": user.role == "manager" or user.id == creator.id,
        "bids": bids,
    }


@app.post("/api/bundles/{bundle_id}/bids")
async def create_bid(
    bundle_id: int,
    payload: BidPayload,
    username: str = Depends(get_current_user_token),
    session: AsyncSession = Depends(get_db),
):
    user = await get_user_by_username(session, username)
    if user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can submit bids")
    if payload.amount <= 0 or payload.timeline_days < 1:
        raise HTTPException(status_code=400, detail="Bid amount must be positive and timeline must be at least 1 day")

    bundle = await session.get(ServiceBundle, bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if bundle.status != "open":
        raise HTTPException(status_code=400, detail="This bundle is no longer accepting bids")

    existing = await session.execute(
        select(Bid).where(Bid.bundle_id == bundle_id, Bid.vendor_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already submitted a bid for this bundle")

    bid = Bid(
        bundle_id=bundle_id,
        vendor_id=user.id,
        amount=payload.amount,
        timeline_days=payload.timeline_days,
        proposal=payload.proposal.strip(),
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    payload_out = {
        "id": bid.id,
        "bundle_id": bundle_id,
        "vendor": user.username,
        "amount": bid.amount,
        "timeline_days": bid.timeline_days,
        "status": bid.status,
    }
    await broadcast_event("bid_created", payload_out)
    return {"ok": True, "bid": payload_out}


@app.post("/api/bundles/{bundle_id}/award/{bid_id}")
async def award_bid(
    bundle_id: int,
    bid_id: int,
    username: str = Depends(get_current_user_token),
    session: AsyncSession = Depends(get_db),
):
    user = await get_user_by_username(session, username)
    bundle = await session.get(ServiceBundle, bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if user.role != "manager" and user.id != bundle.created_by:
        raise HTTPException(status_code=403, detail="You cannot award this bundle")
    if bundle.status != "open":
        raise HTTPException(status_code=400, detail="This bundle has already been awarded")

    bid = await session.get(Bid, bid_id)
    if not bid or bid.bundle_id != bundle_id:
        raise HTTPException(status_code=404, detail="Bid not found")

    all_bids = await session.execute(select(Bid).where(Bid.bundle_id == bundle_id))
    for existing_bid in all_bids.scalars().all():
        existing_bid.status = "winning" if existing_bid.id == bid_id else "closed"
    bundle.status = "awarded"

    await session.commit()

    vendor = await session.get(User, bid.vendor_id)
    await broadcast_event(
        "bundle_awarded",
        {
            "bundle_id": bundle_id,
            "bid_id": bid_id,
            "vendor": vendor.username,
            "amount": bid.amount,
        },
    )
    return {"ok": True}


# ── Add this import at the top of app.py ──────────────────────────────────────
# from llm import chat_completion

# ── Add this Pydantic model with the other models ─────────────────────────────
# class ChatPayload(BaseModel):
#     message: str

# ── Add this endpoint anywhere in app.py ──────────────────────────────────────

@app.post("/api/chat")
async def chat(
    payload: ChatPayload,
    username: str = Depends(get_current_user_token),
):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    reply = None

    if message.endswith("?"):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant for BidBundle, a platform where homeowners "
                    "bundle neighborhood service requests and vendors compete with bids. "
                    "Answer questions concisely and helpfully."
                ),
            },
            {"role": "user", "content": message},
        ]
        reply = await chat_completion(messages)

    # Broadcast to all connected websocket clients
    await broadcast_event("chat_message", {"username": username, "message": message})
    if reply:
        await broadcast_event("bot_reply", {"reply": reply})

    return {"ok": True, "reply": reply}





@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
