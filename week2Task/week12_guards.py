"""Week 12: the deterministic guards around the integrated docs engine. No model call anywhere in this file.

    redact(text)                     PII / secret scrubbing, applied at intake and again on every log write
    resolve_version(question, flag)  the caller's SDK version, resolved BEFORE retrieval
    SymbolTable / check_code(...)    does an emitted sample parse, do its imports resolve, and does every
                                     client method / parameter it uses exist in THAT version?
    CHANGELOG                        week7/changelog_v3.json + the version each change landed in (3.0)

"If you can assert it, never judge it": every check here replaces a question an LLM judge would otherwise be
paid to guess at. The symbol table is built from the corpus itself (headings, parameter tables, code fences)
plus the v3 OpenAPI file's x-sdk-call, so a docs change re-derives it; nothing is hand-listed.
"""
from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent
CORPUS = ROOT / "corpus"
SPEC = json.loads((ROOT / "week7" / "openapi_v3.json").read_text())

# What the docs site publishes. Minor versions map onto the major's docs; the citation names both.
PUBLISHED = {"v2": {"covers": "2.0-2.9", "status": "maintained (security fixes), ~40% of integrators"},
             "v3": {"covers": "3.0-3.2", "status": "current"}}
LATEST = "v3"
DEFAULT_MINOR = {"v2": "2.x", "v3": "3.0"}

# ---------------------------------------------------------------- changelog with the version each change landed in
# The corpus states every one of these changes as "in v3" on the v3.0 changelog page, so removed_in / changed_in is
# 3.0. The docs never say in which 2.x release a symbol was first deprecated, so deprecated_in stays unknown rather
# than invented.

_RAW_CHANGELOG = json.loads((ROOT / "week7" / "changelog_v3.json").read_text())
CHANGELOG = [{**e, "changed_in": "3.0", "deprecated_in": None,
              "kind": {"removed": "removed", "renamed": "renamed", "default_changed": "default changed"}[e["status"]]}
             for e in _RAW_CHANGELOG]
# upload_file is not in the changelog, but the two files pages show v2 Client.upload_file() and v3
# Client.files.upload(); the eval needs it as a known v2-only name, so it is recorded as "docs-only" evidence.
DOCS_ONLY_RENAMES = [{"symbol": "Client.upload_file", "aliases": ["upload_file", "client.upload_file"],
                      "status": "renamed", "kind": "replaced (not in changelog)", "changed_in": "3.0",
                      "deprecated_in": None, "replacement": "Client.files.upload()", "replacement_path": "/v3/files",
                      "note": "v2 uploads go through `Client.upload_file()`; v3 uploads go through "
                              "`Client.files.upload()`. The v3 changelog does not list this change.",
                      "source": "v3-files::file-uploads::0"}]


def _norm(symbol: str) -> str:
    return re.sub(r"\(\)$", "", str(symbol).strip().strip("`")).lower()


def changelog_entry(symbol: str) -> dict | None:
    key = _norm(symbol)
    for entry in CHANGELOG + DOCS_ONLY_RENAMES:
        names = {_norm(entry["symbol"]), *(_norm(a) for a in entry["aliases"])}
        if key in names or key.split(".")[-1] in {n.split(".")[-1] for n in names}:
            return entry
    return None


# ---------------------------------------------------------------- PII / secret redaction

# Integrator questions routinely carry pasted API keys and connection strings. Order matters: the specific
# patterns run before the generic key=value one so the label says what was removed.
REDACTIONS = [
    ("connection_string", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s@/]+@[^\s'\"]+", re.I)),
    ("acme_token", re.compile(r"\bacme_(?:live|test)_[A-Za-z0-9]{12,}\b")),
    ("api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*", re.I)),
    ("secret_assignment", re.compile(
        r"(?P<k>\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|APIKEY)[A-Z0-9_]*\b\s*[=:]\s*)"
        r"(?P<q>['\"]?)(?P<v>(?!\[REDACTED)[^\s'\",)\]};]{6,})(?P=q)", re.I)),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
]


