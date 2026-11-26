# Copyright (c) 2026 Leomar Leite (ruas-leves).
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
"""ruas-leves: gera um arquivo compacto de ruas para cada município do Brasil.

Lê extratos regionais do OpenStreetMap (.osm.pbf), fica só com as ruas de carro e os nomes,
separa por município (limite administrativo de nível 8) e grava um arquivo por município, um
índice por estado, o índice geral e o aviso da licença. Dados © OpenStreetMap contributors,
licença ODbL 1.0. Formato em docs/formato.md.

Uso:
    python ferramentas/gerar.py <tabela.json> <pasta de saída> <extrato.osm.pbf> [mais...]
                                [--so=código,código]

Processe todas as regiões no mesmo comando: um município na divisa aparece incompleto no extrato
vizinho, e o gerador só fica com a versão mais completa dentro da mesma execução.
"""

import collections
import gzip
import hashlib
import io
import json
import math
import os
import sys
import time
import unicodedata
from datetime import datetime, timezone

import osmium

CLASSES = {
    "motorway": 1, "trunk": 1, "primary": 1, "motorway_link": 1, "trunk_link": 1,
    "primary_link": 1, "secondary": 2, "tertiary": 2, "secondary_link": 2,
    "tertiary_link": 2, "unclassified": 3, "residential": 3, "living_street": 3, "road": 3,
}
SIMPLIFY_METERS = 5
ONEWAY = 4  # somado à classe: os pontos seguem o sentido permitido aos veículos
CELL = 0.02  # graus: grade que evita testar o ponto contra todos os municípios
LICENSE = (
    "Ruas por município (ruas-leves).\n"
    "Contém dados de © OpenStreetMap contributors, disponíveis sob a Open Database License "
    "(ODbL) 1.0:\nhttps://opendatacommons.org/licenses/odbl/1-0/\n"
    "https://www.openstreetmap.org/copyright\n"
    "Estes arquivos são uma base derivada e são distribuídos sob a mesma licença.\n"
)
# O Distrito Federal não tem município no mapa (as regiões de nível 8 são administrativas): o
# limite do próprio DF vale para Brasília.
BRASILIA = 5300108


