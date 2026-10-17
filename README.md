# Seguir utilizadores do GitHub (API REST)

Script em Python puro (sem dependências externas) que segue utilizadores do
GitHub através da API oficial, com logs claros, respeito pelos limites de
taxa, checkpoint de progresso e limite diário de follows.

## Ficheiros

| Ficheiro | Descrição |
|---|---|
| `seguir_github.py` | Script principal — segue os utilizadores de uma lista |
| `criar_lista.py` | Gera `lista1000.txt` (1000 devs Python via Search API) |
| `nomes.txt` | Lista pequena de exemplo (um nome por linha) |
| `lista1000.txt` | Lista grande gerada pelo `criar_lista.py` |
| `.env` | Onde guardas o token (**nunca partilhar**) |
| `.env.example` | Modelo do `.env` |
| `checkpoint.json` | Progresso (criado automaticamente na 1.ª execução) |
| `LICENSE` | Licença MIT |

## Requisitos

- Python 3.8+ (usa apenas a biblioteca padrão)
- Um GitHub Personal Access Token com permissão de follow
  - Classic: scope `user:follow`
  - Fine-grained: permissão **Follow users**

## Configuração

1. Cria o token em <https://github.com/settings/tokens>
2. Coloca-o no ficheiro `.env`:

```
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

## Uso

```bash
# Lista pequena (nomes.txt)
python seguir_github.py

# Lista grande, limite de 50 nesta sessão
python seguir_github.py -f lista1000.txt -n 50

# Ajustar o limite diário (por omissão 400/dia)
python seguir_github.py -f lista1000.txt --max-diario 300

# Gerar a lista de 1000 devs Python
python criar_lista.py
```

### Opções

| Opção | Padrão | Descrição |
|---|---|---|
| `-f, --ficheiro` | `nomes.txt` | Ficheiro com os nomes (um por linha) |
| `-n, --limite` | `0` (sem limite) | Máximo de follows nesta sessão |
| `--max-diario` | `400` | Máximo de follows por dia |
| `--checkpoint` | `checkpoint.json` | Ficheiro de progresso |
| `--intervalo` | `8` | Segundos entre pedidos (mínimo 8) |

## Como funciona

1. Lê os nomes do ficheiro linha a linha (ignora vazios e comentários `#`).
2. Autentica com `Authorization: Bearer <token>`, `Accept:
   application/vnd.github+json` e `X-GitHub-Api-Version: 2022-11-28`.
3. Envia `PUT /user/following/{username}` por cada utilizador pendente.
4. Espera 8 segundos entre pedidos.

Códigos tratados:

| Código | Significado | Ação |
|---|---|---|
| `204` | Sucesso | Regista no checkpoint |
| `404` | Utilizador não existe | Regista e passa à frente |
| `401` | Token inválido | Termina |
| `403` / `429` | Limite de taxa | Pausa (Retry-After / X-RateLimit-Reset, mín. 60s) e repete (até 5x) |
| rede / `5xx` | Erro temporário | Repete (até 5x) |

## Checkpoint e limite diário

- Depois de cada `204`/`404` o nome é gravado em `checkpoint.json`.
- Podes fechar o script a meio (Ctrl+C) — na volta ele retoma onde parou.
- O contador de follows volta a zero à meia-noite; ao atingir `--max-diario`
  o script para e pede para correr no dia seguinte.

## Limites da API (GitHub)

- Limite primário: **5000 pedidos/hora** (usamos ~450/h com 8s de intervalo)
- Limite secundário: **900 pontos/minuto por endpoint**
- Recomendação: **300–500 follows/dia**; acima disso o anti-abuse do GitHub
  pode suspender a conta. Respeita sempre os
  [termos do GitHub](https://docs.github.com/site/terms).

## Licença

[MIT](LICENSE)
