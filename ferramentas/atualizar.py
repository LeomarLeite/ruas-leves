# Copyright (c) 2026 Leomar Leite (ruas-leves).
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
"""Atualização completa: baixa os extratos regionais, confere, gera e mostra o que mudou.

    python ferramentas/atualizar.py <tabela.json> <pasta dos extratos> <pasta de saída>

Baixa cerca de 2 GB da Geofabrik (https://download.geofabrik.de/south-america/brazil.html),
conferindo o MD5 de cada arquivo; um download cortado continua de onde parou na mesma execução.
Não publica nada. Os extratos ficam na pasta (a próxima vez só baixa o que mudou); com --apagar,
as cinco regiões são apagadas no fim.
"""

import hashlib
import http.client
import os
import subprocess
import sys
import urllib.error
import urllib.request

BASE = "https://download.geofabrik.de/south-america/brazil/"
REGIONS = ("norte", "centro-oeste", "sul", "nordeste", "sudeste")
AGENT = {"User-Agent": "ruas-leves"}
TRIES = 5


def remote_md5(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url + ".md5", headers=AGENT), timeout=60) as r:
        return r.read().decode("ascii").split()[0]


def file_md5(path: str) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, path: str) -> None:
    """Baixa para [path], continuando o que já houver."""
    have = os.path.getsize(path) if os.path.exists(path) else 0
    headers = dict(AGENT, **({"Range": f"bytes={have}-"} if have else {}))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
            mode = "ab" if r.status == 206 else "wb"
            with open(path, mode) as f:
                for block in iter(lambda: r.read(1 << 20), b""):
                    f.write(block)
    except urllib.error.HTTPError as error:
        if error.code != 416:  # 416 = já está inteiro
            raise


def fetch(region: str, folder: str) -> str:
    url = f"{BASE}{region}-latest.osm.pbf"
    path = os.path.join(folder, f"{region}-latest.osm.pbf")
    wanted = remote_md5(url)
    if os.path.exists(path) and file_md5(path) == wanted:
        print(f"{region}: já baixado e conferido")
        return path
    if os.path.exists(path):
        os.remove(path)  # versão antiga: começa de novo
    for attempt in range(1, TRIES + 1):
        try:
            download(url, path)
        except (OSError, http.client.HTTPException) as error:
            print(f"{region}: tentativa {attempt} cortada ({error})")
        if os.path.exists(path) and file_md5(path) == wanted:
            print(f"{region}: conferido ({os.path.getsize(path) / 1e6:.0f} MB)")
            return path
    raise SystemExit(f"{region}: o arquivo não conferiu; nada foi gerado")


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--apagar"]
    if len(args) != 3:
        raise SystemExit(__doc__)
    table, folder, out = args
    os.makedirs(folder, exist_ok=True)
    paths = [fetch(region, folder) for region in REGIONS]
    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, "-u", os.path.join(here, "gerar.py"), table, out, *paths], check=True)
    if "--apagar" in sys.argv:
        for path in paths:
            os.remove(path)
    print("pronto. Confira o resumo acima antes de assinar e publicar.")


if __name__ == "__main__":
    main()
