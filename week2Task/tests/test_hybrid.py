import unittest

from hybrid import BM25Index, bm25_tokens, rrf_fuse


class HybridTests(unittest.TestCase):
    def test_tokens_keep_symbols_whole_and_split(self):
        tokens = bm25_tokens("Set `retry_backoff_ms` or X-RateLimit-Remaining in v3.0.")
        for expected in ("retry_backoff_ms", "retry", "backoff", "x-ratelimit-remaining", "v3.0"):
            self.assertIn(expected, tokens)

    def test_bm25_ranks_exact_symbol_first(self):
        index = BM25Index(
            ["prose", "table"],
            ["Retries back off exponentially between attempts.",
             "| retry_backoff_ms | int | 500 | no |"],
        )
        self.assertEqual(index.search("default retry_backoff_ms", 2)[0], "table")

    def test_rrf_fuses_ranks_not_scores(self):
        fused = dict(rrf_fuse([["a", "b", "c"], ["c", "a"]], k=60))
        self.assertAlmostEqual(fused["a"], 1 / 61 + 1 / 62)
        self.assertAlmostEqual(fused["b"], 1 / 62)
        self.assertEqual(rrf_fuse([["a", "b", "c"], ["c", "a"]])[0][0], "a")


if __name__ == "__main__":
    unittest.main()
