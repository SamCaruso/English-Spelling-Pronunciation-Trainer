"""
Exercise generator: uses OpenAI API to create sentences for exercises.

Level 1 (easiest): Contextual sentence with IPA embedded — user types the word
Level 2 (medium): Sentence using wrong spellings — user figures out the real word
Level 3 (hardest): Simple IPA recognition, no context (no LLM needed)
"""

import json
import random
import logging
from openai import OpenAI
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = """You are an English pronunciation exercise generator for British English learners.

You will receive spelling data: a list of entries, each with an IPA transcription, the correct spelling, and wrong spelling options.

Your task: for each entry, generate THREE things:

1. CONTEXTUAL IPA sentence (ipa_sentence): A natural English sentence where the target word is replaced by its IPA transcription.
   Example: For /'ɔ:də/ (correct: "order"), write: "The judge maintained /'ɔ:də/ in the courtroom."

2. WRONG SPELLING sentence (wrong_sentence): One natural English sentence that uses one of the wrong spellings in context, so the reader can figure out the real word from meaning.
   - CRITICAL: Every sentence MUST make grammatical and logical sense if you mentally replace the misspelled word(s) with the correct spelling.
   
   GOOD example: 
   -For /dɪ'vɔ:s/ (correct: "divorce", wrong: "divauce", "divawce"), write: "After years of arguments, they decided to get a divauce."
   - "He didn't mean to brake the glass." 
   (Replacing "brake" with "break" works grammatically ✅)
   
   BAD example (AVOID): 
    - "She broke her swar."
   (Replacing "swar" with "swore" gives "She broke her swore" — grammatically broken ❌)
   - " He accidentally let out a swar word in class."
   (Replacing "swar" with "swore" gives "She broke her swore" — grammatically broken ❌)
    - "We need to fix the pipe before it berst." 
   (Replacing "berst" with "burst" does not work grammatically because it should be "bursts" with a final "-s" - grammatically broken ❌)

3. WRONG SPELLING help sentence (wrong_help_sentence): The EXACT same sentence as wrong_sentence, but with the wrong spelling replaced by the IPA transcription.
   Example: If wrong_sentence is "After years of arguments, they decided to get a divauce", then wrong_help_sentence is "After years of arguments, they decided to get a /dɪ'vɔ:s/."

Rules:
- Use British English spelling throughout (e.g. "specialised" not "specialized", "colour" not "color", "centre" not "center").
- Each sentence must be unique and clearly distinguishable from the others. Do not reuse sentence structures across entries.
- Use natural, everyday English sentences.
- The sentences should make the meaning of the target word clear from context.
- The sentence must make grammatical and logical sense if you mentally replace the misspelled word with the correct spelling.
- Do NOT include the correct spelling anywhere in the sentences.
- wrong_help_sentence must be the EXACT same sentence as wrong_sentence with only the wrong spelling swapped for the IPA.
- Each entry must have all three outputs.

Return ONLY valid JSON with this structure:
{
  "items": [
    {
      "ipa": "/'ɔ:də/",
      "correct": "order",
      "wrong1": "aurder",
      "wrong2": "awder",
      "ipa_sentence": "The judge maintained /'ɔ:də/ in the courtroom.",
      "wrong_sentence": "After years of arguments, they decided to get a divauce.",
      "wrong_help_sentence": "After years of arguments, they decided to get a /dɪ'vɔ:s/."
    }
  ]
}"""


def _build_user_prompt(selected_items: list[dict]) -> str:
    lines = ["Generate sentences for these words:", ""]
    for item in selected_items:
        lines.append(f"  IPA: {item['ipa']}, Correct: {item['correct']}, Wrong: {item['wrong1']}, {item['wrong2']}")
    return "\n".join(lines)


def generate_exercises(phoneme: str, spelling: dict, count_per_level: int = 4) -> dict:
    """ Generate exercise items for a phoneme (4 for lessons, 2 for reviews). """
    all_keys = list(spelling.keys())
    total_needed = count_per_level * 3
    selected_keys = random.sample(all_keys, k=total_needed)

    level1_keys = selected_keys[0:count_per_level]
    level2_keys = selected_keys[count_per_level:count_per_level * 2]
    level3_keys = selected_keys[count_per_level * 2:]

    # Build items for LLM (levels 1 and 2)
    llm_items = []
    for key in level1_keys + level2_keys:
        options = spelling[key]
        llm_items.append({
            'ipa': key,
            'correct': options[0],
            'wrong1': options[1],
            'wrong2': options[2],
        })

    # Call OpenAI
    expected_count = count_per_level * 2
    logger.info(f'Generating exercises for /{phoneme}/ via OpenAI ({count_per_level} per level)')
    response = client.chat.completions.create(
        model='gpt-4o',
        response_format={'type': 'json_object'},
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': _build_user_prompt(llm_items)},
        ],
        temperature=0.8,
    )

    content = response.choices[0].message.content
    llm_result = json.loads(content)

    # Check the LLM produces the number and format of items expected
    if 'items' not in llm_result or len(llm_result['items']) != expected_count:
        raise ValueError(f'Expected {expected_count} items from OpenAI, got {len(llm_result.get("items", []))}')

    # Index LLM results by IPA key for reliable matching (LLM may reorder items)
    llm_by_ipa = {}
    for item in llm_result['items']:
        ipa_key = item.get('ipa', '').strip()
        llm_by_ipa[ipa_key] = item

    # Level 1: Contextual IPA (easiest)
    level1_items = []
    for key in level1_keys:
        item = llm_by_ipa.get(key)
        if not item:
            raise ValueError(f'LLM did not return item for IPA key: {key}')
        options = list(spelling[key])
        random.shuffle(options)
        level1_items.append({
            'ipa': key,
            'answer': spelling[key][0],
            'options': options,
            'no_help_prompt': item['ipa_sentence'],
            'help_prompt': item['ipa_sentence'],
        })

    # Level 2: Wrong spelling in context (medium)
    level2_items = []
    for key in level2_keys:
        item = llm_by_ipa.get(key)
        if not item:
            raise ValueError(f'LLM did not return item for IPA key: {key}')
        level2_items.append({
            'ipa': key,
            'answer': spelling[key][0],
            'no_help_prompt': item['wrong_sentence'],
            'help_prompt': item['wrong_help_sentence'],
        })

    # Level 3: Standalone IPA (hardest, no LLM)
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
