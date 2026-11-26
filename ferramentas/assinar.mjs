#!/usr/bin/env node
// Copyright (c) 2026 Leomar Leite (ruas-leves).
// This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
// If a copy of the MPL was not distributed with this file, You can obtain one at
// https://mozilla.org/MPL/2.0/.
//
// Assina o índice geral com Ed25519, para quem baixa saber que os arquivos são os seus. O índice
// geral leva o SHA-256 de cada índice de estado, e o do estado o de cada município: uma
// assinatura cobre tudo.
//
//   node ferramentas/assinar.mjs gerar-chaves
//   node ferramentas/assinar.mjs assinar <pasta de saída>      (chave privada em RUAS_CHAVE)
//   node ferramentas/assinar.mjs conferir <pasta de saída> <chave pública>
import { createHash, webcrypto } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

const { subtle } = webcrypto;
const CONTEXT = Buffer.from("ruas-leves-v1\n");
const text = (bytes) => Buffer.from(bytes).toString("base64url");
const bytes = (value) => new Uint8Array(Buffer.from(value.trim(), "base64url"));
const sha256 = (data) => createHash("sha256").update(data).digest("hex");

async function main([command, folder, publicKey]) {
  if (command === "gerar-chaves") {
    const pair = await subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    console.log(`pública:  ${text(await subtle.exportKey("raw", pair.publicKey))}`);
    console.log(`privada:  ${text(await subtle.exportKey("pkcs8", pair.privateKey))}`);
    console.log("Guarde a privada num cofre de senhas. Nunca a coloque no repositório.");
    return 0;
  }
  if (command === "assinar" && folder) {
    const secret = process.env.RUAS_CHAVE?.trim();
    if (!secret) throw new Error("defina a variável RUAS_CHAVE com a chave privada");
    const index = await readFile(join(folder, "indice.json"));
    const key = await subtle.importKey("pkcs8", bytes(secret), { name: "Ed25519" }, false, ["sign"]);
    const signature = await subtle.sign({ name: "Ed25519" }, key, Buffer.concat([CONTEXT, index]));
    await writeFile(join(folder, "indice.json.sig"), `v1.${text(signature)}\n`, "utf-8");
    console.log("índice assinado");
    return 0;
  }
  if (command === "conferir" && folder && publicKey) {
    const index = await readFile(join(folder, "indice.json"));
    const header = (await readFile(join(folder, "indice.json.sig"), "utf-8")).trim();
    const key = await subtle.importKey("raw", bytes(publicKey), { name: "Ed25519" }, false, ["verify"]);
    const signed =
      header.startsWith("v1.") &&
      (await subtle.verify({ name: "Ed25519" }, key, bytes(header.slice(3)), Buffer.concat([CONTEXT, index])));
    if (!signed) throw new Error("a assinatura não confere");
    let cities = 0;
    for (const [state, info] of Object.entries(JSON.parse(index).states)) {
      const file = await readFile(join(folder, "estados", `${state}.json`));
      if (sha256(file) !== info.sha256) throw new Error(`índice de ${state} diferente`);
      for (const [code, city] of Object.entries(JSON.parse(file).cities)) {
        const data = await readFile(join(folder, `${code}.ruas.gz`));
        if (data.length !== city.bytes || sha256(data) !== city.sha256) {
          throw new Error(`${code}.ruas.gz diferente do índice`);
        }
        cities += 1;
      }
    }
    console.log(`assinatura e ${cities} arquivos conferidos`);
    return 0;
  }
  console.error("uso: gerar-chaves | assinar <pasta> | conferir <pasta> <chave pública>");
  return 1;
}

main(process.argv.slice(2)).then(
  (code) => process.exit(code),
  (error) => {
    console.error(error.message);
    process.exit(1);
  },
);
