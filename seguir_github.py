#!/usr/bin/env python3
"""
Automatiza o seguimento de utilizadores na API do GitHub.

- Lê os nomes de utilizador linha a linha (por omissão "nomes.txt").
- Autentica com um Personal Access Token (Bearer).
- Faz PUT para /user/following/{username}.
- Respeita limites de taxa e espera 8 segundos entre pedidos.
- Guarda progresso em checkpoint.json (retoma se fechar a meio).
- Limite diário de follows (por omissão 400/dia).

Uso:
    1. Coloca o token no ficheiro .env:  GITHUB_TOKEN=ghp_xxxxxxxx
    2. python seguir_github.py [-f lista.txt] [-n 50] [--max-diario 400]

Também aceita a variável de ambiente GITHUB_TOKEN / GH_TOKEN
(a variável de ambiente tem prioridade sobre o .env).

Sem dependências externas (apenas biblioteca padrão).
"""

import argparse
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"
ARQUIVO_NOMES = "nomes.txt"
ARQUIVO_ENV = ".env"
ARQUIVO_CHECKPOINT = "checkpoint.json"
INTERVALO_MINIMO = 8
INTERVALO_PADRAO = 8
PAUSA_RATE_LIMIT = 60
TENTATIVAS_MAX = 5
TIMEOUT_PEDIDO = 30
MAX_DIARIO_PADRAO = 400


# --------------------------------------------------------------------------- #
# Utilidades de output
# --------------------------------------------------------------------------- #
def log(mensagem):
    print(mensagem, flush=True)


def _cor(texto, codigo):
    if not sys.stdout.isatty():
        return texto
    return f"\033[{codigo}m{texto}\033[0m"


def verde(texto):
    return _cor(texto, "32")


def amarelo(texto):
    return _cor(texto, "33")


def vermelho(texto):
    return _cor(texto, "31")


def ciano(texto):
    return _cor(texto, "36")


def hoje():
    return time.strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# Autenticação e leitura do ficheiro
# --------------------------------------------------------------------------- #
def carregar_env(caminho=ARQUIVO_ENV):
    """Carrega CHAVE=VALOR do .env sem sobrepor variáveis já definidas."""
    if not os.path.isfile(caminho):
        return

    with open(caminho, "r", encoding="utf-8") as ficheiro:
        for linha in ficheiro:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            chave = chave.strip()
            valor = valor.strip().strip('"').strip("'")
            if chave and valor and chave not in os.environ:
                os.environ[chave] = valor


def obter_token():
    carregar_env()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    token = token.strip() if token else ""
    if token:
        return token

    log(
        vermelho(
            f"Erro: nenhum token encontrado. Coloca GITHUB_TOKEN=... "
            f"no ficheiro {ARQUIVO_ENV} ou define a variavel de ambiente."
        )
    )
    token = getpass.getpass(
        "Introduz o GitHub Personal Access Token (nao e guardado): "
    ).strip()
    if not token:
        sys.exit(vermelho("Erro: nenhum token fornecido."))
    return token


def ler_nomes(caminho):
    if not os.path.isfile(caminho):
        sys.exit(vermelho(f"Erro: ficheiro '{caminho}' nao encontrado."))

    nomes = []
    with open(caminho, "r", encoding="utf-8") as ficheiro:
        for numero, linha in enumerate(ficheiro, start=1):
            nome = linha.strip()
            if not nome or nome.startswith("#"):
                continue
            if nome.startswith("@"):
                nome = nome[1:]
            if not nome:
                continue
            if " " in nome or "/" in nome:
                log(
                    amarelo(
                        f"Aviso: linha {numero} ignorada (nome invalido): {nome}"
                    )
                )
                continue
            nomes.append(nome)
    return nomes


