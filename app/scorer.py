import json
import re
import time

from google import genai

from .config import settings
from .schemas import Criterion, CriterionScore, FitResponse


CRITERION_PROMPT = """
You are a recruiting fit-analysis assistant.

Given a job description, extract exactly five criteria:
1. skills
2. experience
3. education
4. responsibilities
5. tools

Return ONLY valid JSON.

The criteria must use these names exactly:
skills, experience, education, responsibilities, tools.

Use the following configured weights:
- skills: 0.40
- experience: 0.20
- education: 0.15
- responsibilities: 0.15
- tools: 0.10

The weights must sum to 1.0.

Required JSON structure:
{{
  "criteria": [
    {{
      "name": "skills",
      "requirement": "specific requirement from the job description",
      "weight": 0.40
    }},
    {{
      "name": "experience",
      "requirement": "specific requirement from the job description",
      "weight": 0.20
    }},
    {{
      "name": "education",
      "requirement": "specific requirement from the job description",
      "weight": 0.15
    }},
    {{
      "name": "responsibilities",
      "requirement": "specific requirement from the job description",
      "weight": 0.15
    }},
    {{
      "name": "tools",
      "requirement": "specific requirement from the job description",
      "weight": 0.10
    }}
  ]
}}
"""


SCORE_PROMPT = """
You are a recruiting fit-analysis assistant.

Score a resume against ONE job criterion.

Rules:
- Use only evidence explicitly present in the resume.
- Do not infer missing experience.
- Do not reward a candidate simply because a generic word appears.
- Consider semantic relevance.
- Give a score from 0 to 100.
- Evidence must come directly from the resume.
- Keep the reasoning concise and factual.

Score meaning:
0 = no evidence
25 = weak evidence
50 = partial match
75 = good match
100 = strong/direct match

Return ONLY valid JSON in exactly this structure:
{{
  "score": 0,
  "evidence": "...",
  "reasoning": "..."
}}

JOB CRITERION:
{criterion}

JOB DESCRIPTION:
{jd}

RESUME:
{resume}
"""


def _client():
    """Create Gemini client when an API key is configured."""
    if not settings.api_key:
        return None

    return genai.Client(api_key=settings.api_key)


def _keyword_score(requirement: str, resume: str):
    """
    Deterministic fallback scorer used when Gemini is unavailable.
    """

    terms = [
        t.lower()
        for t in re.findall(
            r"[A-Za-z][A-Za-z0-9+#.-]{2,}",
            requirement,
        )
    ]

    terms = list(dict.fromkeys(terms))
    text = resume.lower()

    hits = [term for term in terms if term in text]

    ratio = len(hits) / max(1, len(terms))
    score = round(min(100, ratio * 100), 1)

    evidence = (
        ", ".join(hits[:8])
        if hits
        else "No matching terms found."
    )

    return (
        score,
        evidence,
        "Deterministic fallback based on requirement-term coverage.",
    )


