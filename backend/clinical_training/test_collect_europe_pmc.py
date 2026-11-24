import unittest

from collect_europe_pmc import normalize_license


class EuropePmcLicenseTests(unittest.TestCase):
    def test_accepts_explicit_cc_by_and_cc0(self):
        self.assertEqual(normalize_license("CC BY 4.0"), "CC-BY-4.0")
        self.assertEqual(normalize_license("CC BY 3.0"), "CC-BY-3.0")
        self.assertEqual(normalize_license("https://creativecommons.org/publicdomain/zero/1.0/"), "CC0-1.0")

    def test_rejects_noncommercial_nd_and_unknown(self):
        self.assertIsNone(normalize_license("CC BY-NC 4.0"))
        self.assertIsNone(normalize_license("CC BY-ND 4.0"))
        self.assertIsNone(normalize_license("all rights reserved"))


if __name__ == "__main__":
    unittest.main()
