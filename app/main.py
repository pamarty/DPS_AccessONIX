from flask import Flask, render_template, request, send_file, jsonify, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import tempfile
import logging
from datetime import datetime
import traceback
from logging.handlers import RotatingFileHandler

from .utils.epub_analyzer import analyze_epub
from .utils.onix_processor import process_onix
from .utils.memory_utils import check_memory_usage, optimize_memory
from .utils.validators import validate_form_data, validate_files
from .config import config

def create_app(config_name='default'):
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
            # Check memory usage at start
            initial_memory = check_memory_usage()
            app.logger.info(f"Initial memory usage: {initial_memory:.2f} MB")

            # Validate files
            file_errors = validate_files(request.files)
            if file_errors:
                return jsonify({'errors': file_errors}), 400

            # Get form data
            epub_isbn = request.form.get('epub_isbn')
            user_role = request.form.get('role', 'production')

            # Validate form data
            form_errors = validate_form_data(request.form, user_role)
            if form_errors:
                return jsonify({'errors': form_errors}), 400

            # Process files
            try:
                # Analyze EPUB
                epub_file = request.files['epub_file']
                app.logger.info(f"Analyzing EPUB file: {epub_file.filename}")
                accessibility_features = analyze_epub(epub_file)

                # Read ONIX file
                onix_file = request.files['onix_file']
                app.logger.info(f"Processing ONIX file: {onix_file.filename}")
                xml_content = onix_file.read()

                # Prepare publisher data if role is publisher
                publisher_data = None
                if user_role == 'publisher':
                    publisher_data = {
                        'sender_name': request.form.get('sender_name'),
                        'contact_name': request.form.get('contact_name'),
                        'email': request.form.get('email'),
                        'product_composition': request.form.get('product_composition'),
                        'product_form': request.form.get('product_form'),
                        'language_code': request.form.get('language_code'),
                        'prices': {
                            'cad': request.form.get('price_cad'),
                            'gbp': request.form.get('price_gbp'),
                            'usd': request.form.get('price_usd')
                        }
                    }

                # Process ONIX
                processed_xml = process_onix(
                    accessibility_features,
                    xml_content,
                    epub_isbn,
                    publisher_data
                )

                # Create output file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"AccessONIX_{epub_isbn}_{timestamp}.xml"
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xml')
                temp_file.write(processed_xml)
                temp_file.close()

                # Check final memory usage
                final_memory = check_memory_usage()
                app.logger.info(f"Final memory usage: {final_memory:.2f} MB")
                
                # Optimize memory if needed
                if final_memory - initial_memory > app.config['MEMORY_OPTIMIZATION_THRESHOLD']:
                    optimize_memory()

                # Send processed file
                return send_file(
                    temp_file.name,
                    mimetype='application/xml',
                    as_attachment=True,
                    download_name=output_filename
                )

            finally:
                # Cleanup
                if 'temp_file' in locals():
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        app.logger.error(f"Error cleaning up temporary file: {str(e)}")

        except Exception as e:
            app.logger.error(f"Error during processing: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', error="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html', error="Internal server error"), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'error': 'File size exceeded the maximum limit (16MB)'}), 413

    return app

# Create the application instance
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    app.run()