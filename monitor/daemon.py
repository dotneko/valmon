import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta, timezone

from pyibc_async import (
    get_latest_block_height,
    get_latest_validator_set_sorted,
    get_number_accounts,
    get_stats_for_validator,
    get_token_data,
)
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from utils import get_config

# from itertools import repeat


# Setup logging
logging.basicConfig(
    format="%(levelname)s | %(asctime)s | %(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def update_valset() -> (int, dict):
    validators: dict = await get_latest_validator_set_sorted(REST_ROOT)
    if validators is None:
        logging.warning("Error getting validators")
    block_number: int = await get_latest_block_height(REST_ROOT)
    if block_number == -1:
        logging.warning("Error getting latest block height")
    return (block_number, validators)


async def update_statistics(engine, validators: dict, timeout: int) -> dict:
    """Get latest validator set"""
    run_time: datetime = datetime.now(timezone.utc)
    block_number: int = await get_latest_block_height(REST_ROOT)
    total_token_share: int = 0
    start_time: time = time.time()
    logging.info(f"Requesting data at block {block_number}")
    num_accounts: int = await get_number_accounts(CHAIN, REST_ROOT)
    token_stats: dict = await get_token_data(CHAIN, REST_ROOT)
    #    val_stats = await asyncio.gather(
    #        *map(
    #            get_stats_for_validator,
    #            repeat(CHAIN),
    #            repeat(REST_ROOT),
    #            val_addrs,
    #            repeat(timeout),
    #            repeat(True),  # include_delegations=True
    #        )
    #    )
    val_stats = []
    for val_addr in validators.keys():
        val_data = await get_stats_for_validator(
            CHAIN, REST_ROOT, val_addr, timeout, include_delegations=True
        )
        val_stats.append(val_data)
    logging.info(f"Elapsed time: {time.time() - start_time}s")

    with engine.connect() as con:

        # Write chain data
        inserted_rowcount = 0
        with con.begin():
            chain_data = {
                "run_time": run_time,
                "block_number": block_number,
                "num_accounts": num_accounts,
                "bonded_tokens": token_stats["bonded_tokens"],
                "unbonded_tokens": token_stats["unbonded_tokens"],
                "pool_total": token_stats["pool_total"],
                "total_supply": token_stats["total_supply"],
            }
            insert_chain_stmt = text(
                """
                    INSERT INTO chain_stats (run_time, block_number, num_accounts,
                        bonded_tokens, unbonded_tokens, pool_total, total_supply)
                    VALUES
                    (:run_time, :block_number, :num_accounts,
                     :bonded_tokens, :unbonded_tokens, :pool_total, :total_supply);
                    """
            )
            result = con.execute(insert_chain_stmt, chain_data)
            if result.rowcount == 0:
                logging.warning(f"Error writing to database table {CHAIN_TB}")
            else:
                inserted_rowcount += result.rowcount
            con.commit()
            logger.info(f"Inserted {inserted_rowcount} record(s) to {CHAIN_TB}")

        # Write validator stats
        inserted_rowcount = 0
        total_token_share = sum(v["bonded_utokens"] for v in val_stats)
        with con.begin():
            for valdata in val_stats:
                data = {
                    "run_time": run_time,
                    "block_number": block_number,
                    "moniker": valdata["moniker"],
                    "address": valdata["operator_address"],
                    "num_delegators": valdata["unique_delegators"],
                    "pc": valdata["bonded_utokens"] / total_token_share,
                    "total": valdata["bonded_utokens"],
                    "top10pc": valdata["top10pc"],
                }
                insert_stmt = text(
                    """
                    INSERT INTO validator_stats (run_time, block_number, moniker, address,
                        num_delegators, pc, total, top10pc)
                    VALUES
                    (:run_time, :block_number, :moniker, :address, :num_delegators, :pc, :total, :top10pc);
                    """
                )
                result = con.execute(insert_stmt, data)
                if result.rowcount == 0:
                    logging.warning(f"Error writing to database table {VAL_TB}")
                else:
                    inserted_rowcount += result.rowcount
            con.commit()
    logger.info(f"Inserted {inserted_rowcount} validator record(s) to {VAL_TB}")


async def interval_statistics(engine, interval, timeout):
    while True:
        validators = {}
        (valset_blocknumber, validators) = await update_valset()
        logger.info(
            f"{len(validators)} active validators at block height {valset_blocknumber}"
        )
        logger.info(
            f"Poll interval: {interval}s [{datetime.now(timezone.utc) + timedelta(seconds=interval)}]"
            + f" | Timeout: {timeout}s"
        )
        if len(validators) > 0:
            await asyncio.gather(
                update_statistics(engine, validators, timeout),
                asyncio.sleep(interval),
            )


if __name__ == "__main__":

    # Load configuration
    CHAIN: str = get_config("chain")
    REST_ROOT: str = get_config("rest_endpoint")
    WAIT: int = get_config("poll_interval")
    TIMEOUT: int = get_config("max_timeout")
    PG: dict = get_config("pg_settings")
    PG_DBPATH: str = (
        f"{PG['username']}:{PG['password']}@{PG['host']}:{PG['port']}/{PG['dbname']}"
    )
    CHAIN_TB: str = "chain_stats"
    VAL_TB: str = "validator_stats"

    engine = create_engine(
        "postgresql+psycopg2://" + PG_DBPATH,
        # execution_options={"isolation_level": "AUTOCOMMIT"},
        future=True,
    )
    asyncio.run(interval_statistics(engine, WAIT, TIMEOUT))
