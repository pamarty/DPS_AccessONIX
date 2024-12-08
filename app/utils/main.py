import os
import logging
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from .utils.epub_analyzer import analyze_epub
from .utils.onix_processor import process_onix
from .utils.memory_utils import log_memory_usage
from .config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        # Log initial memory usage
        initial_memory = log_memory_usage()
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")

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
        logger.info(f"Analyzing EPUB file: {epub_file.filename}")
        epub_features = analyze_epub(epub_file)

        # Process ONIX file
        logger.info(f"Processing ONIX file: {onix_file.filename}")
        
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

        # Process ONIX with publisher data
        processed_xml = process_onix(
            epub_features=epub_features,
            xml_content=onix_file.read(),
            epub_isbn=epub_isbn,
            publisher_data=publisher_data
        )

        # Log final memory usage
        final_memory = log_memory_usage()
        logger.info(f"Final memory usage: {final_memory:.2f} MB")

        # Save and return processed file
        output_filename = f"AccessONIX_{epub_isbn}.xml"
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
        logger.error(f"Error during processing: {str(e)}")
        logger.error(traceback.format_exc())
        flash(str(e), 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)