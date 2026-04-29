import time


def wait_for_tx_receipt(w3, tx_hash, timeout=120):
    start_time = time.time()

    while True:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt:
                return receipt
        except Exception:
            pass

        if time.time() - start_time > timeout:
            raise TimeoutError("Transaction receipt timeout")

        time.sleep(2)