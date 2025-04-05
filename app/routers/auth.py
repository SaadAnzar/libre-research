from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

# Local imports
from app.utils.supabase_client import get_supabase_client
from app.models.user import Token, UserCreate, UserResponse
from app.helpers.auth import create_access_token, get_password_hash, verify_password


supabase = get_supabase_client()

router = APIRouter()


# Routes
@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    # Check if user already exists
    response = supabase.table("users").select("*").eq("email", user.email).execute()
    if response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash the password
    hashed_password = get_password_hash(user.password)

    # Create user in Supabase
    new_user = {
        "email": user.email,
        "hashed_password": hashed_password,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    response = supabase.table("users").insert(new_user).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    created_user = response.data[0]
    return UserResponse(
        id=created_user["id"],
        email=created_user["email"],
        created_at=created_user["created_at"],
    )


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Get user from Supabase
    # username field has to be sent in OAuth2PasswordRequestForm data
    response = (
        supabase.table("users").select("*").eq("email", form_data.username).execute()
    )
    user = response.data[0] if response.data else None

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=timedelta(minutes=30)
    )

    return {"access_token": access_token, "token_type": "bearer"}
