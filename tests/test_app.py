from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

JD = "We need a Java developer with Java, Spring Boot, SQL, REST APIs, Git, and a bachelor's degree. The role involves building backend services, debugging production issues, and collaborating with developers."
RESUME = 'B.Tech Computer Science graduate. Built Spring Boot and Java REST APIs with MySQL. Used Git and SQL in projects. Completed a backend internship and worked on debugging API issues.'

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_text_scoring():
    r = client.post("/score/text", json={"job_description": JD, "resume_text": RESUME})
    assert r.status_code == 200
    data = r.json()
    assert 0 <= data["overall_score"] <= 100
    assert len(data["criteria"]) == 5

def test_unreadable_pdf_is_handled():
    r = client.post("/score", data={"job_description": JD},
                    files={"resume": ("scan.pdf", b"not-a-real-pdf", "application/pdf")})
    assert r.status_code == 200
    assert r.json()["parser_warning"]
