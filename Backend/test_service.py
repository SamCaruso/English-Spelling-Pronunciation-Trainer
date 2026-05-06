"""
Test service: stores exercise answers in Firestore as temporary documents.

Documents are NEVER deleted by the app — Firestore TTL automatically
cleans them up after 5 hours. This avoids ghost-request issues where
TCP delivers a request after the frontend has timed out.
Idempotency is handled at the API layer to prevent duplicate processing.
"""

import logging
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from config import TESTS_COLLECTION, FIRESTORE_DATABASE

logger = logging.getLogger(__name__)

db = firestore.Client(database=FIRESTORE_DATABASE)

EXERCISE_ATTEMPTS = 4
HOMOPHONE_ATTEMPTS = 4


def register_tests(exercises: dict) -> dict:
    """
    Take AI-generated exercises, store each answer in Firestore,
    and return exercises with test_ids added (answers stripped).
    """
    batch = db.batch()

    for exercise in exercises['exercises']:
        for item in exercise['items']:
            test_id = f'ex_{uuid4().hex}'
            doc_ref = db.collection(TESTS_COLLECTION).document(test_id)
            batch.set(doc_ref, {
                'answer': item['answer'].lower().strip(),
                'attempts_left': EXERCISE_ATTEMPTS,
                'expires_at': datetime.now(timezone.utc) + timedelta(hours=5),
            })
            item['test_id'] = test_id
            del item['answer']  # strip answer before sending to frontend

    batch.commit()
    logger.info(f'Registered {sum(len(ex["items"]) for ex in exercises["exercises"])} test items in Firestore')
    return exercises


def check_answer(test_id: str, user_answer: str) -> dict | None:
    """
    Check user's answer against the stored correct answer.
    Tracks attempts in Firestore. Documents are never deleted — TTL handles cleanup.

    Returns:
        {'answered': 'correct'} — correct answer
        {'answered': 'incorrect', 'attempts_left': N} — wrong, tries remaining
        {'answered': 'failed', 'solution': str} — help round exhausted, solution revealed
        {'answered': 'failed_no_help'} — no-help round exhausted, moving to help round
        None — test not found
    """
    doc_ref = db.collection(TESTS_COLLECTION).document(test_id)
    doc = doc_ref.get()

    if not doc.exists:
        return None

    data = doc.to_dict()
    correct_answer = data['answer']
    is_correct = user_answer.lower().strip() == correct_answer

    if is_correct:
        logger.info(f'Test {test_id}: correct answer')
        return {'answered': 'correct'}

    # Wrong answer — decrement attempts
    attempts_left = data['attempts_left'] - 1

    if attempts_left <= 0:
        help_round = data.get('help_round', False)
        if help_round:
            # Help round exhausted — reveal solution
            logger.info(f'Test {test_id}: failed help round')
            return {'answered': 'failed', 'solution': correct_answer}
        else:
            # No-help round exhausted — reset for help round
            doc_ref.update({'attempts_left': 2, 'help_round': True})
            logger.info(f'Test {test_id}: failed no-help round, moving to help')
            return {'answered': 'failed_no_help'}

    doc_ref.update({'attempts_left': attempts_left})
    return {'answered': 'incorrect', 'attempts_left': attempts_left}


def register_homophone_tests(homophones_data: list[dict], phoneme_homophones: dict) -> list[dict]:
    """
    Store homophone answers in Firestore.
    Each homophone test stores the full set of valid spellings.
    """
    from audio_service import get_audio_url

    batch = db.batch()
    tests = []

    for homoph_key in homophones_data:
        all_spellings = phoneme_homophones[homoph_key]
        test_id = f'homoph_{uuid4().hex}'
        doc_ref = db.collection(TESTS_COLLECTION).document(test_id)
        doc_ref_data = {
            'solutions': list(all_spellings),
            'solutions_left': list(all_spellings),
            'attempts_left': HOMOPHONE_ATTEMPTS,
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=5),
        }
        batch.set(doc_ref, doc_ref_data)
        # Pick any word for audio (they all sound the same)
        sample_word = next(iter(all_spellings))
        tests.append({
            'homoph': homoph_key,
            'test_id': test_id,
            'amount': len(all_spellings),
            'audio_url': get_audio_url(sample_word),
        })

    batch.commit()
    logger.info(f'Registered {len(tests)} homophone tests in Firestore')
    return tests


def check_homophone_answer(test_id: str, user_answer: str) -> dict | None:
    """
    Check a homophone answer against Firestore.
    Tracks attempts and remaining solutions.
    Documents are never deleted here — TTL handles cleanup.

    Returns:
        {'answered': 'correct', 'attempts_left': N} — correct guess, more to find
        {'answered': 'done'} — all homophones found
        {'answered': 'incorrect', 'attempts_left': N} — wrong guess
        {'answered': 'failed', 'solution': list} — out of attempts, remaining revealed
        None — test not found
    """
    doc_ref = db.collection(TESTS_COLLECTION).document(test_id)
    doc = doc_ref.get()

    if not doc.exists:
        return None

    data = doc.to_dict()
    solutions_left = set(data['solutions_left'])
    answer = user_answer.lower().strip()

    if answer in solutions_left:
        solutions_left.discard(answer)
        if not solutions_left:
            return {'answered': 'done'}
        doc_ref.update({'solutions_left': list(solutions_left)})
        return {'answered': 'correct', 'attempts_left': data['attempts_left']}

    # Wrong answer — decrement attempts
    attempts_left = data['attempts_left'] - 1

    if attempts_left <= 0:
        remaining = list(solutions_left)
        logger.info(f'Homophone {test_id}: failed')
        return {'answered': 'failed', 'solution': remaining}

    doc_ref.update({'attempts_left': attempts_left})
    return {'answered': 'incorrect', 'attempts_left': attempts_left}
