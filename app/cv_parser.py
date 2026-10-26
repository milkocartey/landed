"""Read a CV (PDF, DOCX or TXT) and split it into sections."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

from .skills import extract_skills

SECTION_HEADINGS = {
    "summary": ["summary", "profile", "about me", "objective", "profil"],
    "education": ["education", "academic background", "formation", "studies"],
    "experience": ["experience", "experiences", "work experience", "professional experience",
                   "internships", "employment", "expérience professionnelle", "expériences"],
    "projects": ["projects", "academic projects", "personal projects", "projets"],
    "skills": ["skills", "technical skills", "competences", "compétences", "tools"],
    "languages": ["languages", "langues"],
    "activities": ["activities", "extracurricular", "associations", "interests", "hobbies",
                   "leadership", "volunteering", "centres d'intérêt"],
}


@dataclass
class ParsedCV:
    raw_text: str
    name: str = ""
    email: str = ""
    sections: dict[str, list[str]] = field(default_factory=dict)
    skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "email": self.email, "sections": self.sections,
                "skills": self.skills, "raw_text": self.raw_text}


def read_file(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in d.paragraphs)
    return data.decode("utf-8", errors="ignore")


def _heading_key(line: str) -> str | None:
    clean = re.sub(r"[^a-zA-Zéèàç' ]", "", line).strip().lower()
    if not clean or len(clean) > 40:
        return None
    for key, names in SECTION_HEADINGS.items():
        if clean in names:
            return key
    return None


def parse_cv(text: str) -> ParsedCV:
    text = text.replace("\r", "")
    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if l]
    cv = ParsedCV(raw_text="\n".join(lines))

    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    cv.email = m.group(0) if m else ""
    # name = first short line that is not contact info
    for l in lines[:5]:
        if "@" not in l and not re.search(r"\d{3}", l) and 1 < len(l.split()) <= 5:
            cv.name = l
            break

    current = "header"
    sections: dict[str, list[str]] = {"header": []}
    for l in lines:
        key = _heading_key(l)
        if key:
            current = key
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(l)
    cv.sections = {k: v for k, v in sections.items() if v}
    cv.skills = extract_skills(text)
    return cv
