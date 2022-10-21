#!/bin/bash
# Create validator_stats table

PG_USER=pgadmin
PG_DB=db_dev
INIT_SQL="CREATE TABLE public.validator_stats (run_time timestamptz NOT NULL,block_number int NOT NULL,moniker text NULL,address text NOT NULL,num_delegators int NULL,pc numeric NULL,total numeric NULL);"
docker compose exec db psql -U $PG_USER -d $PG_DB -c "DROP TABLE IF EXISTS public.validator_stats;"
docker compose exec db psql -U $PG_USER -d $PG_DB -c "$INIT_SQL"
