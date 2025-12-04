"""
Community router - published trips marketplace
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json

from ..database import get_db
from ..models import User, PublishedTrip
from ..routers.auth import get_current_user

router = APIRouter(prefix="/api/community", tags=["Community"])


# Schemas
class PublishTripRequest(BaseModel):
    title: str
    destination: str
    description: Optional[str] = None
    duration_days: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    itinerary_data: dict  # {days: [], hotels: [], restaurants: [], activities: []}
    price_per_person: Optional[float] = None
    is_free: bool = True
    cover_image: Optional[str] = None
    tags: Optional[str] = None
    category: Optional[str] = None
    budget_level: Optional[str] = None


class PublishedTripResponse(BaseModel):
    id: int
    creator_id: int
    creator_username: str
    creator_profile_image: Optional[str]
    title: str
    destination: str
    description: Optional[str]
    duration_days: int
    start_date: Optional[str]
    end_date: Optional[str]
    price_per_person: Optional[float]
    is_free: bool
    currency: str
    cover_image: Optional[str]
    tags: Optional[str]
    category: Optional[str]
    budget_level: Optional[str]
    views_count: int
    bookings_count: int
    likes_count: int
    is_featured: bool
    created_at: str
    
    class Config:
        from_attributes = True


class TripDetailResponse(PublishedTripResponse):
    itinerary_data: dict  # Full itinerary JSON


@router.post("/publish", response_model=PublishedTripResponse, status_code=status.HTTP_201_CREATED)
def publish_trip(
    trip_data: PublishTripRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Publish a new trip to the community"""
    
    # Create published trip
    new_trip = PublishedTrip(
        creator_id=current_user.id,
        title=trip_data.title,
        destination=trip_data.destination,
        description=trip_data.description,
        duration_days=trip_data.duration_days,
        start_date=datetime.fromisoformat(trip_data.start_date) if trip_data.start_date else None,
        end_date=datetime.fromisoformat(trip_data.end_date) if trip_data.end_date else None,
        itinerary_data=json.dumps(trip_data.itinerary_data),
        price_per_person=trip_data.price_per_person,
        is_free=trip_data.is_free,
        cover_image=trip_data.cover_image,
        tags=trip_data.tags,
        category=trip_data.category,
        budget_level=trip_data.budget_level,
        is_published=True
    )
    
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)
    
    return PublishedTripResponse(
        id=new_trip.id,
        creator_id=new_trip.creator_id,
        creator_username=current_user.username,
        creator_profile_image=current_user.profile_image,
        title=new_trip.title,
        destination=new_trip.destination,
        description=new_trip.description,
        duration_days=new_trip.duration_days,
        start_date=new_trip.start_date.isoformat() if new_trip.start_date else None,
        end_date=new_trip.end_date.isoformat() if new_trip.end_date else None,
        price_per_person=new_trip.price_per_person,
        is_free=new_trip.is_free,
        currency=new_trip.currency,
        cover_image=new_trip.cover_image,
        tags=new_trip.tags,
        category=new_trip.category,
        budget_level=new_trip.budget_level,
        views_count=new_trip.views_count,
        bookings_count=new_trip.bookings_count,
        likes_count=new_trip.likes_count,
        is_featured=new_trip.is_featured,
        created_at=new_trip.created_at.isoformat()
    )


