from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from pydantic import BaseModel, Field
from .parser import ResumeParser
from .scorer import assess

app = FastAPI(title="Resume to Job-Description Fit Scorer", version="1.0.0")
parser = ResumeParser()

class TextAssessRequest(BaseModel):
    job_description: str = Field(min_length=50, max_length=30000)
    resume_text: str = Field(min_length=40, max_length=30000)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/score/text")
def score_text(req: TextAssessRequest):
    return assess(req.job_description, req.resume_text)

@app.post("/score")
async def score(
    job_description: str = Form(..., min_length=50, max_length=30000),
    resume: UploadFile = File(...)
):
    if not resume.filename:
        raise HTTPException(400, "Resume filename is required.")
    if not resume.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(400, "Resume must be PDF or TXT.")
    content = await resume.read()
    text, warning = parser.extract(resume.filename, content)
    if not text:
        return {
            "overall_score": 0,
            "verdict": "weak_fit",
            "criteria": [],
            "parser_warning": warning or "Resume parser returned no text.",
            "llm_used": False,
            "latency_ms": 0,
        }
    return assess(job_description, text, warning)
