# Nagrik Lens (నాగరిక్ లెన్స్ / नागरिक लेंस)

> **Neutral, Source-Linked, Multilingual Indian Election Affidavit Verification Platform**

Nagrik Lens converts official Election Commission of India (ECI) **Form 26 sworn candidate affidavits** into plain-language, source-verified civic explanations in **English, Telugu, and Hindi**.

---

## Civic Neutrality & Grounding Rules

1. **Zero Evaluative Language:** Nagrik Lens never scores, ranks, or labels candidates (no "high", "low", "clean", "corrupt", or "guilty").
2. **Explicit Candidate Attribution:** Every point explicitly begins with *"Declared by the candidate in the Form 26 affidavit"* (or spouse/dependent).
3. **Allegation vs. Conviction Separation:** Pending criminal cases are strictly identified as unproven accusations awaiting trial under Indian law and are never conflated with convictions.
4. **Hard Publication Gate:** Public endpoints only return disclosures marked `verification_status == "verified"`. Disclosures marked `needs_review`, `draft`, or `rejected` are filtered directly at the database query level.
5. **Phase 1 Fictional Scope Notice:** Phase 1 uses **fictional sample fixtures** only ("Candidate X (Fictional Sample)" and synthetic Form 26 PDF). Automated OCR/ingestion of real ECI affidavits begins in Phase 2.

---

## Monorepo Architecture

```
nagrik-lens/
├── apps/
│   ├── api/                     # FastAPI backend + SQLAlchemy 2.x ORM
│   │   ├── app/
│   │   │   ├── api/v1/          # Public & Admin API endpoints
│   │   │   ├── core/            # SQLite engine & database session management
│   │   │   ├── models/          # ECI Form 26 normalized SQLAlchemy models
│   │   │   ├── schemas/         # Pydantic v2 validation & response models
│   │   │   └── services/        # Deterministic EN/TE/HI explanation engine
│   │   ├── scripts/             # PyMuPDF 2.x PDF generator & idempotent seeder
│   │   └── tests/               # 17 isolated integration tests (pytest)
│   └── web/                     # Next.js 14 App Router + Tailwind CSS frontend
│       ├── app/                 # Public Landing Page, Candidate Viewer, Review Console
│       ├── components/          # Canvas PDF Viewer (pdfjs-dist), Voice Player, Glossary Pills
│       ├── lib/                 # Language Context (EN/TE/HI) & Typed API Client
│       └── messages/            # Clean UI message dictionaries (en.json, te.json, hi.json)
├── data/
│   └── glossary/                # Open-source JSON legal glossary (IPC 143, 341, CrPC stages)
└── fixtures/
    └── fictional/               # 4-page synthetic Form 26 PDF fixture for Candidate X
```

---

## Quickstart (macOS)

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Backend Setup & Run

In the project root:

```bash
# 1. Create and activate virtual environment
/opt/homebrew/bin/python3.11 -m venv apps/api/.venv
source apps/api/.venv/bin/activate

# 2. Install backend dependencies
pip install -r apps/api/requirements.txt

# 3. Seed SQLite database and synthetic PDF fixture
python apps/api/scripts/seed_fictional.py

# 4. Start the FastAPI development server (runs on port 8000)
uvicorn app.main:app --app-dir apps/api --reload --port 8000
```

FastAPI OpenAPI documentation will be available at: `http://localhost:8000/docs`

### 2. Frontend Setup & Run

In a separate terminal tab:

```bash
# 1. Navigate to web directory
cd apps/web

# 2. Install frontend dependencies
npm install

# 3. Start Next.js development server (runs on port 3000)
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Running the Automated Test Suites

### Backend Test Suite (Pytest)
Runs 17 integration tests against an isolated temporary SQLite database without mutating `nagrik_lens.db`:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/pytest -v apps/api/tests
```

### Frontend Typecheck & Build (Next.js)
Verifies TypeScript validity, ESLint, and bundler compilation:

```bash
cd apps/web && npm run build
```

---

## 60-Second Demo Walkthrough: Verification Gate

This demonstration shows how the human-verification guardrail prevents unverified information from leaking into the public civic interface.

1. **Initial Public State (6 Disclosures):**
   - Open `http://localhost:3000/candidates/1`
   - Notice that **6 verified disclosures** appear (Education, Self Movable Assets, Agricultural Land, Liabilities, Pending Case, and Convictions).
   - Candidate X's **Spouse Movable Assets (₹3,20,000 on Page 2)** is marked `needs_review` in the database and is **strictly omitted** from the public page.
   - Switch languages between **English**, **తెలుగు**, and **हिन्दी** to view verified translations and click **"Listen"** to hear them read aloud.
   - Click **"Inspect Source — Page 4"** on the criminal case card to see the PDF viewer automatically scroll and focus on Page 4.

2. **Open the Reviewer Console (`/admin/review`):**
   - Click **"Reviewer Console"** in the top navigation bar (or visit `http://localhost:3000/admin/review`).
   - The development key is pre-filled as `dev-secret-key`. Click **"Load Affidavit #1"**.
   - Notice that Disclosure **#3 (Spouse Movable Assets)** appears at the top of the queue with an amber **Needs Review** badge.

3. **Verify and Publish:**
   - Select Disclosure #3. The left PDF viewer jumps to **Page 2** (Assets table).
   - Review the raw excerpt: `"Spouse Movable Assets: ₹3,20,000"`.
   - Enter a review note (e.g., *"Bank deposit schedules cross-verified against annexure"*).
   - Click the green **"Verify & Publish"** button. An audit event is logged.

4. **Observe the Public Update (7 Disclosures):**
   - Click the green banner link **"View Updated Public Affidavit View"** (or revisit `http://localhost:3000/candidates/1`).
   - **Spouse Movable Assets** is now published! Exactly **7 verified disclosures** appear across all three languages (`₹3.2 lakh` / `₹3.2 లక్షలు` / `₹3.2 लाख`).
