"""
Pydantic schemas for user validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None  # Format: YYYY-MM-DD
    country: Optional[str] = None
    interests: Optional[str] = None
    travel_frequency: Optional[str] = None
    budget: Optional[str] = None
    travel_reasons: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    preferred_language: Optional[str] = None
    currency: Optional[str] = None
    travel_preferences: Optional[str] = None
    budget_range: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    profile_image: Optional[str] = None
    created_at: datetime
    full_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    age: Optional[int] = None
    country: Optional[str] = None
    interests: Optional[str] = None
    travel_frequency: Optional[str] = None
    budget: Optional[str] = None
    travel_reasons: Optional[str] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

class SurveyData(BaseModel):
    full_name: str
    gender: str
    date_of_birth: str  # Format: YYYY-MM-DD
    country: str
    interests: Optional[str] = None
    travel_frequency: str
    budget: str
    travel_reasons: str
