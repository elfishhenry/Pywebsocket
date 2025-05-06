import os
import uuid
import io
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, abort, current_app, send_from_directory
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from PIL import Image as PILImage
from pillow_heif import register_heif_opener

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
    # Get images sorted by most likes first
    images = Image.query.order_by(Image.likes.desc()).all()
    return render_template('index.html', images=images, search_form=search_form)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    form = ImageUploadForm()
    search_form = SearchForm()  # Create search form for the navbar
    
    if form.validate_on_submit():
        # Process the uploaded file
        f = form.image.data
        
        # Create a secure and unique filename
        filename = secure_filename(f.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        # Get the full file path
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        relative_filepath = f"uploads/{unique_filename}"
        
        try:
            # First, save the uploaded file to a temporary location
            tmp_path = os.path.join('/tmp', unique_filename)
            f.save(tmp_path)
            
            # Open the saved file with PIL
            with PILImage.open(tmp_path) as img:
                # Check if file is HEIC/HEIF format
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in ['.heic', '.heif']:
                    app.logger.info(f"Converting {file_ext} image to JPEG format")
                    # Change the filename to JPEG
                    unique_filename = f"{uuid.uuid4().hex}_{os.path.splitext(filename)[0]}.jpeg"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    relative_filepath = f"uploads/{unique_filename}"
                    
                    # Convert to RGB mode (remove alpha channel if present)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save as JPEG
                    img.save(filepath, 'JPEG', quality=90)
                else:
                    # For non-HEIC formats, save the file directly to the final location
                    with open(tmp_path, 'rb') as tmp_file:
                        with open(filepath, 'wb') as final_file:
                            final_file.write(tmp_file.read())
            
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
            app.logger.error(f"Error uploading file: {str(e)}")
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

@app.route('/like/<int:image_id>', methods=['POST'])
@csrf.exempt  # Exempt this route from CSRF protection since we're handling it via JS
def like_image(image_id):
    image = Image.query.get_or_404(image_id)
    ip_address = get_client_ip()
    
    # Check if user already liked this image
    existing_like = Like.query.filter_by(image_id=image_id, ip_address=ip_address).first()
    
    if existing_like:
        return jsonify({'success': False, 'message': 'You already liked this image', 'likes': image.likes})
    
    # Create new like
    new_like = Like(image_id=image_id, ip_address=ip_address)
    db.session.add(new_like)
    
    # Update image like count
    image.likes += 1
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Like added!', 'likes': image.likes})

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
