import xml.etree.ElementTree as ET
from lxml import etree
import logging
from datetime import datetime
import traceback
from decimal import Decimal
from .epub_analyzer import CODELIST_196

logger = logging.getLogger(__name__)

# Define the output namespace
ONIX_30_NS = "http://ns.editeur.org/onix/3.0/reference"
NSMAP = {None: ONIX_30_NS}

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
    """Process ONIX XML with accessibility features and publisher data"""
    try:
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(xml_content, parser=parser)
        logger.info(f"XML parsed successfully. Root tag: {root.tag}")

        # Create new root with ONIX 3.0 namespace
        new_root = etree.Element('ONIXMessage', nsmap=NSMAP)
        new_root.set("release", "3.0")

        # Create Header
        new_header = etree.SubElement(new_root, 'Header')

        # Extract sender information from input
        sender = etree.SubElement(new_header, 'Sender')
        
        if publisher_data and publisher_data.get('sender_name'):
            etree.SubElement(sender, 'SenderName').text = publisher_data.get('sender_name')
        else:
            from_company = root.xpath('.//*[local-name() = "FromCompany"]/text()')
            etree.SubElement(sender, 'SenderName').text = from_company[0] if from_company else "Default Company Name"

        if publisher_data and publisher_data.get('contact_name'):
            etree.SubElement(sender, 'ContactName').text = publisher_data.get('contact_name')
        else:
            contact_name = root.xpath('.//*[local-name() = "ContactName"]/text()')
            if contact_name:
                etree.SubElement(sender, 'ContactName').text = contact_name[0]

        if publisher_data and publisher_data.get('email'):
            etree.SubElement(sender, 'EmailAddress').text = publisher_data.get('email')
        else:
            email_address = root.xpath('.//*[local-name() = "EmailAddress"]/text()')
            if email_address:
                etree.SubElement(sender, 'EmailAddress').text = email_address[0]

        # Add sent datetime
        etree.SubElement(new_header, 'SentDateTime').text = datetime.now().strftime("%Y%m%dT%H%M%S")

        # Add message note
        message_note = root.xpath('.//*[local-name() = "MessageNote"]/text()')
        etree.SubElement(new_header, 'MessageNote').text = message_note[0] if message_note else "Converted to ONIX 3.0"

        # Process products
        for old_product in root.xpath('.//*[local-name() = "Product"]'):
            new_product = etree.SubElement(new_root, "Product")
            
            # Record Reference
            record_ref = old_product.xpath('.//*[local-name() = "RecordReference"]/text()')
            etree.SubElement(new_product, 'RecordReference').text = record_ref[0] if record_ref else f"EPUB_{epub_isbn}"
            
            # Notification Type
            etree.SubElement(new_product, 'NotificationType').text = '03'
            
            # Product Identifiers
            process_identifiers(old_product, new_product, epub_isbn)
            
            # Descriptive Detail
            descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')
            process_descriptive_detail(old_product, descriptive_detail, epub_features, publisher_data)
            
            # Collateral Detail
            collateral_detail = etree.SubElement(new_product, 'CollateralDetail')
            process_collateral_detail(old_product, collateral_detail)
            
            # Publishing Detail
            publishing_detail = etree.SubElement(new_product, 'PublishingDetail')
            process_publishing_detail(old_product, publishing_detail)
            
            # Product Supply
            product_supply = etree.SubElement(new_product, 'ProductSupply')
            process_product_supply(old_product, product_supply, publisher_data)

        # Return processed XML
        return etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8')

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def process_identifiers(old_product, new_product, epub_isbn):
    """Process product identifiers"""
    for identifier in old_product.xpath('.//*[local-name() = "ProductIdentifier"]'):
        new_identifier = etree.SubElement(new_product, 'ProductIdentifier')
        
        id_type = identifier.xpath('.//*[local-name() = "ProductIDType"]/text()')
        if id_type:
            etree.SubElement(new_identifier, 'ProductIDType').text = id_type[0]
            
            id_value = etree.SubElement(new_identifier, 'IDValue')
            if id_type[0] in ["03", "15"]:  # ISBN-13
                id_value.text = epub_isbn
            else:
                old_value = identifier.xpath('.//*[local-name() = "IDValue"]/text()')
                id_value.text = old_value[0] if old_value else ''

