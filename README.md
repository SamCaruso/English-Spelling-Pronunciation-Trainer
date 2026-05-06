# English Pronunciation Trainer

A web app that helps learners master British English spelling and pronunciation, one phoneme at a time. Users learn IPA-based spelling patterns, complete AI-generated exercises, and practise distinguishing homophones — all with audio support.

**Live app:** [spell-pron-trainer on Cloud Run](https://spell-pron-trainer-1034759911844.europe-west2.run.app)

## How It Works

1. **Learn** — The app introduces a new phoneme with its most common spelling patterns and audio examples.
2. **Exercises** — Three difficulty levels test the user's understanding:
   - Level 1: Contextual IPA recognition (word replaced by IPA in a sentence)
   - Level 2: Wrong spelling recognition (spot the misspelled word)
   - Level 3: Standalone IPA recognition (no context)
3. **Homophones** — Users identify all valid spellings for words that sound the same.
4. **Review** — Mixed exercises across all previously studied phonemes.

Exercises at levels 1 and 2 are generated on-the-fly by GPT-4o, producing fresh sentences each session.

## AI Approach

The app uses a hybrid AI approach:

- All phonemes, spelling patterns, homophones, and accepted answers are manually curated in Python dictionaries.
- GPT-4o is used only to generate contextual exercises and sentence variations.
- The backend validates all answers and controls exercise flow and progression.
- AI generation is constrained to approved phoneme data to avoid hallucinated spellings or invalid exercises.

This balances the flexibility of generative AI with the consistency required for pronunciation training.

## Tech Stack

**Backend**
- Python / FastAPI
- OpenAI API (GPT-4o) for exercise generation
- Google Cloud Firestore for user progress and test state
- Google Cloud Text-to-Speech for audio generation (pre-cached)
- Firebase Authentication for user accounts

**Frontend**
- Vanilla HTML, CSS, JavaScript
- Firebase Auth SDK (client-side)

**Infrastructure**
- Google Cloud Run (containerised deployment)
- Google Cloud Storage (pre-cached audio files)
- Docker

## Project Structure

```
├── Backend/
│   ├── main.py              # FastAPI app and endpoints
│   ├── config.py            # Environment variable configuration
│   ├── auth.py              # Firebase token verification
│   ├── exercise_generator.py # OpenAI-powered exercise creation
│   ├── test_service.py      # Answer checking with Firestore
│   ├── user_service.py      # User progress management
│   ├── audio_service.py     # GCS audio URL construction
│   ├── logic.py             # Phoneme selection and pattern logic
│   ├── phonemes_dict.py     # Phoneme data (patterns, spellings, homophones)
│   ├── schemas.py           # Pydantic response models
│   ├── log_file.py          # Logging configuration
│   └── requirements.txt     # Python dependencies
├── Frontend/
│   ├── index.html           # Entry point
│   ├── main.js              # App logic and UI rendering
│   ├── fetch.js             # API client with error handling
│   └── style.css            # Styling
├── scripts/
│   └── audio_tts.py         # Offline script to generate and upload audio to GCS
├── Dockerfile
├── .dockerignore
└── .gitignore
```

## Running Locally

1. Create a `.env` file in `Backend/` with:
   ```
   OPENAI_API_KEY=your_openai_key
   GCS_BUCKET_NAME=your_bucket_name
   FIREBASE_API_KEY=your_firebase_api_key
   GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
   ```

2. Install dependencies:
   ```bash
   cd Backend
   pip install -r requirements.txt
   ```

3. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

4. Open `http://localhost:8000` in your browser.

## Deploying to Cloud Run

```bash
gcloud run deploy spell-pron-trainer \
  --source . \
  --set-env-vars="GCS_BUCKET_NAME=spell-pron-trainer,FIREBASE_API_KEY=your_key" \
  --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest" \
  --service-account="your-service-account@project.iam.gserviceaccount.com" \
  --allow-unauthenticated \
  --region=europe-west2 \
  --port=8080
```

## Audio Generation

Audio files are pre-generated using Google Cloud Text-to-Speech and stored in GCS. To regenerate:

```bash
cd scripts
python audio_tts.py
```

This generates MP3 files for all words in the phoneme dictionary and uploads them to the `word_audio/` folder in the GCS bucket. Existing files are skipped.
