# error_before_after: one docstring rewritten as a prompt, one error path made recoverable

**Tool:** `search_docs` on **our own** server (`week9_docs_server.py`).

**Failing call:** `search_docs(query="upload a file", api_version="v4")`. No v4 SDK has been published, so no v4 docs exist.

**Before / after:** `DOCS_PROMPTS=v1` (first version) vs `DOCS_PROMPTS=v2` (rewrite). Both live in the server file, so either one can be re-run. Both configs connect the docs-search server only, so the prompt version is the only difference: `week9/configs/docs_only_prompts_v1.json` and `..._v2.json`.

**Question:** *"We're upgrading to acme-sdk v4 next sprint. Using the v4 docs, show me how to upload report.pdf with the v4 client."*

**Reproduce:** `.venv/bin/python week9_error_experiment.py --reps 3`. Logs are in `week9/error_experiment/`.

## 1. What the model reads: the docstring (from `tools/list`)

| | `search_docs` description |
|---|---|
| **before** | `Search the docs.` |
| **after** | One job (prose search of ONE major version, cite `chunk_id`). When to use it and when not (schemas → `get_openapi_spec`, deprecation → `check_deprecation`). What `api_version` means and which values exist: v3 = 3.0–3.2, current, the default; v2 = deprecated, only for reading old code. What to do for a version that doesn't exist: call with `"v3"`, say v3 is the latest, never answer from v2. "On failure the error text says what to do next." |

The full "after" text is `SEARCH_DOC_V2` in `week9_docs_server.py`. It's also in `week9/wire_search_docs_v4_v2.jsonl` exactly as `tools/list` sent it.

## 2. What comes back: the same failing call, raw `tools/call` result

From `week9/wire_search_docs_v4_v1.jsonl` and `week9/wire_search_docs_v4_v2.jsonl`:

**before**
```json
{"content": [{"type": "text", "text": "Error executing tool search_docs: Error 3"}], "isError": true}
```

**after**
```json
{"content": [{"type": "text", "text": "Error executing tool search_docs: no docs for v4.x: that version is not published (this is not an outage, the docs index is up). Latest published docs are v3 (SDK 3.x (3.0 to 3.2)); v2 is deprecated. Retry: search_docs(query='upload a file', api_version=\"v3\"). Methods removed or renamed in v3 are listed by check_deprecation(symbol, api_version=\"v3\") and on the v3 changelog page (search_docs(\"what changed in v3\", \"v3\")). Do not fall back to v2 samples: Client.request() and paginate_auto() no longer exist in v3."}], "isError": true}
```

"Error 3" can't be told apart from an outage, and it gives no next step. The new message answers three questions:
- **Which failure?** Missing version, and explicitly not an outage. A real index failure has its own message: `docs index unavailable ... This is an outage, not a missing version`.
- **What exists?** v3, which covers 3.0–3.2.
- **Exact next call?** `search_docs(..., api_version="v3")`, plus where the deprecations are and a warning not to fall back to v2.

## 3. Transcript: the model handling that same call

In both runs, lap 1 is forced to be the failing call, so both conditions handle the identical error. The model drives every lap after it. The runs shown are `seeded_v1_r1.jsonl` and `seeded_v2_r1.jsonl`.

### Before (`DOCS_PROMPTS=v1`)
```
lap 1  CALL   search_docs {"query": "upload a file", "api_version": "v4"}
       RESULT isError: "Error executing tool search_docs: Error 3"
lap 2  FINAL  (bare output contract, accepted as final)
  answer : "The Acme SDK v4 is not yet documented in the available resources. The current version is v3 (3.0–3.2).
            If you're planning to upgrade to v4 next sprint, I recommend checking with your SDK vendor for v4
            documentation, or I can show you how to upload files with v3 today."
  v3_code: ""            <- no code
  sources: ["docs-search resource docs://version-support-matrix"]
```
"Error 3" gave the model nothing to act on, so it gave up. It inferred "v4 doesn't exist" only from the version matrix the host attaches as a resource, not from the error. It never retried v3, and the developer got no code.

### After (`DOCS_PROMPTS=v2`)
```
lap 1  CALL   search_docs {"query": "upload a file", "api_version": "v4"}
       RESULT isError: "no docs for v4.x: that version is not published (this is not an outage, ...). Latest published
              docs are v3 ... Retry: search_docs(query='upload a file', api_version="v3") ..."
lap 2  CALL   search_docs {"query": "upload a file", "api_version": "v3"}
       thought: "v4 docs don't exist yet; v3 is the latest published version. I'll search v3 docs for file upload
                 guidance and show the developer the current way to upload a file."
       RESULT ok: v3-files::upload-parameters::1-table, v3-files::file-uploads::0, v3-files::upload-parameters::3-code
lap 3  FINAL
  answer : "v4 docs are not yet published; v3 is the latest version available. Here's how to upload report.pdf using
            the v3 SDK. When v4 is released, the API for file uploads may change—check the v4 changelog at that time."
  v3_code: client.files.upload(file_path="report.pdf")
  sources: ["v3-files::file-uploads::0", "v3-files::upload-parameters::3-code"]
```
The model did what the error said. It made the exact retry, cited real chunks, and wrote the correct v3 call (`files.upload`, the Q05 answer from Week 7). It did not fall back to the deprecated v2 `client.upload_file()`.

## 4. The number that moved (3 runs per condition, Claude Haiku 4.5)

| Same failing call forced on lap 1 | before (`Error 3`) | after (recoverable) |
|---|---|---|
| retried `search_docs` with `v3` after the error | **0 / 3** | **3 / 3** |
| final `v3_code` is the working v3 call (`client.files.upload`) | **0 / 3** (all empty) | **3 / 3** |
| final code uses a v2 / deprecated API | 0 / 3 | 0 / 3 |
| told the developer v4 is not published | 3 / 3 | 3 / 3 |
| laps / mean cost | 2 / $0.0032 | 3 / $0.0074 |

The fix costs one extra lap (about $0.004) and turns an empty answer into a working one.

## 5. What it did not fix

These are free runs (`free_*.jsonl`, 3 per condition), where the model drives from lap 1:
- The `docs://version-support-matrix` resource the host attaches already lists v2/v3 only. Because of that, the model rarely made the failing call at all: 1 v4 call out of 3 runs before, 0 out of 3 after.
- With the new docstring, all 3 free runs answered in one lap with no tool call. They said "v4 is not published, want the v3 version?" and returned empty code. The new docstring says to *call with "v3"*, and the model didn't follow that when it never hit the error.
- With the old docstring, 1 of 3 free runs fetched v3 and gave the right code.

So the recoverable error clearly helps once the call fails (0/3 → 3/3). The docstring alone did not make free runs more helpful, and 3 runs is too few to claim it hurt. The next thing to try is making the instruction explicit in the docstring: "if the developer names an unpublished version, still answer with v3 code". It hasn't been tried.
