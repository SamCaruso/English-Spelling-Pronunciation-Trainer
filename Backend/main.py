"""
FastAPI application for the English Pronunciation Trainer.
With Firebase Authentication.
"""

import config 

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
import random
import time

import log_file
import schemas as s
from phonemes_dict import phonemes
from user_service import (
    get_completed_phonemes,
    save_phoneme_progress,
    get_review_status,
    get_user_name,
    save_user_name,
)
from exercise_generator import generate_exercises
from test_service import (
    register_tests,
    check_answer,
    register_homophone_tests,
    check_homophone_answer,
)
import logic
from auth import get_current_user

logger = logging.getLogger(__name__)

# Exercise metadata — single source of truth for UI labels
EXERCISE_META = {
    1: {
        'type': 'Contextual IPA Recognition',
        'instructions': 'Read the sentence and type the correct spelling of the word shown in IPA.',
    },
    2: {
        'type': 'Wrong Spelling Recognition',
        'instructions': 'The sentence contains one intentionally misspelled word. Find it and type the correct spelling.',
    },
    3: {
        'type': 'Standalone IPA Recognition',
        'instructions': 'Type the correct spelling for each IPA transcription.',
    },
}

app = FastAPI(title='English Pronunciation Trainer')

# --- Idempotency ---

IDEMPOTENCY_STORE = {}
IDEMPOTENCY_DURATION = 6000


def clean_idempotency_store():
    now = time.time()
    expired = [key for key, value in IDEMPOTENCY_STORE.items() if now - value['time'] > IDEMPOTENCY_DURATION]
    for key in expired:
        IDEMPOTENCY_STORE.pop(key, None)


def check_idempotency(idempotency_key: str, endpoint: str, func, *args):
    """Check if this request was already processed. If so, return cached response."""
    clean_idempotency_store()

    if not idempotency_key:
        raise HTTPException(status_code=400, detail='Missing Idempotency-Key header')

    store_key = f'{endpoint}:{idempotency_key}'
    cached = IDEMPOTENCY_STORE.get(store_key)
    if cached:
        return JSONResponse(status_code=cached['status'], content=cached['body'])

    result = func(*args)

    IDEMPOTENCY_STORE[store_key] = {
        'time': time.time(),
        'status': 200,
        'body': result,
    }

    return result


# --- Public endpoint (no auth needed) ---

@app.get('/api/firebase-config')
async def firebase_config():
    """Serve Firebase config to the frontend (keeps API key out of source code)."""
    return {
        'apiKey': config.FIREBASE_API_KEY,
        'authDomain': 'spell-pron-trainer.firebaseapp.com',
        'projectId': 'spell-pron-trainer',
        'storageBucket': 'spell-pron-trainer.firebasestorage.app',
        'messagingSenderId': '1034759911844',
        'appId': '1:1034759911844:web:b66abbb21c075f66986931',
    }


# --- Authenticated endpoints (user_id from Firebase token) ---

@app.get('/api/reviewstatus', response_model=s.ReviewResponse)
async def review_status(user_id: str = Depends(get_current_user)):
    status = get_review_status(user_id, len(phonemes))
    return {'status': status}


@app.get('/api/username')
async def get_name(user_id: str = Depends(get_current_user)):
    name = get_user_name(user_id)
    return {'name': name}


@app.post('/api/username')
async def set_name(body: s.SetNameRequest, user_id: str = Depends(get_current_user)):
    save_user_name(user_id, body.name)
    return {'status': 'ok'}


@app.get('/api/phonemescovered', response_model=list[s.PhonemesCoveredResponse])
async def phonemes_covered(user_id: str = Depends(get_current_user)):
    completed = get_completed_phonemes(user_id)
    result = []
    for p in completed:
        patterns = logic.get_patterns(p)
        result.append({'phoneme': p, 'api_word': phonemes[p]['api'], 'patterns': patterns})
    return result


@app.get('/api/learn', response_model=s.LearnResponse)
async def learn(user_id: str = Depends(get_current_user)):
    completed = get_completed_phonemes(user_id)
    phoneme = logic.pick_new_phoneme(completed)
    patterns = logic.get_patterns(phoneme)
    return {
        'phoneme': phoneme,
        'ipa': f'/{phoneme}/',
        'api_word': phonemes[phoneme]['api'],
        'patterns': patterns,
    }


