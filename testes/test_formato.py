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
            (3 | gerar.ONEWAY | gerar.UNPAVED, "", [(-10.5, -48.5), (-10.4, -48.4), (-10.3, -48.6)]),
        ]
        back = ler.read(gerar.pack(streets))
        self.assertEqual([(s[0], s[1], s[3], s[4]) for s in back],
                         [(1, "Avenida Um", False, False), (3, "", True, True)])
        for (_, _, wrote), (_, _, got, _, _) in zip(streets, back):
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

    def test_junctions_are_never_dropped(self):
        line = [(-10.0, -48.0), (-10.0, -48.001), (-10.0, -48.002), (-10.0, -48.003)]
        refs = [1, 2, 3, 4]
        self.assertEqual(gerar.simplify_keeping(line, refs, set()), [line[0], line[-1]])
        self.assertEqual(gerar.simplify_keeping(line, refs, {3}), [line[0], line[2], line[-1]])
        self.assertEqual(gerar.simplify_keeping(line[:2], refs[:2], {1, 2}), line[:2])

    def test_one_way_direction(self):
        self.assertEqual(gerar.direction({"oneway": "yes"}), 1)
        self.assertEqual(gerar.direction({"oneway": "-1"}), -1)
        self.assertEqual(gerar.direction({"junction": "roundabout"}), 1)
        self.assertEqual(gerar.direction({"junction": "roundabout", "oneway": "no"}), 0)
        self.assertEqual(gerar.direction({"highway": "motorway"}), 1)
        self.assertEqual(gerar.direction({"highway": "residential"}), 0)

    def test_unpaved_surface(self):
        for surface in ("unpaved", "Dirt", "ground", "gravel", "compacted"):
            self.assertTrue(gerar.unpaved({"surface": surface}), surface)
        for surface in ("asphalt", "paved", "concrete", "paving_stones", ""):
            self.assertFalse(gerar.unpaved({"surface": surface}), surface)
        self.assertFalse(gerar.unpaved({}))


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
