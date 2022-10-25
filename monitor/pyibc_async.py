import logging
import time
from typing import List

import httpx

DENOM: str = "anom"
HEADERS: dict = {"accept": "application/json"}
REST_ENDPOINTS = {
    # DO NOT START WITH A /, this way we have to do in our f string
    "accounts": "/cosmos/auth/v1beta1/accounts",
    "block_latest": "/blocks/latest",
    "params": "/cosmos/staking/v1beta1/params",
    "pool_tokens": "/cosmos/staking/v1beta1/pool",
    "supply": "/cosmos/bank/v1beta1/supply",
    "validator_info": "/cosmos/staking/v1beta1/validators",
}


async def get_async(url, headers=HEADERS, timeout=5.0):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url, headers=headers, timeout=timeout, follow_redirects=True
        )
        if resp.status_code != 200:
            logging.warning(f"\n(Error): {resp.status_code} on {url}")
            return None
        else:
            return resp


async def get_latest_block_height(rest_root: str) -> int:
    """
    Returns latest block height
    """
    r = await get_async(rest_root.rstrip("/") + REST_ENDPOINTS[r"block_latest"])
    if r is None:
        return -1
    block_number = int(r.json()["block"]["header"]["height"])
    return block_number


async def get_latest_validator_set_sorted(rest_root, bondedOnly: bool = True) -> dict:
    """
    Returns a sorted validator_set
    """
    query_endpoint = "".join(
        [
            rest_root.rstrip("/"),
            REST_ENDPOINTS["validator_info"],
            "?pagination.limit=1000",
            "&status=BOND_STATUS_BONDED" if bondedOnly else "",
        ]
    )

    r = await get_async(query_endpoint)
    if r is None:
        return {}

    validators = {}
    for val in r.json()["validators"]:
        opp_addr = val["operator_address"]
        moniker = val["description"]["moniker"]
        identity = val["description"]["identity"]
        status = val["status"]
        tokens = val["tokens"]
        validators[opp_addr] = {
            "moniker": moniker,
            "identity": identity,
            "status": status,
            "token_share": int(tokens),
        }

    return {
        k: v
        for k, v in sorted(
            validators.items(), key=lambda x: x[1]["token_share"], reverse=True
        )
    }


async def get_token_data(chain: str, rest_root: str, denom=DENOM) -> dict:
    """
    Returns a dict of token data
    """
    # Get pool tokens
    r = await get_async(rest_root.rstrip("/") + f"{REST_ENDPOINTS['pool_tokens']}")
    if r is None:
        return {}
    tokenData = {
        "bonded_tokens": int(r.json()["pool"]["bonded_tokens"]),
        "unbonded_tokens": int(r.json()["pool"]["not_bonded_tokens"]),
    }
    tokenData["pool_total"] = tokenData["bonded_tokens"] + tokenData["unbonded_tokens"]
    # Get total supply
    r = await get_async(rest_root.rstrip("/") + f"{REST_ENDPOINTS['supply']}/{denom}")
    if r is None:
        return {}
    tokenData["total_supply"] = int(r.json()["amount"]["amount"])
    tokenData["denom"] = denom
    logging.info(
        f"Pool  - Bonded: {tokenData['bonded_tokens']/10**18:>14,.2f} "
        + f"| Unbonded: {tokenData['unbonded_tokens']/10**18:>16,.2f} nom"
    )
    logging.info(
        f"Total - Pool  : {tokenData['pool_total']/10**18:>14,.2f} "
        + f"| Supply  : {tokenData['total_supply']/10**18:>16,.2f} nom"
    )
    return tokenData


async def get_number_accounts(chain: str, rest_root: str) -> int:
    """
    Returns number of accounts (wallets)
    """
    r = await get_async(rest_root.rstrip("/") + f"{REST_ENDPOINTS['accounts']}")
    if r is None:
        return {}
    num_accounts = int(r.json()["pagination"]["total"])
    logging.info(f"Accounts: {num_accounts}")
    return num_accounts


async def get_stats_for_validator(
    chain: str, rest_root: str, operator_address: str, include_delegations: bool = False
) -> dict:
    """
    Returns a dict of information about a given validator
    """
    start_time = time.time()
    # Get validator data
    r = await get_async(
        rest_root.rstrip("/") + f"{REST_ENDPOINTS['validator_info']}/{operator_address}"
    )
    if r is None:
        return {}
    validatorData: dict = r.json()["validator"]

    # Get chain params
    r = await get_async(rest_root.rstrip("/") + f"{REST_ENDPOINTS['params']}")
    if r is None:
        return {}
    paramsData: dict = r.json()["params"]

    # ! IMPORTANT, this may take a while
    # Get total # of unique delegators
    uniqueDelegators: int = -1
    top10pc: float = 0.0
    top10shares: float = 0.0
    if include_delegations:
        try:
            query_endpoint = "".join(
                [
                    rest_root.rstrip("/"),
                    f"{REST_ENDPOINTS['validator_info']}/{operator_address}/",
                    "delegations?pagination.limit=10000",
                ]
            )
            r = await get_async(query_endpoint, headers=HEADERS, timeout=30.0)
            uniqueDelegators: int = len(r.json()["delegation_responses"])
            sorted_delegations: List = sorted(
                r.json()["delegation_responses"],
                key=lambda k: int(k["balance"].get("amount")),
                reverse=True,
            )
            for idx in range(0, 10):
                top10shares += float(sorted_delegations[idx]["balance"]["amount"])
            # Calculate % held by top 10 delegators
            top10pc = top10shares / float(validatorData["tokens"])
        except Exception as e:
            logging.warning(e)

    logging.info(
        f"- {validatorData['description']['moniker']:15} "
        + f"| Elapsed: {time.time() - start_time:>5.2f}s | Delegators: {uniqueDelegators:>5} "
        + f"| Top10: {top10pc * 100:>.2f}% "
        + f"| Bonded: {int(validatorData['tokens'])/10**18:>16,.2f} nom"
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
