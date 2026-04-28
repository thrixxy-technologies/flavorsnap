from web3 import Web3
from eth_account import Account
import os

RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY = os.getenv("TEST_PRIVATE_KEY")


def get_web3():
    return Web3(Web3.HTTPProvider(RPC_URL))


def get_test_account():
    if PRIVATE_KEY:
        return Account.from_key(PRIVATE_KEY)
    return Account.create()