import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.github.com"


def github_request(method, endpoint, token, data=None):
    url = f"{API_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "py-github-follower",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            error_json = json.loads(error_body)
            message = error_json.get("message", error_body)
        except json.JSONDecodeError:
            message = error_body
        return e.code, {"message": message}


def follow_user(username, token):
    status, body = github_request("PUT", f"/user/following/{username}", token)
    if status == 204:
        print(f"Voce agora segue '{username}'.")
    else:
        print(f"Erro ao seguir '{username}': {body.get('message', 'erro desconhecido')}")
        sys.exit(1)


def unfollow_user(username, token):
    status, body = github_request("DELETE", f"/user/following/{username}", token)
    if status == 204:
        print(f"Voce deixou de seguir '{username}'.")
    else:
        print(f"Erro ao deixar de seguir '{username}': {body.get('message', 'erro desconhecido')}")
        sys.exit(1)


def list_followers(username, token):
    status, body = github_request("GET", f"/users/{username}/followers?per_page=100", token)
    if status == 200:
        followers = [user["login"] for user in body]
        print(f"Seguidores de '{username}' ({len(followers)}):")
        for f in followers:
            print(f"  - {f}")
        return followers
    else:
        print(f"Erro ao listar seguidores: {body.get('message', 'erro desconhecido')}")
        sys.exit(1)


def list_following(username, token):
    status, body = github_request("GET", f"/users/{username}/following?per_page=100", token)
    if status == 200:
        following = [user["login"] for user in body]
        print(f"'{username}' segue ({len(following)}):")
        for f in following:
            print(f"  - {f}")
        return following
    else:
        print(f"Erro ao listar following: {body.get('message', 'erro desconhecido')}")
        sys.exit(1)


def follow_all_followers(username, token):
    status, body = github_request("GET", f"/users/{username}/followers?per_page=100", token)
    if status != 200:
        print(f"Erro ao listar seguidores: {body.get('message', 'erro desconhecido')}")
        sys.exit(1)
    followers = [user["login"] for user in body]
    print(f"Seguindo {len(followers)} seguidores de '{username}'...")
    for i, f in enumerate(followers, 1):
        status, resp = github_request("PUT", f"/user/following/{f}", token)
        if status == 204:
            print(f"  [{i}/{len(followers)}] Seguiu '{f}'")
        else:
            print(f"  [{i}/{len(followers)}] Falha ao seguir '{f}': {resp.get('message')}")


def main():
    parser = argparse.ArgumentParser(description="Bot para seguir/deixar de seguir usuarios do GitHub")
    parser.add_argument("action", choices=["follow", "unfollow", "followers", "following", "follow-all"])
    parser.add_argument("username", help="Nome de usuario do GitHub")
    parser.add_argument("--token", help="Token de acesso pessoal do GitHub (ou variavel GITHUB_TOKEN)")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Erro: forneça --token ou defina a variavel GITHUB_TOKEN")
        sys.exit(1)

    actions = {
        "follow": follow_user,
        "unfollow": unfollow_user,
        "followers": list_followers,
        "following": list_following,
        "follow-all": follow_all_followers,
    }
    actions[args.action](args.username, token)


if __name__ == "__main__":
    main()
