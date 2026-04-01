import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, DateTime, func, Integer, Float, text
from dotenv import load_dotenv
from typing import Optional


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+asyncmy://chatuser:chatpass@localhost:3306/groupchat",
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="homeowner")
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bundles = relationship("ServiceBundle", back_populates="creator")
    bids = relationship("Bid", back_populates="vendor")


class ServiceBundle(Base):
    __tablename__ = "service_bundles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120))
    service_type: Mapped[str] = mapped_column(String(80))
    neighborhood: Mapped[str] = mapped_column(String(120))
    homes_count: Mapped[int] = mapped_column(Integer())
    target_date: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text())
    budget_notes: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    creator = relationship("User", back_populates="bundles")
    bids = relationship("Bid", back_populates="bundle")


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bundle_id: Mapped[int] = mapped_column(
        ForeignKey("service_bundles.id", ondelete="CASCADE")
    )
    vendor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    amount: Mapped[float] = mapped_column(Float())
    timeline_days: Mapped[int] = mapped_column(Integer())
    proposal: Mapped[str] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bundle = relationship("ServiceBundle", back_populates="bids")
    vendor = relationship("User", back_populates="bids")


engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Check if column exists
        result = await conn.execute(text("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'users' 
              AND COLUMN_NAME = 'role'
        """))

        exists = result.scalar()

        if not exists:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'homeowner'
            """))