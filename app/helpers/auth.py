import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext

from app.utils.supabase_client import get_supabase_client

# JWT settings
SECRET_KEY = os.environ.get("SECRET_KEY", "YOUR_SECRET_KEY_HERE")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS", 12))

# Password hashing settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")


supabase = get_supabase_client()


# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def validate_token(token: str = Depends(oauth2_scheme)) -> dict:
    """Validate the JWT token"""

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub", None)
        if not email:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
            )

        response = supabase.table("users").select("*").eq("email", email).execute()
        user = response.data[0] if response.data else None

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User not found",
            )

        return user

    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Could not validate credentials: {e}",
        )


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current user from the token"""
    return await validate_token(token)
