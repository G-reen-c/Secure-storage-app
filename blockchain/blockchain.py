from web3 import Web3
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AVAX_RPC_URL = os.getenv("https://avalanche-mainnet.infura.io/v3/9e0d26da1f324dda9080cd79da131768")  # Avalanche RPC
CONTRACT_ADDRESS = os.getenv("0x7338410F9c4335422e63ace32b4f7C7abb5C7C8A")
PRIVATE_KEY = os.getenv("9e0d26da1f324dda9080cd79da131768")


CONTRACT_ABI = json.loads("""
[
    {
        "inputs": [{"internalType": "string", "name": "_fileHash", "type": "string"}],
        "name": "logTransaction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "_user", "type": "address"}],
        "name": "getUserTransactions",
        "outputs": [{"internalType": "struct TransactionLogger.Transaction[]", "type": "tuple[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]
""")

web3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))

if not web3.is_connected():
    raise Exception("Failed to connect to Avalanche network. Check INFURA_URL.")

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)


def log_transaction(file_hash, user_address):
    try:
        nonce = web3.eth.get_transaction_count(user_address)

        txn = contract.functions.logTransaction(file_hash).build_transaction({
            "from": user_address,
            "nonce": nonce,
            "gas": 2000000,
            "gasPrice": web3.to_wei("25", "gwei")
        })

        signed_txn = web3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

        return web3.to_hex(txn_hash)

    except Exception as e:
        return f"Transaction failed: {str(e)}"


def get_user_transactions(user_address):
    try:
        return contract.functions.getUserTransactions(user_address).call()
    except Exception as e:
        return f"Error fetching transactions: {str(e)}"
