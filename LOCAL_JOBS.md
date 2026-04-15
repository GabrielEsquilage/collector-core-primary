# Execucao Local

## Preparacao

1. Crie o `.env` a partir do exemplo:

```bash
cp .env.example .env
```

2. Suba o Postgres local:

```bash
docker compose up -d
```

3. Inicialize schema e tabelas:

```bash
./.venv/bin/python -m app.services.transparencia.jobs init-db
```

## Carga do IBGE

Os jobs do Parana dependem dos municipios do IBGE carregados localmente.

```bash
./.venv/bin/python -m app.services.ibge.localidades_sync_service
```

## Jobs de Transparencia

Criar os jobs fixos:

```bash
./.venv/bin/python -m app.services.transparencia.jobs seed
```

Listar jobs:

```bash
./.venv/bin/python -m app.services.transparencia.jobs list-jobs
```

Ver um job:

```bash
./.venv/bin/python -m app.services.transparencia.jobs show-job 6
```

Marcar um job como `queued`:

```bash
./.venv/bin/python -m app.services.transparencia.jobs queue-job 6
```

Executar um job localmente, fora do web service:

```bash
./.venv/bin/python -m app.services.transparencia.jobs run-job 6
```

## API local

Se quiser subir a API local apenas para consulta:

```bash
./.venv/bin/uvicorn app.main:app --reload
```

Mantendo no `.env`:

```bash
IBGE_SYNC_ON_STARTUP=false
TRANSPARENCIA_SYNC_ON_STARTUP=false
```
