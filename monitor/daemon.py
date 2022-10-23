import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from itertools import repeat

from pyibc_async import get_validator_stats_async
from pyibc_chain.queries import get_latest_block_height
from pyibc_chain.validators import get_latest_validator_set_sorted
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from utils import get_config

# Setup logging
logging.basicConfig(
    format="%(levelname)s | %(asctime)s | %(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def update_valset() -> (int, dict):
    validators: dict = get_latest_validator_set_sorted(ONOMY_REST)
    valset_blocknumber: int = get_latest_block_height(ONOMY_REST)
    return (valset_blocknumber, validators)


async def update_statistics(engine, validators: dict) -> dict:
    """Get latest validator set"""
    stats = {}
    run_time: datetime = datetime.now(timezone.utc)
    block_number: int = get_latest_block_height(ONOMY_REST)
    total_token_share: int = 0
    val_addrs = [validator for validator in validators.keys()]
    start_time: time = time.time()
    logging.info(f"Requesting data at block {block_number}")
    val_stats = await asyncio.gather(
        *map(
            get_validator_stats_async,
            repeat(CHAIN),
            repeat(ONOMY_REST),
            val_addrs,
            repeat(True),  # include_number_of_unique_delegations=True
        )
    )
    logging.info(f"Elapsed time: {time.time() - start_time}s")
    inserted_rowcount = 0
    total_token_share = sum(v["bonded_utokens"] for v in val_stats)
    with engine.connect() as con:
        with con.begin():
            for valdata in val_stats:
                data = {
                    "run_time": run_time,
                    "block_number": block_number,
                    "moniker": valdata["moniker"],
                    "address": valdata["operator_address"],
                    "num_delegators": valdata["unique_delegators"],
                    "pc": valdata["bonded_utokens"] / total_token_share * 100,
                    "total": valdata["bonded_utokens"],
                }
                insert_stmt = text(
                    """INSERT INTO validator_stats (run_time, block_number, moniker, address, num_delegators, pc, total)
                             VALUES
                             (:run_time, :block_number, :moniker, :address, :num_delegators, :pc, :total);
                """
                )
                result = con.execute(insert_stmt, data)
                if result.rowcount == 0:
                    logging.warning(f"Error writing database: {data}")
                else:
                    inserted_rowcount += result.rowcount
            con.commit()
    logger.info(f"Inserted {inserted_rowcount} records to database")
    return stats


async def interval_statistics(engine, interval):
    validators = {}
    (valset_blocknumber, validators) = update_valset()
    logger.info(
        f"{len(validators)} active validators at block height {valset_blocknumber} [Poll interval: {interval}s]"
    )
    if len(validators) > 0:
        await asyncio.gather(
            update_statistics(engine, validators), asyncio.sleep(interval)
        )


if __name__ == "__main__":

    # Load configuration
    CHAIN: str = get_config("chain")
    ONOMY_REST: str = get_config("rest_endpoint")
    WAIT: int = get_config("poll_interval")
    PG: dict = get_config("pg_settings")
    PG_DBPATH: str = (
        f"{PG['username']}:{PG['password']}@{PG['host']}:{PG['port']}/{PG['dbname']}"
    )

    engine = create_engine(
        "postgresql+psycopg2://" + PG_DBPATH,
        # execution_options={"isolation_level": "AUTOCOMMIT"},
        future=True,
    )
    while True:
        stats = asyncio.run(interval_statistics(engine, WAIT))