@router.get("/trips", response_model=List[PublishedTripResponse])
def browse_trips(
    destination: Optional[str] = None,
    category: Optional[str] = None,
    budget: Optional[str] = None,
    min_days: Optional[int] = None,
    max_days: Optional[int] = None,
    free_only: bool = False,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Browse published trips with filters"""
    
    query = db.query(PublishedTrip).filter(PublishedTrip.is_published == True)
    
    if destination:
        query = query.filter(PublishedTrip.destination.ilike(f"%{destination}%"))
    
    if category:
        query = query.filter(PublishedTrip.category == category)
    
    if budget:
        query = query.filter(PublishedTrip.budget_level == budget)
    
    if min_days:
        query = query.filter(PublishedTrip.duration_days >= min_days)
    
    if max_days:
        query = query.filter(PublishedTrip.duration_days <= max_days)
    
    if free_only:
        query = query.filter(PublishedTrip.is_free == True)
    
    # Order by featured first, then by popularity (views + bookings)
    query = query.order_by(
        PublishedTrip.is_featured.desc(),
        (PublishedTrip.views_count + PublishedTrip.bookings_count * 5).desc()
    )
    
    trips = query.offset(skip).limit(limit).all()
    
    # Build response with creator info
    results = []
    for trip in trips:
        creator = db.query(User).filter(User.id == trip.creator_id).first()
        results.append(PublishedTripResponse(
            id=trip.id,
            creator_id=trip.creator_id,
            creator_username=creator.username if creator else "Unknown",
            creator_profile_image=creator.profile_image if creator else None,
            title=trip.title,
            destination=trip.destination,
            description=trip.description,
            duration_days=trip.duration_days,
            start_date=trip.start_date.isoformat() if trip.start_date else None,
            end_date=trip.end_date.isoformat() if trip.end_date else None,
            price_per_person=trip.price_per_person,
            is_free=trip.is_free,
            currency=trip.currency,
            cover_image=trip.cover_image,
            tags=trip.tags,
            category=trip.category,
            budget_level=trip.budget_level,
            views_count=trip.views_count,
            bookings_count=trip.bookings_count,
            likes_count=trip.likes_count,
            is_featured=trip.is_featured,
            created_at=trip.created_at.isoformat()
        ))
    
    return results


@router.get("/trips/{trip_id}", response_model=TripDetailResponse)
def get_trip_detail(
    trip_id: int,
    db: Session = Depends(get_db)
):
    """Get full trip details including itinerary"""
    
    trip = db.query(PublishedTrip).filter(
        PublishedTrip.id == trip_id,
        PublishedTrip.is_published == True
    ).first()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Increment view count
    trip.views_count += 1
    db.commit()
    
    # Get creator info
    creator = db.query(User).filter(User.id == trip.creator_id).first()
    
    return TripDetailResponse(
        id=trip.id,
        creator_id=trip.creator_id,
        creator_username=creator.username if creator else "Unknown",
        creator_profile_image=creator.profile_image if creator else None,
        title=trip.title,
        destination=trip.destination,
        description=trip.description,
        duration_days=trip.duration_days,
        start_date=trip.start_date.isoformat() if trip.start_date else None,
        end_date=trip.end_date.isoformat() if trip.end_date else None,
        price_per_person=trip.price_per_person,
        is_free=trip.is_free,
        currency=trip.currency,
        cover_image=trip.cover_image,
        tags=trip.tags,
        category=trip.category,
        budget_level=trip.budget_level,
        views_count=trip.views_count,
        bookings_count=trip.bookings_count,
        likes_count=trip.likes_count,
        is_featured=trip.is_featured,
        created_at=trip.created_at.isoformat(),
        itinerary_data=json.loads(trip.itinerary_data)
    )


@router.get("/my-trips", response_model=List[PublishedTripResponse])
def get_my_published_trips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all trips published by current user"""
    
    trips = db.query(PublishedTrip).filter(
        PublishedTrip.creator_id == current_user.id
    ).order_by(PublishedTrip.created_at.desc()).all()
    
    results = []
    for trip in trips:
        results.append(PublishedTripResponse(
            id=trip.id,
            creator_id=trip.creator_id,
            creator_username=current_user.username,
            creator_profile_image=current_user.profile_image,
            title=trip.title,
            destination=trip.destination,
            description=trip.description,
            duration_days=trip.duration_days,
            start_date=trip.start_date.isoformat() if trip.start_date else None,
            end_date=trip.end_date.isoformat() if trip.end_date else None,
            price_per_person=trip.price_per_person,
            is_free=trip.is_free,
            currency=trip.currency,
            cover_image=trip.cover_image,
            tags=trip.tags,
            category=trip.category,
            budget_level=trip.budget_level,
            views_count=trip.views_count,
            bookings_count=trip.bookings_count,
            likes_count=trip.likes_count,
            is_featured=trip.is_featured,
            created_at=trip.created_at.isoformat()
        ))
    
    return results


@router.delete("/trips/{trip_id}")
def delete_published_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a published trip (only creator can delete)"""
    
    trip = db.query(PublishedTrip).filter(
        PublishedTrip.id == trip_id,
        PublishedTrip.creator_id == current_user.id
    ).first()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found or you don't have permission to delete it"
        )
    
    db.delete(trip)
    db.commit()
    
    return {"message": "Trip deleted successfully"}
