#!/usr/bin/env bash
# Teste de implantação completo: constrói, sobe, verifica e derruba a stack.
# Requer Docker com o plugin Compose. Execute na raiz do projeto.
set -euo pipefail
cd "$(dirname "$0")/../.."
trap 'docker compose down -v' EXIT
docker compose up --build --wait --wait-timeout 120
docker compose ps
python3 tests/deploy/smoke_test.py http://localhost:8080
