import unittest

import week6_eval as ev

CASE = {"state_versions": ["v3"], "cite_version": "v3", "expect": "answer", "must_include": ["\\b500\\b"]}


class AssertionTests(unittest.TestCase):
    def test_good_fenced_code_passes(self):
        body = 'Use it like this:\n```python\nwith client.stream(url="/v3/events") as events:\n    for e in events:\n        print(e)\n```'
        self.assertEqual(ev.check_code_parses(body)[0], "pass")

    def test_squashed_or_truncated_code_fails(self):
        self.assertEqual(ev.check_code_parses("from acme.webhooks import verify_signature verify_signature(")[0], "fail")
        self.assertEqual(ev.check_code_parses("```python with client.stream(url='/v3/events') as e:     print(e) ```")[0], "fail")

    def test_inline_symbol_is_not_code(self):
        self.assertEqual(ev.check_code_parses("Uploads go through `Client.files.upload()`.")[0], "n/a")

    def test_endpoints(self):
        self.assertEqual(ev.check_endpoints('client.send(url="/v3/invoices")')[0], "pass")
        self.assertEqual(ev.check_endpoints('client.request(url="/v2/invoices")')[0], "fail")

    def test_deprecation_needs_migration_note(self):
        self.assertEqual(ev.check_deprecations("`paginate_auto()` walks every page.")[0], "fail")
        self.assertEqual(ev.check_deprecations("`paginate_auto()` was removed in v3; use `list_after()` instead.")[0], "pass")

    def test_repetition(self):
        self.assertEqual(ev.check_no_repetition("A is thread-safe. Share it. A is thread-safe")[0], "fail")
        self.assertEqual(ev.check_no_repetition("The default is 500 ms in v3.")[0], "pass")

    def test_full_good_answer_passes_every_assertion(self):
        results = ev.run_assertions(CASE, "In SDK v3 the default `retry_backoff_ms` is 500 ms. [chunk:v3-client::x::3-table]")
        self.assertTrue(all(status != "fail" for status, _ in results.values()), results)


if __name__ == "__main__":
    unittest.main()
