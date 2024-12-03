import re
from datetime import datetime

# Validation patterns
PATTERNS = {
    'name': re.compile(r'^[a-zA-Z0-9\s\-\'\.]+$'),
    'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
    'price': re.compile(r'^\d+(\.\d{1,2})?$'),
    'isbn': re.compile(r'^\d{13}$'),
    'language_code': re.compile(r'^[a-z]{3}$')
}

VALID_PRODUCT_COMPOSITIONS = ['00', '01', '02', '03', '10', '11', '20', '30']
VALID_PRODUCT_FORMS = ['BA', 'BB', 'BC', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ']

def validate_form_data(form_data, role='production'):
    """
    Validate all form inputs based on role
    Returns: list of error messages (empty if all valid)
    """
    errors = []
    
    # Basic validations for all roles
    if not PATTERNS['isbn'].match(form_data.get('epub_isbn', '')):
        errors.append('Invalid ISBN format (must be 13 digits)')

    # Publisher-specific validations
    if role == 'publisher':
        # Sender information
        if not PATTERNS['name'].match(form_data.get('sender_name', '')):
            errors.append('Invalid Sender Name format')
        if not PATTERNS['name'].match(form_data.get('contact_name', '')):
            errors.append('Invalid Contact Name format')
        if not PATTERNS['email'].match(form_data.get('email', '')):
            errors.append('Invalid Email format')
            
        # Product information
        if form_data.get('product_composition') not in VALID_PRODUCT_COMPOSITIONS:
            errors.append('Invalid Product Composition code')
        if form_data.get('product_form') not in VALID_PRODUCT_FORMS:
            errors.append('Invalid Product Form code')
        if not PATTERNS['language_code'].match(form_data.get('language_code', '')):
            errors.append('Invalid Language Code format')
            
        # Price validations
        for currency in ['cad', 'gbp', 'usd']:
            price = form_data.get(f'price_{currency}')
            if price and not PATTERNS['price'].match(str(price)):
                errors.append(f'Invalid {currency.upper()} Price format')
    
    return errors

def validate_files(files):
    """
    Validate uploaded files
    Returns: list of error messages (empty if all valid)
    """
    errors = []
    
    if 'epub_file' not in files or 'onix_file' not in files:
        errors.append('Both EPUB and ONIX files are required')
        return errors
    
    epub_file = files['epub_file']
    onix_file = files['onix_file']
    
    if epub_file.filename == '' or onix_file.filename == '':
        errors.append('Both files must be selected')
    
    if not epub_file.filename.endswith('.epub'):
        errors.append('Invalid EPUB file format')
    
    if not onix_file.filename.endswith('.xml'):
        errors.append('Invalid ONIX file format')
    
    return errors

def format_date(date_string):
    """Format date string to YYYYMMDD"""
    try:
        date_formats = [
            "%Y%m%d",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%m-%d-%Y"
        ]
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime("%Y%m%d")
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse date: {date_string}")
    
    except Exception as e:
        raise ValueError(f"Error formatting date {date_string}: {str(e)}")