import ipfshttpclient
import hashlib
import time
import bcrypt  # For secure password hashing
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes


# Blockchain Class
class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.create_block(data="Genesis Block", previous_hash="0")

    def create_block(self, data, previous_hash):
        block = {
            "index": len(self.chain) + 1,
            "timestamp": str(time.time()),
            "transactions": self.transactions,
            "data": data,
            "previous_hash": previous_hash,
            "hash": self.hash_block(data, previous_hash),
        }
        self.transactions = []
        self.chain.append(block)
        return block

    def hash_block(self, data, previous_hash):
        return hashlib.sha256(f"{data}{previous_hash}".encode()).hexdigest()

    def add_transaction(self, user_wallet, cid, file_metadata):
        transaction = {
            "user_wallet": user_wallet,
            "cid": cid,
            "file_metadata": file_metadata,
            "timestamp": str(time.time()),
        }
        self.transactions.append(transaction)

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current["previous_hash"] != previous["hash"]:
                return False
            if current["hash"] != self.hash_block(
                current["data"], current["previous_hash"]
            ):
                return False
        return True


# Secure Storage with Encryption
class SecureIPFSStorage:
    def encrypt_data(self, plaintext, public_key):
        return public_key.encrypt(
            plaintext.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    def decrypt_data(self, ciphertext, private_key):
        return private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        ).decode()

    def upload_to_ipfs(self, data):
        with open("tempfile.txt", "wb") as f:
            f.write(data)
        result = self.ipfs_client.add("tempfile.txt")
        return result["Hash"]

    def retrieve_from_ipfs(self, cid):
        return self.ipfs_client.cat(cid)


# User Management with RSA Key Pairs
class UserManager:
    def __init__(self):
        self.users = {}

    def register_user(self, first_name, last_name, wallet_address, password):
        if wallet_address in self.users:
            return "Wallet address already registered."
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()
        self.users[wallet_address] = {
            "first_name": first_name,
            "last_name": last_name,
            "password": hashed_password,
            "private_key": private_key,
            "public_key": public_key,
        }
        return "User registered successfully."

    def login_user(self, wallet_address, password):
        user = self.users.get(wallet_address)

        if not user:
            print("Login Debug: User not found")  # Debugging
            return False, "User not found.", None  

        if bcrypt.checkpw(password.encode(), user["password"]):
            print(f"Login Debug: User {user['first_name']} logged in with Wallet {wallet_address}")  # Debugging
            return True, f"Welcome {user['first_name']}!", user

        print("Login Debug: Invalid credentials")  # Debugging
        return False, "Invalid credentials.", None  

    