# Diagnóstico local do ArangoDB ENEM — somente leitura

Objetivo: coletar evidências da instância **já existente**, sem importar arquivos,
alterar índices ou executar migrations. O banco testado no GitHub Actions é
descartável e **não é** o banco local.

## 1. Preparar o checkout

Na cópia local do repositório:

```bash
git fetch origin
git switch --track origin/feat/integrate-enem-audit-gate
python3 -m venv .venv-db-check
source .venv-db-check/bin/activate
python -m pip install 'python-arango>=7,<9'
```

Se a branch já existir localmente, use `git switch feat/integrate-enem-audit-gate`
em vez de `git switch --track`. Não é necessário fazer merge.

## 2. Auditar arquivos JSONL sem acesso ao servidor

```bash
python scripts/audit_fused_db.py --fused data/fused --output /tmp/enem-fused-audit.json
```

O programa sai com código 1 se houver erro estrutural. A cobertura incompleta,
como a posição 50 ausente do ENEM 2025 D1 azul, aparece separadamente e não
bloqueia a validação estrutural.

## 3. Verificar o banco EXISTENTE, sem qualquer escrita

**Se a sua instância é a configuração antiga do projeto, SEM autenticação,
e atende apenas a localhost:**

```bash
export ARANGO_HOST='http://127.0.0.1:8529'
export ARANGO_DB='enem'
python scripts/check_arangodb_integrity.py \
  --legacy-no-auth \
  --output /tmp/enem-local-db-report.json
```

**Se o ArangoDB tem autenticação:**

```bash
export ARANGO_HOST='http://127.0.0.1:8529'
export ARANGO_DB='enem'
export ARANGO_USER='root'
read -rsp 'Senha local ArangoDB: ' ARANGO_PASSWORD
echo
export ARANGO_PASSWORD
python scripts/check_arangodb_integrity.py \
  --output /tmp/enem-local-db-report.json
```

Se os dados em `data/fused/` correspondem exatamente ao universo de questões
esperado no banco, faça também o confronto estrito com a fonte:

```bash
python scripts/check_arangodb_integrity.py \
  --fused data/fused \
  --output /tmp/enem-local-db-vs-jsonl.json
```

Para a configuração antiga sem autenticação, acrescente
`--legacy-no-auth` ao último comando.

**Não execute `scripts/load_arangodb.py --apply` no banco existente.**
O carregador novo se recusa a migrar silenciosamente índices exclusivos
`co_item` antigos e arestas antigas com chaves geradas automaticamente.
É preciso revisar o diagnóstico e obter backup comprovado antes de migrar.

## 4. Compartilhar resultados, sem credenciais

Envie os dois JSONs `/tmp/enem-fused-audit.json` e
`/tmp/enem-local-db-report.json` (e o relatório de confronto, se executado).
Eles contêm contagens, nomes de coleções, identificadores de questões e problemas
detectados; confira se há informações que deseja ocultar antes do envio.
**Não envie** `.env`, `ARANGO_PASSWORD`, tokens ou dumps completos do banco.

Se não houver `data/fused/` nesta cópia local, informe onde estão os JSONL.
Se o ArangoDB estiver em Docker, verifique `docker ps` e o mapeamento de porta
antes dos comandos; não remova volumes nem reinicie containers.

## 5. Critério de aprovação e limitações

O ensaio automatizado no GitHub usa 89 questões ENEM 2025 AZUL D1, duas cargas
idempotentes, consultas negativas de integridade, dump e restore em banco novo.
Isso prova o caminho de ingestão **para esse conjunto**, mas não elimina o
risco de índices/arestas legados ou dados diferentes no servidor local.

O diagnóstico da instância local avalia tipos de coleções, referências e
cardinalidades de arestas, coerência TRI, unicidade das posições, índices
relevantes e cobertura. A comparação opcional contra JSONL verifica chaves
e metadados, não fidelidade textual/visual ao PDF oficial do INEP.
