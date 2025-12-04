"""
Authentication router - register, login, profile
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import shutil
import os
import time
from pathlib import Path
from datetime import datetime

from ..database import SessionLocal, get_db
from ..models import User
from ..schemas import UserCreate, UserLogin, Token, UserResponse, SurveyData
from ..utils.auth import get_password_hash, verify_password, create_access_token, decode_access_token

# Email configuration (using smtplib for simplicity)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()

def send_welcome_email(user_email: str, username: str):
    """Send welcome email to new user"""
    try:
        # SMTP configuration - update with your email credentials
        # For production, use environment variables
        sender_email = "noreply@mobix.com"  # Replace with actual email
        sender_password = "your_password"  # Replace with actual password or use env var
        
        message = MIMEMultipart("alternative")
        message["Subject"] = "Welcome to MOBIX Travel! 🌍"
        message["From"] = sender_email
        message["To"] = user_email
        
        # Email body
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h1 style="color: #4F46E5;">Welcome to MOBIX Travel, {username}! 🎉</h1>
              <p>Thank you for joining MOBIX Travel - your AI-powered travel planning companion.</p>
              <p>We're excited to help you plan your next adventure!</p>
              
              <h2 style="color: #4F46E5;">What you can do with MOBIX:</h2>
              <ul>
                <li>🤖 Chat with our AI travel assistant</li>
                <li>🗺️ Create detailed itineraries</li>
                <li>✈️ Get personalized travel recommendations</li>
                <li>📱 Access everything from your profile</li>
              </ul>
              
              <p>Start exploring now: <a href="http://127.0.0.1:8004">Launch MOBIX</a></p>
              
              <p style="margin-top: 30px; color: #666; font-size: 14px;">
                Happy travels!<br>
                The MOBIX Team
              </p>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, "html")
        message.attach(part)
        
        # NOTE: This will fail without proper SMTP configuration
        # For testing, we'll just log it
        print(f"\n{'='*60}")
        print(f"📧 WELCOME EMAIL (Simulated)")
        print(f"{'='*60}")
        print(f"To: {user_email}")
        print(f"Subject: {message['Subject']}")
        print(f"Username: {username}")
        print(f"{'='*60}\n")
        
        # Uncomment below for actual email sending
        # with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        #     server.login(sender_email, sender_password)
        #     server.sendmail(sender_email, user_email, message.as_string())
        
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email: {e}")
        return False

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        is_active=True,
        full_name=user_data.full_name,
        gender=user_data.gender,
        country=user_data.country,
        interests=user_data.interests,
        travel_frequency=user_data.travel_frequency,
        budget=user_data.budget,
        travel_reasons=user_data.travel_reasons
    )
    
    # Parse date_of_birth if provided
    if user_data.date_of_birth:
        try:
            from datetime import datetime
            dob = datetime.strptime(user_data.date_of_birth, '%Y-%m-%d')
            new_user.date_of_birth = dob
            # Calculate age
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            new_user.age = age
        except ValueError:
            pass  # Invalid date format, skip
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": str(new_user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user
    }

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's information"""
    return current_user

# Password reset token storage (in production, use Redis or database)
password_reset_tokens = {}

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