# Policy v1 redacted ANY value after a secret-named key, so it also ate code that only REFERENCES a secret:
# `WEBHOOK_SIGNING_SECRET = os.environ["..."]` became unparseable (C18, tr-5871db30a290; the Week 12 closed loop).
# v2 redacts a value only if it is a literal: quoted, or unquoted with a digit or 20+ chars, and never a reference.
REDACTION_POLICY = os.environ.get("W12_REDACTION_POLICY", "v2")
_REFERENCE = re.compile(r"(?:os\.|getenv|environ|settings\.|config\.)|[(\[]|^[A-Za-z_][A-Za-z_.]*,?$")


def _is_literal_secret(value: str, quoted: bool) -> bool:
    if REDACTION_POLICY == "v1":
        return True
    if _REFERENCE.search(value) and not quoted:
        return False
    return quoted or bool(re.search(r"\d", value)) or len(value) >= 20


def redact(text: str) -> tuple[str, list[str]]:
    """Text with every secret replaced by [REDACTED:<kind>], plus the kinds found (never the values)."""
    found = []
    for kind, pattern in REDACTIONS:
        def sub(m: re.Match, kind=kind) -> str:
            if kind == "secret_assignment" and not _is_literal_secret(m.group("v"), bool(m.group("q"))):
                return m.group(0)
            found.append(kind)
            if kind == "secret_assignment":
                return f"{m.group('k')}{m.group('q')}[REDACTED:{kind}]{m.group('q')}"
            return f"[REDACTED:{kind}]"
        text = pattern.sub(sub, text)
    return text, found


def redact_obj(obj):
    """redact() applied to every string inside a JSON-able object (the log writer's last line of defence)."""
    if isinstance(obj, str):
        return redact(obj)[0]
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------- version resolution (before retrieval)

_VERSION_IN_TEXT = re.compile(r"(?:(?<!/)\bv|\bsdk\s*v?|\bacme\s*v?|\bversion\s*v?|\bon\s+v?)(\d+)(?:\.(\d+|x))?\b", re.I)
_BARE_SEMVER = re.compile(r"\b([23])\.(\d+|x)\b")
_MIGRATION = re.compile(r"\b(upgrad\w*|migrat\w*|rewrite|port\w* (?:it |this )?to|move to|moving to|switch\w* to)\b",
                        re.I)
# v2-only / v3-only names a pasted snippet or error message gives away. Built from the changelog, not by hand.
_V2_ONLY = sorted({_norm(a).split(".")[-1] for e in CHANGELOG + DOCS_ONLY_RENAMES
                   if e["status"] in ("removed", "renamed") for a in [e["symbol"], *e["aliases"]]})
_V3_ONLY = ["send", "list_after", "files.upload", "timeout_ms", "ratelimiterror", "retry_after_seconds", "stream",
            "verify_signature"]


@dataclass
class Resolved:
    major: str              # v2 | v3: the docs that retrieval is pinned to
    minor: str              # "2.4", "3.0", "2.x" ...: what the caller said, for the citation
    source: str             # flag | question | code_fingerprint | default
    code_target: str        # the version emitted code must compile against (v3 for a migration)
    allowed: list[str]      # versions retrieval may touch
    migration: bool = False
    unsupported: str | None = None   # a version the caller named that has no docs (v4, v1)
    evidence: str = ""

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _major_minor(text: str) -> tuple[str, str] | None:
    """The first SDK version stated in text: 'v2', 'SDK 2.4', 'on 3.0', 'acme 3'."""
    for m in _VERSION_IN_TEXT.finditer(text):
        major = m.group(1)
        if major in ("1", "2", "3", "4", "5"):
            return f"v{major}", f"{major}.{m.group(2)}" if m.group(2) else f"{major}.x"
    m = _BARE_SEMVER.search(text)
    if m:
        return f"v{m.group(1)}", f"{m.group(1)}.{m.group(2)}"
    return None


