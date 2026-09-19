# 3–5 minute walkthrough script

**0:00–0:30 — What it is**
“This is a Resume-to-Job-Description Fit Scorer. It accepts a job description and PDF/TXT resume, extracts criteria, scores each criterion, and returns weighted reasoning.”

**0:30–1:20 — Run it**
Start:
`uvicorn app.main:app --reload`
Open `/docs`. Paste a new job description and upload a resume. Show the JSON response: overall score, each criterion, evidence, reasoning, parser warning, LLM usage, and latency.

**1:20–2:10 — Calibration**
Show `samples/resume_a.txt` and `resume_b.txt`: they are identical and therefore should not diverge. Show `resume_c.txt`, which lacks the backend stack, and explain that it is intentionally different. Mention that a real calibration study needs a labeled dataset.

**2:10–3:10 — Code**
Open `app/scorer.py`. Point to `extract_criteria()` for the LLM JSON extraction, `score_one()` for per-criterion scoring, and `assess()` for the weighted sum. Then open `app/config.py` and show that weights are configuration.

**3:10–4:00 — Prompt**
Show `SCORE_PROMPT`. Explain that it explicitly forbids inferring missing experience and asks for evidence plus reasoning. Temperature is 0 and JSON output is requested for consistency.

**4:00–4:30 — Failure case**
Upload an invalid/scanned PDF. Show `parser_warning` rather than a crash or fabricated score. Mention LLM failure also falls back to deterministic scoring.

**4:30–5:00 — Limitations**
State that OCR and a large recruiter-labeled evaluation set are not finished. Explain those are the next production steps.