def send_password_reset_email(user_email: str, reset_token: str):
    """Send password reset email"""
    try:
        reset_link = f"http://localhost:8005?reset_token={reset_token}"
        
        print(f"\n{'='*60}")
        print(f"🔐 PASSWORD RESET EMAIL (Simulated)")
        print(f"{'='*60}")
        print(f"To: {user_email}")
        print(f"Subject: MOBIX - Resetiranje lozinke")
        print(f"Reset Link: {reset_link}")
        print(f"Token: {reset_token}")
        print(f"{'='*60}\n")
        
        # TODO: Add actual email sending here
        # You'll need to configure SMTP settings
        
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send reset email: {e}")
        return False

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset email"""
    import secrets
    
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If an account with that email exists, a reset link has been sent."}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    
    # Store token with expiry (1 hour)
    password_reset_tokens[reset_token] = {
        "user_id": user.id,
        "email": user.email,
        "expires": time.time() + 3600  # 1 hour
    }
    
    # Send email
    send_password_reset_email(user.email, reset_token)
    
    return {"message": "If an account with that email exists, a reset link has been sent."}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password with token"""
    token_data = password_reset_tokens.get(request.token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check expiry
    if time.time() > token_data["expires"]:
        del password_reset_tokens[request.token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Find user
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.password_hash = get_password_hash(request.new_password)
    db.commit()
    
    # Remove used token
    del password_reset_tokens[request.token]
    
    return {"message": "Password has been reset successfully"}

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    country: Optional[str] = None
    interests: Optional[str] = None
    travel_frequency: Optional[str] = None
    budget: Optional[str] = None
    travel_reasons: Optional[str] = None

@router.put("/profile")
def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    if profile_data.full_name:
        current_user.full_name = profile_data.full_name
    if profile_data.gender:
        current_user.gender = profile_data.gender
    if profile_data.date_of_birth:
        try:
            current_user.date_of_birth = datetime.strptime(profile_data.date_of_birth, "%Y-%m-%d")
        except:
            pass
    if profile_data.country:
        current_user.country = profile_data.country
    if profile_data.interests:
        current_user.interests = profile_data.interests
    if profile_data.travel_frequency:
        current_user.travel_frequency = profile_data.travel_frequency
    if profile_data.budget:
        current_user.budget = profile_data.budget
    if profile_data.travel_reasons:
        current_user.travel_reasons = profile_data.travel_reasons
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Profile updated successfully",
        "user": current_user
    }

@router.post("/profile/image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload profile image"""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and WebP images are allowed"
        )
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("public/uploads/profiles")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    filename = f"user_{current_user.id}_{int(time.time())}.{file_extension}"
    file_path = upload_dir / filename
    
    # Save file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update user profile_image in database
    current_user.profile_image = f"/uploads/profiles/{filename}"
    db.commit()
    
    return {
        "message": "Profile image uploaded successfully",
        "image_url": current_user.profile_image
    }

@router.delete("/profile/image")
async def delete_profile_image(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete profile image"""
    # Remove image file if it exists
    if current_user.profile_image and current_user.profile_image.startswith("/uploads/profiles/"):
        file_path = Path(f"public{current_user.profile_image}")
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Failed to delete image file: {e}")
    
    # Update user profile_image in database
    current_user.profile_image = None
    db.commit()
    
    return {"message": "Profile image removed successfully"}

@router.delete("/profile")
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user account"""
    # Delete user from database
    db.delete(current_user)
    db.commit()
    
    return {"message": "Account deleted successfully"}

@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload profile image"""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and WebP images are allowed"
        )
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("public/uploads/profiles")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    filename = f"user_{current_user.id}_{int(time.time())}.{file_extension}"
    file_path = upload_dir / filename
    
    # Save file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update user profile_image in database
    current_user.profile_image = f"/uploads/profiles/{filename}"
    db.commit()
    
    return {
        "message": "Profile image uploaded successfully",
        "image_url": current_user.profile_image
    }

@router.post("/survey")
def submit_survey(
    survey_data: SurveyData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit onboarding survey and send welcome email"""
    from datetime import datetime
    
    # Update user with survey data
    current_user.full_name = survey_data.full_name
    current_user.gender = survey_data.gender
    # Parse date_of_birth string to datetime
    try:
        current_user.date_of_birth = datetime.strptime(survey_data.date_of_birth, "%Y-%m-%d")
    except:
        pass
    current_user.country = survey_data.country
    current_user.interests = survey_data.interests
    current_user.travel_frequency = survey_data.travel_frequency
    current_user.budget = survey_data.budget
    current_user.travel_reasons = survey_data.travel_reasons
    
    db.commit()
    
    # Send welcome email
    send_welcome_email(current_user.email, current_user.username)
    
    return {
        "message": "Survey submitted successfully",
        "user": current_user
    }