def _fingerprint(text: str) -> tuple[str | None, str]:
    low = text.lower()
    v2 = [s for s in _V2_ONLY if re.search(rf"(?<![\w.]){re.escape(s)}\b", low)
          or re.search(rf"\.{re.escape(s)}\(", low)]
    v2 += ["/v2/ path"] if "/v2/" in low else []
    v3 = [s for s in _V3_ONLY if re.search(rf"\.{re.escape(s)}\(|\b{re.escape(s)}\b", low)
          and s not in ("send", "stream")]
    v3 += ["/v3/ path"] if "/v3/" in low else []
    if v2 and not v3:
        return "v2", f"v2-only names in the question: {v2}"
    if v3 and not v2:
        return "v3", f"v3-only names in the question: {v3}"
    return None, ""


def resolve_version(question: str, flag: str | None = None) -> Resolved:
    """The caller's version: the IDE flag if given, else a version the question states, else a v2/v3-only symbol
    in pasted code, else the current release (and the answer says it assumed so)."""
    migration = bool(_MIGRATION.search(question))
    unsupported = None
    if flag:
        mm = _major_minor(flag if flag.lower().startswith("v") else f"v{flag}")
        if not mm:
            raise ValueError(f"cannot read SDK version {flag!r}; pass e.g. 2.4 or 3.0")
        major, minor = mm
        source, evidence = "flag", f"--sdk-version {flag}"
        named = _major_minor(question)
        if named and named[0] != major and named[0] in PUBLISHED and migration:
            pass  # "I'm on 2.4, upgrading to 3.0": the flag is where they are, the question is where they go
    else:
        named = _major_minor(question)
        if named:
            (major, minor), source, evidence = named, "question", "version stated in the question"
        else:
            fp, evidence = _fingerprint(question)
            if fp:
                major, minor, source = fp, DEFAULT_MINOR[fp], "code_fingerprint"
            else:
                major, minor, source, evidence = LATEST, DEFAULT_MINOR[LATEST], "default", \
                    "no version given; assumed the current release"
    if major not in PUBLISHED:
        unsupported, evidence = minor, evidence + f"; {minor} has no published docs"
        major, minor = LATEST, DEFAULT_MINOR[LATEST]
    # A migration question from a v2 caller is answered with v3 code, and may read both doc sets.
    if migration and major == "v2" and re.search(r"\b(v?3(\.\d+)?|latest|new(er)? version)\b", question, re.I):
        return Resolved(major, minor, source, "v3", ["v2", "v3"], True, unsupported, evidence + "; migration to v3")
    return Resolved(major, minor, source, major, [major], False, unsupported, evidence)


# ---------------------------------------------------------------- the per-version symbol table, from the corpus

_FENCE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_CALLABLE_MENTION = re.compile(r"`((?:Client\.)?[A-Za-z_][\w.]*)\(\)`")


def _dotted(node: ast.AST) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _method_key(name: str) -> str:
    """Client.files.upload / client.files.upload / files.upload -> files.upload"""
    return re.sub(r"^(?:[Cc]lient\.)", "", name)


@dataclass
class SymbolTable:
    version: str
    modules: dict[str, set[str]] = field(default_factory=dict)        # module -> exported names
    methods: dict[str, set[str] | None] = field(default_factory=dict)  # client method -> params (None = unknown)
    functions: dict[str, set[str] | None] = field(default_factory=dict)  # module.func -> params
    constructor: set[str] = field(default_factory=set)
    attributes: set[str] = field(default_factory=set)                  # documented attribute names

    def to_json(self) -> dict:
        return {"version": self.version,
                "modules": {k: sorted(v) for k, v in sorted(self.modules.items())},
                "client_methods": {k: (sorted(v) if v is not None else None) for k, v in sorted(self.methods.items())},
                "functions": {k: (sorted(v) if v is not None else None) for k, v in sorted(self.functions.items())},
                "constructor": sorted(self.constructor)}

    def exists(self, symbol: str) -> dict:
        """symbol_exists: is this name part of the SDK surface in this version?"""
        s = re.sub(r"\(\)$", "", symbol.strip().strip("`"))
        key = _method_key(s)
        low = key.lower()
        for m, params in self.methods.items():
            if m.lower() == low:
                return {"exists": True, "kind": "client method", "symbol": f"Client.{m}",
                        "params": sorted(params) if params else None}
        for f, params in self.functions.items():
            if f.lower() == low or f.split(".")[-1].lower() == low:
                return {"exists": True, "kind": "function", "symbol": f, "params": sorted(params) if params else None}
        for mod, names in self.modules.items():
            for n in names:
                if n.lower() == low or f"{mod}.{n}".lower() == s.lower():
                    return {"exists": True, "kind": "import", "symbol": f"from {mod} import {n}"}
        if low in {c.lower() for c in self.constructor}:
            return {"exists": True, "kind": "Client constructor parameter", "symbol": key}
        return {"exists": False, "symbol": s}


