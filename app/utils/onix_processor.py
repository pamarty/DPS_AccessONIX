import xml.etree.ElementTree as ET
from lxml import etree
import logging
from datetime import datetime
import traceback
from decimal import Decimal
from .epub_analyzer import CODELIST_196

logger = logging.getLogger(__name__)

def get_original_version(root):
    """Determine ONIX version and format"""
    xmlns = root.get('xmlns')
    if xmlns:
        if 'onix/3.0' in xmlns:
            return '3.0', True
        elif 'onix/2.1' in xmlns:
            return '2.1', True
    
    header = root.find('Header') or root.find('header')
    if header is not None:
        release = header.find('Release') or header.find('release')
        if release is not None:
            return release.text, True
    
    if root.find('.//ProductComposition') is not None:
        return '3.0', True
    
    if root.find('.//a001') is not None:
        return '2.1', False
    
    return '2.1', True

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
    """Process ONIX XML with accessibility features and publisher data"""
    try:
        # Parse XML
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        tree = etree.fromstring(xml_content, parser=parser)
        logger.info(f"XML parsed successfully. Root tag: {tree.tag}")
        
        # Determine version and format
        original_version, is_reference = get_original_version(tree)
        logger.info(f"Original ONIX version: {original_version}, Reference format: {is_reference}")

        # Create new root
        new_root = etree.Element('ONIXMessage')
        if is_reference:
            if original_version.startswith('3'):
                new_root.set('xmlns', 'http://ns.editeur.org/onix/3.0/reference')
            else:
                new_root.set('xmlns', 'http://www.editeur.org/onix/2.1/reference')
        
        new_root.set('release', '3.0')

        # Process header first
        process_header(new_root, original_version, publisher_data)
        logger.info("Header processed")

        # Process products
        for product in tree.findall('.//Product'):
            new_product = process_product(
                product, 
                epub_features, 
                epub_isbn, 
                original_version.startswith('3'),
                publisher_data
            )
            new_root.append(new_product)
            logger.info("Product processed successfully")

        # Register namespace if using reference format
        if is_reference:
            etree.register_namespace('', new_root.get('xmlns'))

        # Return processed XML
        return etree.tostring(
            new_root,
            pretty_print=True,
            xml_declaration=True,
            encoding='utf-8'
        )

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def process_header(root, original_version, publisher_data=None):
    """Process ONIX header"""
    header = etree.SubElement(root, 'Header')
    
    # Sender information
    sender = etree.SubElement(header, 'Sender')
    
    if publisher_data:
        sender_name = etree.SubElement(sender, 'SenderName')
        sender_name.text = publisher_data.get('sender_name', 'Default Company Name')
        
        if publisher_data.get('contact_name'):
            contact_name = etree.SubElement(sender, 'ContactName')
            contact_name.text = publisher_data['contact_name']
        
        if publisher_data.get('email'):
            email = etree.SubElement(sender, 'EmailAddress')
            email.text = publisher_data['email']
    else:
        sender_name = etree.SubElement(sender, 'SenderName')
        sender_name.text = "Default Company Name"

    # Always create SentDateTime for ONIX 3.0
    sent_date_time = etree.SubElement(header, 'SentDateTime')
    sent_date_time.text = datetime.now().strftime("%Y%m%dT%H%M%S")

    # Add MessageNote
    note_elem = etree.SubElement(header, 'MessageNote')
    note_elem.text = f"This file was remediated to include accessibility information. Original ONIX version: {original_version}"
def process_product(product, accessibility_features, epub_isbn, is_onix3, publisher_data=None):
    """Process ONIX product"""
    new_product = etree.Element('Product')

    # Process record reference
    record_ref = product.find('.//RecordReference')
    if record_ref is not None:
        new_ref = etree.SubElement(new_product, 'RecordReference')
        new_ref.text = record_ref.text
    else:
        new_ref = etree.SubElement(new_product, 'RecordReference')
        new_ref.text = f"EPUB_{epub_isbn}"

    # Process identifiers
    process_identifiers(product, new_product, epub_isbn)

    # Process descriptive detail section
    descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')
    process_descriptive_detail(product, descriptive_detail, accessibility_features, is_onix3, publisher_data)

    # Process collateral detail
    collateral_detail = etree.SubElement(new_product, 'CollateralDetail')
    process_collateral_detail(product, collateral_detail)

    # Process publishing detail
    publishing_detail = etree.SubElement(new_product, 'PublishingDetail')
    process_publishing_detail(product, publishing_detail)

    # Process product supply
    process_product_supply(product, new_product, publisher_data)

    return new_product

