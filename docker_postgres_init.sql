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

CREATE TABLE public.chain_stats (
    run_time timestamptz NOT NULL,
    block_number int NOT NULL,
    num_accounts int NULL,
    bonded_tokens numeric NOT NULL,
    unbonded_tokens numeric NOT NULL,
    pool_total numeric NOT NULL,
    total_supply numeric NOT NULL
);
