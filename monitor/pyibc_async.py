# Modified get_validator_stats from pyibc_chain/validator.py to show "bonded_utokens" as int
import logging
import time
from typing import List

import httpx
from pyibc_api.chain_apis import REST_ENDPOINTS
from pyibc_utils.convert import (  # . when live, remove . for testing here
    simplify_balance_str,
)

headers = {"accept": "application/json"}
# PAGE_LIMIT = "?pagination.limit=1000"


async def get_async(url, headers=headers, timeout=5.0):
    async with httpx.AsyncClient() as client:
        return await client.get(
            url, headers=headers, timeout=timeout, follow_redirects=True
        )


async def get_validator_stats_async(
    chain: str, rest_root: str, operator_address: str, include_delegations: bool = False
) -> dict:
    """
    Returns a dict of information about a given validator
    https://api.cosmos.network/cosmos/staking/v1beta1/validators/cosmosvaloper16s96n9k9zztdgjy8q4qcxp4hn7ww98qkrka4zk
    Adapted and modified from https://github.com/Reecepbcups/python-ibc
    """
    start_time: time = time.time()
    ROOT_URL: str = rest_root

    # Get a validators details
    queryEndpoint: str = (
        f"{ROOT_URL}/{REST_ENDPOINTS['validator_info']}/{operator_address}".replace(
            "{EPOCH}", f"{int(time.time())}"
        )
    )

    r = await get_async(queryEndpoint, headers=headers)
    if r.status_code != 200:
        logging.warning(f"\n(Error): {r.status_code} on {queryEndpoint}")
        return {}
    validatorData: dict = r.json()["validator"]

    # Get chain params
    params_url: str = f"{ROOT_URL}/{REST_ENDPOINTS['params']}"
    r = await get_async(params_url, headers=headers)
    if r.status_code != 200:
        logging.warning(f"\n(Error): {r.status_code} on {params_url}")
        return {}
    paramsData: dict = r.json()["params"]

    # ! IMPORTANT, this may take a while
    # get total # of unique delegators
    #  https://lcd-osmosis.blockapsis.com/cosmos/staking/v1beta1/validators/osmovaloper16s96n9k9zztdgjy8q4qcxp4hn7ww98qk5wjn0s/delegations?pagination.limit=10000
    uniqueDelegators: int = -1
    top10pc: float = 0.0
    if include_delegations:
        try:
            delegators_url: str = f"{queryEndpoint}/delegations?pagination.limit=10000"
            r = await get_async(delegators_url, headers=headers, timeout=30.0)
            if r.status_code != 200:
                logging.warning(
                    f"\n(Error): {r.status_code} on delegators_url: {delegators_url}"
                )
            uniqueDelegators: int = len(r.json()["delegation_responses"])
            sorted_delegations: List = sorted(
                r.json()["delegation_responses"],
                key=lambda k: int(k["balance"].get("amount")),
                reverse=True,
            )
            top10shares: float = 0
            for idx in range(0, 10):
                top10shares += float(sorted_delegations[idx]["balance"]["amount"])
            # Calculate % held by top 10 delegators
            top10pc: float = top10shares / float(validatorData["tokens"])
        except Exception as e:
            logging.warning(e)
            pass

    logging.info(
        f"- {validatorData['description']['moniker']:15} "
        + f"| Elapsed: {time.time() - start_time:>5.2f}s | Delegators: {uniqueDelegators:>6} "
        + f"| Top10: {float(top10shares) / float(validatorData['tokens']) * 100:>.2f}% "
        + f"| Bonded: {simplify_balance_str(paramsData['bond_denom'], int(validatorData['tokens'])):>18} "
    )

    return {
        "chain": chain,
        "operator_address": validatorData["operator_address"],
        "jailed": validatorData["jailed"],
        "status": validatorData["status"],  # BOND_STATUS_BONDED
        "bonded_utokens": int(validatorData["tokens"]),
        "moniker": validatorData["description"]["moniker"],
        "identity": validatorData["description"]["identity"],
        "website": validatorData["description"]["website"],
        "security_contact": validatorData["description"]["security_contact"],
        "commission": validatorData["commission"]["commission_rates"]["rate"],
        "max_validators": paramsData["max_validators"],
        "bond_denom": paramsData["bond_denom"],
        "unique_delegators": uniqueDelegators,
        "top10pc": top10pc,
    }
