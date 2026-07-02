"""
Exercise generator: serves exercises from the pre-generated Firestore pool.

All 12 words from the phoneme's spelling dict appear exactly once per session:
- 4 words assigned to Level 1 (Contextual IPA)
- 4 words assigned to Level 2 (Wrong spelling)
- 4 words assigned to Level 3 (Standalone IPA — no pool needed)

Each word has 2 pre-generated sentences per level in the pool, giving variety between sessions.
The pool is populated offline by scripts/generate_exercise_pool.py.
"""

import random
import logging
from google.cloud import firestore
from config import FIRESTORE_DATABASE, POOL_COLLECTION

logger = logging.getLogger(__name__)

db = firestore.Client(database=FIRESTORE_DATABASE)


def _fetch_random_sentence(phoneme: str, level: int, ipa_key: str) -> dict:
    """Fetch one random sentence from the pool for a given word and level."""
    docs = list(
        db.collection(POOL_COLLECTION)
        .where('phoneme', '==', phoneme)
        .where('level', '==', level)
        .where('ipa', '==', ipa_key)
        .stream()
    )
    if not docs:
        raise ValueError(f'No pool entries found for /{phoneme}/, level {level}, IPA {ipa_key}')
    return random.choice(docs).to_dict()


def generate_exercises(phoneme: str, spelling: dict, count_per_level: int = 4) -> dict:
    """
    Fetch exercise items from the pre-generated Firestore pool.
    All words appear exactly once, distributed across 3 levels.

    Args:
        phoneme: The phoneme IPA key.
        spelling: The spelling dict from phonemes_dict.
        count_per_level: Items per level (4 for lessons, 2 for reviews).

    Returns:
        {'level1_items': [...], 'level2_items': [...], 'level3_items': [...]}
    """
    all_keys = list(spelling.keys())
    total_needed = count_per_level * 3
    selected_keys = random.sample(all_keys, k=total_needed)

    level1_keys = selected_keys[0:count_per_level]
    level2_keys = selected_keys[count_per_level:count_per_level * 2]
    level3_keys = selected_keys[count_per_level * 2:]

    logger.info(f'Fetching exercises for /{phoneme}/ from pool ({count_per_level} per level)')

    # Level 1: Contextual IPA — fetch random sentence from pool
    level1_items = []
    for key in level1_keys:
        doc = _fetch_random_sentence(phoneme, 1, key)
        options = list(spelling[key])
        random.shuffle(options)
        level1_items.append({
            'ipa': key,
            'answer': spelling[key][0],
            'options': options,
            'no_help_prompt': doc['ipa_sentence'],
            'help_prompt': doc['ipa_sentence'],
        })

    # Level 2: Wrong spelling — fetch random sentence from pool
    level2_items = []
    for key in level2_keys:
        doc = _fetch_random_sentence(phoneme, 2, key)
        level2_items.append({
            'ipa': key,
            'answer': spelling[key][0],
            'no_help_prompt': doc['wrong_sentence'],
            'help_prompt': doc['wrong_help_sentence'],
        })

    # Level 3: Standalone IPA — no pool needed
    level3_items = []
    for key in level3_keys:
        options = list(spelling[key])
        random.shuffle(options)
        level3_items.append({
            'ipa': key,
            'answer': spelling[key][0],
            'options': options,
            'no_help_prompt': f'How do you spell {key}?',
            'help_prompt': f'How do you spell {key}?',
        })

    return {
        'level1_items': level1_items,
        'level2_items': level2_items,
        'level3_items': level3_items,
    }
