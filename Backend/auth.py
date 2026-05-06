"""
Firebase Authentication middleware.

Verifies Firebase ID tokens sent from the frontend.
Extracts the user's Firebase UID to use as user_id.
"""

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Request, HTTPException
import logging
import os

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
# On Cloud Run: uses default credentials automatically
# Locally: uses GOOGLE_APPLICATION_CREDENTIALS from .env
if not firebase_admin._apps:
    try:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {'projectId': 'spell-pron-trainer'})
    except Exception as e:
        logger.warning(f'Firebase init with ApplicationDefault failed: {e}')
        firebase_admin.initialize_app()


async def get_current_user(request: Request) -> str:
    """
    Extract and verify the Firebase ID token from the Authorization header.
    Returns the Firebase UID as the user_id.
    """
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing or invalid Authorization header')

    token = auth_header.split('Bearer ')[1]

    try:
        decoded = auth.verify_id_token(token)
        return decoded['uid']
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail='Token expired. Please log in again.')
    except auth.InvalidIdTokenError as e:
        logger.error(f'InvalidIdTokenError: {e}')
        raise HTTPException(status_code=401, detail='Invalid token')
    except Exception as e:
        logger.error(f'Auth error ({type(e).__name__}): {e}')
        raise HTTPException(status_code=401, detail='Authentication failed')