# --------------------------------------------------------------------------- #
# Checkpoint (progresso)
# --------------------------------------------------------------------------- #
def carregar_checkpoint(caminho):
    dados = {"dia": hoje(), "processados": [], "feitos_hoje": 0}
    if os.path.isfile(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as ficheiro:
                bruto = json.load(ficheiro)
            if isinstance(bruto, dict):
                dados["processados"] = [
                    str(x) for x in bruto.get("processados", [])
                ]
                dados["dia"] = str(bruto.get("dia") or hoje())
                dados["feitos_hoje"] = int(bruto.get("feitos_hoje", 0) or 0)
        except (OSError, ValueError):
            log(amarelo("Aviso: checkpoint ilegivel; a comecar do zero."))

    if dados["dia"] != hoje():
        dados["dia"] = hoje()
        dados["feitos_hoje"] = 0
    return dados


def guardar_checkpoint(caminho, dados):
    temporario = caminho + ".tmp"
    with open(temporario, "w", encoding="utf-8") as ficheiro:
        json.dump(dados, ficheiro, ensure_ascii=False, indent=0)
    os.replace(temporario, caminho)


# --------------------------------------------------------------------------- #
# Pedido á API
# --------------------------------------------------------------------------- #
def _obter_retry_after(headers):
    """Devolve os segundos a esperar, com base nos cabeçalhos de rate limit."""
    if headers is None:
        return PAUSA_RATE_LIMIT

    retry_after = headers.get("Retry-After")
    if retry_after:
        try:
            return max(int(float(retry_after)), INTERVALO_MINIMO)
        except ValueError:
            pass

    reset = headers.get("X-RateLimit-Reset")
    if reset:
        try:
            espera = int(reset) - int(time.time()) + 1
            return max(espera, INTERVALO_MINIMO)
        except ValueError:
            pass

    return PAUSA_RATE_LIMIT


def seguir_utilizador(token, username):
    """
    Envia PUT /user/following/{username}.

    Devolve (codigo, retry_after, mensagem).
    codigo = None quando falha de rede.
    """
    url = f"{API_BASE}/user/following/{urllib.parse.quote(username)}"
    pedido = urllib.request.Request(url, method="PUT")
    pedido.add_header("Authorization", f"Bearer {token}")
    pedido.add_header("Accept", "application/vnd.github+json")
    pedido.add_header("X-GitHub-Api-Version", API_VERSION)
    pedido.add_header("User-Agent", "github-follow-script")

    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT_PEDIDO) as resposta:
            return resposta.status, _obter_retry_after(resposta.headers), ""
    except urllib.error.HTTPError as erro:
        corpo = erro.read().decode("utf-8", errors="replace")[:300]
        return erro.code, _obter_retry_after(erro.headers), corpo
    except urllib.error.URLError as erro:
        return None, None, str(erro.reason)
    except Exception as erro:  # noqa: BLE001
        return None, None, str(erro)


