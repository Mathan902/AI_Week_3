"""Week 6: one-command eval over 25 mode-tagged cases, with a judge that must earn trust.

    .venv/bin/python week6_eval.py                    # everything: answers, assertions, judge*, pass rate by mode
    .venv/bin/python week6_eval.py --judge v1         # pick the judge prompt (week6/judge_v1.txt | judge_v2.txt)
    .venv/bin/python week6_eval.py --judge none       # assertions only
    .venv/bin/python week6_eval.py sheet              # blind labelling sheet + empty labels_25.json
    .venv/bin/python week6_eval.py lock-labels        # freeze labels_25.json (sha256 + UTC time) BEFORE any judge run

* The judge refuses to run until labels_25.json is complete and locked, and the answers it grades
  are byte-identical to the answers that were labelled. That is the blind protocol, enforced in code.
  judge_v2 also refuses to run until week6/prediction.txt exists.

Deterministic assertions replace every judge criterion a parser or lookup can check. The judge keeps
exactly one binary criterion ("directly answers"), the same criterion the human labels use.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
W6 = ROOT / "week6"
EVAL_SET = W6 / "eval_set.jsonl"
LABELS = W6 / "labels_25.json"
LOCK = W6 / "labels_lock.json"
PREDICTION = W6 / "prediction.txt"
ANSWERS = W6 / "answers.json"
RUNS = W6 / "judge_runs"
JUDGE_MODEL = "haiku"

MODES = {  # names verbatim from week5/taxonomy.md
    "M1": "Code sample squashed onto one line or cut off mid-call",
    "M2": "Describes a v2-only API as current, no 'removed in v3' warning",
    "M3": "Quotes the sentence next to the fact instead of the fact",
    "M4": "Says 'I don't know' while a top-3 chunk states the answer",
    "M5": "Fetches chunks about a different topic, then says 'I don't know'",
    "M6": "Prints the same sentence twice in one answer",
}
CRITERION = "DIRECTLY ANSWERS"
REFUSAL_PREFIX = "I don't know"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(text: str | bytes) -> str:
    return hashlib.sha256(text if isinstance(text, bytes) else text.encode()).hexdigest()


def load_cases() -> list[dict]:
    return [json.loads(line) for line in EVAL_SET.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------- answers (the system under test)

def generate_answers(cases: list[dict]) -> dict[str, dict]:
    """Run the shipped pipeline (unchanged Week 5 system) on every case question."""
    from tracing import TracedAssistant

    trace_file = W6 / "eval_traces.jsonl"
    trace_file.unlink(missing_ok=True)
    bot = TracedAssistant(trace_file=trace_file)
    out = {}
    for case in cases:
        trace = bot.ask(case["question"], session=f"eval-{case['id']}")
        out[case["id"]] = {
            "trace_id": trace["trace_id"],
            "answer": trace["raw_output"],
            "retrieved": [{k: r[k] for k in ("rank", "chunk_id", "sdk_version", "final", "text")}
                          for r in trace["retrieved"]],
        }
    ANSWERS.write_text(json.dumps(out, indent=2))
    return out


def answers_fingerprint(answers: dict[str, dict]) -> str:
    return sha(json.dumps({cid: a["answer"] for cid, a in sorted(answers.items())}, sort_keys=True))


# ---------------------------------------------------------------- deterministic assertions

SPEC_PATHS = set(json.loads((W6 / "openapi_v3.json").read_text())["paths"])
DEPRECATIONS = json.loads((W6 / "deprecations.json").read_text())
MIGRATION_NOTE = re.compile(r"\b(removed|renamed|replaced|deprecated|is now|no longer|instead|in favou?r of)\b", re.I)
CITATION = re.compile(r"\s*\[chunk:([^\]]+)\]\s*$")
FENCE = re.compile(r"```[a-zA-Z]*[ \t]*\n?(.*?)```", re.S)
UNFENCED_CODE = re.compile(
    r"\bfrom acme[\w.]* import\b|\bimport acme\b|\bwith client\.\w+\(|\b\w+\s*=\s*client\.\w+\(|^\s*client\.\w+\(", re.M)
PATH = re.compile(r"/v\d+/[A-Za-z0-9_\-/{}]*[A-Za-z0-9_}]")


def split_answer(answer: str) -> tuple[str, str | None]:
    m = CITATION.search(answer)
    return (answer[:m.start()], m.group(1)) if m else (answer, None)


def check_code_parses(body: str) -> tuple[str, str]:
    blocks = FENCE.findall(body)
    outside = re.sub(r"`[^`\n]*`", "", FENCE.sub("", body))  # drop fences and inline `code` spans
    stray = UNFENCED_CODE.findall(outside)
    if not blocks and not stray:
        return "n/a", "no code"
    if stray:
        return "fail", f"code outside a fenced block: {stray[0]!r}"
    for block in blocks:
        if "\n" not in block.strip():
            return "fail", "fenced code is on a single line"
        try:
            ast.parse(block)
        except SyntaxError as exc:
            return "fail", f"SyntaxError: {exc.msg}"
    return "pass", f"{len(blocks)} block(s) parse"


def check_endpoints(body: str) -> tuple[str, str]:
    paths = PATH.findall(body)
    if not paths:
        return "n/a", "no endpoint paths"
    missing = sorted({p for p in paths if p not in SPEC_PATHS})
    return ("fail", f"not in openapi_v3.json: {missing}") if missing else ("pass", f"{sorted(set(paths))}")


def check_version_stated(body: str, case: dict) -> tuple[str, str]:
    need = case["state_versions"]
    if not need:
        return "n/a", "version-insensitive question"
    missing = [v for v in need if not re.search(rf"\b{v}\b", body, re.I)]
    return ("fail", f"answer text never says {missing}") if missing else ("pass", f"states {need}")


def check_deprecations(body: str) -> tuple[str, str]:
    hits = [d for d in DEPRECATIONS if re.search(d["pattern"], body)]
    if not hits:
        return "n/a", "no deprecated symbols"
    if MIGRATION_NOTE.search(body):
        return "pass", f"{[d['symbol'] for d in hits]} with migration note"
    return "fail", f"{[d['symbol'] for d in hits]} with no migration note (use {hits[0]['replacement']})"


def check_no_repetition(body: str, n: int = 8) -> tuple[str, str]:
    words = re.findall(r"[a-z0-9_]+", body.lower())
    grams = Counter(tuple(words[i:i + n]) for i in range(len(words) - n + 1))
    dup = [" ".join(g) + "..." for g, c in grams.items() if c > 1]
    sentences = [s.strip().rstrip(".!?").lower() for s in re.split(r"(?<=[.!?])\s+", body) if len(s.split()) >= 3]
    dup += [s for s, c in Counter(sentences).items() if c > 1]
    return ("fail", f"repeats: '{dup[0]}'") if dup else ("pass", "no repeated sentence or 8-word run")


def check_cited_version(citation: str | None, case: dict, refused: bool) -> tuple[str, str]:
    want = case["cite_version"]
    if not want or refused:
        return "n/a", "no version target" if not want else "refused"
    got = (citation or "").split("-", 1)[0]
    return ("pass", f"cites {got}") if got == want else ("fail", f"cites {got or 'nothing'}, question is {want}")


def check_answered(refused: bool, case: dict) -> tuple[str, str]:
    if case["expect"] == "answer":
        return ("fail", "refused an answerable question") if refused else ("pass", "answered")
    return ("pass", "refused") if refused else ("fail", "answered an unanswerable question")


def check_facts(body: str, case: dict, refused: bool) -> tuple[str, str]:
    if not case["must_include"]:
        return "n/a", "no facts"
    if refused:
        return "fail", "refused"
    missing = [p for p in case["must_include"] if not re.search(p, body, re.I)]
    return ("fail", f"missing /{missing[0]}/") if missing else ("pass", "all facts present")


ASSERTIONS = {  # name -> what it replaced in judge_v0_pre_split.txt
    "code_parses": "criterion 2 (code parses and runs)",
    "endpoints_in_spec": "criterion 3 (endpoint paths exist)",
    "version_stated": "criterion 4 (states the SDK version)",
    "deprecation_has_migration_note": "criterion 5 (deprecated symbol has migration note)",
    "no_repeated_sentence": "criterion 6 (no duplicated sentences)",
    "cites_question_version": "new: the cited chunk is from the version the question is about",
    "answered_when_answerable": "new: no refusal on a question the docs answer",
    "required_facts_present": "new: the case's expected fact(s) appear",
}


def run_assertions(case: dict, answer: str) -> dict[str, tuple[str, str]]:
    body, citation = split_answer(answer)
    refused = answer.startswith(REFUSAL_PREFIX)
    return {
        "code_parses": check_code_parses(body),
        "endpoints_in_spec": check_endpoints(body),
        "version_stated": check_version_stated(body, case) if not refused else ("n/a", "refused"),
        "deprecation_has_migration_note": check_deprecations(body),
        "no_repeated_sentence": check_no_repetition(body),
        "cites_question_version": check_cited_version(citation, case, refused),
        "answered_when_answerable": check_answered(refused, case),
        "required_facts_present": check_facts(body, case, refused),
    }


# ---------------------------------------------------------------- judge

def load_prompt(version: str) -> tuple[str, list[str]]:
    """Lines starting with '#!' are metadata for humans and are never sent to the model."""
    raw = (W6 / f"judge_{version}.txt").read_text()
    fewshot = re.findall(r"^#!\s*fewshot_ids:\s*(.+)$", raw, re.M)
    prompt = "\n".join(line for line in raw.splitlines() if not line.startswith("#!")).strip() + "\n"
    return prompt, [s.strip() for s in fewshot[0].split(",")] if fewshot else []


def render_context(retrieved: list[dict]) -> str:
    return "\n\n".join(f"[{r['rank']}] {r['chunk_id']} (SDK {r['sdk_version']})\n{r['text']}" for r in retrieved)


def call_judge(prompt: str) -> dict:
    cmd = ["claude", "-p", "--model", JUDGE_MODEL, "--output-format", "json", "--tools", "",
           "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config",
           "--setting-sources", "", "--system-prompt",
           "You are an evaluation judge. Apply the rubric exactly as written. Output only the JSON object requested."]
    for attempt in range(3):
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              cwd=tempfile.gettempdir(), timeout=180)
        try:
            envelope = json.loads(proc.stdout)
            text = envelope["result"]
            verdict = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            if verdict.get("verdict") in ("PASS", "FAIL"):
                return {"verdict": verdict["verdict"], "reason": verdict.get("reason", ""),
                        "model": next(iter(envelope.get("modelUsage", {})), JUDGE_MODEL), "raw": text}
        except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
            pass
    raise RuntimeError(f"judge gave no parseable verdict after 3 tries: {proc.stdout[:300]} {proc.stderr[:300]}")


def require_blind_protocol(answers: dict[str, dict], version: str) -> dict:
    if not LOCK.exists():
        sys.exit("BLIND PROTOCOL: week6/labels_25.json is not locked. Label every answer, then run "
                 "`week6_eval.py lock-labels` before any judge run.")
    lock = json.loads(LOCK.read_text())
    if sha(LABELS.read_bytes()) != lock["labels_sha256"]:
        sys.exit("BLIND PROTOCOL: labels_25.json changed after it was locked. Relabelling after seeing the "
                 "judge moves the ruler; restore the locked file.")
    if answers_fingerprint(answers) != lock["answers_sha256"]:
        sys.exit("BLIND PROTOCOL: the answers differ from the ones that were labelled; the labels do not apply.")
    if version != "v1" and not PREDICTION.exists():
        sys.exit(f"judge_{version} needs week6/prediction.txt written BEFORE the iteration is run.")
    return lock


def run_judge(version: str, cases: list[dict], answers: dict[str, dict], fresh: bool) -> dict:
    lock = require_blind_protocol(answers, version)
    template, fewshot = load_prompt(version)
    RUNS.mkdir(exist_ok=True)
    run_file = RUNS / f"judge_{version}.json"
    cached = json.loads(run_file.read_text()) if run_file.exists() and not fresh else {}
    prompts = {c["id"]: template.replace("{question}", c["question"])
                                .replace("{context}", render_context(answers[c["id"]]["retrieved"]))
                                .replace("{answer}", answers[c["id"]]["answer"]) for c in cases}
    reuse = cached.get("prompt_sha256") == sha(template) and cached.get("answers_sha256") == lock["answers_sha256"]
    verdicts = cached["verdicts"] if reuse else {}
    todo = [cid for cid in prompts if cid not in verdicts]
    if todo:
        started = now()
        with ThreadPoolExecutor(4) as pool:
            for cid, result in zip(todo, pool.map(lambda cid: call_judge(prompts[cid]), todo)):
                verdicts[cid] = result
        run = {"judge": version, "model_alias": JUDGE_MODEL, "started_at_utc": started, "finished_at_utc": now(),
               "prompt_sha256": sha(template), "answers_sha256": lock["answers_sha256"],
               "labels_sha256": lock["labels_sha256"], "labels_locked_at_utc": lock["locked_at_utc"],
               "prediction_sha256": sha(PREDICTION.read_bytes()) if PREDICTION.exists() else None,
               "prediction_mtime_utc": datetime.fromtimestamp(PREDICTION.stat().st_mtime, timezone.utc)
               .isoformat(timespec="seconds") if PREDICTION.exists() else None,
               "fewshot_ids": fewshot, "verdicts": verdicts}
        run_file.write_text(json.dumps(run, indent=2))
        return run
    return cached


# ---------------------------------------------------------------- reporting

def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "—"


def report(cases: list[dict], answers: dict, results: dict, judge: dict | None) -> None:
    verdicts = judge["verdicts"] if judge else {}
    print(f"\nWeek 6 eval: {len(cases)} cases, {sum(c['source'].startswith('regression') for c in cases)} "
          f"regression cases replayed verbatim from real failed traces")
    original = {}
    for f in ("traces.jsonl", "demo_traces.jsonl"):
        for line in (ROOT / "week5" / f).read_text().splitlines():
            t = json.loads(line)
            original[t["trace_id"]] = t["raw_output"]
    reg = [c for c in cases if c["source"].startswith("regression")]
    same = sum(answers[c["id"]]["answer"] == original[c["trace_id"]] for c in reg)
    print(f"Regression replay: {same}/{len(reg)} answers byte-identical to the original failed trace's raw_output")
    print(f"Criteria: {len(ASSERTIONS)} deterministic assertions, 1 judged criterion ({CRITERION}"
          f"{', judge_' + judge['judge'] if judge else ', judge not run'})\n")
    head = f"{'mode':4} {'failure mode (week 5 taxonomy)':66} {'n':>2}  {'assertions':>11}  {'judge':>11}  {'overall':>11}"
    print(head + "\n" + "-" * len(head))
    by_mode = defaultdict(list)
    for c in cases:
        by_mode[c["mode"]].append(c["id"])
    totals = Counter()
    for mode, ids in sorted(by_mode.items()):
        a_ok = [cid for cid in ids if all(s != "fail" for s, _ in results[cid].values())]
        j_ok = [cid for cid in ids if verdicts.get(cid, {}).get("verdict") == "PASS"]
        both = [cid for cid in a_ok if not judge or cid in j_ok]
        totals.update(n=len(ids), a=len(a_ok), j=len(j_ok), o=len(both))
        print(f"{mode:4} {MODES[mode]:66} {len(ids):>2}  {pct(len(a_ok), len(ids)):>11}  "
              f"{pct(len(j_ok), len(ids)) if judge else '—':>11}  {pct(len(both), len(ids)):>11}")
    print("-" * len(head))
    print(f"{'all':4} {'':66} {totals['n']:>2}  {pct(totals['a'], totals['n']):>11}  "
          f"{pct(totals['j'], totals['n']) if judge else '—':>11}  {pct(totals['o'], totals['n']):>11}")

    print(f"\n{'assertion':32} {'applies':>7} {'fails':>5}  replaces")
    for name, why in ASSERTIONS.items():
        statuses = [results[c["id"]][name][0] for c in cases]
        print(f"{name:32} {sum(s != 'n/a' for s in statuses):>7} {statuses.count('fail'):>5}  {why}")

    print("\nper case (assertion failures | judge):")
    for c in cases:
        fails = [f"{n}: {d}" for n, (s, d) in results[c["id"]].items() if s == "fail"]
        j = verdicts.get(c["id"], {}).get("verdict", "")
        print(f"  {c['id']} {c['mode']} {j:4} {c['question'][:44]:44} | {'; '.join(fails) or 'all assertions pass'}")

    if judge and LABELS.exists():
        agreement(cases, judge)


def agreement(cases: list[dict], judge: dict) -> None:
    labels = {row["id"]: row["label"] for row in json.loads(LABELS.read_text())["labels"]}
    fewshot = set(judge.get("fewshot_ids") or [])
    pairs = [(cid, labels[cid], judge["verdicts"][cid]["verdict"]) for cid in labels]
    agree = [p for p in pairs if p[1] == p[2]]
    grid = Counter((h, j) for _, h, j in pairs)
    print(f"\nAGREEMENT judge_{judge['judge']} vs hand labels: {pct(len(agree), len(pairs))}")
    if fewshot:
        held = [p for p in pairs if p[0] not in fewshot]
        print(f"  excluding its {len(fewshot)} few-shot cases {sorted(fewshot)}: "
              f"{pct(sum(h == j for _, h, j in held), len(held))}")
    print(f"  human PASS / judge PASS {grid['PASS', 'PASS']:>2}   human PASS / judge FAIL {grid['PASS', 'FAIL']:>2}")
    print(f"  human FAIL / judge PASS {grid['FAIL', 'PASS']:>2}   human FAIL / judge FAIL {grid['FAIL', 'FAIL']:>2}")
    by_id = {c["id"]: c for c in cases}
    for cid, h, j in pairs:
        if h != j:
            print(f"  DISAGREE {cid} ({by_id[cid]['mode']}) human={h} judge={j}: {judge['verdicts'][cid]['reason']}")


# ---------------------------------------------------------------- labelling

def cmd_sheet(cases: list[dict], answers: dict) -> None:
    order = random.Random(20260928).sample([c["id"] for c in cases], len(cases))  # hide the mode grouping
    by_id = {c["id"]: c for c in cases}
    lines = [
        "# Blind labelling sheet: 25 answers, one binary criterion", "",
        f"**Criterion: {CRITERION}.** This is the same wording the judge gets (`week6/judge_v1.txt`).", "",
        "- **PASS**: a developer who asked this could act on the answer alone. It states the specific fact, value, "
        "behaviour or usage they asked for, and that is correct according to the documentation shown.",
        "- **FAIL**: it quotes nearby text that doesn't answer the question, answers a different question, or says "
        "\"I don't know\" when the documentation shown contains the answer.",
        "- \"I don't know\" is PASS only if the documentation shown really does not contain the answer.",
        "- If the question names no version, the developer is on SDK v3.",
        "- **Ignore** code formatting/parsing, endpoint validity, version labelling, deprecation notes, repetition "
        "and citation format. Assertions check those in code.", "",
        "The cases are in a shuffled order and don't show their failure mode. No judge output exists yet.", "",
        "**How to label:** put `\"PASS\"` or `\"FAIL\"` in each `label` field of `week6/labels_25.json` "
        "(the `note` field is optional). Then run `.venv/bin/python week6_eval.py lock-labels`.", "",
    ]
    for n, cid in enumerate(order, 1):
        a = answers[cid]
        lines += [f"---\n\n## {n}. `{cid}`: {by_id[cid]['question']}", "", "<details><summary>documentation shown "
                  "(top 3 retrieved)</summary>", ""]
        for r in a["retrieved"]:
            lines += [f"**[{r['rank']}] `{r['chunk_id']}`** (SDK {r['sdk_version']})", "", "```", r["text"], "```", ""]
        lines += ["</details>", "", "**Answer:**", "", "```text", a["answer"], "```", "", "Label: ____", ""]
    (W6 / "labeling_sheet.md").write_text("\n".join(lines))
    if LABELS.exists():
        print("labels_25.json already exists; not overwritten.")
    else:
        LABELS.write_text(json.dumps({
            "criterion": CRITERION, "labeler": "", "labelled_without_seeing_judge_output": True,
            "answers_sha256": answers_fingerprint(answers),
            "labels": [{"id": c["id"], "label": None, "note": ""} for c in cases],
        }, indent=2))
    print(f"wrote week6/labeling_sheet.md (order: {', '.join(order)}) and week6/labels_25.json")


def cmd_lock(answers: dict) -> None:
    data = json.loads(LABELS.read_text())
    bad = [row["id"] for row in data["labels"] if row["label"] not in ("PASS", "FAIL")]
    if bad or len(data["labels"]) != 25:
        sys.exit(f"labels_25.json is incomplete: {bad or 'need 25 rows'}")
    if data["answers_sha256"] != answers_fingerprint(answers):
        sys.exit("the pipeline's answers changed since the sheet was generated; regenerate the sheet and relabel.")
    if RUNS.exists() and any(RUNS.iterdir()):
        sys.exit("a judge run already exists, so these labels cannot be blind.")
    lock = {"labels_sha256": sha(LABELS.read_bytes()), "answers_sha256": data["answers_sha256"],
            "locked_at_utc": now(), "labels_mtime_utc": datetime.fromtimestamp(
                LABELS.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "counts": dict(Counter(row["label"] for row in data["labels"]))}
    LOCK.write_text(json.dumps(lock, indent=2))
    print(json.dumps(lock, indent=2))
    print("\nLocked. Commit labels_25.json + labels_lock.json now, BEFORE running the judge, so the git history "
          "also proves the order.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", nargs="?", default="run", choices=["run", "sheet", "lock-labels"])
    parser.add_argument("--judge", default="auto", help="v1 | v2 | none | auto (latest prompt if labels are locked)")
    parser.add_argument("--fresh", action="store_true", help="ignore cached judge verdicts")
    args = parser.parse_args()

    cases = load_cases()
    answers = generate_answers(cases)
    if args.cmd == "sheet":
        return cmd_sheet(cases, answers)
    if args.cmd == "lock-labels":
        return cmd_lock(answers)

    results = {c["id"]: run_assertions(c, answers[c["id"]]["answer"]) for c in cases}
    version = args.judge
    if version == "auto":
        version = "none" if not LOCK.exists() else ("v2" if (W6 / "judge_v2.txt").exists() else "v1")
    judge = None if version == "none" else run_judge(version, cases, answers, args.fresh)
    report(cases, answers, results, judge)


if __name__ == "__main__":
    main()
