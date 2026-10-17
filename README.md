# Py GitHub Follower

Bot em Python para interagir com seguidores do GitHub usando a API oficial.

## Funcionalidades

- Seguir um usuário
- Deixar de seguir um usuário
- Listar seguidores de um usuário
- Listar quem um usuário segue
- Seguir todos os seguidores de um usuário (follow-back)

## Requisitos

- Python 3.7+
- Token de acesso pessoal do GitHub com escopo `user:follow`

## Como obter um token

1. Acesse https://github.com/settings/tokens
2. Clique em "Generate new token (classic)"
3. Marque o escopo `user:follow`
4. Copie o token gerado

## Instalação

```bash
git clone https://github.com/pedro12345lisboa-sudo/py-github-follower.git
cd py-github-follower
```

Nenhuma dependência externa é necessária — o script usa apenas a biblioteca padrão.

## Uso

Defina o token como variável de ambiente (recomendado):

```bash
set GITHUB_TOKEN=seu_token_aqui
```

Ou passe diretamente com `--token`.

### Seguir um usuário

```bash
python github_follower.py follow usuario_exemplo
```

### Deixar de seguir um usuário

```bash
python github_follower.py unfollow usuario_exemplo
```

### Listar seguidores de um usuário

```bash
python github_follower.py followers usuario_exemplo
```

### Listar quem um usuário segue

```bash
python github_follower.py following usuario_exemplo
```

### Seguir todos os seguidores de um usuário

```bash
python github_follower.py follow-all usuario_exemplo
```

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.
