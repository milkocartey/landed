"""Tailored CV + cover letter generation, with an anti-hallucination guard.

Design choices
* The tailored CV is built mostly *algorithmically* from the user's own CV:
  skills that the offer asks for are moved first, and inside each section the
  bullet points are re-ranked by semantic similarity to the offer. Only the short
  profile summary is written by the language model. This keeps the CV truthful.
* The cover letter is written by an open-source LLM running locally
  (default: Qwen/Qwen2.5-1.5B-Instruct via transformers, or any Ollama model).
  If no LLM is available, a structured template is used so the app still works.
* Guard: every skill mentioned in a generated text is checked against the skills
  found in the CV. Skills the candidate never claimed are flagged in the UI.
"""
from __future__ import annotations

import os
import re
import threading

import requests

from .matcher import similarities, offer_text
from .skills import extract_skills

LLM_BACKEND = os.getenv("LANDED_LLM", "auto")  # auto | transformers | ollama | template
HF_MODEL = os.getenv("LANDED_HF_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

_pipe = None
_lock = threading.Lock()
_active = None

SYSTEM = (
    "You are a careful career coach helping a student apply for an internship. "
    "You only use facts present in the candidate's CV. You NEVER invent experiences, "
    "degrees, tools, numbers or skills the candidate does not have. If the offer asks "
    "for something the candidate lacks, you may express motivation to learn it, but "
    "you never claim it. Write in clear, natural, professional English."
)


# --------------------------------------------------------------------------- LLM
def _try_ollama() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return r.ok
    except Exception:  # noqa: BLE001
        return False


def active_backend() -> str:
    global _active
    if _active:
        return _active
    choice = LLM_BACKEND
    if choice == "auto":
        if _try_ollama():
            choice = "ollama"
        else:
            try:
                import transformers  # noqa: F401
                import torch  # noqa: F401
                choice = "transformers"
            except Exception:  # noqa: BLE001
                choice = "template"
    _active = choice
    return _active


def _hf_generate(messages: list[dict], max_new_tokens: int) -> str:
    global _pipe
    with _lock:
        if _pipe is None:
            from transformers import pipeline
            import torch
            _pipe = pipeline("text-generation", model=HF_MODEL,
                             torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                             device_map="auto")
    # Greedy decoding (do_sample=False) is ~2× faster than sampling on CPU
    out = _pipe(messages, max_new_tokens=max_new_tokens, do_sample=False,
                return_full_text=False)
    gen = out[0]["generated_text"]
    if isinstance(gen, list):  # some transformers versions return the whole chat
        gen = gen[-1]["content"]
    return gen.strip()


def _ollama_generate(messages: list[dict], max_new_tokens: int) -> str:
    r = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": OLLAMA_MODEL, "messages": messages, "stream": False,
        "options": {"temperature": 0.6, "num_predict": max_new_tokens},
    }, timeout=300)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def llm(messages: list[dict], max_new_tokens: int = 450) -> str | None:
    global _active
    b = active_backend()
    try:
        if b == "ollama":
            return _ollama_generate(messages, max_new_tokens)
        if b == "transformers":
            return _hf_generate(messages, max_new_tokens)
    except Exception as e:  # noqa: BLE001
        print(f"[generator] LLM backend '{b}' failed ({e}); falling back to template")
        _active = "template"
    return None


# --------------------------------------------------------------------------- guard
LEARNING = re.compile(r"\b(learn|learning|develop my|discover|eager to|keen to|improve my|grow)\b", re.I)


def guard(text: str, cv_skills: list[str]) -> list[str]:
    """Skills claimed in `text` that the CV does not support.

    Sentences that only express a wish to learn ("eager to develop my Tableau skills")
    are not claims, so they are ignored.
    """
    allowed = set(cv_skills)
    flagged: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        if LEARNING.search(sentence):
            continue
        for s in extract_skills(sentence):
            if s not in allowed and s not in flagged:
                flagged.append(s)
    return flagged


# --------------------------------------------------------------------------- CV helpers
BULLET = "-•*–▪"