def process_descriptive_detail(old_product, descriptive_detail, epub_features, publisher_data):
    """Process descriptive detail section"""
    # Product Composition
    comp = etree.SubElement(descriptive_detail, 'ProductComposition')
    comp.text = publisher_data.get('product_composition', '00')

    # Product Form
    form = etree.SubElement(descriptive_detail, 'ProductForm')
    form.text = publisher_data.get('product_form', 'EB')

    # Product Form Detail
    form_detail = etree.SubElement(descriptive_detail, 'ProductFormDetail')
    form_detail.text = 'E101'

    # Process accessibility features
    for code, is_present in epub_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
            etree.SubElement(feature, 'ProductFormFeatureValue').text = code
            etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]

    # Process titles
    for old_title in old_product.xpath('.//*[local-name() = "Title"]'):
        title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
        etree.SubElement(title_detail, 'TitleType').text = '01'
        
        title_element = etree.SubElement(title_detail, 'TitleElement')
        etree.SubElement(title_element, 'TitleElementLevel').text = '01'
        
        title_text = old_title.xpath('.//*[local-name() = "TitleText"]/text()')
        if title_text:
            etree.SubElement(title_element, 'TitleText').text = title_text[0]
        
        subtitle = old_title.xpath('.//*[local-name() = "Subtitle"]/text()')
        if subtitle:
            etree.SubElement(title_element, 'Subtitle').text = subtitle[0]

    # Process contributors
    for old_contributor in old_product.xpath('.//*[local-name() = "Contributor"]'):
        contributor = etree.SubElement(descriptive_detail, 'Contributor')
        
        role = old_contributor.xpath('.//*[local-name() = "ContributorRole"]/text()')
        if role:
            etree.SubElement(contributor, 'ContributorRole').text = role[0]
        
        name = old_contributor.xpath('.//*[local-name() = "PersonName"]/text()')
        if name:
            etree.SubElement(contributor, 'PersonName').text = name[0]

    # Language
    language = etree.SubElement(descriptive_detail, 'Language')
    etree.SubElement(language, 'LanguageRole').text = '01'
    etree.SubElement(language, 'LanguageCode').text = publisher_data.get('language_code', 'eng')

def process_collateral_detail(old_product, collateral_detail):
    """Process collateral detail section"""
    # Convert OtherText to TextContent
    for old_text in old_product.xpath('.//*[local-name() = "OtherText"]'):
        text_content = etree.SubElement(collateral_detail, 'TextContent')
        
        text_type = old_text.xpath('.//*[local-name() = "TextTypeCode"]/text()')
        etree.SubElement(text_content, 'TextType').text = text_type[0] if text_type else '03'
        
        etree.SubElement(text_content, 'ContentAudience').text = '00'
        
        text = old_text.xpath('.//*[local-name() = "Text"]/text()')
        if text:
            etree.SubElement(text_content, 'Text').text = text[0]

    # Convert MediaFile to SupportingResource
    for old_media in old_product.xpath('.//*[local-name() = "MediaFile"]'):
        resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        media_type = old_media.xpath('.//*[local-name() = "MediaFileTypeCode"]/text()')
        etree.SubElement(resource, 'ResourceContentType').text = media_type[0] if media_type else '01'
        
        etree.SubElement(resource, 'ResourceMode').text = '03'
        
        version = etree.SubElement(resource, 'ResourceVersion')
        etree.SubElement(version, 'ResourceForm').text = '02'
        
        link = old_media.xpath('.//*[local-name() = "MediaFileLink"]/text()')
        if link:
            etree.SubElement(version, 'ResourceLink').text = link[0]

def process_publishing_detail(old_product, publishing_detail):
    """Process publishing detail section"""
    # Imprint
    imprint_name = old_product.xpath('.//*[local-name() = "ImprintName"]/text()')
    if imprint_name:
        imprint = etree.SubElement(publishing_detail, 'Imprint')
        etree.SubElement(imprint, 'ImprintName').text = imprint_name[0]
    
    # Publisher
    publisher_name = old_product.xpath('.//*[local-name() = "PublisherName"]/text()')
    if publisher_name:
        publisher = etree.SubElement(publishing_detail, 'Publisher')
        etree.SubElement(publisher, 'PublisherName').text = publisher_name[0]
    
    # Publishing Status
    status = old_product.xpath('.//*[local-name() = "PublishingStatus"]/text()')
    etree.SubElement(publishing_detail, 'PublishingStatus').text = status[0] if status else '04'
    
    # Publication Date
    pub_date = old_product.xpath('.//*[local-name() = "PublicationDate"]/text()')
    if pub_date:
        pub_date_elem = etree.SubElement(publishing_detail, 'PublishingDate')
        etree.SubElement(pub_date_elem, 'PublishingDateRole').text = '01'
        etree.SubElement(pub_date_elem, 'Date').text = pub_date[0]

