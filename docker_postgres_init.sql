CREATE TABLE public.validator_stats (
    run_time timestamptz NOT NULL,
    block_number int NOT NULL,
    moniker text NULL,
    address text NOT NULL,
    num_delegators int NULL,
    pc numeric NULL,
    total numeric NULL,
    top10pc numeric NULL
);
