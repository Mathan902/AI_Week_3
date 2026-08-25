# Ask Six Documents

A coursework RAG application that searches six synthetic documents. It uses dense embeddings and direct NumPy cosine similarity; it does not use a vector database.

## Features

- Six documents covering support, recipes, HR, insurance, SDK documentation, and contracts
- Two chunking configurations: 120/25 and 300/60 words
- `all-MiniLM-L6-v2` dense embeddings held in memory
- Top-K cosine-similarity retrieval with source metadata
- Configurable evidence threshold and an explicit “I don't know” response
- Source, section, chunk ID, and score shown for every retrieved result
- Side-by-side chunking comparison for each question
- Optional OpenAI grounded generation; an extractive fallback works without an API key

## Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The embedding model is downloaded the first time the app starts. To enable generated answers, set `OPENAI_API_KEY`. Without it, the app returns a short extract from the best-supported source.

## Test

```powershell
python -B -m unittest discover -s tests -v
```

## Demonstration

Use each prepared question in the app and show its cited source. Then select **Not in documents** and verify that the app refuses to answer. Compare the best retrieval score and source in the chunking comparison table. The documents are synthetic training material and should not be treated as real company policies or legal terms.