@app.get('/api/exercises/{phoneme}', response_model=s.ExercisesResponse)
async def get_exercises(phoneme: str, user_id: str = Depends(get_current_user)):
    if phoneme not in phonemes:
        raise HTTPException(status_code=404, detail=f'Phoneme /{phoneme}/ not found')
    spelling = phonemes[phoneme]['spelling']
    result = generate_exercises(phoneme, spelling)
    exercises = {
        'exercises': [
            {'level': 1, **EXERCISE_META[1], 'items': result['level1_items']},
            {'level': 2, **EXERCISE_META[2], 'items': result['level2_items']},
            {'level': 3, **EXERCISE_META[3], 'items': result['level3_items']},
        ]
    }
    exercises = register_tests(exercises)
    return exercises


@app.post('/api/checkanswer', response_model=s.AnswerResponse)
async def check_exercise_answer(
    body: s.AnswerRequest,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(None, alias='Idempotency-Key'),
):
    def process():
        result = check_answer(body.test_id, body.answer)
        if result is None:
            raise HTTPException(status_code=404, detail='Test not found')
        return result

    return check_idempotency(idempotency_key, 'checkanswer', process)


@app.get('/api/homophones/{phoneme}', response_model=list[s.HomophResponse])
async def get_homophones(phoneme: str, user_id: str = Depends(get_current_user)):
    if phoneme not in phonemes:
        raise HTTPException(status_code=404, detail=f'Phoneme /{phoneme}/ not found')
    keys = logic.get_homophone_keys(phoneme)
    return register_homophone_tests(keys, phonemes[phoneme]['homophones'])


@app.get('/api/reviewexercises', response_model=s.ExercisesResponse)
async def get_review_exercises(user_id: str = Depends(get_current_user)):
    """Generate mixed review exercises for all completed phonemes (2 items per phoneme per level)."""
    completed = get_completed_phonemes(user_id)
    if not completed:
        raise HTTPException(status_code=404, detail='No phonemes to review')

    all_level1 = []
    all_level2 = []
    all_level3 = []

    for p in completed:
        spelling = phonemes[p]['spelling']
        result = generate_exercises(p, spelling, count_per_level=2)
        all_level1.extend(result['level1_items'])
        all_level2.extend(result['level2_items'])
        all_level3.extend(result['level3_items'])

    random.shuffle(all_level1)
    random.shuffle(all_level2)
    random.shuffle(all_level3)

    exercises = {
        'exercises': [
            {'level': 1, **EXERCISE_META[1], 'items': all_level1},
            {'level': 2, **EXERCISE_META[2], 'items': all_level2},
            {'level': 3, **EXERCISE_META[3], 'items': all_level3},
        ]
    }

    exercises = register_tests(exercises)
    return exercises


@app.get('/api/reviewhomophones', response_model=list[s.HomophResponse])
async def review_homophones(user_id: str = Depends(get_current_user)):
    completed = get_completed_phonemes(user_id)
    if not completed:
        return []
    all_keys = logic.get_review_homophone_keys(completed)
    merged = {}
    for p in completed:
        merged.update(phonemes[p]['homophones'])
    return register_homophone_tests(all_keys, merged)


@app.post('/api/checkhomophanswer', response_model=s.HomophAnswerResponse)
async def check_homoph(
    body: s.AnswerRequest,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(None, alias='Idempotency-Key'),
):
    def process():
        result = check_homophone_answer(body.test_id, body.answer)
        if result is None:
            raise HTTPException(status_code=404, detail='Homophone test not found')
        return result

    return check_idempotency(idempotency_key, 'checkhomophanswer', process)


@app.post('/api/saveprogress', response_model=s.SaveProgressResponse)
async def save_progress(body: s.SaveProgress, user_id: str = Depends(get_current_user)):
    save_phoneme_progress(user_id, body.phoneme)
    return {'status': 'ok'}


# --- Serve frontend ---

FRONTEND_DIR = Path(__file__).resolve().parent.parent / 'Frontend'
if FRONTEND_DIR.exists():
    app.mount('/', StaticFiles(directory=str(FRONTEND_DIR), html=True), name='frontend')