def process_product_supply(old_product, product_supply, publisher_data):
    """Process product supply section"""
    supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
    
    # Supplier
    supplier = etree.SubElement(supply_detail, 'Supplier')
    etree.SubElement(supplier, 'SupplierRole').text = '01'
    if publisher_data and publisher_data.get('sender_name'):
        etree.SubElement(supplier, 'SupplierName').text = publisher_data['sender_name']
    
    # Product Availability
    etree.SubElement(supply_detail, 'ProductAvailability').text = '20'
    
    # Process prices
    if publisher_data and 'prices' in publisher_data:
        for currency, amount in publisher_data['prices'].items():
            if amount:
                price = etree.SubElement(supply_detail, 'Price')
                etree.SubElement(price, 'PriceType').text = '02'
                etree.SubElement(price, 'CurrencyCode').text = currency.upper()
                etree.SubElement(price, 'PriceAmount').text = str(Decimal(amount))
                # Media file type mapping
MEDIA_FILE_TYPE_MAPPING = {
    '04': '01',  # Front cover image
    '05': '02',  # Back cover image
    '01': '03',  # Product image
    '02': '04',  # Author photo
    '03': '05',  # Logo
}

# Media file format mapping
MEDIA_FILE_FORMAT_MAPPING = {
    '02': '03',  # GIF maps to Image
    '03': '03',  # JPEG maps to Image
    '04': '04',  # PDF
    '05': '01',  # XML
}

# ONIX code mappings
PRODUCT_FORM_FEATURE_VALUE_MAPPING = {
    '10': '12',  # Accessible DRM
    '11': '14',  # Table of contents navigation
    '13': '17',  # Single logical reading order
    '19': '07',  # Print-equivalent page numbering
    '22': '20',  # Language tagging
    '24': '22',  # Dyslexia readability
    '26': '24',  # High contrast
    '29': '27',  # Navigation via structure
    '30': '28',  # ARIA roles
    '32': '30',  # Landmarks
    '34': '31',  # Reading without sight
    '36': '34',  # Text reflowable
    '52': '31',  # Reading without sight
}

# Accessibility compliance mappings
ACCESSIBILITY_COMPLIANCE_MAPPING = {
    '2': '94',   # EPUB Accessibility 1.0 A
    '3': '95',   # EPUB Accessibility 1.0 AA
    '4': '96',   # EPUB Accessibility 1.1
    '80': 'A01', # WCAG 2.0
    '81': 'A02', # WCAG 2.1
    '84': 'B201', # WCAG A
    '85': 'B202', # WCAG AA
}

def transform_title(old_title):
    """Transform Title element to TitleDetail structure"""
    title_detail = etree.Element('TitleDetail')
    title_type = old_title.find('TitleType')
    
    if title_type is not None:
        type_elem = etree.SubElement(title_detail, 'TitleType')
        type_elem.text = title_type.text
    else:
        type_elem = etree.SubElement(title_detail, 'TitleType')
        type_elem.text = '01'

    title_element = etree.SubElement(title_detail, 'TitleElement')
    level = etree.SubElement(title_element, 'TitleElementLevel')
    level.text = '01'

    title_text = old_title.find('TitleText')
    if title_text is not None:
        text_elem = etree.SubElement(title_element, 'TitleText')
        text_elem.text = title_text.text

    subtitle = old_title.find('Subtitle')
    if subtitle is not None:
        subtitle_elem = etree.SubElement(title_element, 'Subtitle')
        subtitle_elem.text = subtitle.text

    return title_detail

def transform_contributor(old_contributor):
    """Transform Contributor element"""
    new_contributor = etree.Element('Contributor')
    
    role = old_contributor.find('ContributorRole')
    if role is not None:
        role_elem = etree.SubElement(new_contributor, 'ContributorRole')
        role_elem.text = role.text

    for name_type in ['PersonName', 'PersonNameInverted', 'CorporateName']:
        name = old_contributor.find(name_type)
        if name is not None:
            name_elem = etree.SubElement(new_contributor, name_type)
            name_elem.text = name.text

    # Add biographical note if present
    bio = old_contributor.find('BiographicalNote')
    if bio is not None:
        bio_elem = etree.SubElement(new_contributor, 'BiographicalNote')
        bio_elem.text = bio.text

    return new_contributor

