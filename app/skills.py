"""Skill vocabulary and extraction.

A deterministic, explainable skill extractor: each canonical skill has a list of
aliases matched with word boundaries. Used for (1) the skill-coverage part of the
match score, (2) explaining a match (matched / missing skills) and (3) the
anti-hallucination guard on generated documents.
"""
from __future__ import annotations

import re
from functools import lru_cache

# canonical name -> (category, [aliases])
SKILLS: dict[str, tuple[str, list[str]]] = {
    # Programming & data
    "Python": ("Tech", ["python", "pandas", "numpy"]),
    "R": ("Tech", ["rstudio"]),  # special-cased in extract_skills
    "SQL": ("Tech", ["sql", "postgresql", "mysql", "sqlite", "bigquery"]),
    "Java": ("Tech", [r"java(?!script)"]),
    "JavaScript": ("Tech", ["javascript", "typescript", "node.js", "nodejs"]),
    "React": ("Tech", ["react", "react.js", "reactjs"]),
    "C++": ("Tech", [r"c\+\+"]),
    "Git": ("Tech", ["git", "github", "gitlab"]),
    "Docker": ("Tech", ["docker", "kubernetes", "containers"]),
    "Cloud": ("Tech", ["aws", "azure", "gcp", "google cloud", "cloud computing"]),
    "APIs": ("Tech", ["api", "apis", "rest api", "fastapi", "flask"]),
    "Linux": ("Tech", ["linux", "bash", "shell scripting"]),
    "Spark": ("Tech", ["spark", "pyspark", "hadoop", "databricks"]),
    # Data science / AI
    "Machine Learning": ("Data & AI", ["machine learning", "ml models?", "scikit-learn", "sklearn", "xgboost", "random forest"]),
    "Deep Learning": ("Data & AI", ["deep learning", "neural networks?", "pytorch", "tensorflow", "keras", "cnn", "transformers?"]),
    "NLP": ("Data & AI", ["nlp", "natural language processing", "text mining", "llms?", "large language models?", "rag"]),
    "Computer Vision": ("Data & AI", ["computer vision", "image recognition", "object detection", "opencv"]),
    "Statistics": ("Data & AI", ["statistics", "statistical", "econometrics", "hypothesis testing", "regression", "a/b test(?:ing|s)?"]),
    "Data Analysis": ("Data & AI", ["data analysis", "data analytics", "analytics", "data-driven", "data analyst"]),
    "Data Visualization": ("Data & AI", ["data visuali[sz]ation", "dashboards?", "matplotlib", "plotly", "seaborn"]),
    "Power BI": ("Data & AI", ["power bi", "powerbi"]),
    "Tableau": ("Data & AI", ["tableau"]),
    "Excel": ("Data & AI", ["excel", "spreadsheets?", "vba", "pivot tables?"]),
    "Generative AI": ("Data & AI", ["generative ai", "genai", "prompt engineering", "chatgpt", "hugging ?face"]),
    "Data Engineering": ("Data & AI", ["data engineering", "etl", "data pipelines?", "airflow", "dbt"]),
    # Business
    "Financial Analysis": ("Business", ["financial analysis", "financial modell?ing", "valuation", "dcf", "financial statements"]),
    "Accounting": ("Business", ["accounting", "audit", "ifrs", "bookkeeping"]),
    "Corporate Finance": ("Business", ["corporate finance", "m&a", "mergers and acquisitions", "private equity", "investment banking"]),
    "Market Research": ("Business", ["market research", "market analysis", "competitive analysis", "benchmark(?:ing)?", "market stud(?:y|ies)"]),
    "Strategy": ("Business", ["strategy", "strategic", "business plan", "go-to-market", "consulting"]),
    "Project Management": ("Business", ["project management", "project manager", "agile", "scrum", "kanban", "jira", "planning"]),
    "Product Management": ("Business", ["product management", "product manager", "product owner", "roadmap", "user stories"]),
    "Business Development": ("Business", ["business development", "lead generation", "prospecting", "partnerships"]),
    "Sales": ("Business", ["sales (?:assistant|representative|team|internship|intern|skills|experience)", "selling", "b2b sales", "account management", "crm"]),
    "Supply Chain": ("Business", ["supply chain", "logistics", "procurement", "purchasing", "inventory"]),
    "Operations": ("Business", ["operations", "process improvement", "lean", "six sigma"]),
    "HR": ("Business", ["human resources", r"\bhr\b", "recruitment", "talent acquisition"]),
    "Sustainability": ("Business", ["sustainability", "csr", "esg", "carbon footprint", "climate"]),
    # Marketing & communication
    "Digital Marketing": ("Marketing", ["digital marketing", "online marketing", "growth marketing", "performance marketing"]),
    "SEO": ("Marketing", ["seo", "sea", "search engine optimi[sz]ation", "google ads"]),
    "Social Media": ("Marketing", ["social media", "instagram", "tiktok", r"linkedin(?!\.com)", "community management"]),
    "Content Creation": ("Marketing", ["content creation", "copywriting", "content marketing", "storytelling", "blog"]),
    "Brand Management": ("Marketing", ["brand management", "branding", "brand strategy", "marketing campaigns?"]),
    "Google Analytics": ("Marketing", ["google analytics", "ga4", "web analytics"]),
    "Design": ("Marketing", ["figma", "canva", "adobe", "photoshop", "illustrator", "ui/ux", "ux design", "ui design"]),
    "Communication": ("Marketing", ["communication", "public relations", "press relations", "events?"]),
    # Soft skills
    "Teamwork": ("Soft skills", ["teamwork", "team player", "collaborat(?:ion|ive|ed|ing)", "cross-functional"]),
    "Leadership": ("Soft skills", ["leadership", "led a team", "team lead", "managed a team", "president", "captain"]),
    "Problem Solving": ("Soft skills", ["problem[- ]solving", "analytical skills", "critical thinking"]),
    "Presentation": ("Soft skills", ["presentation skills?", "public speaking", "pitch(?:ed|ing)?", "presented"]),
    "Autonomy": ("Soft skills", ["autonom(?:y|ous)", "self-starter", "independent(?:ly)?", "proactive"]),
    # Languages
    "English": ("Languages", ["english", "toeic", "toefl", "ielts"]),
    "French": ("Languages", ["french", "français"]),
    "Spanish": ("Languages", ["spanish", "español"]),
    "German": ("Languages", ["german", "deutsch"]),
    "Italian": ("Languages", ["italian"]),
    "Chinese": ("Languages", ["chinese", "mandarin"]),
    "Arabic": ("Languages", ["arabic"]),
}


@lru_cache(maxsize=None)
def _patterns() -> dict[str, re.Pattern]:
    compiled = {}
    for name, (_, aliases) in SKILLS.items():
        parts = []
        for a in aliases:
            # aliases that already contain regex word logic are used as-is
            if a.startswith(r"\b") or "(?" in a:
                parts.append(a)
            else:
                parts.append(r"(?<![\w+#])" + a + r"(?![\w+#])")
        compiled[name] = re.compile("|".join(parts), re.IGNORECASE)
    return compiled


def extract_skills(text: str) -> list[str]:
    """Return canonical skills found in `text`, in vocabulary order."""
    if not text:
        return []
    found = []
    for name, pat in _patterns().items():
        if name == "R":
            # 'R' is too ambiguous: only case-sensitive matches
            if re.search(r"\bR\b(?= ?(?:language|studio|programming|,|/))|RStudio", text):
                found.append(name)
            continue
        if pat.search(text):
            found.append(name)
    return found


def category(skill: str) -> str:
    return SKILLS.get(skill, ("Other", []))[0]