def _params_from_table(table: str) -> set[str]:
    rows = [r for r in table.splitlines() if r.strip().startswith("|")]
    if not rows or "parameter" not in rows[0].lower():
        return set()
    return {r.strip("|").split("|")[0].strip() for r in rows[2:] if r.strip("|").split("|")[0].strip()}


def build_symbol_table(version: str) -> SymbolTable:
    t = SymbolTable(version)
    t.modules["acme"] = {"Client"}
    for page in sorted((CORPUS / f"sdk_{version}").glob("*.md")):
        text = page.read_text()
        # 1. code fences: imports, client calls (with their keyword args), module functions
        for code in _FENCE.findall(text):
            try:
                tree = ast.parse(code)
            except SyntaxError:
                continue
            imported = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("acme"):
                    for a in node.names:
                        t.modules.setdefault(node.module, set()).add(a.name)
                        imported[a.asname or a.name] = f"{node.module}.{a.name}"
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = _dotted(node.func)
                    if not name:
                        continue
                    kws = {k.arg for k in node.keywords if k.arg}
                    if name.lower().startswith("client.") and name.count(".") >= 1:
                        key = _method_key(name)
                        t.methods[key] = (t.methods.get(key) or set()) | kws
                    elif name in imported and name != "Client":
                        t.functions[imported[name]] = (t.functions.get(imported[name]) or set()) | kws
                    elif name == "Client":
                        t.constructor |= kws
        # 2. headings + parameter tables: a table belongs to the last callable named in a heading or in prose
        last_callable = None
        section = ""
        for block in re.split(r"\n(?=#)|\n\n", text):
            head = _HEADING.match(block.strip().splitlines()[0]) if block.strip() else None
            if head:
                section = head.group(2)
                m = re.match(r"((?:Client\.)?[A-Za-z_][\w.]*)\(\)", section)
                if m:
                    last_callable = m.group(1)
            for mention in _CALLABLE_MENTION.findall(block):
                if mention.startswith("Client.") or mention in ("paginate_auto", "list_after"):
                    last_callable = last_callable if head and last_callable else mention
                    if not head:
                        last_callable = mention
            if "|" in block and "Parameter" in block:
                params = _params_from_table(block[block.index("|"):])
                if "constructor" in section.lower():
                    t.constructor |= params
                elif "verification" in section.lower():
                    t.functions.setdefault("acme.webhooks.verify_signature", set())
                    t.functions["acme.webhooks.verify_signature"] |= params
                elif last_callable:
                    key = _method_key(last_callable)
                    t.methods[key] = (t.methods.get(key) or set()) | params
            if "| Exception" in block:
                for row in block.splitlines()[2:]:
                    name = row.strip("|").split("|")[0].strip()
                    if name.endswith("Error"):
                        t.modules.setdefault("acme.errors", set()).add(name)
        if page.stem == "errors":
            # prose mentions count, except a sentence about another version ("In v3 this exception was renamed
            # to `RateLimitError`" sits on the v2 page and must not put RateLimitError into v2)
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                if re.search(r"\bv\d\b", sentence) and f"v{version[1:]}" not in sentence.split():
                    continue
                for err in re.findall(r"`(\w+Error)`", sentence):
                    t.modules.setdefault("acme.errors", set()).add(err)
    # 3. the v3 OpenAPI file's x-sdk-call is SDK documentation too
    if version == "v3":
        for ops in SPEC["paths"].values():
            for op in ops.values():
                try:
                    tree = ast.parse(op.get("x-sdk-call", ""))
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and (_dotted(node.func) or "").startswith("client."):
                        key = _method_key(_dotted(node.func))
                        t.methods[key] = (t.methods.get(key) or set()) | {k.arg for k in node.keywords if k.arg}
    return t


