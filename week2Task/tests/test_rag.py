import unittest

import numpy as np

from rag import Chunk, Document, InMemoryIndex, chunk_document, has_evidence


class FakeEmbedder:
    def encode(self, texts, **kwargs):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vector = np.array([
                float("damaged" in lowered or "parcel" in lowered),
                float("remote" in lowered),
                float("password" in lowered),
            ])
            norm = np.linalg.norm(vector)
            vectors.append(vector / norm if norm else vector)
        return np.asarray(vectors)


class RagTests(unittest.TestCase):
    def test_chunking_preserves_metadata_and_overlap(self):
        doc = Document(
            "# Rules\nOne two three four. Five six seven eight. Nine ten eleven.",
            "rules.md",
            "Rules",
        )
        chunks = chunk_document(doc, chunk_size=8, overlap=4)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual(chunks[0].source, "rules.md")
        self.assertTrue(any("Five six seven eight" in chunk.text for chunk in chunks[1:]))

    def test_search_returns_matching_chunk_first(self):
        chunks = [
            Chunk("Damaged parcels must be reported.", "support.md", "Support", "Damage", 0),
            Chunk("Remote work is available.", "hr.md", "HR", "Work", 0),
        ]
        results = InMemoryIndex(FakeEmbedder(), chunks).search(
            "When do I report a damaged parcel?", 1
        )
        self.assertEqual(results[0].chunk.source, "support.md")
        self.assertTrue(has_evidence(results, 0.5))

    def test_low_similarity_is_not_evidence(self):
        chunk = Chunk("Remote work is available.", "hr.md", "HR", "Work", 0)
        results = InMemoryIndex(FakeEmbedder(), [chunk]).search(
            "What is the Wi-Fi password?", 1
        )
        self.assertFalse(has_evidence(results, 0.5))


if __name__ == "__main__":
    unittest.main()
