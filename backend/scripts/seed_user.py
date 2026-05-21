#!/usr/bin/env python3
"""Seed the database with an initial user if not present.

Usage: python backend/scripts/seed_user.py
Make sure backend .env is configured so get_db() can connect.
"""
import os
import sys
# ensure backend directory is on sys.path so we can import models
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models.user import User

EMAIL = 'makanakakanyai@gmail.com'
PASSWORD = 'Business7mogul'

def main():
    existing = User.find_by_email(EMAIL)
    if existing:
        print(f"User already exists: {EMAIL}")
        sys.exit(0)

    user_id = User.create_user(EMAIL, PASSWORD, 'Makanakakanyai', '')
    if user_id:
        print(f"Created user {EMAIL} with id {user_id}")
    else:
        print("Failed to create user. Check DB connection and .env")

if __name__ == '__main__':
    main()
