from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import requests
import secrets
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import re

# Flask app setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "0x7338410F9c4335422e63ace32b4f7C7abb5C7C8A")  # More secure session key

# Get database URL from environment variables
db_url = os.getenv("DATABASE_URL")

# Fix 'postgres://' to 'postgresql://' (required for SQLAlchemy)
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url  
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database and migration
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from models import User, File

from blockchain_system import Blockchain, SecureIPFSStorage, UserManager  # Backend logic
from blockchain.blockchain import log_transaction

# System components
blockchain = Blockchain()
storage = SecureIPFSStorage()
user_manager = UserManager()

# Pinata API Credentials 
PINATA_API_KEY = "cbcb0e4497940aa8aa0c"
PINATA_SECRET_API_KEY = "5241e3eae68dcaad306ff1671fe3b42cd228a6b7266351f11a3e911f4c719184"

# Set Upload Folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}  # Restrict file types

# Home Route
@app.route('/')
def home():
    return redirect(url_for('login'))

import csv
import time # for testing

# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    start_time = time.time()  # Start time
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        wallet_address = request.form['wallet_address']
        password = request.form['password']

        # Check if user already exists
        existing_user = User.query.filter_by(wallet_address=wallet_address).first()
        if existing_user:
            flash("Wallet already registered.")
            return redirect(url_for('register'))

        # Hash password securely before saving
        hashed_password = generate_password_hash(password)

        # Create new user and commit to DB
        new_user = User(first_name=first_name, last_name=last_name, wallet_address=wallet_address, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()  

        flash("Registration successful. Please log in.")
        
        end_time = time.time()  # End time
        latency = end_time - start_time  # Calculate latency

        # Save latency data to CSV
        log_latency("register", latency)
        
        return redirect(url_for('login'))
    return render_template('register.html')


# Function to log latency data into a CSV file
def log_latency(action, latency):
    file_path = "latency_data.csv"
    try:
        with open(file_path, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([action, latency])
    except Exception as e:
        print(f"Error writing latency data: {e}")
        
        
# User Login
from datetime import timedelta
app.permanent_session_lifetime = timedelta(days=7)  # Keep session for a week

@app.route('/login', methods=['GET', 'POST'])
def login():
    start_time = time.time()  # Start time
    
    if request.method == 'POST':
        wallet_address = request.form['wallet_address']
        password = request.form['password']

        # Check if user exists
        user = User.query.filter_by(wallet_address=wallet_address).first()

        if not user:
            flash("User not found. Please register first.")
            return redirect(url_for('register'))

        # Check password hash
        if not check_password_hash(user.password_hash, password):
            flash("Incorrect password. Please try again.")
            return redirect(url_for('login'))

        # If login successful, store user in session
        session['user'] = user.wallet_address  # Use wallet_address as session key
        flash("Login successful!")
        end_time = time.time()  # End time
        log_latency("login", end_time - start_time)  # Log latency
        return redirect(url_for('dashboard'))
    
    
    end_time = time.time()  # End time for failed attempts
    log_latency("login_failed", end_time - start_time)
    return render_template('login.html')


# User Dashboard
@app.route('/dashboard')
def dashboard():
    if not session.get('user'):
        flash("Please log in first.")
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# Check File Type Before Uploading
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to Upload File to Pinata
def upload_to_ipfs(file_path):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_API_KEY
    }

    with open(file_path, "rb") as f:
        response = requests.post(url, headers=headers, files={"file": f})

    if response.status_code == 200:
        return response.json()["IpfsHash"]
    else:
        raise Exception(f"Failed to upload to IPFS: {response.text}")

# File Upload & Secure Blockchain Logging
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if not session.get('user'):
        flash("Please log in first.")
        return redirect(url_for('login'))

    start_time = time.time()  # Start time

    if request.method == "POST":
        file = request.files["file"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)  # Secure filename
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            try:
                # Upload file to Pinata (IPFS)
                ipfs_cid = upload_to_ipfs(file_path)

                # Blockchain Logging
                user_wallet = session['user']  # This should be the real wallet address
                private_key = session.get("private_key")  # Ensure private key is secure

                # Debug: Print wallet address and check if it's valid
                print(f"Debug - Stored Wallet Address: {user_wallet}")

                if user_wallet == "1":
                    print("ERROR: Invalid Wallet Address! Expected a real wallet address.")
                    flash("Invalid wallet address. Please re-login with a valid address.")
                    return redirect(url_for("login"))

                txn_hash = log_transaction(ipfs_cid, user_wallet)

                print(f"Blockchain Debug - Transaction Hash: {txn_hash}")

                # Store Transaction in the Database
                new_transaction = File(file_hash=ipfs_cid, owner_wallet=user_wallet)
                db.session.add(new_transaction)
                db.session.commit()

                print(f"Transaction Saved: {txn_hash}")

                flash(f"File uploaded successfully. CID: {ipfs_cid}")
                
                end_time = time.time()  # End time
                log_latency("upload_file", end_time - start_time)  # Log latency
                
                return render_template("upload.html", file_hash=ipfs_cid, txn_hash=txn_hash)

            except Exception as e:
                flash(f"Upload failed: {str(e)}")
                print(f"Error: {e}")

        flash("Invalid file type. Allowed types: txt, pdf, png, jpg, jpeg, gif.")
        return redirect(url_for('upload_file'))
    
    
    end_time = time.time()  # End time for failed attempts
    log_latency("upload_failed", end_time - start_time)
    return render_template("upload.html")


# Retrieve File from IPFS
@app.route('/retrieve', methods=['GET', 'POST'])
def retrieve_file():
    if not session.get('user'):
        flash("Please log in first.")
        return redirect(url_for('login'))


    if request.method == "POST":
        file_hash = request.form["file_hash"]
        file_url = f"https://beige-actual-cattle-585.mypinata.cloud/ipfs/{file_hash}" if file_hash else None
        return render_template("retrieve.html", file_url=file_url)

    return render_template("retrieve.html")

@app.route('/transactions')
def transactions():
    if not session.get('user'):
        flash("Please log in first.")
        return redirect(url_for('login'))

    start_time = time.time()  # Start time

    # Retrieve transactions from DB
    transactions = File.query.filter_by(owner_wallet=session['user']).all()

    # Convert transactions to required format
    transactions_data = [
        {
            "index": i + 1,
            "timestamp": "Stored in Database",
            "user_wallet": txn.owner_wallet,
            "cid": txn.file_hash,
            "file_metadata": "File stored in IPFS"
        }
        for i, txn in enumerate(transactions)
    ]

    end_time = time.time()  # End time
    log_latency("retrieve_transactions", end_time - start_time)  # Log latency

    return render_template("transactions.html", transactions=transactions_data)

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully.")
    return redirect(url_for('login'))

# Run Flask
if __name__ == '__main__':
    app.run(debug=True)
