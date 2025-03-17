from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import requests
import secrets
from blockchain_system import Blockchain, SecureIPFSStorage, UserManager  # Backend logic
from blockchain.blockchain import log_transaction
from werkzeug.utils import secure_filename

# Flask app setup
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # More secure session key

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

# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        wallet_address = request.form['wallet_address']
        password = request.form['password']

        message = user_manager.register_user(first_name, last_name, wallet_address, password)
        flash(message)
        return redirect(url_for('login'))
    return render_template('register.html')

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        wallet_address = request.form['wallet_address']
        password = request.form['password']
        is_logged_in, message, user = user_manager.login_user(wallet_address, password)

        flash(message)
        if is_logged_in:
            session['user'] = wallet_address  # Store session
            return redirect(url_for('dashboard'))
    return render_template('login.html')

# User Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
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
    if 'user' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

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
                user_wallet = session['user']
                private_key = session.get("private_key")  # Ensure private key is secure
                txn_hash = log_transaction(ipfs_cid, user_wallet, private_key) if private_key else "Blockchain logging failed."

                flash(f"File uploaded successfully. CID: {ipfs_cid}")
                return render_template("upload.html", file_hash=ipfs_cid, txn_hash=txn_hash)

            except Exception as e:
                flash(f"Upload failed: {str(e)}")

        flash("Invalid file type. Allowed types: txt, pdf, png, jpg, jpeg, gif.")
        return redirect(url_for('upload_file'))

    return render_template("upload.html")

# Retrieve File from IPFS
@app.route('/retrieve', methods=['GET', 'POST'])
def retrieve_file():
    if 'user' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    if request.method == "POST":
        file_hash = request.form["file_hash"]
        file_url = f"https://gateway.pinata.cloud/ipfs/{file_hash}" if file_hash else None
        return render_template("retrieve.html", file_url=file_url)

    return render_template("retrieve.html")

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully.")
    return redirect(url_for('login'))

# Run Flask
if __name__ == '__main__':
    app.run(debug=True)
