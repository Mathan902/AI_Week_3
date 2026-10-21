"""Week 11: fill week11/logs with two weeks of production traffic for the support drill.

    .venv/bin/python week11_traffic.py --n 700          # real requests through DocsAssistant on the live release

The repo has no real users, so the traffic is replayed: questions are drawn (seeded) from the Week 5 traffic
file, the Week 6 eval set, the Week 7 code-paste questions and the golden set; users follow a Zipf curve; event
times follow a weekday/office-hours curve over 2026-10-05..2026-10-20 UTC. Every request is a real pipeline
run (real retrieval, real LLM call, real tokens and cost). Only `ts` is assigned by the schedule instead of the
wall clock, and each such trace says so in `ts_source`.
"""
from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from week11_app import LIVE, LOG_DIR, DocsAssistant

ROOT = Path(__file__).parent
START = datetime(2026, 10, 5, tzinfo=timezone.utc)
DAYS = 16
SEED = 1111


def question_pool() -> list[str]:
    qs = [l.strip() for l in (ROOT / "week5" / "traffic_questions.txt").read_text().splitlines()
          if l.strip() and not l.startswith("#")]
    for f, key in (("week6/eval_set.jsonl", "question"), ("week7/questions.jsonl", "question"),
                   ("golden_set.jsonl", "question")):
        qs += [json.loads(l)[key] for l in (ROOT / f).read_text().splitlines() if l.strip()]
    return sorted(set(qs))


def schedule(n: int, rng: random.Random) -> list[datetime]:
    hour_w = [1, 1, 2, 4, 6, 8, 9, 9, 8, 9, 9, 8, 7, 6, 5, 4, 3, 2, 2, 1, 1, 1, 1, 1]  # UTC; IST + EU office hours
    slots, weights = [], []
    for d in range(DAYS):
        day = START + timedelta(days=d)
        for h in range(24):
            slots.append(day + timedelta(hours=h))
            weights.append(hour_w[h] * (1.0 if day.weekday() < 5 else 0.3))
    times = [rng.choices(slots, weights)[0] + timedelta(seconds=rng.randrange(3600)) for _ in range(n)]
    return sorted(times)


def plan(n: int) -> list[dict]:
    rng = random.Random(SEED)
    pool = question_pool()
    users = [f"u-{rng.randrange(16**4):04x}" for _ in range(45)]
    user_w = [1 / (i + 1) for i in range(len(users))]
    last: dict[str, tuple[datetime, str]] = {}
    jobs = []
    for ts in schedule(n, rng):
        user = rng.choices(users, user_w)[0]
        prev = last.get(user)
        session = prev[1] if prev and ts - prev[0] < timedelta(minutes=30) else f"s-{rng.randrange(16**8):08x}"
        last[user] = (ts, session)
        jobs.append({"question": rng.choice(pool), "user_id": user, "session_id": session,
                     "ts": ts.isoformat(timespec="seconds")})
    return jobs


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=700)
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    jobs = plan(a.n)
    bot = DocsAssistant(log_dir=LOG_DIR)
    done = 0

    def one(job: dict) -> str:
        t = bot.ask(job["question"], user_id=job["user_id"], session_id=job["session_id"], prompt_version=LIVE,
                    ts=job["ts"], extra={"ts_source": "traffic-replay"})
        return t["status"]

    with ThreadPoolExecutor(a.workers) as pool:
        for status in pool.map(one, jobs):
            done += 1
            if done % 50 == 0:
                print(f"{done}/{len(jobs)} last={status}", flush=True)
    for f in sorted(LOG_DIR.glob("requests-*.jsonl")):  # completion order -> event-time order within each day
        rows = sorted((json.loads(l) for l in f.read_text().splitlines() if l.strip()), key=lambda r: r["ts"])
        f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"wrote {len(jobs)} traces to {LOG_DIR}")


if __name__ == "__main__":
    main()
