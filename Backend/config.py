"""
Configuration for Cloud Run deployment.
Reads environment variables directly from os.environ.
On Cloud Run, env vars are set via the platform — no .env file needed.
"""

import os

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', '')
FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY', '')

# Firestore collection names
USERS_COLLECTION = 'users'
TESTS_COLLECTION = 'active_tests'
POOL_COLLECTION = 'exercise_pool'
FIRESTORE_DATABASE = 'spell-pron-trainer'
