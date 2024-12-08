"""Main application module"""
import os
import logging
from datetime import datetime
import traceback
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

from .utils.epub_analyzer import analyze_epub
from .utils.onix_processor import process_onix
from .utils.memory_utils import log_memory_usage
from .config import config

def create_app(config_name='default'):
    """Create Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Configure logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/accessonix.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('AccessONIX startup')

    def allowed_file(filename, allowed_extensions):
        """Check if file has an allowed extension"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    @app.route('/')
    def index():
        """Render the main page"""
        return render_template('index.html')

    @app.route('/help')
    def help():
        """Render the help page"""
        return render_template('help.html')

    @app.route('/process', methods=['POST'])
    def process():
        """Process uploaded files and generate ONIX"""
        try:
            # Log initial memory usage
            initial_memory = log_memory_usage()
            app.logger.info(f"Initial memory usage: {initial_memory:.2f} MB")

            # Check if files were uploaded
            if 'epub_file' not in request.files or 'onix_file' not in request.files:
                flash('No files uploaded', 'error')
                return redirect(url_for('index'))

            epub_file = request.files['epub_file']
            onix_file = request.files['onix_file']
            epub_isbn = request.form.get('epub_isbn', '')
            role = request.form.get('role', 'basic')

            # Validate files
            if epub_file.filename == '' or onix_file.filename == '':
                flash('No selected files', 'error')
                return redirect(url_for('index'))

            if not allowed_file(epub_file.filename, {'epub'}) or not allowed_file(onix_file.filename, {'xml'}):
                flash('Invalid file type', 'error')
                return redirect(url_for('index'))

            # Process EPUB file
            app.logger.info(f"Analyzing EPUB file: {epub_file.filename}")
            epub_features = analyze_epub(epub_file)

            # Process ONIX file
            app.logger.info(f"Processing ONIX file: {onix_file.filename}")
            
            # Get publisher data if in enhanced mode
            publisher_data = None
            if role == 'enhanced':
                publisher_data = {
                    'sender_name': request.form.get('sender_name'),
                    'contact_name': request.form.get('contact_name'),
                    'email': request.form.get('email'),
                    'product_composition': request.form.get('product_composition'),
                    'product_form': request.form.get('product_form'),
                    'language_code': request.form.get('language_code'),
                    'price_cad': request.form.get('price_cad'),
                    'price_gbp': request.form.get('price_gbp'),
                    'price_usd': request.form.get('price_usd')
                }
                
                # Log publisher data for debugging
                app.logger.info(f"Publisher data: {publisher_data}")

            # Process ONIX with publisher data
            processed_xml = process_onix(
                epub_features=epub_features,
                xml_content=onix_file.read(),
                epub_isbn=epub_isbn,
                publisher_data=publisher_data
            )

            # Log final memory usage
            final_memory = log_memory_usage()
            app.logger.info(f"Final memory usage: {final_memory:.2f} MB")

            # Save and return processed file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"AccessONIX_{epub_isbn}_{timestamp}.xml"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            
            with open(output_path, 'wb') as f:
                f.write(processed_xml)

            return send_file(
                output_path,
                mimetype='application/xml',
                as_attachment=True,
                download_name=output_filename
            )

        except Exception as e:
            app.logger.error(f"Error during processing: {str(e)}")
            app.logger.error(traceback.format_exc())
            flash(str(e), 'error')
            return redirect(url_for('index'))

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors"""
        return render_template('error.html', error="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        return render_template('error.html', error="Internal server error"), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle file size exceeded errors"""
        flash('File size exceeded the maximum limit (16MB)', 'error')
        return redirect(url_for('index'))

    return app

# Create the application instance
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    app.run()