def _generate(client, prompt):
    """Send a prompt to Gemini and return the generated text."""

    response = client.models.generate_content(
        model=settings.model,
        contents=prompt,
        config={
            "temperature": 0,
            "response_mime_type": "application/json",
        },
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    return response.text


def extract_criteria(jd: str):
    """
    Extract the five job criteria using Gemini.
    Falls back to deterministic criteria if Gemini fails.
    """

    client = _client()

    if not client:
        return _fallback_criteria(jd), False

    try:
        result = _generate(
            client,
            CRITERION_PROMPT
            + "\n\nJOB DESCRIPTION:\n"
            + jd,
        )

        data = json.loads(result)

        criteria = [
            Criterion(**item)
            for item in data["criteria"]
        ]

        expected_names = {
            "skills",
            "experience",
            "education",
            "responsibilities",
            "tools",
        }

        actual_names = {
            criterion.name
            for criterion in criteria
        }

        total_weight = sum(
            criterion.weight
            for criterion in criteria
        )

        if len(criteria) != 5:
            raise ValueError(
                "Gemini did not return exactly five criteria."
            )

        if actual_names != expected_names:
            raise ValueError(
                "Gemini returned invalid criterion names."
            )

        if abs(total_weight - 1.0) > 0.02:
            raise ValueError(
                f"Invalid criterion weights: {total_weight}"
            )

        return criteria, True

    except Exception as exc:
        print(
            "LLM criterion extraction failed: "
            f"{type(exc).__name__}: {exc}"
        )

        return _fallback_criteria(jd), False


def score_one(jd, resume, criterion, client):
    """
    Score one criterion using Gemini.
    Falls back to deterministic scoring when the LLM fails.
    """

    if not client:
        score, evidence, reasoning = _keyword_score(
            criterion.requirement,
            resume,
        )

        return (
            CriterionScore(
                criterion=criterion.name,
                weight=criterion.weight,
                score=score,
                evidence=evidence,
                reasoning=reasoning,
            ),
            False,
        )

    try:
        prompt = SCORE_PROMPT.format(
            criterion=criterion.requirement,
            jd=jd[:12000],
            resume=resume[:12000],
        )

        result = _generate(client, prompt)

        data = json.loads(result)

        score_value = float(data["score"])

        if not 0 <= score_value <= 100:
            raise ValueError(
                f"Invalid score returned by Gemini: {score_value}"
            )

        evidence = str(data["evidence"]).strip()
        reasoning = str(data["reasoning"]).strip()

        return (
            CriterionScore(
                criterion=criterion.name,
                weight=criterion.weight,
                score=score_value,
                evidence=evidence,
                reasoning=reasoning,
            ),
            True,
        )

    except Exception as exc:
        print(
            f"LLM scoring failed for {criterion.name}: "
            f"{type(exc).__name__}: {exc}"
        )

        score, evidence, reasoning = _keyword_score(
            criterion.requirement,
            resume,
        )

        return (
            CriterionScore(
                criterion=criterion.name,
                weight=criterion.weight,
                score=score,
                evidence=evidence,
                reasoning=(
                    reasoning
                    + " LLM call failed, so fallback scoring was used."
                ),
            ),
            False,
        )


def assess(
    jd: str,
    resume: str,
    parser_warning: str | None = None,
):
    """
    Main scoring pipeline.

    1. Extract criteria
    2. Score every criterion
    3. Calculate weighted overall score
    4. Return structured response
    """

    started = time.perf_counter()

    criteria, llm_extract = extract_criteria(jd)

    client = _client()

    scores = []
    used_flags = []

    for criterion in criteria:
        score, used = score_one(
            jd,
            resume,
            criterion,
            client,
        )

        scores.append(score)
        used_flags.append(used)

    overall = round(
        sum(
            item.score * item.weight
            for item in scores
        ),
        1,
    )

    if overall >= 75:
        verdict = "strong_fit"
    elif overall >= 50:
        verdict = "partial_fit"
    else:
        verdict = "weak_fit"

    return FitResponse(
        overall_score=overall,
        verdict=verdict,
        criteria=scores,
        parser_warning=parser_warning,
        llm_used=llm_extract or any(used_flags),
        latency_ms=round(
            (time.perf_counter() - started) * 1000,
            1,
        ),
    )


def _fallback_criteria(jd: str):
    """
    Fallback criteria used when Gemini is unavailable.
    Weights are read from configuration rather than hardcoded.
    """

    return [
        Criterion(
            name="skills",
            requirement=(
                "Technical skills explicitly required "
                "in the job description"
            ),
            weight=settings.weights["skills"],
        ),
        Criterion(
            name="experience",
            requirement=(
                "Relevant professional, internship, "
                "or project experience"
            ),
            weight=settings.weights["experience"],
        ),
        Criterion(
            name="education",
            requirement=(
                "Required degree or educational background"
            ),
            weight=settings.weights["education"],
        ),
        Criterion(
            name="responsibilities",
            requirement=(
                "Evidence of experience with the stated "
                "job responsibilities"
            ),
            weight=settings.weights["responsibilities"],
        ),
        Criterion(
            name="tools",
            requirement=(
                "Required tools, frameworks, platforms, "
                "or databases"
            ),
            weight=settings.weights["tools"],
        ),
    ]