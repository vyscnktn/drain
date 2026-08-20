import unittest
from app.services.llm_engine import calculate_unknown_ratio

class TestKrashenRatio(unittest.TestCase):
    def test_empty_text(self):
        ratio = calculate_unknown_ratio("", ["haus", "baum"])
        self.assertEqual(ratio, 0.0)

    def test_all_known_words(self):
        text = "Das Haus ist sehr groß und schön."
        known = ["das", "haus", "ist", "sehr", "groß", "und", "schön"]
        ratio = calculate_unknown_ratio(text, known)
        self.assertEqual(ratio, 0.0)

    def test_all_unknown_words(self):
        text = "Vollkommen unbekannte Vokabeln ohne Kontext."
        known = ["hund", "katze"]
        ratio = calculate_unknown_ratio(text, known)
        self.assertEqual(ratio, 1.0)

    def test_german_umlauts_and_sz(self):
        text = "Ärzte müssen regelmäßig Überweisungen prüfen."
        known = ["ärzte", "müssen", "regelmäßig", "überweisungen", "prüfen"]
        ratio = calculate_unknown_ratio(text, known)
        self.assertEqual(ratio, 0.0)

    def test_ninety_five_percent_target(self):
        # 20 words in total: 19 known, 1 unknown (5% unknown ratio -> 95% comprehensibility)
        known_words = [f"wort{i}" for i in range(1, 20)]
        unknown_word = "neueswort"
        text = " ".join(known_words) + f" {unknown_word}."
        
        ratio = calculate_unknown_ratio(text, known_words)
        self.assertAlmostEqual(ratio, 0.05, places=2)
        self.assertLessEqual(ratio, 0.40) # passes Krashen threshold

if __name__ == '__main__':
    unittest.main()
