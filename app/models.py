from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    profile_image = Column(String(500), nullable=True)  # URL or path to profile image
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Survey/Profile fields
    full_name = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    age = Column(Integer, nullable=True)
    country = Column(String(100), nullable=True)
    interests = Column(String(500), nullable=True)
    travel_frequency = Column(String(50), nullable=True)
    budget = Column(String(50), nullable=True)
    travel_reasons = Column(String(500), nullable=True)
    
    # Relationships
    published_trips = relationship("PublishedTrip", back_populates="creator")


class PublishedTrip(Base):
    """Community published travel plans"""
    __tablename__ = "published_trips"
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    duration_days = Column(Integer, nullable=False)  # Trip length in days
    start_date = Column(DateTime, nullable=True)  # Optional specific dates
    end_date = Column(DateTime, nullable=True)
    
    # Itinerary data (JSON stored as text)
    itinerary_data = Column(Text, nullable=False)  # JSON: {days: [], hotels: [], restaurants: [], activities: []}
    
    # Pricing & monetization
    price_per_person = Column(Float, nullable=True)  # Price if creator wants to monetize
    is_free = Column(Boolean, default=True)
    currency = Column(String(10), default="EUR")
    
    # Metadata
    cover_image = Column(String(500), nullable=True)  # Hero image URL
    tags = Column(String(500), nullable=True)  # Comma-separated: "beach,adventure,budget"
    category = Column(String(50), nullable=True)  # "backpacking", "luxury", "family", "solo"
    budget_level = Column(String(20), nullable=True)  # "low", "medium", "high"
    
    # Stats & engagement
    views_count = Column(Integer, default=0)
    bookings_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    
    # Status
    is_published = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)  # Admin can feature quality trips
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="published_trips")

