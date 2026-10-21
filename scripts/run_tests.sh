#!/usr/bin/env bash
# Executa toda a suíte automatizada (sem Docker). Execute na raiz do projeto.
set -u
cd "$(dirname "$0")/.."
status=0
echo "== Backend (unittest) ==";            (cd backend && python3 -m unittest discover -s tests -t . -v) || status=1
echo "== Frontend unitário (node:test) =="; (cd frontend && node --test tests/*.test.js) || status=1
echo "== Interface / ponta a ponta (Playwright) =="; python3 -m unittest discover -s tests/e2e -t tests/e2e -v || status=1
exit $status
