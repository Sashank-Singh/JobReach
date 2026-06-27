import bcrypt
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import JobFilter, User

ALGORITHM = "HS256"
DEFAULT_FILTERS = [
    {"name": "AI Engineer", "filters": {"keyword": "AI Engineer"}},
    {"name": "Software Engineer", "filters": {"keyword": "Software Engineer"}},
    {"name": "Product Manager", "filters": {"keyword": "Product Manager"}},
]


class AuthService:
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    def create_token(self, user_id: UUID) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
        payload = {"sub": str(user_id), "exp": expire}
        return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

    def decode_token(self, token: str) -> UUID | None:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
            return UUID(payload["sub"])
        except (JWTError, ValueError, KeyError):
            return None

    async def register(self, db: AsyncSession, email: str, password: str, name: str | None) -> User:
        existing = await db.execute(select(User).where(User.email == email.lower()))
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        user = User(
            email=email.lower().strip(),
            name=name,
            password_hash=self.hash_password(password),
        )
        db.add(user)
        await db.flush()

        for f in DEFAULT_FILTERS:
            db.add(JobFilter(user_id=user.id, name=f["name"], filters=f["filters"], notify=True))

        await db.commit()
        await db.refresh(user)
        return user

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email.lower().strip()))
        user = result.scalar_one_or_none()
        if not user or not user.password_hash:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user

    async def get_user(self, db: AsyncSession, user_id: UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

auth_service = AuthService()
