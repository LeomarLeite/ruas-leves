# Endereços e formato

## Endereços
Publicados sob um prefixo com a versão (`/v1/`), todos arquivos estáticos:

| Endereço | Conteúdo |
|---|---|
| `/v1/indice.json` | índice geral, pequeno, com o SHA-256 de cada índice de estado |
| `/v1/indice.json.sig` | assinatura Ed25519 do índice geral: `v1.<base64url>` sobre `ruas-leves-v1\n` + os bytes do índice |
| `/v1/estados/TO.json` | os municípios do estado: tamanho, ruas, SHA-256 e data de cada arquivo |
| `/v1/<código IBGE>.ruas.gz` | as ruas do município |
| `/v1/LICENCA.txt` | aviso da licença dos dados |

**Como um app confere:** valida a assinatura do índice geral, o SHA-256 do índice do estado e o do arquivo do município. Para saber se precisa baixar de novo, compara o SHA-256 que guardou.

## `indice.json`
```json
{"version":1,"generatedAt":"2026-11-26T12:00:00Z","license":"ODbL-1.0",
 "attribution":"© OpenStreetMap contributors",
 "states":{"TO":{"cities":139,"bytes":0,"sha256":"…"}}}
```

## `estados/TO.json`
```json
{"uf":"TO","cities":{"1721000":{"bytes":0,"streets":0,"sha256":"…","generatedAt":"…"}}}
```

## `<código>.ruas.gz`
Compactado com gzip. Números em **varint** (7 bits por byte, os menos significativos primeiro; o bit alto indica que continua). Os com sinal usam **zigzag**.

1. Os 4 bytes `FRU1`.
2. Quantidade de nomes; para cada um, o tamanho em bytes e o texto em UTF-8. O primeiro é o texto vazio.
3. Quantidade de ruas; para cada uma:
   - 1 byte: os 2 bits baixos são a classe (1 principal, 2 secundária, 3 local); o bit de valor 4 marca **mão única**, e então os pontos estão no sentido permitido aos veículos (quem vai a pé pode ignorar);
   - índice do nome (varint);
   - quantidade de pontos (varint);
   - para cada ponto, a diferença de latitude e de longitude, em graus × 100.000, para o ponto anterior **do arquivo** (o primeiro parte de 0, 0).

A precisão é de cerca de 1 m; as linhas são simplificadas com folga de 5 m, **menos nos cruzamentos**: ruas que se encontram têm um ponto com a mesma coordenada, e com isso dá para calcular distâncias pelas ruas. O arquivo não traz restrições de conversão: serve para uma noção de distância, não para navegar. Nomes com mais de 80 caracteres são cortados.

Mudança incompatível = novo prefixo (`/v2/`) e nova marca no começo do arquivo.
