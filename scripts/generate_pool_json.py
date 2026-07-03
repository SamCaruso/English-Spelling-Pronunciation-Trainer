"""
Step 1: Generate exercise sentences via OpenAI and save to a local JSON file for review.

For each word in each phoneme's spelling dict, generates:
- 2 sentences for level 1 (contextual IPA)
- 2 sentences for level 2 (wrong spelling)

Output: scripts/exercise_pool.json

Usage:
    cd Capstone_Deploy
    python scripts/generate_pool_json.py

After running, open exercise_pool.json, review/edit the sentences, then run upload_pool_to_firestore.py.
"""

import sys
import os
import json
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'Backend', '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Backend'))

from openai import OpenAI
from config import OPENAI_API_KEY
from phonemes_dict import phonemes

client = OpenAI(api_key=OPENAI_API_KEY)

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'exercise_pool.json')

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
- Use the target word EXACTLY as provided (same form). Do not add suffixes like -s, -ed, -ing, or change the word form in any way.
- Within each set, the ipa_sentence and the wrong_sentence must use DIFFERENT sentence contexts. Do not rephrase the same sentence — create two completely unrelated scenarios for the word.
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


def main() -> None:
    # Load existing file if it exists (to skip already-generated words)
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            pool = json.load(f)
        print(f'Loaded existing pool with {sum(len(words) for words in pool.values())} word entries')
    else:
        pool = {}

    total_words = sum(len(data['spelling']) for data in phonemes.values())
    print(f'Phonemes: {list(phonemes.keys())}')
    print(f'Total words to generate: {total_words}')
    print()

    for phoneme, data in phonemes.items():
        print(f'=== Phoneme: /{phoneme}/ ===')

        if phoneme not in pool:
            pool[phoneme] = {}

        for ipa_key, options in data['spelling'].items():
            correct, wrong1, wrong2 = options[0], options[1], options[2]

            # Skip if already generated
            if ipa_key in pool[phoneme]:
                print(f'  {ipa_key} ({correct}): already in file, skipping')
                continue

            print(f'  {ipa_key} ({correct}): generating...', end=' ')

            try:
                sentences = generate_for_word(ipa_key, correct, wrong1, wrong2)
                pool[phoneme][ipa_key] = {
                    'answer': correct,
                    'wrong1': wrong1,
                    'wrong2': wrong2,
                    'sentences': sentences,
                }
                print('✓')

                # Save after each word (in case of interruption)
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(pool, f, indent=2, ensure_ascii=False)

            except Exception as e:
                print(f'✗ Error: {e}')

    print(f'\n✓ Done! Review the sentences in: {OUTPUT_FILE}')
    print('When satisfied, run: python scripts/upload_pool_to_firestore.py')


if __name__ == '__main__':
    main()
