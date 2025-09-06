from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, require_admin
from app.crud.user import (
    authenticate_user, create_user, get_user_by_email, 
    update_user_password, verify_user_password, get_users_by_role,
    update_user_role, delete_user, get_users, get_user,
    update_login_time, update_logout_time, create_bulk_users
)
from app.core.security import create_access_token
from app.schemas.user import (
    UserLogin, Token, UserCreate, UserResponse, 
    PasswordResetRequest, PasswordReset, ChangePassword,
    BulkUserCreate, BulkUserResponse
)
from datetime import timedelta
from app.core.config import settings

router = APIRouter()

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 🎯 UPDATE LOGIN TIME
    update_login_time(db, user.id)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_id": user.id,
        "user_name": user.user_name,
        "user_role": user.role
    }

@router.post("/register", response_model=UserResponse)
def register(
    user: UserCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Register new user (Admin only)
    """
    # Check if user already exists
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    db_user = create_user(db=db, user=user)
    return db_user

@router.post("/bulk-register", response_model=BulkUserResponse)
def bulk_register(
    bulk_data: BulkUserCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Register multiple users in bulk (Admin only)
    """
    result = create_bulk_users(db=db, users=bulk_data.users)
    return result

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Get current user information
    """
    # Add user_name field to match UserResponse schema
    user_data = dict(current_user)
    user_data['user_name'] = current_user.get('name', 'User')  # Use name as user_name
    return user_data

@router.post("/change-password")
def change_password(
    password_data: ChangePassword,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user password
    """
    # Verify current password
    if not verify_user_password(db, current_user["id"], password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    if update_user_password(db, current_user["id"], password_data.new_password):
        return {"message": "Password updated successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )

@router.get("/", response_model=list[UserResponse])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users with pagination (Admin only)
    """
    users = get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get specific user by ID (Admin only)
    """
    db_user = get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/role/{role}", response_model=list[UserResponse])
def get_users_by_role_endpoint(
    role: str,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get users by role (Admin only)
    """
    users = get_users_by_role(db, role)
    return users

@router.put("/{user_id}/role")
def update_user_role_endpoint(
    user_id: int,
    new_role: str,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user role (Admin only)
    """
    if update_user_role(db, user_id, new_role):
        return {"message": f"User role updated to {new_role}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

@router.delete("/{user_id}")
def delete_user_endpoint(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete user (Admin only)
    """
    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    if delete_user(db, user_id):
        return {"message": "User deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

@router.post("/logout")
def logout(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user (client should discard token)
    """
    # 🎯 UPDATE LOGOUT TIME
    update_logout_time(db, current_user["id"])
    
    return {"message": "Successfully logged out"}

 