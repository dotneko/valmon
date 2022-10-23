# Modified get_validator_stats from pyibc_chain/validator.py to show "bonded_utokens" as int
import logging
import time

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
    chain, rest_url, operator_address, include_number_of_unique_delegations=False
) -> dict:
    """
    Returns a dict of information about a given validator
    https://api.cosmos.network/cosmos/staking/v1beta1/validators/cosmosvaloper16s96n9k9zztdgjy8q4qcxp4hn7ww98qkrka4zk
    Adapted and modified from https://github.com/Reecepbcups/python-ibc
    """
    start_time = time.time()
    ROOT_URL = rest_url

    # get a validators details
    queryEndpoint = (
        f"{ROOT_URL}/{REST_ENDPOINTS['validator_info']}/{operator_address}".replace(
            "{EPOCH}", f"{int(time.time())}"
        )
    )

    r = await get_async(queryEndpoint, headers=headers)
    # r = requests.get(queryEndpoint, headers=headers)
    if r.status_code != 200:
        logging.warning(f"\n(Error): {r.status_code} on {queryEndpoint}")
        return {}
    validatorData = r.json()["validator"]

    # get chain params
    params_url = f"{ROOT_URL}/{REST_ENDPOINTS['params']}"
    r = await get_async(params_url, headers=headers)
    # r = requests.get(params_url, headers=headers)
    if r.status_code != 200:
        logging.warning(f"\n(Error): {r.status_code} on {params_url}")
        return {}
    paramsData = r.json()["params"]
    # ! IMPORTANT, this may take a while
    # get total # of unique delegators
    #  https://lcd-osmosis.blockapsis.com/cosmos/staking/v1beta1/validators/osmovaloper16s96n9k9zztdgjy8q4qcxp4hn7ww98qk5wjn0s/delegations?pagination.limit=10000
    uniqueDelegators = "-1"
    try:
        if include_number_of_unique_delegations:
            # raise Exception("test")
            delegators_url = f"{queryEndpoint}/delegations?pagination.limit=10000"
            r = await get_async(delegators_url, headers=headers, timeout=30.0)
            # r = requests.get(delegators_url, headers=headers)
            if r.status_code != 200:
                logging.warning(
                    f"\n(Error): {r.status_code} on delegators_url: {delegators_url}"
                )
            uniqueDelegators = f"{len(r.json()['delegation_responses'])}"
    except Exception as e:
        logging.warning(e)
        pass
    # validator_ranking = get_latest_validator_set_sorted(rest_url, bondedOnly=False)
    # find index of operator_address in validator_ranking
    # index = 1
    # for k in validator_ranking.keys():
    #    if k == operator_address:
    #        break
    #    index += 1

    logging.info(
        f"- {validatorData['description']['moniker']:15} | "
        + f"Elapsed: {time.time() - start_time:>5.2f}s | Delegators: {uniqueDelegators:>6} | "
        + f"Bonded: {simplify_balance_str(paramsData['bond_denom'], int(validatorData['tokens']))}"
    )

    return {
        "chain": chain,
        "operator_address": validatorData["operator_address"],
        "jailed": validatorData["jailed"],
        "status": validatorData["status"],  # BOND_STATUS_BONDED
        # "bonded_utokens": f"{int(validatorData['tokens'])}", # then based onbond_denom, convert
        "bonded_utokens": int(
            validatorData["tokens"]
        ),  # modified from above to keep as int
        "bonded_tokens": simplify_balance_str(
            paramsData["bond_denom"], int(validatorData["tokens"])
        ),
        "moniker": validatorData["description"]["moniker"],
        "identity": validatorData["description"]["identity"],
        "website": validatorData["description"]["website"],
        "security_contact": validatorData["description"]["security_contact"],
        "commission": validatorData["commission"]["commission_rates"]["rate"],
        # "validator_ranking": index,
        "max_validators": paramsData["max_validators"],
        "bond_denom": paramsData["bond_denom"],
        "unique_delegators": uniqueDelegators,
    }