# --------------------------------------------------------------------------- #
# Programa principal
# --------------------------------------------------------------------------- #
def parse_args():
    parser = argparse.ArgumentParser(
        description="Segue utilizadores do GitHub via API."
    )
    parser.add_argument(
        "-f", "--ficheiro", default=ARQUIVO_NOMES,
        help=f"ficheiro com os nomes (por omissao: {ARQUIVO_NOMES})",
    )
    parser.add_argument(
        "-n", "--limite", type=int, default=0,
        help="maximo de follows nesta sessao (0 = sem limite)",
    )
    parser.add_argument(
        "--max-diario", type=int, default=MAX_DIARIO_PADRAO,
        help=f"maximo de follows por dia (por omissao: {MAX_DIARIO_PADRAO})",
    )
    parser.add_argument(
        "--checkpoint", default=ARQUIVO_CHECKPOINT,
        help=f"ficheiro de progresso (por omissao: {ARQUIVO_CHECKPOINT})",
    )
    parser.add_argument(
        "--intervalo", type=int, default=INTERVALO_PADRAO,
        help=f"segundos entre pedidos (minimo {INTERVALO_MINIMO})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    intervalo = max(args.intervalo, INTERVALO_MINIMO)

    nomes = ler_nomes(args.ficheiro)
    if not nomes:
        sys.exit(vermelho(f"Erro: '{args.ficheiro}' nao contem nomes validos."))

    checkpoint = carregar_checkpoint(args.checkpoint)
    processados = set(checkpoint["processados"])
    pendentes = [nome for nome in nomes if nome not in processados]

    if not pendentes:
        log(verde(f"Nothing to do: os {len(nomes)} nomes ja foram processados."))
        return

    token = obter_token()
    posicao = {nome: indice + 1 for indice, nome in enumerate(nomes)}
    total = len(nomes)

    sessao_sucessos = 0
    sessao_nao_encontrados = 0
    sessao_falhas = 0
    sessao_rate_limits = 0
    motivo_paragem = "lista concluida"

    log(ciano("=" * 60))
    log(ciano(f" Lista: {total} nomes | ja processados: {total - len(pendentes)}"))
    log(ciano(f" Nesta sessao: {len(pendentes)} pendente(s)"))
    log(ciano(f" Hoje: {checkpoint['feitos_hoje']}/{args.max_diario} follows"))
    log(ciano(f" Intervalo entre pedidos: {intervalo}s"))
    log(ciano("=" * 60))

    for username in pendentes:
        indice = posicao[username]
        prefixo = f"[{indice}/{total}]"

        if args.limite and sessao_sucessos + sessao_nao_encontrados >= args.limite:
            motivo_paragem = f"limite da sessao (-n {args.limite}) atingido"
            break

        if checkpoint["feitos_hoje"] >= args.max_diario:
            motivo_paragem = (
                f"limite diario ({args.max_diario}/dia) atingido - "
                "corre o script novamente amanha"
            )
            break

        tentativa = 0
        while True:
            tentativa += 1
            codigo, retry_after, mensagem = seguir_utilizador(token, username)

            if codigo == 204:
                sessao_sucessos += 1
                checkpoint["feitos_hoje"] += 1
                checkpoint["processados"].append(username)
                guardar_checkpoint(args.checkpoint, checkpoint)
                log(f"{prefixo} {verde('[SUCESSO]')} @{username} foi seguido.")
                break

            if codigo == 404:
                sessao_nao_encontrados += 1
                checkpoint["processados"].append(username)
                guardar_checkpoint(args.checkpoint, checkpoint)
                log(
                    f"{prefixo} {amarelo('[NAO ENCONTRADO]')} "
                    f"@{username} nao existe."
                )
                break

            if codigo == 401:
                sys.exit(
                    f"{prefixo} {vermelho('[ERRO DE AUTENTICACAO]')} "
                    "token invalido ou sem permissao 'user:follow'. Terminando."
                )

            if codigo in (403, 429):
                sessao_rate_limits += 1
                pausa = max(retry_after or PAUSA_RATE_LIMIT, PAUSA_RATE_LIMIT)
                log(
                    f"{prefixo} {amarelo('[LIMITE DE TAXA]')} @{username} - "
                    f"a aguardar {pausa}s (tentativa "
                    f"{tentativa}/{TENTATIVAS_MAX})."
                )
                if tentativa >= TENTATIVAS_MAX:
                    sessao_falhas += 1
                    log(
                        f"{prefixo} {vermelho('[FALHA]')} @{username} - "
                        "limite de taxa persistente."
                    )
                    break
                time.sleep(pausa)
                continue

            if codigo is None or codigo >= 500:
                if tentativa >= TENTATIVAS_MAX:
                    sessao_falhas += 1
                    log(
                        f"{prefixo} {vermelho('[FALHA]')} @{username} - "
                        f"erro {codigo}: {mensagem}"
                    )
                    break
                log(
                    f"{prefixo} {amarelo('[ERRO TEMPORARIO]')} @{username} - "
                    f"erro {codigo}: {mensagem}. A tentar novamente..."
                )
                time.sleep(intervalo)
                continue

            sessao_falhas += 1
            log(
                f"{prefixo} {vermelho('[FALHA]')} @{username} - "
                f"codigo {codigo}: {mensagem}"
            )
            break

        time.sleep(intervalo)

    log(ciano("=" * 60))
    log(ciano(" Resumo da sessao"))
    log(ciano("=" * 60))
    log(f" Motivo de paragem     : {motivo_paragem}")
    log(f" {verde('[SUCESSO]'):<22}: {sessao_sucessos}")
    log(f" {amarelo('[NAO ENCONTRADO]'):<22}: {sessao_nao_encontrados}")
    log(f" {vermelho('[FALHA]'):<22}: {sessao_falhas}")
    log(f" {amarelo('[LIMITE DE TAXA]'):<22}: {sessao_rate_limits}")
    log(
        f" Progresso na lista    : "
        f"{total - len(pendentes) + sessao_sucessos + sessao_nao_encontrados}"
        f"/{total}"
    )
    log(f" Feitos hoje           : {checkpoint['feitos_hoje']}/{args.max_diario}")
    log(ciano("=" * 60))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n" + amarelo("Interrompido pelo utilizador."))
        sys.exit(130)
