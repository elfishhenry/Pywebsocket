from datetime import datetime as dtime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Column, Integer
# models.py
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()  # Single instance

def setup_db(app):
    db.init_app(app)  # Initialize once
    with app.app_context():
        db.create_all()


# Association table for likes
likes = db.Table('likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('image_id', db.Integer, db.ForeignKey('image.id'), primary_key=True)
)
 
class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=dtime.utcnow)
    liked_images = db.relationship('Image', secondary=likes, backref='liked_by')
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


    def __repr__(self):
        return f"<User {self.username}>"


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(200), nullable=False)
    likes = db.Column(db.Integer, default=0)  # Ensure this column exists
    upload_date = db.Column(db.DateTime, nullable=False, default=dtime.utcnow)


    def __repr__(self):
        return f"<Image {self.title}>"


class Like(db.Model):
    __tablename__ = 'like'

    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # Store IP to prevent duplicate likes
    created_at = db.Column(db.DateTime, default=dtime.utcnow)

    # Unique constraint to prevent duplicate likes from the same IP for the same image
    __table_args__ = (
        db.UniqueConstraint('image_id', 'ip_address', name='_image_ip_uc'),
    )

    def __repr__(self):
        return f"<Like for Image {self.image_id}>"