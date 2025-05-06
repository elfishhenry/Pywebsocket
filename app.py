import os
import logging

from flask import Flask, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect
from models import db  # Import from where `db` is defined
from flask_login import LoginManager
from models import User
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from models import db, User, Image

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)

# Set up CSRF protection
csrf = CSRFProtect(app)

# Configure app
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Needed for url_for to generate with HTTPS

# Configure the database with a persistent path if needed
persistent_db_path = os.getenv("DATABASE_DIR", "instance")  # Path to store DB
os.makedirs(persistent_db_path, exist_ok=True)  # Ensure directory exists

db_file = os.path.join(persistent_db_path, "imageshare.db")

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", f"sqlite:///{db_file}")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Disable event notifications for performance

# Set upload folder configuration
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom ModelView to restrict access to admins only
class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

# Admin setup
admin = Admin(app, name='ImageShare Admin', template_mode='bootstrap4')
admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Image, db.session))

# Initialize the app with the extension
db.init_app(app)

# Create all tables if they do not exist
if not os.path.exists(db_file):
    logging.info(f"Database not found at {db_file}. Creating database...")
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
else:
    logging.info(f"Database found at {db_file}. No need to create.")
