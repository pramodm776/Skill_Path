"""Seed script to pre-populate demo job postings into the local SQLite database.

Run with:
    python -m backend.seed_jobs
"""

from __future__ import annotations

import sys
from backend.config import Settings
from backend.skills import extract_job_skills
from backend.storage import SQLiteStore


DEMO_JOBS = [
    {
        "title": "Python Cloud Backend Engineer",
        "company": "Nexus Cloud Systems",
        "source_url": "https://careers.nexuscloud.io/jobs/backend-python-fastapi",
        "description": (
            "We are looking for a Backend Engineer to build resilient microservices.\n"
            "Requirements:\n"
            "- Strong proficiency in Python and FastAPI for REST API development.\n"
            "- Hands-on experience with SQL databases (PostgreSQL/MySQL), schema design, and parameterized queries.\n"
            "- Commitment to automated testing with Pytest, unit tests, and CI/CD automation pipelines.\n"
            "- Experience with Docker containerization and clean backend architectures."
        ),
    },
    {
        "title": "Full-Stack Web Developer",
        "company": "Vanguard Digital Labs",
        "source_url": "https://vanguardlabs.example.org/careers/fullstack-developer",
        "description": (
            "Join our engineering team to build modern client-facing applications.\n"
            "Requirements:\n"
            "- Strong skills in React, TypeScript, and modern JavaScript (ES6+).\n"
            "- Experience designing and integrating RESTful API endpoints and frontend styling with HTML/CSS.\n"
            "- Knowledge of relational SQL databases and query optimization.\n"
            "- Dedication to automated testing (unit tests, integration tests) and version control with Git and GitHub."
        ),
    },
    {
        "title": "AI / Generative AI Engineer",
        "company": "Cognitive Horizon AI",
        "source_url": "https://cognitivehorizon.ai/jobs/generative-ai-engineer",
        "description": (
            "We are hiring an AI Engineer to build LLM-powered applications and agentic workflows.\n"
            "Requirements:\n"
            "- Deep experience in Python and machine learning frameworks (PyTorch or TensorFlow).\n"
            "- Hands-on implementation of Retrieval-Augmented Generation (RAG) and vector search with Chroma or FAISS.\n"
            "- Experience generating embeddings and integrating OpenAI API or open-source LLMs.\n"
            "- Building robust backend API development boundaries and automated tests."
        ),
    },
    {
        "title": "Systems Software Engineer",
        "company": "AeroLogic Systems",
        "source_url": "https://aerologic.example.com/careers/systems-engineer",
        "description": (
            "Seeking a Software Engineer to develop high-performance core services.\n"
            "Requirements:\n"
            "- Strong core foundation in Java and C++ programming.\n"
            "- Solid understanding of SQL databases, transactions, and relational data modeling.\n"
            "- Rigorous automated testing and continuous integration with Git and GitHub workflows."
        ),
    },
]


def seed_database(store: SQLiteStore | None = None) -> int:
    settings = Settings.from_env()
    store = store or SQLiteStore(settings.database_path)
    existing_titles = {j["title"] for j in store.list_jobs()}
    added = 0
    for job in DEMO_JOBS:
        if job["title"] not in existing_titles:
            skills = extract_job_skills(job["description"])
            store.create_job(
                title=job["title"],
                company=job["company"],
                source_url=job["source_url"],
                description=job["description"],
                skills=skills,
            )
            added += 1
            print(f"  + Added: {job['title']} ({len(skills)} skills extracted)")
        else:
            print(f"  = Exists: {job['title']}")
    return added


def main() -> None:
    print("Seeding demo jobs into SkillPath AI database...")
    count = seed_database()
    print(f"Done! {count} new jobs seeded.")


if __name__ == "__main__":
    main()
