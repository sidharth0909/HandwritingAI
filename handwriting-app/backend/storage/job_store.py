"""In-memory job and style storage for local development."""

jobs: dict = {}
styles: dict = {}


def set_job(job_id: str, data: dict) -> None:
    jobs[job_id] = data


def get_job(job_id: str) -> dict | None:
    return jobs.get(job_id)


def update_job(job_id: str, **kwargs) -> None:
    if job_id in jobs:
        jobs[job_id].update(kwargs)


def set_style(session_id: str, data: dict) -> None:
    styles[f"style:{session_id}"] = data


def get_style(session_id: str) -> dict | None:
    return styles.get(f"style:{session_id}")


def has_style(session_id: str) -> bool:
    return f"style:{session_id}" in styles
