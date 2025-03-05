import os
import json
import bcrypt
import pyotp
from flask import session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USERS_FILE = "auth/users.json"

# Ensure users file exists
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)


def load_users():
    """Load user data from JSON file."""
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    """Save user data to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def register_user(first_name, last_name, wallet_address, password):
    """Registers a new user with hashed password and a 2FA secret key."""
    users = load_users()

    if wallet_address in users:
        return "User already exists."

    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    otp_secret = pyotp.random_base32()  # Generate 2FA secret key

    users[wallet_address] = {
        "first_name": first_name,
        "last_name": last_name,
        "password": hashed_password,
        "otp_secret": otp_secret
    }

    save_users(users)
    return "Success"


def verify_user(wallet_address, password):
    """Verifies user login credentials."""
    users = load_users()

    if wallet_address not in users:
        return "User not found."

    stored_password = users[wallet_address]["password"]
    if bcrypt.checkpw(password.encode(), stored_password.encode()):
        return "Success"
    return "Invalid credentials."


def generate_otp(wallet_address):
    """Generates a One-Time Password (OTP) for 2FA."""
    users = load_users()

    if wallet_address not in users:
        return None

    otp_secret = users[wallet_address]["otp_secret"]
    otp = pyotp.TOTP(otp_secret).now()

    # Store OTP in session for verification
    session["otp"] = otp
    return otp


def verify_otp(wallet_address, otp):
    """Verifies the OTP for 2FA authentication."""
    users = load_users()

    if wallet_address not in users:
        return False

    otp_secret = users[wallet_address]["otp_secret"]
    return pyotp.TOTP(otp_secret).verify(otp)
