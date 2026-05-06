"""
User service: manages user progress in Firestore.

Firestore stores only completed_phonemes per user.
"""

import logging
from google.cloud import firestore
from fastapi import HTTPException
from config import USERS_COLLECTION, FIRESTORE_DATABASE

logger = logging.getLogger(__name__)

db = firestore.Client(database=FIRESTORE_DATABASE)


def get_or_create_user(user_id: str) -> dict:
    """Get user document from Firestore, or create a new one."""
    doc_ref = db.collection(USERS_COLLECTION).document(user_id)

    try:
        doc = doc_ref.get()
    except Exception as e:
        logger.error(f'Firestore unreachable (get user {user_id}): {e}')
        raise HTTPException(status_code=503, detail='Database temporarily unavailable')

    if doc.exists:
        return doc.to_dict()

    new_user = {'completed_phonemes': [], 'name': ''}
    try:
        doc_ref.set(new_user)
    except Exception as e:
        logger.error(f'Firestore unreachable (create user {user_id}): {e}')
        raise HTTPException(status_code=503, detail='Database temporarily unavailable')

    logger.info(f'Created new user: {user_id}')
    return new_user


def get_completed_phonemes(user_id: str) -> list[str]:
    """Return list of phonemes the user has already studied."""
    user = get_or_create_user(user_id)
    return user.get('completed_phonemes', [])


def get_user_name(user_id: str) -> str:
    """Return the user's display name."""
    user = get_or_create_user(user_id)
    return user.get('name', '')


def save_user_name(user_id: str, name: str):
    """Save the user's display name."""
    doc_ref = db.collection(USERS_COLLECTION).document(user_id)
    try:
        doc_ref.set({'name': name}, merge=True)
    except Exception as e:
        logger.error(f'Firestore unreachable (save name for {user_id}): {e}')
        raise HTTPException(status_code=503, detail='Database temporarily unavailable')
    logger.info(f'Saved name for user {user_id}: {name}')


def save_phoneme_progress(user_id: str, phoneme: str):
    """Mark a phoneme as completed."""
    doc_ref = db.collection(USERS_COLLECTION).document(user_id)
    try:
        doc_ref.set({
            'completed_phonemes': firestore.ArrayUnion([phoneme]),
        }, merge=True)
    except Exception as e:
        logger.error(f'Firestore unreachable (save progress for {user_id}): {e}')
        raise HTTPException(status_code=503, detail='Database temporarily unavailable')
    logger.info(f'Saved progress for user {user_id}: phoneme={phoneme}')


def get_review_status(user_id: str, total_phonemes: int) -> str:
    """
    Determine review status:
    - 'no_progress': user hasn't studied anything yet
    - 'review_and_learn': user has studied some, more to learn
    - 'review_only': user has studied all available phonemes
    """
    completed = get_completed_phonemes(user_id)

    if not completed:
        return 'no_progress'
    if len(completed) >= total_phonemes:
        return 'review_only'
    return 'review_and_learn'