SYMBOLS = {v: build_symbol_table(v) for v in PUBLISHED}


# ---------------------------------------------------------------- the code check

def strip_fence(code: str) -> str:
    code = code.strip()
    m = re.match(r"^```[a-zA-Z]*\n?(.*?)\n?```$", code, re.S)
    return m.group(1) if m else code


def check_code(code: str, version: str) -> dict:
    """Parse the sample, then check it against `version`'s symbol table. Returns
    {"status": "pass"|"fail"|"n/a", "violations": [...], "checked": n}. A violation names the exact symbol."""
    code = strip_fence(code or "")
    if not code.strip():
        return {"status": "n/a", "violations": [], "checked": 0, "version": version}
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"status": "fail", "violations": [f"does not parse: {exc.msg} (line {exc.lineno})"], "checked": 0,
                "version": version}
    t = SYMBOLS[version]
    other = next(v for v in PUBLISHED if v != version)
    violations, checked = [], 0
    clients = {"client"}
    imported: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and _dotted(node.value.func) == "Client":
            clients |= {tg.id for tg in node.targets if isinstance(tg, ast.Name)}
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "acme":
            for a in node.names:
                checked += 1
                imported[a.asname or a.name] = f"{node.module}.{a.name}"
                if a.name not in t.modules.get(node.module, set()):
                    violations.append(f"`from {node.module} import {a.name}` does not resolve in {version}")
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] == "acme" and a.name not in t.modules:
                    checked += 1
                    violations.append(f"`import {a.name}` does not resolve in {version}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _dotted(node.func)
            if not name:
                continue
            kws = {k.arg for k in node.keywords if k.arg}
            root, _, rest = name.partition(".")
            if root in clients and rest:
                checked += 1
                key = rest
                if key not in t.methods:
                    where = f" (it exists in {other})" if key in SYMBOLS[other].methods else ""
                    violations.append(f"`client.{key}()` does not exist in {version}{where}")
                elif t.methods[key]:
                    bad = sorted(kws - t.methods[key])
                    if bad:
                        violations.append(f"`client.{key}()` has no parameter {bad} in {version}")
            elif name == "Client" or imported.get(name) == "acme.Client":
                checked += 1
                bad = sorted(kws - t.constructor)
                if bad:
                    violations.append(f"`Client()` has no parameter {bad} in {version}")
            elif name in imported and imported[name] in t.functions and t.functions[imported[name]]:
                checked += 1
                bad = sorted(kws - t.functions[imported[name]])
                if bad:
                    violations.append(f"`{name}()` has no parameter {bad} in {version}")
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            for n in (node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]):
                if isinstance(n, ast.Name) and n.id.endswith("Error") and n.id not in imported:
                    checked += 1
                    if n.id not in t.modules.get("acme.errors", set()):
                        violations.append(f"exception `{n.id}` is not raised by the SDK in {version}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            m = re.search(r"/v(\d+)/", node.value)
            if m and f"v{m.group(1)}" != version:
                checked += 1
                violations.append(f"endpoint path {node.value!r} is a v{m.group(1)} path, caller is on {version}")
    return {"status": "fail" if violations else "pass", "violations": violations, "checked": checked,
            "version": version}


if __name__ == "__main__":
    print(json.dumps({v: SYMBOLS[v].to_json() for v in SYMBOLS}, indent=1))