def key_of(text: str) -> str:
    """Nome sem acento, minúsculo e sem sinais, para casar com a tabela de municípios."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(c for c in plain.lower() if c.isalnum())


def inside(point, ring) -> bool:
    lat, lon = point
    hit = False
    for (a_lat, a_lon), (b_lat, b_lon) in zip(ring, ring[1:]):
        if (a_lat > lat) != (b_lat > lat):
            if lon < (b_lon - a_lon) * (lat - a_lat) / (b_lat - a_lat) + a_lon:
                hit = not hit
    return hit


class Cities:
    """Os limites dos municípios, com uma grade para achar depressa o de um ponto."""

    def __init__(self):
        self.shapes = {}  # código -> lista de (anel externo, caixa)
        self.border = collections.defaultdict(set)  # célula cortada por um limite
        self.whole = {}  # célula inteira dentro de um município (ou nenhum)

    def add(self, code, ring):
        lats = [p[0] for p in ring]
        lons = [p[1] for p in ring]
        box = (min(lats), min(lons), max(lats), max(lons))
        self.shapes.setdefault(code, []).append((ring, box))
        for a, b in zip(ring, ring[1:]):
            steps = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / (CELL / 2)) + 1
            for i in range(steps + 1):
                lat = a[0] + (b[0] - a[0]) * i / steps
                lon = a[1] + (b[1] - a[1]) * i / steps
                self.border[self._cell(lat, lon)].add(code)

    @staticmethod
    def _cell(lat, lon):
        return int(math.floor(lat / CELL)), int(math.floor(lon / CELL))

    def _test(self, point, codes):
        lat, lon = point
        for code in codes:
            for ring, (s, w, n, e) in self.shapes[code]:
                if s <= lat <= n and w <= lon <= e and inside(point, ring):
                    return code
        return None

    def find(self, point):
        cell = self._cell(*point)
        near = set()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                near |= self.border.get((cell[0] + dy, cell[1] + dx), set())
        if cell in self.border:
            return self._test(point, near) or self._test(point, self.shapes)
        if cell not in self.whole:
            centre = ((cell[0] + 0.5) * CELL, (cell[1] + 0.5) * CELL)
            self.whole[cell] = self._test(centre, near) or self._test(centre, self.shapes)
        return self.whole[cell]


def holds(rings, seat) -> bool:
    """A sede está dentro da caixa de algum anel do limite?"""
    if seat is None:
        return False
    return any(min(p[0] for p in r) <= seat[0] <= max(p[0] for p in r)
               and min(p[1] for p in r) <= seat[1] <= max(p[1] for p in r) for r in rings)


def read_cities(path, table, seats, cities, problems):
    names = collections.defaultdict(list)
    for code, (name, uf) in table.items():
        names[key_of(name)].append(code)
    processor = (osmium.FileProcessor(path)
                 .with_areas(osmium.filter.KeyFilter("admin_level"))
                 .with_filter(osmium.filter.EntityFilter(osmium.osm.AREA)))
    for area in processor:
        tags = area.tags
        if tags.get("boundary") != "administrative":
            continue
        level = tags.get("admin_level")
        federal = level == "4" and tags.get("ISO3166-2") == "BR-DF"
        if level != "8" and not federal:
            continue
        raw = (tags.get("IBGE:GEOCODIGO") or "").strip()
        code = int(raw) if raw.isdigit() and int(raw) in table else None
        if federal:
            code = BRASILIA if BRASILIA in table else None
        rings = [[(n.lat, n.lon) for n in outer] for outer in area.outer_rings()]
        rings = [r for r in rings if len(r) > 3]
        if code is None:
            # Só pelo nome, o limite precisa conter a sede: há bairros e regiões de nível 8 com o
            # nome de um município de outro estado (ex.: no Distrito Federal).
            same = [c for c in names.get(key_of(tags.get("name", "")), [])
                    if holds(rings, seats.get(c))]
            code = same[0] if len(same) == 1 else None
        if code is None:
            problems.append(tags.get("name", "?"))
            continue
        for ring in rings:
            cities.add(code, ring)


def simplify(points, meters):
    """Douglas-Peucker em metros (aproximação plana, suficiente para uma cidade)."""
    if len(points) < 3:
        return points
    k = math.cos(math.radians(points[0][0]))
    xy = [(lon * 111320 * k, lat * 110540) for lat, lon in points]
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = xy[a]
        dx, dy = xy[b][0] - ax, xy[b][1] - ay
        length = math.hypot(dx, dy)
        best, far = None, 0.0
        for i in range(a + 1, b):
            px, py = xy[i][0] - ax, xy[i][1] - ay
            d = abs(dx * py - dy * px) / length if length else math.hypot(px, py)
            if d > far:
                best, far = i, d
        if best is not None and far > meters:
            keep.add(best)
            stack += [(a, best), (best, b)]
    return [points[i] for i in sorted(keep)]


def simplify_keeping(points, refs, shared):
    """Simplifica só entre os cruzamentos: o ponto em que as ruas se encontram nunca sai, para
    quem usa o arquivo poder seguir de uma rua para outra."""
    out, start = [], 0
    for i in range(1, len(points)):
        if i == len(points) - 1 or refs[i] in shared:
            part = simplify(points[start:i + 1], SIMPLIFY_METERS)
            out += part if not out else part[1:]
            start = i
    return out


def junctions(path) -> set:
    """Os nós usados mais de uma vez pelas ruas de carro do extrato."""
    processor = (osmium.FileProcessor(path)
                 .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
                 .with_filter(osmium.filter.KeyFilter("highway")))
    seen, shared = set(), set()
    for way in processor:
        if way.tags.get("highway") not in CLASSES:
            continue
        for node in way.nodes:
            (shared if node.ref in seen else seen).add(node.ref)
    return shared


def direction(tags) -> int:
    """1 = mão única no sentido dos pontos; -1 = no sentido contrário; 0 = mão dupla."""
    value = tags.get("oneway")
    if value in ("yes", "true", "1"):
        return 1
    if value in ("-1", "reverse"):
        return -1
    if value is None and (tags.get("junction") in ("roundabout", "circular")
                          or tags.get("highway") == "motorway"):
        return 1  # rotatórias e rodovias são de mão única mesmo sem a marca
    return 0


def varint(n, out):
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return


def signed(n, out):
    varint(n * 2 if n >= 0 else -n * 2 - 1, out)


def pack(streets) -> bytes:
    """[streets] = lista de (classe, nome, [(lat, lon)]); classe + ONEWAY = mão única."""
    names = {"": 0}
    for _, name, _ in streets:
        names.setdefault(name, len(names))
    out = bytearray(b"FRU1")
    varint(len(names), out)
    for name in names:
        text = name.encode("utf-8")
        varint(len(text), out)
        out += text
    varint(len(streets), out)
    last = (0, 0)
    for cls, name, points in streets:
        out.append(cls)
        varint(names[name], out)
        varint(len(points), out)
        for lat, lon in points:
            q = (round(lat * 1e5), round(lon * 1e5))
            signed(q[0] - last[0], out)
            signed(q[1] - last[1], out)
            last = q
    return gzip.compress(bytes(out), 9, mtime=0)


# Município sem limite montado no extrato: as ruas que não são de nenhum outro e ficam perto da
# sede dele (graus; ~9 km).
NEAR_SEAT = 0.08


def near_seat(point, seats):
    lat, lon = point
    for code, (s_lat, s_lon) in seats:
        if abs(lat - s_lat) <= NEAR_SEAT and abs(lon - s_lon) <= NEAR_SEAT:
            return code
    return None


def read_streets(path, cities, found, orphans):
    shared = junctions(path)
    processor = (osmium.FileProcessor(path)
                 .with_locations()
                 .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
                 .with_filter(osmium.filter.KeyFilter("highway")))
    outside = 0
    for way in processor:
        cls = CLASSES.get(way.tags.get("highway"))
        if cls is None:
            continue
        nodes = [(n.ref, (n.lat, n.lon)) for n in way.nodes if n.location.valid()]
        points = [p for _, p in nodes]
        if len(points) < 2:
            continue
        middle = points[len(points) // 2]
        code = cities.find(middle) or near_seat(middle, orphans)
        if code is None:
            outside += 1
            continue
        name = (way.tags.get("name") or "")[:80]
        line = simplify_keeping(points, [r for r, _ in nodes], shared)
        way_direction = direction(way.tags)
        if way_direction:
            cls |= ONEWAY
            if way_direction < 0:
                line = line[::-1]
        found[code].append((cls, name, line))
    return outside


def write_json(path, data) -> bytes:
    text = (json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
    with open(path, "wb") as f:
        f.write(text)
    return text


def load_index(out) -> dict:
    """O que a pasta de saída já tem: código (texto) -> dados do município."""
    found = {}
    folder = os.path.join(out, "estados")
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            with io.open(os.path.join(folder, name), encoding="utf-8") as f:
                found.update(json.load(f)["cities"])
    return found


def write_indexes(out, table, cities, generated) -> None:
    """Um índice por estado e o índice geral (pequeno), com o SHA-256 de cada estado."""
    os.makedirs(os.path.join(out, "estados"), exist_ok=True)
    by_state = collections.defaultdict(dict)
    for code, data in cities.items():
        by_state[table[int(code)][1]][code] = data
    states = {}
    for uf, found in sorted(by_state.items()):
        text = write_json(os.path.join(out, "estados", f"{uf}.json"), {"uf": uf, "cities": found})
        states[uf] = {"cities": len(found), "bytes": sum(v["bytes"] for v in found.values()),
                      "sha256": hashlib.sha256(text).hexdigest()}
    write_json(os.path.join(out, "indice.json"), {
        "version": 1, "generatedAt": generated, "license": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors", "states": states})


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--so=")]
    # --so=código[,código]: grava só esses municípios (refazer um sem mexer nos outros).
    only = {int(c) for a in sys.argv[1:] if a.startswith("--so=") for c in a[5:].split(",")}
    if len(args) < 3:
        raise SystemExit(__doc__)
    table_path, out, extracts = args[0], args[1], args[2:]
    os.makedirs(out, exist_ok=True)
    with io.open(table_path, encoding="utf-8") as f:
        listed = json.load(f)
    table = {c[0]: (c[1], uf) for uf, entries in listed.items() for c in entries}
    seats = {c[0]: (c[2], c[3]) for entries in listed.values() for c in entries if len(c) >= 4}
    # quem saiu da tabela sai também do índice
    before = {k: v for k, v in load_index(out).items() if int(k) in table}
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    written = {}  # código -> dados gravados nesta execução
    for path in extracts:
        started = time.time()
        cities, problems = Cities(), []
        read_cities(path, table, seats, cities, problems)
        print(f"{os.path.basename(path)}: {len(cities.shapes)} municípios com limite "
              f"({time.time() - started:.0f} s)", flush=True)
        streets = collections.defaultdict(list)
        orphans = [(code, seat) for code, seat in seats.items() if code not in cities.shapes]
        outside = read_streets(path, cities, streets, orphans)
        for code, found in streets.items():
            if only and code not in only:
                continue
            key = str(code)
            if key in written and written[key]["streets"] >= len(found):
                continue  # divisa de extratos: fica a versão com mais ruas
            data = pack(found)
            with open(os.path.join(out, f"{code}.ruas.gz"), "wb") as f:
                f.write(data)
            sha = hashlib.sha256(data).hexdigest()
            old = before.get(key)
            written[key] = {"bytes": len(data), "streets": len(found), "sha256": sha,
                            # sem mudança no conteúdo, a data antiga fica
                            "generatedAt": old["generatedAt"] if old and old["sha256"] == sha else generated}
        print(f"  {len(streets)} municípios com ruas, {outside} ruas fora de município, "
              f"{time.time() - started:.0f} s no total", flush=True)
        if problems:
            print(f"  limites sem município na tabela: {len(problems)} (ex.: {', '.join(problems[:5])})")
    index = {**before, **written}
    if not index:
        raise SystemExit("nenhum município gerado: confira a tabela e os extratos")
    write_indexes(out, table, index, generated)
    with io.open(os.path.join(out, "LICENCA.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(LICENSE)
    report(table, before, written, index)


def report(table, before, written, index) -> None:
    sizes = sorted((v["bytes"], k) for k, v in index.items())
    total = sum(s for s, _ in sizes)
    print(f"total: {len(sizes)} municípios, {total / 1e6:.1f} MB; média {total / len(sizes) / 1e3:.1f} KB; "
          f"mediana {sizes[len(sizes) // 2][0] / 1e3:.1f} KB")
    for size, code in sizes[-5:]:
        print(f"  maior: {table[int(code)][0]} - {table[int(code)][1]}: {size / 1e3:.0f} KB")
    if before:
        new = [k for k in written if k not in before]
        changed = [k for k in written if k in before and before[k]["sha256"] != written[k]["sha256"]]
        lost = [k for k in changed if written[k]["streets"] < before[k]["streets"] * 0.8]
        print(f"desde a geração anterior: {len(new)} novos, {len(changed)} alterados")
        for k in lost[:20]:
            print(f"  ATENÇÃO: {table[int(k)][0]} - {table[int(k)][1]} perdeu ruas: "
                  f"{before[k]['streets']} -> {written[k]['streets']}")
    missing = [f"{n} - {uf}" for code, (n, uf) in table.items() if str(code) not in index]
    print(f"sem arquivo: {len(missing)} ({', '.join(missing[:10])})")


if __name__ == "__main__":
    main()