def process_identifiers(product, new_product, epub_isbn):
    """Process product identifiers"""
    # Handle default identifier
    if not product.findall('.//ProductIdentifier'):
        identifier = etree.SubElement(new_product, 'ProductIdentifier')
        id_type = etree.SubElement(identifier, 'ProductIDType')
        id_type.text = '15'  # ISBN-13
        id_value = etree.SubElement(identifier, 'IDValue')
        id_value.text = epub_isbn
        return

    # Process existing identifiers
    for identifier in product.findall('.//ProductIdentifier'):
        new_identifier = etree.SubElement(new_product, 'ProductIdentifier')
        id_type = identifier.find('ProductIDType')
        if id_type is not None:
            new_type = etree.SubElement(new_identifier, 'ProductIDType')
            new_type.text = id_type.text
            id_value = etree.SubElement(new_identifier, 'IDValue')
            
            # Update ISBN if appropriate
            if id_type.text in ['03', '15']:  # ISBN-13
                id_value.text = epub_isbn
            else:
                old_value = identifier.find('IDValue')
                id_value.text = old_value.text if old_value is not None else ''

def process_descriptive_detail(product, descriptive_detail, accessibility_features, is_onix3, publisher_data):
    """Process descriptive detail section"""
    # Product composition
    comp = etree.SubElement(descriptive_detail, 'ProductComposition')
    comp.text = publisher_data.get('product_composition', '00')  # Single-item retail product

    # Product form
    form = etree.SubElement(descriptive_detail, 'ProductForm')
    form.text = publisher_data.get('product_form', 'EB')  # Digital download

    # Product form detail
    form_detail = etree.SubElement(descriptive_detail, 'ProductFormDetail')
    form_detail.text = 'E101'  # EPUB

    # Process accessibility features
    process_accessibility_features(descriptive_detail, accessibility_features)

    # Process title details
    if is_onix3:
        process_title_details_onix3(product, descriptive_detail)
    else:
        process_title_details_onix2(product, descriptive_detail)

    # Process contributors
    process_contributors(product, descriptive_detail)

    # Process language
    process_language(product, descriptive_detail, publisher_data)

def process_accessibility_features(descriptive_detail, accessibility_features):
    """Process accessibility features"""
    # Remove any existing accessibility features
    for feature in descriptive_detail.findall('ProductFormFeature'):
        if feature.find('ProductFormFeatureType') is not None and feature.find('ProductFormFeatureType').text == "09":
            descriptive_detail.remove(feature)

    insert_after = [
        'ProductForm', 'ProductFormDetail', 'ProductFormDescription',
        'ProductFormFeature', 'ProductPackaging', 'ProductFormDescription',
        'NumberOfPieces', 'TradeCategory', 'ProductContentType', 'EpubType',
        'EpubTypeVersion', 'EpubTypeDescription', 'EpubFormat', 'EpubFormatVersion',
        'EpubFormatDescription', 'EpubSource', 'EpubSourceVersion',
        'EpubSourceDescription', 'EpubTypeNote'
    ]

    # Find insert position
    insert_position = 0
    for tag in insert_after:
        elements = descriptive_detail.findall(tag)
        if elements:
            insert_position = list(descriptive_detail).index(elements[-1]) + 1

    # Add new accessibility features
    for code, is_present in accessibility_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.Element('ProductFormFeature')
            feature_type = etree.SubElement(feature, 'ProductFormFeatureType')
            feature_type.text = "09"
            
            feature_value = etree.SubElement(feature, 'ProductFormFeatureValue')
            feature_value.text = code
            
            feature_desc = etree.SubElement(feature, 'ProductFormFeatureDescription')
            feature_desc.text = CODELIST_196[code]
            
            descriptive_detail.insert(insert_position, feature)
            insert_position += 1

def process_title_details_onix3(product, descriptive_detail):
    """Process title details for ONIX 3.0"""
    title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
    title_type = etree.SubElement(title_detail, 'TitleType')
    title_type.text = '01'  # Distinctive title

    title_element = etree.SubElement(title_detail, 'TitleElement')
    level = etree.SubElement(title_element, 'TitleElementLevel')
    level.text = '01'

    # Get title text from TitleText or TitleStatement
    title_text = product.find('.//TitleText')
    if title_text is not None:
        text_elem = etree.SubElement(title_element, 'TitleText')
        text_elem.text = title_text.text

    # Handle subtitle if present
    subtitle = product.find('.//Subtitle')
    if subtitle is not None:
        subtitle_elem = etree.SubElement(title_element, 'Subtitle')
        subtitle_elem.text = subtitle.text