def _cv_for_prompt(cv: dict, max_chars: int = 900) -> str:
    """Extract the most useful CV text for a generation prompt (short summary + experience)."""
    parts: list[str] = []
    sections = cv.get("sections", {})
    if cv.get("name"):
        parts.append(cv["name"])
    for item in (sections.get("summary") or [])[:2]:
        parts.append(item)
    for item in (sections.get("experience") or [])[:14]:
        parts.append(item)
    result = "\n".join(parts)[:max_chars]
    return result or cv.get("raw_text", "")[:max_chars]


def _is_bullet(line: str) -> bool:
    return line[:1] in BULLET


def _rank_lines(lines: list[str], offer: str) -> list[str]:
    """Re-order bullet points by relevance to the offer, *inside* each block.

    A block = a heading line (job title, degree...) followed by its bullets, so a
    bullet never moves to another job. Blocks themselves keep their order
    (chronology matters on a CV).
    """
    if len(lines) < 2:
        return lines
    sims = similarities(offer, lines)
    blocks: list[list[int]] = []
    for i, line in enumerate(lines):
        if not _is_bullet(line) or not blocks:
            blocks.append([i])
        else:
            blocks[-1].append(i)
    out: list[str] = []
    for b in blocks:
        head, bullets = (b[:1], b[1:]) if not _is_bullet(lines[b[0]]) else ([], b)
        bullets = sorted(bullets, key=lambda i: -sims[i])
        out += [lines[i] for i in head + bullets]
    return out


def _bullets(cv: dict) -> list[str]:
    sec = cv.get("sections", {})
    return [l for l in sec.get("experience", []) + sec.get("projects", []) + sec.get("activities", [])
            if _is_bullet(l)]


def _template_cv(cv: dict, offer: dict, matched: list[str]) -> dict:
    """Template-only CV tailoring — no LLM call, used as fallback on timeout."""
    cv_skills = cv.get("skills", [])
    focus = ", ".join(matched[:4]) if matched else ", ".join(cv_skills[:4])
    summary = (f"Motivated student seeking a {offer.get('title', 'internship').lower()} position, "
               f"bringing hands-on experience in {focus}. Eager to contribute to "
               f"{offer.get('company', 'your team')} and keep learning in a demanding environment.")
    otext = offer_text(offer)
    sections = cv.get("sections", {})
    skills_first = [s for s in cv_skills if s in matched] + [s for s in cv_skills if s not in matched]
    order = ["experience", "projects", "education", "activities", "languages"]
    tailored_sections = {}
    for key in order + [k for k in sections if k not in order and k not in ("header", "skills", "summary")]:
        if key in sections and key not in ("header", "skills", "summary"):
            tailored_sections[key] = _rank_lines(sections[key], otext)
    return {
        "header": sections.get("header", [])[:4],
        "summary": summary,
        "skills": skills_first,
        "highlighted_skills": [s for s in skills_first if s in matched],
        "sections": tailored_sections,
        "flags": [],
    }


def tailor_cv(cv: dict, offer: dict, matched: list[str]) -> dict:
    otext = offer_text(offer)
    sections = cv.get("sections", {})
    cv_skills = cv.get("skills", [])

    # 1. summary written by the LLM (short, constrained)
    summary = None
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": (
            f"Write a 2-sentence CV profile summary (max 55 words) for this candidate, "
            f"targeted at the offer. Mention only skills from this list: {', '.join(matched or cv_skills[:6])}.\n\n"
            f"OFFER: {offer.get('title')} at {offer.get('company')}\n{offer.get('description', '')[:600]}\n\n"
            f"CV:\n{_cv_for_prompt(cv, 900)}\n\nReturn only the summary text.")},
    ]
    summary = llm(msgs, 80)
    if not summary:
        focus = ", ".join(matched[:4]) if matched else ", ".join(cv_skills[:4])
        summary = (f"Motivated student seeking a {offer.get('title', 'internship').lower()} position, "
                   f"bringing hands-on experience in {focus}. Eager to contribute to "
                   f"{offer.get('company', 'your team')} and to keep learning in a demanding environment.")
    summary = re.sub(r"^(summary|profile)\s*:\s*", "", summary.strip(), flags=re.I).strip('"')

    # 2. skills: offer-relevant first
    skills_first = [s for s in cv_skills if s in matched] + [s for s in cv_skills if s not in matched]

    # 3. sections: re-rank bullets by relevance to the offer
    order = ["experience", "projects", "education", "activities", "languages"]
    tailored_sections = {}
    for key in order + [k for k in sections if k not in order and k not in ("header", "skills", "summary")]:
        if key in sections and key not in ("header", "skills", "summary"):
            tailored_sections[key] = _rank_lines(sections[key], otext)

    return {
        "header": sections.get("header", [])[:4],
        "summary": summary,
        "skills": skills_first,
        "highlighted_skills": [s for s in skills_first if s in matched],
        "sections": tailored_sections,
        "flags": guard(summary, cv_skills),
    }


