from enum import Enum


class SourceMethod(str, Enum):
    api = "api"
    scrape = "scrape"
    llm = "llm"
    inferred = "inferred"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    needs_disambiguation = "needs_disambiguation"
    completed = "completed"
    failed = "failed"

