import pytest
from web3 import Web3
from eth_account import Account

from tests.integration.fixtures.blockchain import get_web3, get_test_account
from tests.integration.utils.helpers import wait_for_tx_receipt

# ---------------------------
# 🔌 Connection Test
# ---------------------------

def test_blockchain_connection():
    w3 = get_web3()
    assert w3.is_connected(), "Web3 is not connected to the blockchain"


# ---------------------------
# 👤 Account Test
# ---------------------------

def test_account_creation():
    account = get_test_account()
    assert account.address is not None
    assert account.key is not None


# ---------------------------
# 💸 Transaction Test
# ---------------------------

def test_send_transaction():
    w3 = get_web3()
    sender = get_test_account()
    receiver = Account.create()

    tx = {
        "to": receiver.address,
        "value": w3.to_wei(0.001, "ether"),
        "gas": 21000,
        "gasPrice": w3.to_wei("10", "gwei"),
        "nonce": w3.eth.get_transaction_count(sender.address),
    }

    signed_tx = w3.eth.account.sign_transaction(tx, sender.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    receipt = wait_for_tx_receipt(w3, tx_hash)

    assert receipt.status == 1, "Transaction failed"


# ---------------------------
# 📜 Smart Contract Interaction
# ---------------------------

@pytest.mark.skip(reason="Requires deployed contract")
def test_contract_interaction():
    w3 = get_web3()
    contract_address = "0xYourContractAddress"

    abi = [
        {
            "inputs": [],
            "name": "getValue",
            "outputs": [{"internalType": "uint256", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]

    contract = w3.eth.contract(address=contract_address, abi=abi)

    result = contract.functions.getValue().call()
    assert isinstance(result, int)


# ---------------------------
# 📡 Event Log Test
# ---------------------------

@pytest.mark.skip(reason="Requires event-emitting contract")
def test_event_logs():
    w3 = get_web3()

    # Example placeholder
    logs = w3.eth.get_logs({
        "fromBlock": "latest",
    })

    assert isinstance(logs, list)


# ---------------------------
# ❌ Failure Scenario
# ---------------------------

def test_invalid_transaction_fails():
    w3 = get_web3()
    sender = get_test_account()

    tx = {
        "to": "0x0000000000000000000000000000000000000000",
        "value": -1,  # invalid
        "gas": 21000,
        "gasPrice": w3.to_wei("10", "gwei"),
        "nonce": w3.eth.get_transaction_count(sender.address),
    }

    with pytest.raises(Exception):
        w3.eth.account.sign_transaction(tx, sender.key)