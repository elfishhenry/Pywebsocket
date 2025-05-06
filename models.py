import datetime
from app import db

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f"<Image {self.title}>"

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # Store IP to prevent duplicate likes
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Define unique constraint to prevent duplicate likes from same IP for same image
    __table_args__ = (
        db.UniqueConstraint('image_id', 'ip_address', name='_image_ip_uc'),
    )
    
    def __repr__(self):
        return f"<Like for Image {self.image_id}>"
