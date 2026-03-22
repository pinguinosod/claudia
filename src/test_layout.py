import unittest
import layout


class TestCalcStandard(unittest.TestCase):
    """Terminal 80×30 — equivalent to original fixed constants."""

    def test_hit_zone_row(self):
        L = layout.calc(80, 30)
        self.assertEqual(L.hit_zone_row, 22)

    def test_playfield_rows(self):
        L = layout.calc(80, 30)
        self.assertEqual(L.playfield_rows, L.hit_zone_row + L.ghost_rows)

    def test_marker_rows_positive(self):
        L = layout.calc(80, 30)
        self.assertGreater(L.ok_marker_row, 0)
        self.assertGreater(L.good_marker_row, L.ok_marker_row)


class TestClampingMinimum(unittest.TestCase):
    """Terminal 80×24 — minimum valid size."""

    def test_hit_zone_clamped(self):
        L = layout.calc(80, 24)
        self.assertEqual(L.hit_zone_row, 16)

    def test_playfield_rows_from_clamp(self):
        L = layout.calc(80, 24)
        self.assertEqual(L.playfield_rows, L.hit_zone_row + L.ghost_rows)


class TestLargeTerminal(unittest.TestCase):
    """Terminal 120×50 — large terminal."""

    def test_hit_zone_scales(self):
        L = layout.calc(120, 50)
        self.assertEqual(L.hit_zone_row, 42)

    def test_playfield_rows_scales(self):
        L = layout.calc(120, 50)
        self.assertEqual(L.playfield_rows, L.hit_zone_row + L.ghost_rows)


class TestDeterminism(unittest.TestCase):
    def test_same_input_same_output(self):
        a = layout.calc(100, 35)
        b = layout.calc(100, 35)
        self.assertEqual(a, b)


class TestGhostExpiryInvariant(unittest.TestCase):
    def test_invariant_holds_for_range(self):
        for rows in range(24, 61):
            L = layout.calc(80, rows)
            ghost_limit = L.hit_zone_row * (1.0 + 250 / 2000.0)
            self.assertLess(ghost_limit, L.playfield_rows,
                            f"Ghost expiry violated at rows={rows}")


class TestIsTerminalValid(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(layout.is_terminal_valid(80, 24))
        self.assertTrue(layout.is_terminal_valid(120, 50))

    def test_too_small(self):
        self.assertFalse(layout.is_terminal_valid(79, 24))
        self.assertFalse(layout.is_terminal_valid(80, 23))
        self.assertFalse(layout.is_terminal_valid(40, 10))


if __name__ == "__main__":
    unittest.main()
