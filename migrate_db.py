"""
Database migration script - creates new tables for community features
Run this script once to add published_trips table
"""
from app.database import engine
from app import models

print("🔄 Creating database tables...")

# This will create ALL tables defined in models.py
# Existing tables won't be affected (SQLAlchemy skips them)
models.Base.metadata.create_all(bind=engine)

print("✅ Database migration completed!")
print("✅ published_trips table created (if it didn't exist)")
print("\nYou can now:")
print("  - Publish trips via /api/community/publish")
print("  - Browse trips via /api/community/trips")
print("  - View trip details via /api/community/trips/{id}")
