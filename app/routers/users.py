from fastapi import APIRouter, Depends, HTTPException, status

# Local imports
from app.utils.supabase_client import get_supabase_client
from app.models.user import UserResponse
from app.helpers.auth import get_current_user


supabase = get_supabase_client()

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get the current user's profile"""
    print("Fetching user profile for:", current_user.get("email"))

    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        created_at=current_user["created_at"],
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str, _=Depends(get_current_user)):
    """Get a user by ID (requires authentication)"""
    print("Fetching user profile for:", user_id)

    response = (
        supabase.table("users")
        .select("*")
        .eq("id", user_id)
        .eq("deleted", False)
        .execute()
    )
    user = response.data[0] if response.data else None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse(
        id=user["id"],
        email=user["email"],
        created_at=user["created_at"],
    )
