# Publicar no seu domínio

Qualquer hospedagem de arquivos estáticos serve. Exemplo com a Cloudflare (Workers só com arquivos estáticos; confira os limites atuais do seu plano, como a quantidade de arquivos e o tamanho de cada um):

1. Monte a pasta de publicação com o prefixo da versão: copie o conteúdo de `saida/` (com o `indice.json.sig`) para `publicacao/v1/` e o arquivo `publicar/_headers` para `publicacao/`.
2. Copie `wrangler.exemplo.jsonc` para `wrangler.jsonc` e troque `seu-dominio.exemplo` pelo seu domínio. O `wrangler.jsonc` fica fora do Git.
3. Publique, a partir da pasta do projeto: `npx wrangler deploy --config publicar/wrangler.jsonc`.

Confira depois: `https://seu-dominio.exemplo/v1/indice.json`.