def process_title_details_onix2(product, descriptive_detail):
    """Process title details from ONIX 2.1"""
    for title in product.findall('.//Title'):
        title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
        title_type = etree.SubElement(title_detail, 'TitleType')
        title_type.text = '01'  # Distinctive title

        title_element = etree.SubElement(title_detail, 'TitleElement')
        level = etree.SubElement(title_element, 'TitleElementLevel')
        level.text = '01'

        title_text = title.find('TitleText')
        if title_text is not None:
            text_elem = etree.SubElement(title_element, 'TitleText')
            text_elem.text = title_text.text

        subtitle = title.find('Subtitle')
        if subtitle is not None:
            subtitle_elem = etree.SubElement(title_element, 'Subtitle')
            subtitle_elem.text = subtitle.text

def process_contributors(product, descriptive_detail):
    """Process contributor information"""
    for contributor in product.findall('.//Contributor'):
        new_contributor = etree.SubElement(descriptive_detail, 'Contributor')
        
        role = contributor.find('ContributorRole')
        if role is not None:
            role_elem = etree.SubElement(new_contributor, 'ContributorRole')
            role_elem.text = role.text

        name = contributor.find('PersonName')
        if name is not None:
            name_elem = etree.SubElement(new_contributor, 'PersonName')
            name_elem.text = name.text

def process_language(product, descriptive_detail, publisher_data):
    """Process language information"""
    language = etree.SubElement(descriptive_detail, 'Language')
    role = etree.SubElement(language, 'LanguageRole')
    role.text = '01'  # Language of text
    
    code = etree.SubElement(language, 'LanguageCode')
    if publisher_data and publisher_data.get('language_code'):
        code.text = publisher_data['language_code']
    else:
        old_code = product.find('.//LanguageCode')
        code.text = old_code.text if old_code is not None else 'eng'

def process_collateral_detail(product, new_product):
    """Process collateral detail section"""
    collateral_detail = etree.SubElement(new_product, 'CollateralDetail')
    
    # Convert OtherText to TextContent
    for other_text in product.findall('.//OtherText'):
        text_content = etree.SubElement(collateral_detail, 'TextContent')
        
        # Convert TextTypeCode to TextType
        type_code = other_text.find('TextTypeCode')
        if type_code is not None:
            text_type = etree.SubElement(text_content, 'TextType')
            text_type.text = type_code.text
        
        # Add mandatory ContentAudience
        audience = etree.SubElement(text_content, 'ContentAudience')
        audience.text = '00'
        
        # Convert Text content
        text = other_text.find('Text')
        if text is not None:
            text_elem = etree.SubElement(text_content, 'Text')
            text_elem.text = text.text

def process_publishing_detail(product, new_product):
    """Process publishing detail section"""
    publishing_detail = etree.SubElement(new_product, 'PublishingDetail')
    
    # Publishing status
    status = product.find('.//PublishingStatus')
    status_elem = etree.SubElement(publishing_detail, 'PublishingStatus')
    status_elem.text = status.text if status is not None else '04'
    
    # Publication date
    pub_date = product.find('.//PublicationDate')
    if pub_date is not None:
        date_elem = etree.SubElement(publishing_detail, 'PublishingDate')
        role = etree.SubElement(date_elem, 'PublishingDateRole')
        role.text = '01'
        date = etree.SubElement(date_elem, 'Date')
        date.text = pub_date.text

def process_product_supply(product, new_product, publisher_data):
    """Process product supply section"""
    product_supply = etree.SubElement(new_product, 'ProductSupply')
    supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
    
    # Supplier information
    supplier = etree.SubElement(supply_detail, 'Supplier')
    role = etree.SubElement(supplier, 'SupplierRole')
    role.text = '01'  # Publisher
    
    if publisher_data and publisher_data.get('sender_name'):
        name = etree.SubElement(supplier, 'SupplierName')
        name.text = publisher_data['sender_name']
    
    # Product availability
    availability = etree.SubElement(supply_detail, 'ProductAvailability')
    availability.text = '20'  # Available
    
    # Process prices
    if publisher_data and 'prices' in publisher_data:
        for currency, amount in publisher_data['prices'].items():
            if amount:
                price = etree.SubElement(supply_detail, 'Price')
                
                # Price type
                price_type = etree.SubElement(price, 'PriceType')
                price_type.text = '02'  # RRP including tax
                
                # Currency
                currency_elem = etree.SubElement(price, 'CurrencyCode')
                currency_elem.text = currency.upper()
                
                # Amount
                amount_elem = etree.SubElement(price, 'PriceAmount')
                amount_elem.text = str(Decimal(amount))