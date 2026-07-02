"""
Offline script: pre-generates exercise sentences via OpenAI and uploads to Firestore.

For each word in each phoneme's spelling dict, generates:
- 2 sentences for level 1 (contextual IPA)
- 2 sentences for level 2 (wrong spelling)

Level 3 doesn't need pre-generated sentences (it's just standalone IPA recognition).

Usage:
    cd Capstone_Deploy
    python scripts/generate_exercise_pool.py

Firestore structure (exercise_pool collection):
    Document fields: phoneme, level, ipa, answer, ipa_sentence OR wrong_sentence/wrong_help_sentence
"""

import sys
import os
import json
import hashlib
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'Backend', '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Backend'))

from openai import OpenAI
from google.cloud import firestore
from config import OPENAI_API_KEY, FIRESTORE_DATABASE, POOL_COLLECTION
from phonemes_dict import phonemes

client = OpenAI(api_key=OPENAI_API_KEY)
db = firestore.Client(database=FIRESTORE_DATABASE)

SENTENCES_PER_WORD = 2  # 2 sentences per word per level

SYSTEM_PROMPT = """You are an English pronunciation exercise generator for British English learners.

You will receive ONE word with its IPA transcription, correct spelling, and wrong spelling options.

Generate EXACTLY 2 DIFFERENT sets of sentences for this word. Each set contains:

1. CONTEXTUAL IPA sentence (ipa_sentence): A natural English sentence where the target word is replaced by its IPA transcription.
   Example: For /'ɔ:də/ (correct: "order"), write: "The judge maintained /'ɔ:də/ in the courtroom."

2. WRONG SPELLING sentence (wrong_sentence): One natural English sentence that uses one of the wrong spellings in context.
   - CRITICAL: Every sentence MUST make grammatical and logical sense if you mentally replace the misspelled word with the correct spelling.

3. WRONG SPELLING help sentence (wrong_help_sentence): The EXACT same sentence as wrong_sentence, but with the wrong spelling replaced by the IPA transcription.

Rules:
- Use British English spelling throughout.
- The two sets must use DIFFERENT sentences — do not repeat or rephrase the same sentence.
- Use natural, everyday English sentences.
- The sentences should make the meaning of the target word clear from context.
- Do NOT include the correct spelling anywhere in the sentences.
- wrong_help_sentence must be the EXACT same sentence as wrong_sentence with only the wrong spelling swapped for the IPA.

Return ONLY valid JSON with this structure:
{
  "sentences": [
    {
      "ipa_sentence": "...",
      "wrong_sentence": "...",
      "wrong_help_sentence": "..."
    },
    {
      "ipa_sentence": "...",
      "wrong_sentence": "...",
      "wrong_help_sentence": "..."
    }
  ]
}"""


def make_doc_id(phoneme: str, level: int, ipa_key: str, index: int) -> str:
    """Create a stable, unique document ID."""
    key_hash = hashlib.md5(ipa_key.encode()).hexdigest()[:8]
    safe_phoneme = phoneme.replace(':', '_').replace('/', '_')
    return f'{safe_phoneme}_L{level}_{key_hash}_{index}'


def generate_for_word(ipa_key: str, correct: str, wrong1: str, wrong2: str) -> list[dict]:
    """Call OpenAI to generate 2 sentence sets for one word."""
    user_prompt = f"IPA: {ipa_key}, Correct: {correct}, Wrong: {wrong1}, {wrong2}"

    response = client.chat.completions.create(
        model='gpt-4o',
        response_format={'type': 'json_object'},
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_prompt},
        ],
        temperature=0.9,
    )

    result = json.loads(response.choices[0].message.content)
    if 'sentences' not in result or len(result['sentences']) != 2:
        raise ValueError(f'Expected 2 sentence sets, got {len(result.get("sentences", []))}')
    return result['sentences']


def populate_phoneme(phoneme: str, spelling: dict):
    """Generate and upload sentences for all words in a phoneme."""
    print(f'\n=== Phoneme: /{phoneme}/ ({len(spelling)} words) ===')

    for ipa_key, options in spelling.items():
        correct, wrong1, wrong2 = options[0], options[1], options[2]

        # Check if already populated
        existing = list(
            db.collection(POOL_COLLECTION)
            .where('phoneme', '==', phoneme)
            .where('ipa', '==', ipa_key)
            .limit(1)
            .stream()
        )
        if existing:
            print(f'  {ipa_key} ({correct}): already exists, skipping')
            continue

        print(f'  {ipa_key} ({correct}): generating...', end=' ')

        try:
            sentences = generate_for_word(ipa_key, correct, wrong1, wrong2)
            batch = db.batch()

            for i, sent in enumerate(sentences):
                # Level 1 document (ipa_sentence)
                doc_id_l1 = make_doc_id(phoneme, 1, ipa_key, i)
                doc_ref_l1 = db.collection(POOL_COLLECTION).document(doc_id_l1)
                batch.set(doc_ref_l1, {
                    'phoneme': phoneme,
                    'level': 1,
                    'ipa': ipa_key,
                    'answer': correct,
                    'ipa_sentence': sent['ipa_sentence'],
                })

                # Level 2 document (wrong_sentence)
                doc_id_l2 = make_doc_id(phoneme, 2, ipa_key, i)
                doc_ref_l2 = db.collection(POOL_COLLECTION).document(doc_id_l2)
                batch.set(doc_ref_l2, {
                    'phoneme': phoneme,
                    'level': 2,
                    'ipa': ipa_key,
                    'answer': correct,
                    'wrong_sentence': sent['wrong_sentence'],
                    'wrong_help_sentence': sent['wrong_help_sentence'],
                })

            batch.commit()
            print('✓')

        except Exception as e:
            print(f'✗ Error: {e}')


if __name__ == '__main__':
    print('Starting exercise pool generation...')
    print(f'Target: {SENTENCES_PER_WORD} sentences per word per level')
    print(f'Phonemes to process: {list(phonemes.keys())}')

    total_words = sum(len(data['spelling']) for data in phonemes.values())
    total_docs = total_words * SENTENCES_PER_WORD * 2  # 2 levels
    print(f'Total words: {total_words}, Expected documents: {total_docs}')

    for phoneme, data in phonemes.items():
        populate_phoneme(phoneme, data['spelling'])

    print('\n✓ Done! Exercise pool populated in Firestore.')
