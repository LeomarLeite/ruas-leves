# Copyright (c) 2026 Leomar Leite (ruas-leves).
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
"""Leitor de referência do formato (docs/formato.md), sem dependências.

    python ferramentas/ler.py <arquivo.ruas.gz>
"""

import gzip
import sys


def read(data: bytes) -> list:
    """Devolve [(classe, nome, [(latitude, longitude)], mão única)] de um arquivo .ruas.gz.

    Na mão única, os pontos seguem o sentido permitido aos veículos.
    """
    raw = gzip.decompress(data)
    if raw[:4] != b"FRU1":
        raise ValueError("não é um arquivo de ruas (FRU1)")
    at = 4

    def number() -> int:
        nonlocal at
        value = shift = 0
        while True:
            byte = raw[at]
            at += 1
            value |= (byte & 0x7F) << shift
            shift += 7
            if byte < 0x80:
                return value

    def signed() -> int:
        value = number()
        return (value >> 1) ^ -(value & 1)

    names = []
    for _ in range(number()):
        size = number()
        names.append(raw[at:at + size].decode("utf-8"))
        at += size
    streets, lat, lng = [], 0, 0
    for _ in range(number()):
        kind = raw[at]
        at += 1
        name = names[number()]
        points = []
        for _ in range(number()):
            lat += signed()
            lng += signed()
            points.append((lat / 1e5, lng / 1e5))
        streets.append((kind & 3, name, points, bool(kind & 4)))
    if at != len(raw):
        raise ValueError("sobraram dados no fim do arquivo")
    return streets


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    with open(sys.argv[1], "rb") as f:
        streets = read(f.read())
    names = sorted({name for _, name, _, _ in streets if name})
    print(f"{len(streets)} ruas, {sum(len(s[2]) for s in streets)} pontos, {len(names)} nomes, {sum(s[3] for s in streets)} de mão única")
    for name in names[:10]:
        print(" ", name)


if __name__ == "__main__":
    main()
