import os
import uuid
import io
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, abort, current_app, send_from_directory, session
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from PIL import Image as PILImage
from pillow_heif import register_heif_opener
from forms import SignupForm, LoginForm
from models import User, Image
from flask_login import login_user, logout_user, login_required, current_user
from forms import SettingsForm

# Register HEIF opener to handle Apple HEIC/HEIF formats
register_heif_opener()

from app import app, db, csrf
from models import Image, Like
from forms import ImageUploadForm, SearchForm
from utils import get_client_ip


# Add context processor to make 'now' variable available in all templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


@app.route('/')
def index():
    search_form = SearchForm()
    images = Image.query.order_by(Image.likes.desc()).all()
    liked_images = set()
    if current_user.is_authenticated:
        # Assuming you have a relationship set up
       liked_images = set(image.id for image in current_user.liked_images) if current_user.is_authenticated else set()

    return render_template('index.html', images=images, search_form=search_form, liked_images=liked_images)

@app.route('/make-me-admin')
def make_me_admin():
    user = User.query.filter_by(username='elfishhenry').first()
    if not user:
        return "User not found", 404
    user.is_admin = True
    db.session.commit()
    return f"User {user.username} is now admin."

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = ImageUploadForm()
    search_form = SearchForm()  # Create search form for the navbar

    if form.validate_on_submit():
        # Process the uploaded file
        f = form.image.data
        
        # Create a secure and unique filename
        filename = secure_filename(f.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        # Define the upload and temporary file paths
        try:
            # Ensure the upload folder exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            relative_filepath = f"uploads/{unique_filename}"

            # Save the uploaded file to a temporary location
            tmp_dir = os.getenv('TMP', '/tmp')  # Use 'TMP' environment variable for cross-platform compatibility
            os.makedirs(tmp_dir, exist_ok=True)  # Ensure temp directory exists
            tmp_path = os.path.join(tmp_dir, unique_filename)
            
            app.logger.debug(f"TMP directory: {tmp_dir}")
            app.logger.debug(f"Temporary file path: {tmp_path}")
            app.logger.debug(f"Upload folder: {app.config['UPLOAD_FOLDER']}")

            f.save(tmp_path)
            if not os.path.exists(tmp_path):
                app.logger.error(f"File not found after saving: {tmp_path}")
                raise FileNotFoundError(f"Temporary file not found: {tmp_path}")
            
            # Open the saved file with PIL
            with PILImage.open(tmp_path) as img:
                # Check if file is HEIC/HEIF format
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in ['.heic', '.heif']:
                    app.logger.info(f"Converting {file_ext} image to JPEG format")
                    unique_filename = f"{uuid.uuid4().hex}_{os.path.splitext(filename)[0]}.jpeg"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    relative_filepath = f"uploads/{unique_filename}"
                    
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(filepath, 'JPEG', quality=90)
                else:
                    # For non-HEIC formats, save the file directly to the final location
                    img.save(filepath)

            # Clean up the temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            # Create a database record for the image
            new_image = Image(
                title=form.title.data,
                description=form.description.data,
                filename=unique_filename,
                filepath=relative_filepath,
                upload_date=datetime.utcnow()
            )
            
            db.session.add(new_image)
            db.session.commit()

            flash('Image uploaded successfully!', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            app.logger.error(f"Error uploading file: {str(e)}", exc_info=True)
            flash(f'Error uploading file: {str(e)}', 'danger')

    return render_template('upload.html', form=form, search_form=search_form)

@app.route('/search', methods=['GET'])
def search():
    search_form = SearchForm()
    query = request.args.get('query', '')
    
    if query:
        # Search for images matching the query in title or description
        images = Image.query.filter(
            or_(
                Image.title.ilike(f'%{query}%'),
                Image.description.ilike(f'%{query}%')
            )
        ).order_by(Image.likes.desc()).all()
        
        return render_template('search.html', images=images, query=query, search_form=search_form)
    
    # If no query provided, redirect to home
    return redirect(url_for('index'))

@app.route('/image/<int:image_id>')
def image_details(image_id):
    search_form = SearchForm()
    image = Image.query.get_or_404(image_id)
    return render_template('image_details.html', image=image, search_form=search_form)

@app.errorhandler(404)
def page_not_found(e):
    search_form = SearchForm()
    return render_template('404.html', search_form=search_form), 404

@app.errorhandler(500)
def server_error(e):
    search_form = SearchForm()
    return render_template('500.html', search_form=search_form), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files directly."""
    app.logger.debug(f"Attempting to serve file: {filename}")
    try:
        # Check if file exists
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.isfile(filepath):
            app.logger.warning(f"File not found: {filename}")
            # Return a placeholder image instead of 404
            return send_from_directory(
                'static',
                'img/image-not-found.jpg' if os.path.exists('static/img/image-not-found.jpg') else 'img/placeholder.jpg',
            ), 200
        
        # Return the requested file
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        app.logger.error(f"Error serving file {filename}: {str(e)}")
        abort(404)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists.', 'danger')
            return render_template('signup.html', form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists.', 'danger')
            return render_template('signup.html', form=form)
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['is_admin'] = user.is_admin
        flash('Account created successfully! You are now logged in.', 'success')
        return redirect(url_for('index'))
    return render_template('signup.html', form=form)



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)  # Flask-Login
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()  # Flask-Login
    flash('You have logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm(obj=current_user)
    search_form = SearchForm()
    if form.validate_on_submit():
        # Check if username/email is changing and unique
        if form.username.data != current_user.username:
            if User.query.filter_by(username=form.username.data).first():
                flash('Username already taken.', 'danger')
                return render_template('settings.html', form=form, search_form=search_form)
            current_user.username = form.username.data

        if form.email.data != current_user.email:
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already in use.', 'danger')
                return render_template('settings.html', form=form, search_form=search_form)
            current_user.email = form.email.data

        # If password fields are filled, update password
        if form.password.data:
            current_user.set_password(form.password.data)
            flash('Password updated.', 'success')

        db.session.commit()
        flash('Settings updated!', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', form=form, search_form=search_form)

@app.route('/like/<int:image_id>', methods=['POST'])
@csrf.exempt  # Exempt this route from CSRF protection since we're handling it via JS
@login_required
def like_image(image_id):
    # Ensure the user is logged in
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None

    # Fetch the image
    image = Image.query.get_or_404(image_id)
    
    # Get the IP address of the client
    ip_address = get_client_ip()
    
    if user:
        # Toggle like/unlike for logged-in users
        if user in image.likes:
            image.likes.remove(user)
            db.session.commit()
            return jsonify({'message': 'Image unliked', 'likes_count': len(image.likes)})
        else:
            image.likes.append(user)
            db.session.commit()
            return jsonify({'message': 'Image liked', 'likes_count': len(image.likes)})
    else:
        # Handle anonymous likes based on IP address
        existing_like = Like.query.filter_by(image_id=image_id, ip_address=ip_address).first()
        if existing_like:
            return jsonify({'success': False, 'message': 'You already liked this image', 'likes': image.likes})
        
        # Create a new like
        new_like = Like(image_id=image_id, ip_address=ip_address)
        db.session.add(new_like)
        
        # Update the image like count
        image.likes += 1
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Like added!', 'likes': image.likes})
    
@app.route('/admin/delete_image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    image = Image.query.get_or_404(image_id)
    db.session.delete(image)
    db.session.commit()
    flash('Image deleted successfully!', 'success')
    return redirect(url_for('index'))