docker compose exec db psql -U pgadmin -d db_dev -c "SELECT * from public.validator_stats;"
