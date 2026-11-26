# Roadmap

## Objetivo
Ter **o próprio mapa de ruas**: arquivos pequenos por município, que qualquer pessoa gera, publica no próprio endereço e usa sem internet, **sem ficar presa a um fornecedor de mapas**.

## O que não pode ser quebrado
1. **Licença primeiro:** uma fonte de dados só entra depois de conferidos os termos dela. Nunca extrair de serviços que proíbem copiar ou criar bases (como o Google Maps). Os créditos e a licença de cada fonte acompanham os arquivos.
2. **Arquivos pequenos:** só ruas de carro e nomes.
3. **Sem servidor com código:** o resultado são arquivos estáticos, assinados.
4. **Formato estável:** mudança incompatível ganha versão nova (`/v2/` e nova marca no arquivo); quem usa a anterior continua funcionando.
5. **O formato não depende da fonte:** ler a origem e gravar os arquivos são partes separadas.
6. **Download gratuito** e código sob MPL 2.0.
7. **Nunca substituir arquivos bons por piores:** conferir o resumo da geração antes de publicar.

## ▶ Próximo passo
**1. Primeiro pacote do Brasil na aba Releases.**

## Etapas
| # | Etapa | Pronto quando | Situação |
|---|---|---|---|
| 1 | Pacote do Brasil nas Releases | geração completa, assinada, conferida e anexada, com o aviso da licença | a fazer |
| 2 | Proteger arquivos completos | gerar uma região só não troca um município completo por um parcial; teste cobrindo | a fazer |
| 3 | Atualização real de ponta a ponta | `atualizar.py` testado baixando as cinco regiões; publicação real conferida | a fazer |
| 4 | Testes automáticos no GitHub | os testes rodam a cada envio | a fazer |
| 5 | Avisar quando houver mudança | um comando (ou tarefa agendada) diz se a origem mudou, sem baixar tudo | a fazer |
| 6 | Retomar download interrompido | continuar mesmo depois de fechar o programa | a fazer |
| 7 | Pendências dos dados | Afuá (PA) sem arquivo investigado; termos de uso da base do IBGE conferidos | a fazer |
| 8 | Divulgação | tópicos no repositório e doações pelo GitHub Sponsors (o download segue grátis) | a fazer |
| 9 | Fontes independentes | leitor da origem separado do gravador, com a fonte atual sem mudança no resultado | a fazer |
| 10 | Segunda fonte | avaliar licença e qualidade (ex.: Faces de Logradouros do IBGE, Overture Maps) e comparar com a atual | depende da 9 |

## Rotina de atualização (quando as etapas 1 a 3 estiverem prontas)
1. `python ferramentas/atualizar.py tabela/municipios.json extratos saida`
2. Conferir o resumo: cidades novas, alteradas, sem arquivo e as que perderam muitas ruas.
3. `node ferramentas/assinar.mjs assinar saida` e depois `conferir`.
4. Publicar (veja [publicar/](publicar/)) e anexar o pacote a uma nova Release.

## Como manter este arquivo
Ao terminar uma etapa, mudar a situação com a data e atualizar o **▶ Próximo passo**. Ideia nova entra como linha na tabela, sem apagar as anteriores.
