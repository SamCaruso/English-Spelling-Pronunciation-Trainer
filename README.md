# English Pronunciation Trainer

A web app that helps learners master British English spelling and pronunciation, one phoneme at a time. Users learn IPA-based spelling patterns, complete exercises with pre-generated sentences, and practise distinguishing homophones — all with audio support.

**Live app:** [spell-pron-trainer on Cloud Run](https://spell-pron-trainer-1034759911844.europe-west2.run.app)

## How It Works

1. **Learn** — The app introduces a new phoneme with its most common spelling patterns and clickable audio examples.
2. **Exercises** — Three difficulty levels test the user's understanding:
   - Level 1: Contextual IPA recognition (word replaced by IPA in a sentence)
   - Level 2: Wrong spelling recognition (spot the misspelled word)
   - Level 3: Standalone IPA recognition (no context)
3. **Homophones** — Users identify all valid spellings for words that sound the same.
4. **Review** — Mixed exercises across all previously studied phonemes.

## AI Approach

The app uses a hybrid AI approach:

- All phonemes, spelling patterns, homophones, and accepted answers are manually curated in Python dictionaries.
- GPT-4o is used **offline** to pre-generate exercise sentences, which are reviewed for quality before deployment.
- The backend validates all answers server-side and controls exercise flow and progression.
- AI generation is constrained to approved phoneme data to avoid hallucinated spellings or invalid exercises.
- No LLM calls happen at runtime — exercises are served from a pre-built Firestore pool, ensuring instant response times and zero API costs per session.

This balances the flexibility of generative AI with the consistency and speed required for production deployment.

## Tech Stack

**Backend**
- Python / FastAPI
- Google Cloud Firestore (user progress, test state, exercise pool)
- Firebase Authentication (user accounts)
- Structured JSON logging for Google Cloud Logging

**Frontend**
- Vanilla HTML, CSS, JavaScript (no framework, no build tools)
- Firebase Auth SDK (client-side)
- Google Cloud Storage (direct audio fetch from browser)

**Infrastructure**
- Google Cloud Run (containerised deployment)
- Google Cloud Storage (pre-cached TTS audio)
- Docker

**Offline Tooling**
- OpenAI GPT-4o (sentence generation — offline only)
- Google Cloud Text-to-Speech (audio generation — offline only)

## Project Structure

```
├── Backend/
│   ├── main.py               # FastAPI app and endpoints
│   ├── config.py             # Environment variable configuration
│   ├── auth.py               # Firebase token verification
│   ├── exercise_generator.py # Fetches exercises from Firestore pool
│   ├── test_service.py       # Answer checking with Firestore
│   ├── user_service.py       # User progress management
│   ├── logic.py              # Phoneme selection and pattern logic
│   ├── phonemes_dict.py      # Phoneme data (patterns, spellings, homophones)
│   ├── schemas.py            # Pydantic response models
│   ├── log_file.py           # JSON logging for Cloud Run
│   └── requirements.txt      # Python dependencies
├── Frontend/
│   ├── index.html            # Entry point (fetches Firebase config from backend)
│   ├── main.js               # App flow, auth, exercises, error handling
│   ├── dom-utils.js          # Reusable DOM rendering utilities
│   ├── fetch.js              # API client with error handling
│   └── style.css             # Styling
├── scripts/
│   ├── generate_pool_json.py     # Generate exercise sentences → local JSON
│   ├── upload_pool_to_firestore.py # Upload reviewed JSON → Firestore
│   └── audio_tts.py              # Generate and upload word audio to GCS
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
   GOOGLE_APPLICATION_CREDENTIALS=your-service-account.json
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
  --service-account="your-service-account@project.iam.gserviceaccount.com" \
  --allow-unauthenticated \
  --region=europe-west2 \
  --port=8080
```

No secrets needed at runtime — the deployed app reads only from Firestore and GCS.

## Content Pipeline

### Exercise Generation

Exercises are generated offline and reviewed before deployment:

```bash
cd Capstone_Deploy

# Step 1: Generate sentences via OpenAI → local JSON file
python scripts/generate_pool_json.py

# Step 2: Review and edit scripts/exercise_pool.json

# Step 3: Upload reviewed sentences to Firestore
python scripts/upload_pool_to_firestore.py --clear
```

### Audio Generation

Audio files are pre-generated using Google Cloud Text-to-Speech:

```bash
python scripts/audio_tts.py
```

This generates MP3 files for all words in the phoneme dictionary and uploads them to the `word_audio/` folder in the GCS bucket. Existing files are skipped.
