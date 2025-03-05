from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import ipfshttpclient
from blockchain_system import Blockchain, SecureIPFSStorage, UserManager  # Import backend logic

# Flask app setup
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management

# Initialize system components
blockchain = Blockchain()  # Blockchain instance for recording CID and metadata
storage = SecureIPFSStorage()  # IPFS instance for storing/retrieving files
user_manager = UserManager()  # User manager instance to handle registration and login

# Initialize IPFS Client
ipfs = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')

# Home route
@app.route('/')
def home():
    return redirect(url_for('login'))

# Set Upload Folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
            session['user'] = wallet_address  # Store user session
            return redirect(url_for('dashboard'))  # Redirect to dashboard on success
    return render_template('login.html')


# User Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))
    return render_template('dashboard.html')


# Upload Data
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_wallet = session['user']
        data = request.form['data']  # Data to upload

        # Fetch the user and their public key
        user = user_manager.users[user_wallet]
        encrypted_data = storage.encrypt_data(data, user['public_key'])  # Encrypt the data with the user's public key

        # Upload the encrypted data to IPFS
        ipfs_cid = storage.upload_to_ipfs(encrypted_data)

        # Metadata for blockchain (file name, size)
        file_metadata = {"file_name": "data.txt", "size": f"{len(data)} bytes"}

        # Add transaction to blockchain
        blockchain.add_transaction(user_wallet, ipfs_cid, file_metadata)
        blockchain.create_block(data=ipfs_cid, previous_hash=blockchain.chain[-1]['hash'])
        

    
    flash(f"Data uploaded to IPFS. CID: {ipfs_cid}")
    return redirect(url_for('dashboard'))  # Redirect to dashboard after upload
    return render_template("upload.html")
    

def upload_file():
    if request.method == "POST":
    file = request.files["file"]
    if file:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)  # Save locally first 
        
        # Upload file to IPFS
        res = ipfs.add(file_path)
        file_hash = res['Hash']
        return render_template("upload.html", file_hash=file_hash)
    

# Retrieve Data
@app.route('/retrieve', methods=['GET', 'POST'])
def retrieve():
    if 'user' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        cid = request.form['cid']  # CID to retrieve

        # Fetch the user and their private key
        user_wallet = session['user']
        user = user_manager.users[user_wallet]

        # Retrieve encrypted data from IPFS
        encrypted_data = storage.retrieve_from_ipfs(cid)

        # Decrypt the data using the user's private key
        decrypted_data = storage.decrypt_data(encrypted_data, user['private_key'])

        flash(f"Retrieved Data: {decrypted_data}")
        return redirect(url_for('dashboard'))  # Redirect to dashboard after retrieval

    return render_template('retrieve.html')

def retrieve_file():
    if request.method == "POST":
        file_hash = request.form["file_hash"]
        file_url = f"https://ipfs.io/ipfs/{file_hash}"
        return render_template("retrieve.html", file_url=file_url)
    return render_template("retrieve.html")


# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully.")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
