import unittest
from app.services.krashen_engine import is_valid_target_word

class TestKrashenFilter(unittest.TestCase):
    def test_valid_target_words(self):
        valid_samples = [
            {"lemma": "Pflegekraft"},
            {"lemma": "untersuchen"},
            {"lemma": "Blutdruck"},
            {"lemma": "Überweisung"},
            {"lemma": "Schlüssel"},
            {"lemma": "Fahrplan"},
        ]
        for item in valid_samples:
            with self.subTest(lemma=item["lemma"]):
                self.assertTrue(is_valid_target_word(item))

    def test_invalid_corporate_entities(self):
        invalid_entities = ["GmbH", "AG", "e.V.", "Ltd", "OHG", "KG", "KGaA"]
        for entity in invalid_entities:
            with self.subTest(lemma=entity):
                self.assertFalse(is_valid_target_word({"lemma": entity}))

    def test_invalid_abbreviations_and_names(self):
        invalid_noise = ["z.B.", "zb", "d.h.", "dh", "bzw.", "etc.", "Herr", "Frau", "Müller"]
        for word in invalid_noise:
            with self.subTest(lemma=word):
                self.assertFalse(is_valid_target_word({"lemma": word}))

    def test_valid_medical_short_terms(self):
        valid_short = ["OP", "CT", "EKG", "MRT", "HNO", "BMI", "HIV", "DNA"]
        for term in valid_short:
            with self.subTest(lemma=term):
                self.assertTrue(is_valid_target_word({"lemma": term}))

    def test_empty_or_invalid_inputs(self):
        self.assertFalse(is_valid_target_word({}))
        self.assertFalse(is_valid_target_word(None))
        self.assertFalse(is_valid_target_word({"lemma": ""}))
        self.assertFalse(is_valid_target_word({"lemma": "a"}))
        self.assertFalse(is_valid_target_word({"lemma": "1234"}))

if __name__ == '__main__':
    unittest.main()
