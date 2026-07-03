"""
Pre-cache script: generates ALL audio via Google Cloud TTS
and uploads to GCS bucket (word_audio/ folder).

Generates audio for:
- Phoneme pronunciation words (or, er, air, e)
- All pattern example words
- First word (correct spelling) of each spelling entry
- All homophone words

Uses British English male voice for all.
Run this once to populate GCS, then the app serves audio from there.
"""

from dotenv import load_dotenv
load_dotenv()

from google.cloud import texttospeech, storage
from phonemes_dict import phonemes

tts_client = texttospeech.TextToSpeechClient()
storage_client = storage.Client()

GCS_BUCKET_NAME = 'spell-pron-trainer'
AUDIO_PREFIX = 'word_audio'

voice = texttospeech.VoiceSelectionParams(
    language_code='en-GB',
    ssml_gender=texttospeech.SsmlVoiceGender.MALE,
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
)

bucket = storage_client.bucket(GCS_BUCKET_NAME)


def collect_all_words() -> list[str]:
    """Collect all unique words that need audio across all phonemes."""
    words = set()

    for phoneme_data in phonemes.values():
        # Phoneme pronunciation word (e.g. 'or', 'er', 'air', 'e')
        words.add(phoneme_data['api'].lower())

        # Pattern example words
        for pattern_words in phoneme_data['patterns'].values():
            for word in pattern_words:
                words.add(word.lower())

        # Spelling: first word of each tuple (correct answer)
        for options in phoneme_data['spelling'].values():
            words.add(options[0].lower())

        # Homophones: all words in each set
        for homoph_set in phoneme_data['homophones'].values():
            for word in homoph_set:
                words.add(word.lower())

    return sorted(words)


def generate_and_upload(word: str) -> None:
    """Generate TTS audio for a word and upload to GCS."""
    filename = f'{AUDIO_PREFIX}/{word}.mp3'
    blob = bucket.blob(filename)

    # Skip if already exists
    if blob.exists():
        print(f'  Skipping "{word}" (already exists)')
        return

    synthesis_input = texttospeech.SynthesisInput(text=word)

    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )

    blob.upload_from_string(response.audio_content, content_type='audio/mpeg')
    print(f'  Uploaded: {word} -> {filename}')


if __name__ == '__main__':
    words = collect_all_words()
    print(f'Found {len(words)} unique words to generate audio for.\n')

    for i, word in enumerate(words, 1):
        print(f'[{i}/{len(words)}] Generating: "{word}"')
        generate_and_upload(word)

    print(f'\nDone! {len(words)} audio files cached in GCS ({AUDIO_PREFIX}/).')
