#!/usr/bin/env python3
"""
Constroi uma lista grande de utilizadores reais do GitHub.

Usa a Search API (GET /search/users) com queries variadas de
linguagem/followers/data de criação para obter contas diversificadas,
filtra bots e contas ja processadas, baralha e grava "lista1000.txt".

Uso: python criar_lista.py
"""

import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import seguir_github as sg

CONSULTAS = [
    "type:user language:python followers:>100",
    "type:user language:python followers:20..100",
    "type:user language:python followers:5..19 created:<2021-01-01",
    "type:user language:python followers:1..4 created:2022-01-01..2024-12-31",
    "type:user language:python followers:>10 created:>2024-01-01",
]
PAGINAS_POR_CONSULTA = 10
POR_CONSULTA = 200
TOTAL_DESEJADO = 1000
SAIDA = "lista1000.txt"
SEMENTE = 42
PAUSA_PEDIDO = 3


def get(url, token=None):
    pedido = urllib.request.Request(url)
    if token:
        pedido.add_header("Authorization", f"Bearer {token}")
    pedido.add_header("Accept", "application/vnd.github+json")
    pedido.add_header("X-GitHub-Api-Version", sg.API_VERSION)
    pedido.add_header("User-Agent", "criar-lista")
    try:
        with urllib.request.urlopen(pedido, timeout=30) as resposta:
            return resposta.status, json.loads(resposta.read().decode())
    except urllib.error.HTTPError as erro:
        corpo = erro.read().decode("utf-8", errors="replace")[:200]
        sg.log(sg.amarelo(f"HTTP {erro.code} em {url}: {corpo}"))
        return erro.code, None
    except Exception as erro:  # noqa: BLE001
        sg.log(sg.amarelo(f"Erro em {url}: {erro}"))
        return None, None


def main():
    sg.carregar_env()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    token = token.strip() if token else ""

    excluidos = set()

    status, dados = get(f"{sg.API_BASE}/user", token)
    if status == 200 and isinstance(dados, dict):
        excluidos.add(dados.get("login", "").lower())
        sg.log(f"Conta propria excluida da lista: {dados.get('login')}")

    if os.path.isfile(sg.ARQUIVO_NOMES):
        for nome in sg.ler_nomes(sg.ARQUIVO_NOMES):
            excluidos.add(nome.lower())

    checkpoint = sg.carregar_checkpoint(sg.ARQUIVO_CHECKPOINT)
    excluidos.update(nome.lower() for nome in checkpoint["processados"])

    encontrados = {}
    pedidos = 0

    for consulta in CONSULTAS:
        para_esta_consulta = 0
        for pagina in range(1, PAGINAS_POR_CONSULTA + 1):
            url = (
                f"{sg.API_BASE}/search/users?"
                f"q={urllib.parse.quote(consulta)}"
                f"&per_page=100&page={pagina}"
            )
            status, resposta = get(url, token)
            pedidos += 1
            if status != 200 or not isinstance(resposta, dict):
                break
            itens = resposta.get("items") or []
            if not itens:
                break
            novos = 0
            for item in itens:
                login = item.get("login")
                if not login or item.get("type") != "User":
                    continue
                if login.lower().endswith("[bot]"):
                    continue
                if login.lower() in excluidos:
                    continue
                if login.lower() not in encontrados:
                    encontrados[login.lower()] = login
                    novos += 1
                    para_esta_consulta += 1
            sg.log(
                f"[{consulta}] p.{pagina}: +{novos} "
                f"(total {len(encontrados)})"
            )
            time.sleep(PAUSA_PEDIDO)
            if para_esta_consulta >= POR_CONSULTA:
                break

        if len(encontrados) >= TOTAL_DESEJADO * 2:
            sg.log("Suficientes candidatos recolhidos.")

    if len(encontrados) < TOTAL_DESEJADO:
        sg.log(
            sg.amarelo(
                f"Aviso: apenas {len(encontrados)} contas recolhidas "
                f"(esperadas {TOTAL_DESEJADO})."
            )
        )

    nomes = list(encontrados.values())
    random.seed(SEMENTE)
    random.shuffle(nomes)
    nomes = nomes[:TOTAL_DESEJADO]

    with open(SAIDA, "w", encoding="utf-8") as ficheiro:
        ficheiro.write("# Lista gerada por criar_lista.py (GitHub Search API)\n")
        ficheiro.write(f"# Queries: {len(CONSULTAS)} filtros language:python\n")
        for nome in nomes:
            ficheiro.write(nome + "\n")

    sg.log(
        sg.verde(
            f"{len(nomes)} nomes gravados em {SAIDA} ({pedidos} pedidos)."
        )
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
