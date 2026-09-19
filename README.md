# Resume to Job-Description Fit Scorer

Applied-AI take-home implementation using Python + FastAPI + Pydantic.

## What it does
- Accepts a job description plus a PDF/TXT resume.
- Extracts five weighted criteria using an LLM when `OPENAI_API_KEY` is available.
- Scores each criterion separately with evidence and reasoning.
- Produces a weighted overall score.
- Falls back to deterministic keyword coverage if the LLM is unavailable or fails.
- Handles unreadable/scanned PDFs with a clear parser warning instead of crashing.
- Keeps scoring weights in `app/config.py`, not inside the scoring formula.
- Includes tests and three calibration samples.

## Setup
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Put OPENAI_API_KEY in .env if you want LLM scoring.
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## API
`POST /score` — multipart form with:
- `job_description`: text
- `resume`: `.pdf` or `.txt`

`POST /score/text` — JSON:
```json
{"job_description":"...","resume_text":"..."}
```

`GET /health`

## Calibration
`tests/test_app.py` verifies the API and unreadable-PDF path. `samples/resume_a.txt` and `resume_b.txt` are intentionally identical: they should produce identical scores. `resume_c.txt` is a materially different profile and should score lower. This is a simple consistency check, not a statistical calibration study.

A production version should collect a labeled validation set and report pairwise score variance, correlation with recruiter labels, and threshold stability.

## Scoring design
Default weights:
- skills 40%
- experience 20%
- education 15%
- responsibilities 15%
- tools 10%

These are configuration values and can be changed without editing the scoring logic.

## LLM failure handling
LLM calls use temperature 0 and JSON output. Any API, JSON, or validation failure falls back to deterministic term-coverage scoring, so a transient model failure does not break the API.

## Parser failure handling
A malformed PDF or a PDF with too little extractable text returns a structured `parser_warning` and a safe zero-result response. It does not fabricate resume evidence.

## Known limitations
- Keyword fallback is intentionally simple and can miss synonyms.
- PDF extraction does not perform OCR on scanned documents.
- LLM extraction/scoring has not been validated against a large recruiter-labeled dataset.
- The demo has no authentication, database, or frontend because they were not required.
