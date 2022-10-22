docker compose exec db psql -U postgres -d db_dev -c "SELECT * from public.validator_stats;"