# --------------------------------------------------------------------------- letter
def cover_letter(cv: dict, offer: dict, matched: list[str], missing: list[str]) -> dict:
    name = cv.get("name") or "[Your name]"
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": (
            "Write a concise cover letter (180-240 words, 4 short paragraphs) for this internship.\n"
            "Paragraph 1: why this company and role. Paragraph 2 and 3: two concrete experiences "
            "from the CV that prove the matching skills. Paragraph 4: availability and polite closing.\n"
            f"Matching skills: {', '.join(matched) or 'none'}.\n"
            f"Skills NOT in CV (do not claim them): {', '.join(missing) or 'none'}.\n"
            f"Start with 'Dear Hiring Team,' and sign with '{name}'.\n\n"
            f"OFFER: {offer.get('title')} at {offer.get('company')}\n"
            f"{offer.get('description', '')[:500]}\n\nCV:\n{_cv_for_prompt(cv, 800)}")},
    ]
    text = llm(msgs, 300)
    used = "llm"
    if not text:
        used = "template"
        text = _template_letter(cv, offer, matched, missing)
    return {"text": text, "flags": guard(text, cv.get("skills", [])), "engine": used}


def _template_letter(cv: dict, offer: dict, matched: list[str], missing: list[str]) -> str:
    name = cv.get("name") or "[Your name]"
    title, company = offer.get("title", "internship"), offer.get("company", "your company")
    exp = _bullets(cv)
    proofs = []
    if exp:
        sims = similarities(offer_text(offer), exp)
        proofs = [exp[i].lstrip(BULLET + " ").rstrip(".") for i in sims.argsort()[::-1][:2]]
    irregular = {"built", "ran", "led", "wrote", "made", "won", "taught", "drove", "grew", "met", "sold"}

    def low(s: str) -> str:
        if not (len(s) > 1 and s[1].isupper()):  # keep acronyms such as "NLP"
            s = s[:1].lower() + s[1:]
        first = s.split()[0].lower() if s.split() else ""
        # "Built a dashboard" -> "built a dashboard"; "Customer churn prediction" -> "worked on customer..."
        return s if (first.endswith("ed") or first in irregular) else "worked on " + s

    skills = ", ".join(matched[:3]) if matched else "my academic background"
    p2 = (f"The experience most relevant to this role: I {low(proofs[0])}."
          if proofs else "My studies gave me a solid and practical foundation for this role.")
    p3 = (f"I also {low(proofs[1])}, which strengthened my skills in {skills}."
          if len(proofs) > 1 else f"These experiences strengthened my skills in {skills}.")
    learn = f" I am also eager to develop my {missing[0]} skills alongside your team." if missing else ""
    return (
        f"Dear Hiring Team,\n\n"
        f"I am writing to apply for the {title} position at {company}. The role matches what I want "
        f"to build in my career, and the chance to apply {skills} to real challenges at {company} "
        f"strongly motivates me.\n\n{p2}\n\n{p3}{learn}\n\n"
        f"I would be glad to discuss how I could contribute to your team. I am available for the "
        f"internship period you indicated and can share any further information.\n\n"
        f"Kind regards,\n{name}"
    )
