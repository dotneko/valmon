from datetime import datetime, timezone
from time import sleep

from pyibc_chain.queries import get_latest_block_height
from pyibc_chain.validators import get_latest_validator_set_sorted
from pyibc_modified import get_validator_stats
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from utils import get_config


def update_valset() -> (int, dict):
    validators = get_latest_validator_set_sorted(ONOMY_REST)
    valset_blocknumber = get_latest_block_height(ONOMY_REST)
    return (valset_blocknumber, validators)


def update_statistics(engine, validators: dict) -> dict:
    """Get latest validator set"""
    stats = {}
    run_time = datetime.now(timezone.utc)
    block_number: int = get_latest_block_height(ONOMY_REST)
    total_token_share: int = 0
    for idx, op_addr in enumerate(validators):
        stats[op_addr] = {}
        stats[op_addr]["moniker"]: str = validators[op_addr]["moniker"]
        # Get validator unique delegators
        print(f"Retrieving delegator stats for {stats[op_addr]['moniker']}")
        detailed: dict = get_validator_stats(CHAIN, ONOMY_REST, op_addr, True)
        stats[op_addr]["num_delegators"]: int = detailed["unique_delegators"]
        stats[op_addr]["bonded_utokens"]: int = detailed["bonded_utokens"]
        stats[op_addr]["bonded_tokens"]: str = detailed["bonded_tokens"]
        total_token_share += int(detailed["bonded_utokens"])

    for op_addr in validators:
        stats[op_addr]["pc"]: float = (
            stats[op_addr]["bonded_utokens"] / total_token_share * 100
        )
        data = {
            "run_time": run_time,
            "block_number": block_number,
            "moniker": stats[op_addr]["moniker"],
            "address": op_addr,
            "num_delegators": stats[op_addr]["num_delegators"],
            "pc": stats[op_addr]["pc"],
            "total": stats[op_addr]["bonded_utokens"],
        }
        print(
            "{} {} {} {:15} {:>6} {}% {}".format(
                run_time,
                block_number,
                op_addr,
                stats[op_addr]["moniker"],
                stats[op_addr]["num_delegators"],
                stats[op_addr]["pc"],
                #                stats[op_addr]["bonded_utokens"],
                stats[op_addr]["bonded_tokens"],
            )
        )
        insert = text(
            """INSERT INTO validator_stats (run_time, block_number, moniker, address, num_delegators, pc, total)
                     VALUES
                     (:run_time, :block_number, :moniker, :address, :num_delegators, :pc, :total);
        """
        )
        with engine.connect() as con:
            with con.begin():
                con.execute(insert, data)
                con.commit()
    return stats


if __name__ == "__main__":

    # Load configuration
    CHAIN: str = get_config("chain")
    ONOMY_REST: str = get_config("rest_endpoint")
    WAIT: int = get_config("poll_interval")
    PG: dict = get_config("pg_settings")
    with open(PG["pwd_file"]) as f:
        PG_PASSWORD = f.read().strip()
    PG_DBPATH: str = f"{PG['username']}:{PG_PASSWORD}@{PG['host']}/{PG['dbname']}"
    validators = {}
    valset_blocknumber: int = None

    print("Get validator set")
    (valset_blocknumber, validators) = update_valset()

    engine = create_engine(
        "postgresql+psycopg2://" + PG_DBPATH,
        # execution_options={"isolation_level": "AUTOCOMMIT"},
        future=True,
    )
    count: int = 0
    while True:
        # for count in range(5):
        count += 1
        print(f"Get statistics [{count}]")
        stats = update_statistics(engine, validators)
        print(f"Waiting for {WAIT}s")
        sleep(WAIT)
