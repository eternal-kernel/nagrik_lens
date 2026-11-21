# Nagrik Lens (నాగరిక్ లెన్స్ / नागरिक लेंस)

> **Understand Candidate Affidavits — Not Political Spin.**
>
> A non-partisan, source-linked, multilingual civic transparency platform for Election Commission of India (ECI) **Form 26** candidate affidavits.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Our Solution](#2-our-solution)
3. [Core Civic Neutrality & Anti-Hallucination Rules](#3-core-civic-neutrality--anti-hallucination-rules)
4. [Key Features](#4-key-features-phases-03-complete)
5. [Tech Stack & Monorepo Architecture](#5-tech-stack--monorepo-architecture)
6. [Local Installation & Execution](#6-step-by-step-local-installation--execution)
7. [2-Minute Judge Demo Walkthrough](#7-2-minute-judge-demo-walkthrough)
8. [Why We Use Fictional Fixtures](#8-why-this-public-repo-uses-fictional-fixtures)
9. [Roadmap](#9-roadmap--phase-4-production-launch)
10. [License](#10-license)

---

## 1. Problem Statement

During Indian elections, voters are surrounded by street campaign posters and partisan messaging, yet verifying a candidate's sworn legal, financial, and educational record remains practically inaccessible.

### Key Challenges

**1. High Friction**

Official Form 26 affidavits are distributed across government portals as multi-page, scanned, and sometimes handwritten PDFs, often obscured by notary stamps.

**2. Language & Legal Barriers**

Declarations contain dense statutory terminology such as:

- Cognizance taken
- Charges framed
- IPC/BNS sections
- Pending criminal proceedings

These disclosures are rarely presented in plain-language regional translations.

**3. AI Hallucination & Defamation Risk**

Blindly processing scanned election affidavits through generative AI can introduce serious factual errors, including:

- Misreading wrapped financial asset columns
- Hallucinating criminal records
- Misinterpreting monetary declarations
- Conflating pending allegations with convictions

**4. Personally Identifiable Information (PII) Exposure**

Raw Form 26 filings can contain sensitive personal information, including:

- Phone numbers
- Residential addresses
- PAN numbers
- Personal details of candidates and dependents

A responsible civic transparency platform must account for these privacy risks.

---

## 2. Our Solution

**Nagrik Lens** separates the workflow into two purpose-built portals, allowing citizens to access human-verified affidavit disclosures without navigating complex government websites.

### A. Public Citizen Application

**Routes:** `/` and `/scan`

Citizens can:

- Search for election candidates.
- Scan street campaign posters using a camera.
- Upload poster images to identify candidates.
- View verified Form 26 disclosures.
- Switch between English, Telugu (తెలుగు), and Hindi (हिन्दी).
- Listen to explanations using browser-based speech synthesis.
- Inspect the original affidavit PDF pages supporting each disclosure.

The platform presents candidate-declared information without assigning political judgments, scores, or rankings.

### B. Reviewer Console

**Route:** `/admin/review`

Authorized civic reviewers can:

- Upload official Form 26 affidavit PDFs.
- Extract structured information from digital and scanned documents.
- Inspect extraction results alongside original source pages.
- Identify discrepancies between Part-A and Part-B declarations.
- Review and correct extracted disclosures.
- Approve individual disclosures for publication.
- Maintain an audit trail of review activity.

**Critical principle:** Automatically extracted information is never published without human verification.

---

## 3. Core Civic Neutrality & Anti-Hallucination Rules

Nagrik Lens is designed around five foundational safeguards.

### Rule 1: Zero LLM Calls in Production Explanations

Public explanations are generated deterministically from human-verified structured JSON data.

This avoids introducing generative AI hallucinations during public explanation rendering.

### Rule 2: Zero Evaluative Language

The platform does not label, score, or rank candidates using subjective terms such as:

- Clean
- Corrupt
- High risk
- Guilty

Nagrik Lens provides disclosures, not political recommendations.

### Rule 3: Explicit Attribution

Every disclosure is attributed to its source.

Example:

> Declared by the candidate in the Form 26 affidavit.

Where applicable, disclosures are attributed to the candidate's spouse or dependents.

### Rule 4: Allegations and Convictions Are Separate

Pending criminal cases are presented as allegations or proceedings awaiting judicial resolution.

They are never presented as proven convictions.

### Rule 5: Mandatory Human Verification

Automated extraction results default to:

`verification_status = "needs_review"`

Public API endpoints expose only disclosures satisfying:

`verification_status == "verified"`

This restriction is enforced at the database query level.

---

## 4. Key Features (Phases 0–3 Complete)

### 4.1 Privacy-First Campaign Poster Scanner

**Route:** `/scan`

The campaign poster scanner supports:

- Drag-and-drop image upload
- Standard file upload
- Live camera capture using `getUserMedia`
- Local Tesseract OCR
- Fuzzy candidate-name matching
- Indian honorific normalization
- Multi-candidate disambiguation
- Raw OCR output inspection

#### In-Memory Image Processing

Uploaded poster images are processed using Python `io.BytesIO`.

Images are not intentionally written to disk or logged during scanner processing.

#### Indian Name Matching

The matching pipeline handles common honorifics such as:

- Garu
- Ji
- Anna
- Sri

Distinctive-token gating helps reduce incorrect matches.

#### Multi-Candidate Disambiguation

Indian campaign posters frequently feature several political leaders.

Instead of assuming the most prominent name is the intended candidate, the scanner can present multiple matching candidates and allow the citizen to select one.

#### OCR Transparency

Users can expand the **Inspect Raw Extracted OCR Text** section to view the text returned by Tesseract.

This makes recognition results inspectable rather than hiding the OCR output.

### 4.2 Multilingual Source-Linked Affidavit Viewer

**Route:** `/candidates/[id]`

The affidavit viewer includes:

- English, Telugu, and Hindi explanations
- A synchronized PDF viewer
- Direct navigation to source PDF pages
- Browser-based text-to-speech
- Plain-language legal glossary explanations
- Human-verified candidate disclosures

#### Source Page Navigation

Each disclosure can include an **Inspect Source — Page X** action.

Selecting this action navigates the embedded PDF viewer to the corresponding affidavit page.

The PDF viewer uses `pdfjs-dist`.

#### Multilingual Explanations

Users can switch between:

- English
- తెలుగు
- हिन्दी

The explanation system uses deterministic templates and verified structured data.

#### Audio Accessibility

The **Listen** feature uses the browser's speech synthesis capabilities to read explanations aloud.

Audio availability and voice quality depend on browser and operating-system language support.

#### Legal Glossary

Contextual glossary elements explain procedural terminology without introducing political judgments.

### 4.3 Form 26 PDF Extraction Pipeline

The extraction pipeline uses a hybrid approach.

**Digital PDF extraction:**

`PyMuPDF (fitz)`

**Scanned document fallback:**

`Tesseract OCR (pytesseract)`

The pipeline also supports:

- Indian currency normalization
- Structured disclosure extraction
- PDF page references
- Part-A versus Part-B consistency checks
- Extraction anomaly detection

#### Indian Currency Normalization

The pipeline handles monetary representations such as:

- ₹
- Lacs
- Lakhs
- Cr.
- Crores

#### Consistency Checking

Form 26 includes detailed declarations and summary information.

The consistency checker flags numeric contradictions between Part-A and Part-B for human inspection.

**Important:** A detected discrepancy is a review flag, not proof of wrongdoing.

### 4.4 Human Review and Audit Trail

The reviewer console implements a publication approval workflow.

1. Extract disclosure information.
2. Assign `needs_review` status.
3. Display the source PDF page.
4. Allow a reviewer to inspect the extracted information.
5. Record reviewer notes.
6. Approve verified disclosures.
7. Publish only approved records.

The `review_events` audit log tracks automated extraction and human approval activity.

---

## 5. Tech Stack & Monorepo Architecture

### Backend

| Technology | Purpose |
|---|---|
| Python 3.11+ | Backend programming language |
| FastAPI | REST API framework |
| SQLAlchemy 2.x | Database ORM |
| SQLite | Local development database |
| PostgreSQL | Planned production database |
| Pydantic v2 | Data validation |
| PyMuPDF | Digital PDF extraction |
| Tesseract OCR | Scanned document and poster OCR |
| pytesseract | Python OCR integration |
| Pillow | Image processing |
| Pytest | Automated backend testing |

**Reported test status:** 36/36 backend tests passing.

### Frontend

| Technology | Purpose |
|---|---|
| Next.js 14 | React application framework |
| TypeScript | Type-safe frontend development |
| Tailwind CSS | UI styling |
| pdfjs-dist | Embedded affidavit PDF rendering |
| lucide-react | Interface icons |
| Web Speech API | Browser-based text-to-speech |
| getUserMedia | Live camera capture |

### Repository Structure

```text
nagrik_lens/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/v1/
│   │   │   │   └── Public, admin, PDF ingestion,
│   │   │   │       and poster scanning endpoints
│   │   │   ├── core/
│   │   │   │   └── Database engine and sessions
│   │   │   ├── models/
│   │   │   │   └── ECI Form 26 SQLAlchemy models
│   │   │   ├── schemas/
│   │   │   │   └── Pydantic validation schemas
│   │   │   └── services/
│   │   │       └── Explanation engine,
│   │   │           PDF pipeline, and OCR matcher
│   │   ├── scripts/
│   │   │   └── Synthetic fixture generators
│   │   │       and database seeder
│   │   ├── tests/
│   │   │   └── Automated backend tests
│   │   └── requirements.txt
│   │
│   └── web/
│       ├── app/
│       │   └── Landing, scanner, candidate,
│       │       and reviewer pages
│       ├── components/
│       │   └── PDF viewer, voice player,
│       │       glossary, and navbar
│       ├── lib/
│       │   └── Language context and API client
│       └── messages/
│           ├── en.json
│           ├── te.json
│           └── hi.json
│
├── data/
│   └── glossary/
│       └── Verified legal glossary JSON
│
└── fixtures/
    └── fictional/
        └── Synthetic Form 26 PDFs
            and campaign poster PNGs
```

---

## 6. Step-by-Step Local Installation & Execution

This section explains how to run Nagrik Lens locally for development, evaluation, or hackathon judging.

### Prerequisites

Ensure the following software is installed.

**1. Python 3.11 or newer**

Check your installation:

```bash
python3 --version
```

**2. Node.js 18+ and npm**

Check your installation:

```bash
node -v
npm -v
```

**3. Tesseract OCR**

Tesseract is required for:

- Scanned PDF extraction fallback
- Campaign poster OCR
- Candidate name recognition from images

#### macOS

Using Homebrew:

```bash
brew install tesseract
```

#### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### Windows

Install Tesseract using the UB Mannheim Windows distribution.

Ensure the Tesseract executable directory is included in the system `PATH`.

Verify installation:

```bash
tesseract --version
```

### Step 1: Clone the Repository

Open a terminal and run:

```bash
git clone https://github.com/eternal-kernel/nagrik_lens.git
cd nagrik_lens
```

All subsequent backend commands assume that you are in the repository root directory.

### Step 2: Set Up the Backend

**Terminal 1 — Backend**

#### 2.1 Create a Python Virtual Environment

On macOS or Linux:

```bash
python3 -m venv apps/api/.venv
```

Activate the environment:

```bash
source apps/api/.venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv apps/api/.venv
apps\api\.venv\Scripts\Activate.ps1
```

#### 2.2 Install Backend Dependencies

```bash
pip install -r apps/api/requirements.txt
```

#### 2.3 Seed the Local Database

The repository includes fictional candidate data for safe testing.

On macOS or Linux:

```bash
PYTHONPATH=apps/api python apps/api/scripts/seed_fictional.py
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="apps/api"
python apps/api/scripts/seed_fictional.py
```

This initializes the local SQLite database with three fictional candidates and their associated Form 26 fixtures.

#### 2.4 Start the FastAPI Server

On macOS or Linux:

```bash
PYTHONPATH=apps/api uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell, after setting `PYTHONPATH`:

```powershell
uvicorn app.main:app --reload --port 8000
```

The backend should now be accessible at:

**Backend:** http://localhost:8000

**Health Check:** http://localhost:8000/health

**Interactive API Documentation:** http://localhost:8000/docs

Keep this terminal running.

### Step 3: Set Up the Frontend

**Terminal 2 — Frontend**

Open a second terminal in the repository root.

#### 3.1 Navigate to the Frontend

```bash
cd apps/web
```

#### 3.2 Install Node Dependencies

```bash
npm install
```

#### 3.3 Start the Development Server

```bash
npm run dev
```

Open the application in your browser:

**http://localhost:3000**

The frontend and backend must both be running for the full application workflow.

### Step 4: Run Automated Verification Suites

#### Backend Tests

From the repository root on macOS or Linux:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/pytest -v apps/api/tests
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="apps/api"
apps\api\.venv\Scripts\python.exe -m pytest -v apps/api/tests
```

The backend test suite contains 36 isolated tests, according to the supplied project documentation.

These tests are designed not to mutate the local `nagrik_lens.db` database.

#### Frontend Production Build

From the repository root:

```bash
cd apps/web
npm run build
```

This validates the frontend production build, including its TypeScript compilation checks.

---

## 7. 2-Minute Judge Demo Walkthrough

This walkthrough demonstrates the three major capabilities of Nagrik Lens:

1. Campaign poster recognition
2. Multilingual, source-linked affidavit explanations
3. Human verification before publication

### Demo A: Campaign Poster Scanner

**Route:** http://localhost:3000/scan

**Step 1:** Open the scanner page.

**Step 2:** Upload the provided fictional campaign poster:

```text
fixtures/fictional/poster_multi_candidate.png
```

Alternatively, select **Scan with Camera** to test live camera capture.

**Step 3:** Observe the candidate matching results.

The multi-candidate example contains:

- Kiran Rao
- Ananya Sharma

The application presents a candidate disambiguation picker rather than assuming which individual the voter wants to inspect.

**Step 4:** Expand:

**Inspect Raw Extracted OCR Text**

This displays the text extracted by Tesseract.

**What this demonstrates:**

- Poster-based candidate discovery
- Local OCR processing
- Multi-candidate handling
- Transparent OCR output
- In-memory image processing

### Demo B: Multilingual Source-Linked Affidavit Viewer

**Route:** http://localhost:3000/candidates/1

**Step 1:** Open Candidate 1.

The seeded example initially contains six publicly verified disclosures.

A seventh disclosure, **Spouse Movable Assets**, remains in `needs_review` status and is hidden from the public view.

**Step 2:** Switch languages using the top navigation bar.

Test:

- English
- తెలుగు
- हिन्दी

**Step 3:** Select **Listen** to test browser-based audio playback.

**Step 4:** Select:

**Inspect Source — Page 4**

The PDF viewer navigates to the source page containing the relevant criminal case declaration.

**What this demonstrates:**

- Human-verified disclosure filtering
- Multilingual explanations
- Audio accessibility
- Direct source verification
- Clear separation of legal allegations and convictions

### Demo C: Human Verification Gate

**Route:** http://localhost:3000/admin/review

**Step 1:** Open the Reviewer Console.

For the local development demonstration, use the pre-filled development key:

```text
dev-secret-key
```

**Important:** This is a local demonstration credential and must not be used as a production authentication secret.

**Step 2:** Load:

```text
Affidavit #1
```

**Step 3:** Select:

```text
Disclosure #3 — Spouse Movable Assets
```

The source PDF viewer automatically navigates to Page 2.

**Step 4:** Inspect the source document and enter a review note.

**Step 5:** Click:

**Verify & Publish**

**Step 6:** Return to:

http://localhost:3000/candidates/1

The public viewer should now display seven verified disclosures instead of six.

The newly approved disclosure becomes available across all three supported languages.

**What this demonstrates:**

- Human-in-the-loop verification
- Source-linked reviewer workflow
- Disclosure-level approval
- Audit logging
- Publication status enforcement
- Immediate availability of verified information

---

## 8. Why This Public Repo Uses Fictional Fixtures

The public repository intentionally uses fictional candidates and synthetic affidavit documents.

This design decision supports privacy, reproducibility, and responsible testing.

### Real-World Benchmarking Observations

During local benchmarking against scanned Telangana Form 26 affidavits, two important challenges were identified.

#### 1. Unredacted Personal Information

Real affidavits can expose sensitive information such as:

- Mobile numbers
- Residential addresses
- PAN numbers
- Personal details of dependents

Some of these details appear on the first pages of official filings.

#### 2. OCR Hazards and Filing Inconsistencies

Real scanned affidavits may contain:

- Overlapping notary stamps
- Handwritten entries
- Skewed or rotated pages
- Poor-quality scans
- Complex financial tables
- Numeric inconsistencies between Part-A and Part-B

Some benchmarked filings contained apparent 100× numerical discrepancies.

These observations reinforce the importance of source inspection and mandatory human verification.

### Public Repository Safety

The public repository includes fictional test assets under:

```text
fixtures/fictional/
```

The fictional fixture collection contains:

- Three synthetic Form 26 PDFs
- Two synthetic campaign poster PNGs

The following sensitive or machine-local paths are excluded from version control:

```gitignore
fixtures/real_private/
uploads/
*.db
```

**Important:** The public repository's fictional fixtures do not imply that real candidate affidavits are safe to publish without privacy review.

---

## 9. Roadmap — Phase 4 (Production Launch)

The following capabilities are planned for future development.

### Privacy and Document Safety

- [ ] **Visual PII Redaction Overlay**

  Render `redaction_boxes` masks over sensitive information such as phone numbers, residential addresses, and PAN fields before displaying real affidavit PDFs publicly.

### Legal Explanation Coverage

- [ ] **Expanded Legal Glossary**

  Add reviewed plain-language explanations for additional IPC/BNS provisions and special legislation, including:

  - IPC 120B
  - MCOCA
  - Charges framed
  - Additional procedural terminology

### OCR Improvements

- [ ] **Automatic Image Rotation Fallback**

  Retry OCR processing after rotating sideways poster images by 90° or 270° when appropriate.

### Production Infrastructure

- [ ] **PostgreSQL Migration**

  Migrate the application from local SQLite storage to managed PostgreSQL.

- [ ] **Live Pilot Constituency**

  Publish human-verified Form 26 disclosures for a real pilot constituency after implementing the required privacy safeguards.

---

## 10. License

This project is distributed under the **MIT License**.

See the [LICENSE](LICENSE) file for details.

---

**Nagrik Lens — Understand Candidate Affidavits. Not Political Spin.**

*Built to make public election disclosures easier to understand, verify, and access across languages.*

**Repository:** https://github.com/eternal-kernel/nagrik_lens
