# Copyright (c) 2026 Leomar Leite (ruas-leves).
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
"""Testes com dados inventados: formato, simplificação e a escolha do município de um ponto.

    python -m unittest discover -s testes
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ferramentas"))

import gerar  # noqa: E402
import ler  # noqa: E402


def square(lat, lng, size):
    return [(lat, lng), (lat + size, lng), (lat + size, lng + size), (lat, lng + size), (lat, lng)]


class Format(unittest.TestCase):
    def test_write_and_read_back(self):
        streets = [
            (1, "Avenida Um", [(-10.0, -48.0), (-10.001, -48.002)]),
            (3, "", [(-10.5, -48.5), (-10.4, -48.4), (-10.3, -48.6)]),
        ]
        back = ler.read(gerar.pack(streets))
        self.assertEqual([(k, n) for k, n, _ in back], [(1, "Avenida Um"), (3, "")])
        for (_, _, wrote), (_, _, got) in zip(streets, back):
            for a, b in zip(wrote, got):
                self.assertAlmostEqual(a[0], b[0], places=5)
                self.assertAlmostEqual(a[1], b[1], places=5)

    def test_same_content_same_bytes(self):
        streets = [(2, "Rua", [(-10.0, -48.0), (-10.1, -48.1)])]
        self.assertEqual(gerar.pack(streets), gerar.pack(streets))

    def test_simplify_drops_points_on_the_line(self):
        line = [(-10.0, -48.0), (-10.0, -48.001), (-10.0, -48.002)]
        self.assertEqual(gerar.simplify(line, 5), [line[0], line[-1]])
        corner = [(-10.0, -48.0), (-10.01, -48.001), (-10.0, -48.002)]
        self.assertEqual(gerar.simplify(corner, 5), corner)


class Boundaries(unittest.TestCase):
    def test_find_city_of_a_point(self):
        cities = gerar.Cities()
        cities.add(1, square(-10.0, -48.0, 0.5))
        cities.add(2, square(-10.0, -47.5, 0.5))
        self.assertEqual(cities.find((-9.8, -47.8)), 1)
        self.assertEqual(cities.find((-9.8, -47.2)), 2)
        self.assertEqual(cities.find((-9.8, -47.501)), 1)
        self.assertIsNone(cities.find((-5.0, -40.0)))

    def test_name_only_match_needs_the_town_inside(self):
        rings = [square(-16.0, -48.0, 0.2)]
        self.assertTrue(gerar.holds(rings, (-15.9, -47.9)))
        self.assertFalse(gerar.holds(rings, (-11.0, -47.9)))
        self.assertFalse(gerar.holds(rings, None))


if __name__ == "__main__":
    unittest.main()
