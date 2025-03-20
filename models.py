from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    wallet_address = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_hash = db.Column(db.String(255), nullable=False)
    owner_wallet = db.Column(db.String(255), db.ForeignKey('user.wallet_address'), nullable=False)
