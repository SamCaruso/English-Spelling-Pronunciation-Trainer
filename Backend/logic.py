"""
Core business logic: phoneme selection, patterns, homophone setup.
No in-memory state — all test state lives in Firestore via test_service.
"""

import random
import logging
from fastapi import HTTPException
from phonemes_dict import phonemes

logger = logging.getLogger(__name__)


def pick_new_phoneme(completed: list[str]) -> str:
    """Pick a random phoneme the user hasn't studied yet."""
    pool = [p for p in phonemes if p not in completed]
    if not pool:
        raise HTTPException(status_code=404, detail='No new phonemes available')
    return random.choice(pool)


def get_patterns(phoneme: str) -> dict:
    """Get spelling patterns with 2 random examples each."""
    return {
        pattern: random.sample(list(examples), k=min(2, len(examples)))
        for pattern, examples in phonemes[phoneme]['patterns'].items()
    }


def get_homophone_keys(phoneme: str, max_count: int = 5) -> list[str]:
    """Get a random selection of homophone keys for a phoneme."""
    keys = list(phonemes[phoneme]['homophones'].keys())
    if len(keys) > max_count:
        return random.sample(keys, k=max_count)
    random.shuffle(keys)
    return keys


def get_review_homophone_keys(completed: list[str]) -> list[str]:
    """Get 2 random homophone keys per completed phoneme for review."""
    all_keys = []
    for phoneme in completed:
        keys = list(phonemes[phoneme]['homophones'].keys())
        selected = random.sample(keys, k=min(2, len(keys)))
        all_keys.extend(selected)
    random.shuffle(all_keys)
    return all_keys


def find_phoneme_for_homophone(homoph_key: str) -> str | None:
    """Find which phoneme a homophone key belongs to."""
    for phoneme, data in phonemes.items():
        if homoph_key in data['homophones']:
            return phoneme
    return None