def transform_subject(old_subject):
    """Transform Subject element"""
    new_subject = etree.Element('Subject')
    
    scheme = old_subject.find('SubjectSchemeIdentifier')
    if scheme is not None:
        scheme_elem = etree.SubElement(new_subject, 'SubjectSchemeIdentifier')
        scheme_elem.text = scheme.text

    code = old_subject.find('SubjectCode')
    if code is not None:
        code_elem = etree.SubElement(new_subject, 'SubjectCode')
        code_elem.text = code.text

    heading = old_subject.find('SubjectHeadingText')
    if heading is not None:
        heading_elem = etree.SubElement(new_subject, 'SubjectHeadingText')
        heading_elem.text = heading.text

    return new_subject

def transform_text_content(old_text):
    """Transform OtherText to TextContent"""
    text_content = etree.Element('TextContent')
    
    type_code = old_text.find('TextTypeCode')
    text_type = etree.SubElement(text_content, 'TextType')
    text_type.text = type_code.text if type_code is not None else '03'
    
    audience = etree.SubElement(text_content, 'ContentAudience')
    audience.text = '00'
    
    text = old_text.find('Text')
    if text is not None:
        text_elem = etree.SubElement(text_content, 'Text')
        text_elem.text = text.text
        
        format_code = old_text.find('TextFormat')
        if format_code is not None:
            text_elem.set('textformat', format_code.text.lower())

    return text_content

def transform_supporting_resource(old_media):
    """Transform MediaFile to SupportingResource"""
    resource = etree.Element('SupportingResource')
    
    # Content type
    type_code = old_media.find('MediaFileTypeCode')
    content_type = etree.SubElement(resource, 'ResourceContentType')
    content_type.text = MEDIA_FILE_TYPE_MAPPING.get(
        type_code.text if type_code is not None else '01', 
        '01'
    )
    
    # Resource mode
    format_code = old_media.find('MediaFileFormatCode')
    mode = etree.SubElement(resource, 'ResourceMode')
    mode.text = MEDIA_FILE_FORMAT_MAPPING.get(
        format_code.text if format_code is not None else '03',
        '03'
    )
    
    # Version information
    version = etree.SubElement(resource, 'ResourceVersion')
    form = etree.SubElement(version, 'ResourceForm')
    form.text = '02'
    
    link = old_media.find('MediaFileLink')
    if link is not None:
        resource_link = etree.SubElement(version, 'ResourceLink')
        resource_link.text = link.text

    return resource

def transform_price(old_price):
    """Transform Price element"""
    new_price = etree.Element('Price')
    
    type_code = old_price.find('PriceTypeCode')
    if type_code is not None:
        type_elem = etree.SubElement(new_price, 'PriceType')
        type_elem.text = type_code.text
    
    amount = old_price.find('PriceAmount')
    if amount is not None:
        amount_elem = etree.SubElement(new_price, 'PriceAmount')
        amount_elem.text = amount.text
    
    currency = old_price.find('CurrencyCode')
    if currency is not None:
        currency_elem = etree.SubElement(new_price, 'CurrencyCode')
        currency_elem.text = currency.text

    return new_price

def format_date(date_string):
    """Format date to ONIX 3.0 format"""
    try:
        formats = [
            "%Y%m%d",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%m-%d-%Y"
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime("%Y%m%d")
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse date: {date_string}")
    
    except Exception as e:
        logger.error(f"Error formatting date {date_string}: {str(e)}")
        return date_string

def clean_text(text):
    """Clean and normalize text content"""
    if text is None:
        return None
    return ' '.join(text.split())

def validate_currency_code(code):
    """Validate currency code"""
    valid_codes = {'USD', 'CAD', 'GBP', 'EUR', 'AUD', 'NZD'}
    return code.upper() if code.upper() in valid_codes else None

def validate_language_code(code):
    """Validate language code"""
    if code and len(code) == 3 and code.isalpha():
        return code.lower()
    return None

def get_element_text(element, xpath, default=None):
    """Safely get element text using xpath"""
    result = element.xpath(xpath)
    return result[0] if result else default

# End of file