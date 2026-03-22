import unittest
import scoring


class TestAccuracyPct(unittest.TestCase):
    def test_accuracy_all_perfect(self):
        self.assertAlmostEqual(scoring.accuracy_pct(10, 0, 0, 10), 100.0)

    def test_accuracy_all_miss(self):
        self.assertAlmostEqual(scoring.accuracy_pct(0, 0, 0, 10), 0.0)

    def test_accuracy_mixed(self):
        # 5 perfect (5.0) + 3 good (2.1) + 2 ok (0.6) = 7.7 / 10 * 100 = 77.0
        self.assertAlmostEqual(scoring.accuracy_pct(5, 3, 2, 10), 77.0)

    def test_accuracy_zero_notes(self):
        self.assertAlmostEqual(scoring.accuracy_pct(0, 0, 0, 0), 100.0)


class TestGradeLetter(unittest.TestCase):
    def test_grade_splus_all_perfect(self):
        self.assertEqual(scoring.grade_letter(10, 0, 0, 0, 10), "S+")

    def test_grade_splus_zero_notes(self):
        self.assertEqual(scoring.grade_letter(0, 0, 0, 0, 0), "S+")

    def test_grade_s_no_miss_high_acc(self):
        # 19 perfect + 1 good, no miss: acc = (19 + 0.7) / 20 * 100 = 98.5%
        self.assertEqual(scoring.grade_letter(19, 1, 0, 0, 20), "S")

    def test_grade_s_requires_no_miss(self):
        # same accuracy but 1 miss → should not be "S"
        self.assertNotEqual(scoring.grade_letter(18, 1, 0, 1, 20), "S")

    def test_grade_boundaries(self):
        # A: acc >= 90, B: >= 80, C: >= 70, D: >= 50, F: < 50
        # 9 perfect + 1 miss, total=10: acc = 9.0/10*100 = 90% → A
        self.assertEqual(scoring.grade_letter(9, 0, 0, 1, 10), "A")
        # 8 perfect + 2 miss, total=10: acc = 80% → B
        self.assertEqual(scoring.grade_letter(8, 0, 0, 2, 10), "B")
        # 7 perfect + 3 miss, total=10: acc = 70% → C
        self.assertEqual(scoring.grade_letter(7, 0, 0, 3, 10), "C")
        # 4 perfect + 6 miss, total=10: acc = 40% → F
        self.assertEqual(scoring.grade_letter(4, 0, 0, 6, 10), "F")
        # 5 ok + 5 miss, total=10: acc = (5*0.3)/10*100 = 15% → F
        self.assertEqual(scoring.grade_letter(0, 0, 5, 5, 10), "F")
        # 5 perfect + 5 miss, total=10: acc = 50% → D
        self.assertEqual(scoring.grade_letter(5, 0, 0, 5, 10), "D")
        # 6 perfect + 4 miss, total=10: acc = 60% → D (was C before threshold change)
        self.assertEqual(scoring.grade_letter(6, 0, 0, 4, 10), "D")


class TestClearBadge(unittest.TestCase):
    def test_all_perfect(self):
        self.assertEqual(scoring.clear_badge(10, 0, 0, 0, 10), "PERFECT")

    def test_full_combo_with_good(self):
        self.assertEqual(scoring.clear_badge(8, 2, 0, 0, 10), "FULL COMBO")

    def test_miss_no_badge(self):
        self.assertEqual(scoring.clear_badge(8, 0, 0, 2, 10), "")

    def test_zero_notes_no_badge(self):
        self.assertEqual(scoring.clear_badge(0, 0, 0, 0, 0), "")


class TestNoteScore(unittest.TestCase):
    def test_note_score_all_perfect_full_combo_is_900k(self):
        # Last note of 10, no misses, all perfect → exactly 900K
        score = 0
        total = 10
        for i in range(1, total + 1):
            score = scoring.note_score(score, scoring.SCORE_WEIGHT_PERFECT, total, i, 0, i)
        self.assertEqual(score, 900_000)

    def test_note_score_rounding_N3(self):
        # 3-note all-PERFECT chart: each note_value = 300000
        # With branch, last note yields exactly 900_000
        score = 0
        total = 3
        for i in range(1, total + 1):
            score = scoring.note_score(score, scoring.SCORE_WEIGHT_PERFECT, total, i, 0, i)
        self.assertEqual(score, 900_000)

    def test_note_score_full_ok_not_900k(self):
        # All notes hit as OK, no misses → should NOT be 900K
        score = 0
        total = 10
        for i in range(1, total + 1):
            score = scoring.note_score(score, scoring.SCORE_WEIGHT_OK, total, i, 0, 0)
        self.assertLess(score, 900_000)
        self.assertEqual(score, round(total * (scoring.ACCURACY_SCORE_MAX / total) * scoring.SCORE_WEIGHT_OK))

    def test_note_score_partial(self):
        # 1 miss present → full-combo branch not taken
        # note 2 of 10, 1 miss: normal rounding
        score = 90_000
        new_score = scoring.note_score(score, scoring.SCORE_WEIGHT_PERFECT, 10, 2, 1, 0)
        self.assertNotEqual(new_score, 900_000)
        self.assertEqual(new_score, round(90_000 + 90_000 * 1.0))

    def test_note_score_cap(self):
        # Force a situation where arithmetic might exceed 900K
        score = 899_999
        new_score = scoring.note_score(score, scoring.SCORE_WEIGHT_PERFECT, 1, 0, 1, 0)
        self.assertLessEqual(new_score, 900_000)


class TestComboBonus(unittest.TestCase):
    def test_combo_bonus_full_combo(self):
        self.assertEqual(scoring.combo_bonus(10, 10), 100_000)

    def test_combo_bonus_half(self):
        self.assertEqual(scoring.combo_bonus(5, 10), 50_000)

    def test_combo_bonus_zero(self):
        self.assertEqual(scoring.combo_bonus(0, 10), 0)

    def test_combo_bonus_zero_notes(self):
        self.assertEqual(scoring.combo_bonus(0, 0), 0)

    def test_combo_bonus_capped_at_total(self):
        # max_combo can't exceed total_notes, but guard against it anyway
        self.assertEqual(scoring.combo_bonus(15, 10), 100_000)


class TestFinalScore(unittest.TestCase):
    def test_final_score_all_perfect(self):
        self.assertEqual(scoring.final_score(900_000, 10, 10), 1_000_000)

    def test_final_score_good_full_combo(self):
        # All GOOD: accuracy score = 10 * (900000/10) * 0.5 = 450_000
        self.assertEqual(scoring.final_score(450_000, 10, 10), 550_000)

    def test_final_score_no_combo(self):
        self.assertEqual(scoring.final_score(900_000, 0, 10), 900_000)

    def test_final_score_capped_at_1m(self):
        self.assertEqual(scoring.final_score(1_000_000, 10, 10), 1_000_000)


if __name__ == "__main__":
    unittest.main()
