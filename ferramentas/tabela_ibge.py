# Copyright (c) 2026 Leomar Leite (ruas-leves).
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
"""Monta a tabela de municípios que o gerador usa (código, nome, estado e posição da sede).

A tabela não vem no repositório: baixe você mesmo o pacote "Localidades do Brasil" do IBGE
(arquivo Localidades_Brasil_gpkg.zip, em
https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/Localidades_do_Brasil/2022/),
confira os termos de uso do IBGE, extraia o .gpkg e rode:

    python ferramentas/tabela_ibge.py <arquivo.gpkg> tabela/municipios.json
"""

import io
import json
import os
import sqlite3
import sys
from pathlib import Path


def build(gpkg: str) -> dict:
    db = sqlite3.connect(Path(gpkg).resolve().as_uri() + "?mode=ro", uri=True)
    layer = db.execute("SELECT table_name FROM gpkg_contents").fetchone()[0]
    table: dict = {}
    rows = db.execute(
        f'SELECT CD_MUN, NM_MUN, SIGLA_UF, LAT_LOCALIDADE, LONG_LOCALIDADE FROM "{layer}" '
        "WHERE SCT_LOCALIDADE IN ('Sede Municipal', 'Capital Federal') ORDER BY SIGLA_UF, NM_MUN")
    for code, name, state, lat, lng in rows:
        table.setdefault(state, []).append([int(code), name, round(lat, 4), round(lng, 4)])
    # Quem não tem sede marcada (Fernando de Noronha) usa a primeira localidade do município.
    seated = {c[0] for entries in table.values() for c in entries}
    for code, name, state, lat, lng in db.execute(
            f'SELECT CD_MUN, NM_MUN, SIGLA_UF, LAT_LOCALIDADE, LONG_LOCALIDADE FROM "{layer}" '
            "ORDER BY CD_MUN"):
        if int(code) not in seated:
            seated.add(int(code))
            table.setdefault(state, []).append([int(code), name, round(lat, 4), round(lng, 4)])
    db.close()
    return table


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    table = build(sys.argv[1])
    os.makedirs(os.path.dirname(os.path.abspath(sys.argv[2])), exist_ok=True)
    with io.open(sys.argv[2], "w", encoding="utf-8", newline="\n") as out:
        out.write(json.dumps(table, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"{sum(len(v) for v in table.values())} municípios em {len(table)} estados")


if __name__ == "__main__":
    main()
