"""The 8 known-answer questions (written from the pages BEFORE running search)
and the 3 out-of-corpus questions that must be refused."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldQuestion:
    number: int
    question: str
    gold_page_id: str
    gold_section: str
    answer_facts: tuple[str, ...]  # substrings that must co-occur in a hit chunk
    depends_on: str  # "table row", "code fence" or "prose"


GOLD_QUESTIONS = (
    GoldQuestion(
        1,
        "What are the type and default value of retry_backoff_ms on Client.send()?",
        "v3-client",
        "Client.send()",
        ("retry_backoff_ms", "int", "500"),
        "parameter table row",
    ),
    GoldQuestion(
        2,
        "Which exception does the SDK raise on HTTP 429 and what attribute carries the wait time?",
        "v3-errors",
        "RateLimitError",
        ("RateLimitError", "retry_after_seconds"),
        "table row + prose",
    ),
    GoldQuestion(
        3,
        "What is the maximum file size accepted by uploads in v3?",
        "v3-files",
        "Upload parameters",
        ("max_file_size_mb", "25"),
        "parameter table row",
    ),
    GoldQuestion(
        4,
        "How do I verify a webhook signature in v3?",
        "v3-webhooks",
        "Signature verification",
        ("verify_signature", "X-Acme-Signature"),
        "code fence",
    ),
    GoldQuestion(
        5,
        "What is the default buffer_size_ms for streaming?",
        "v3-streaming",
        "Client.stream()",
        ("buffer_size_ms", "250"),
        "parameter table row",
    ),
    GoldQuestion(
        6,
        "How many requests per minute does the free tier allow?",
        "v3-ratelimits",
        "Limit tiers",
        ("Free", "60"),
        "parameter table row",
    ),
    GoldQuestion(
        7,
        "How do I disable automatic retries when creating the client?",
        "v3-client",
        "Client constructor parameters",
        ("max_retries=0",),
        "prose under table",
    ),
    GoldQuestion(
        8,
        "Which environment variable holds the API token?",
        "v3-client",
        "Authentication",
        ("ACME_API_TOKEN",),
        "prose + code fence",
    ),
)


@dataclass(frozen=True)
class RefusalCase:
    question: str
    why_unanswerable: str


REFUSAL_CASES = (
    RefusalCase(
        "How do I rotate my account password with the SDK?",
        "Password management is documented nowhere in the corpus.",
    ),
    RefusalCase(
        "Does the SDK publish events to Kafka for stream processing?",
        "Kafka integration appears nowhere in the corpus.",
    ),
    RefusalCase(
        "How do I install the SDK with pip?",
        "Installation instructions are not part of any indexed page.",
    ),
)
