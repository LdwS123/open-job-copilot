import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'runner'))
from sanitize import clean, ok_url


class Clean(unittest.TestCase):
    def test_strips_delimiters(self):
        out = clean("a|b<c>d")
        for ch in "|<>":
            self.assertNotIn(ch, out)

    def test_normalises_lookalikes(self):
        self.assertEqual(clean("ＳＤＲ"), "SDR")  # full-width letters fold to ASCII

    def test_drops_control_and_markup(self):
        self.assertNotIn("\n", clean("x\ny‮"))
        self.assertNotIn("`", clean("`rm -rf`"))

    def test_truncates(self):
        self.assertEqual(len(clean("a" * 500, 40)), 40)


class Urls(unittest.TestCase):
    def test_allows_ats_hosts(self):
        self.assertTrue(ok_url("https://jobs.ashbyhq.com/acme/123"))
        self.assertTrue(ok_url("https://jobs.lever.co/acme/abc-def"))

    def test_rejects_other_hosts_and_schemes(self):
        self.assertFalse(ok_url("https://evil.example/apply"))
        self.assertFalse(ok_url("http://jobs.lever.co/acme"))
        self.assertFalse(ok_url("javascript:alert(1)"))

    def test_rejects_hostname_tricks(self):
        self.assertFalse(ok_url("https://jobs.lever.co.evil.example/x"))
        self.assertFalse(ok_url("https://jobs.lever.co@evil.example/x"))
        self.assertFalse(ok_url("https://jobs.lever.co/x y"))


if __name__ == "__main__":
    unittest.main()
