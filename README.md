# ruas-leves

Um arquivo pequeno de ruas por município do Brasil, para desenhar um mapa simples no celular **sem depender de um serviço de imagens** e sem internet depois de baixado.

*Lightweight per-city street files for Brazil, generated from OpenStreetMap, to draw a simple offline map. Docs are in Portuguese.*

| Medida (geração de novembro de 2026) | Valor |
|---|---|
| Arquivos | 5.570 dos 5.571 municípios (Afuá, no Pará, ficou sem arquivo) |
| Total | cerca de 119 MB |
| Mediana por município | cerca de 13 KB |
| Maior (São Paulo) | cerca de 1,6 MB |

Cada arquivo tem só as **ruas de carro, os nomes, a mão única e a marca de rua sem asfalto**, com os cruzamentos preservados (dá para estimar distâncias pelas ruas): sem prédios, comércios, parques ou rios.

## Baixar os arquivos prontos
O pacote com o Brasil inteiro sai na aba **Releases** deste repositório. Os arquivos seguem a licença do OpenStreetMap: veja [DADOS.md](DADOS.md).

Este projeto **não oferece um serviço de download**: quem for usar publica os arquivos no próprio endereço.

## Gerar os seus
Precisa de Python 3.10 ou mais novo, Node 20 ou mais novo (só para assinar), cerca de 3 GB livres e, de preferência, 8 GB de memória (o pico medido foi de 5,1 GB).

```bash
python -m venv .venv
source .venv/bin/activate          # no Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

1. **Tabela de municípios** (uma vez): baixe o pacote "Localidades do Brasil" do IBGE e rode
   `python ferramentas/tabela_ibge.py <arquivo.gpkg> tabela/municipios.json`. A tabela não vem no repositório; confira os termos de uso do IBGE.
2. **Gerar:** `python ferramentas/atualizar.py tabela/municipios.json extratos saida`
   Baixa as cinco regiões (cerca de 2 GB), confere cada arquivo e gera tudo. Levou cerca de 45 minutos num computador comum. Os extratos ficam na pasta; com `--apagar`, são removidos no fim.
3. **Conferir o resumo:** ele mostra o total, os maiores, o que mudou desde a última vez e avisa quando uma cidade perdeu muitas ruas.
4. **Assinar:** `node ferramentas/assinar.mjs gerar-chaves` (uma vez); depois, com a chave privada na variável `RUAS_CHAVE`, `node ferramentas/assinar.mjs assinar saida`.
5. **Publicar** no seu domínio: veja [publicar/](publicar/).

Testes: `python -m unittest discover -s testes` (usam dados inventados).

## Painel de administração
Não há: são ferramentas de linha de comando, e o resultado são arquivos estáticos, sem código no servidor.

## Usar no seu app
Os endereços e o formato estão em [docs/formato.md](docs/formato.md); [ferramentas/ler.py](ferramentas/ler.py) é um leitor de referência sem dependências.

## Contribuir
- **Rua faltando ou errada?** Corrija no [OpenStreetMap](https://www.openstreetmap.org): a correção chega a todos na geração seguinte.
- **Melhoria no gerador?** Abra um pull request.

## Licenças e créditos
- **Código:** Mozilla Public License 2.0 (arquivo `LICENSE`). Quem modificar arquivos deste projeto publica as mudanças deles; o app que os usa pode continuar fechado.
- **Dados:** © OpenStreetMap contributors, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
- **Crédito:** ruas-leves, de Leomar Leite (arquivo [NOTICE.md](NOTICE.md)).

Sem garantia de nenhum tipo: confira os dados antes de depender deles.
