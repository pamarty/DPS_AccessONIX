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
        
        # Determine version
        original_version, is_reference = get_original_version(tree)
        logger.info(f"Original ONIX version: {original_version}, Reference format: {is_reference}")

        # Create new root with correct namespace
        xmlns = 'http://ns.editeur.org/onix/3.0/reference' if is_reference else None
        new_root = etree.Element('ONIXMessage', nsmap={None: xmlns} if xmlns else None)
        new_root.set('release', '3.0')

        # Process header first
        process_header(new_root, original_version, publisher_data)
        logger.info("Header processed")

        # Process products
        changes = []
        for product in tree.findall('.//Product'):
            new_product = process_product(
                product, 
                epub_features, 
                epub_isbn, 
                original_version.startswith('3'),
                publisher_data
            )
            new_root.append(new_product)
            changes.append("Product processed successfully")

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

    # Date/time
    if original_version.startswith('3'):
        sent_date_time = etree.SubElement(header, 'SentDateTime')
        sent_date_time.text = datetime.now().strftime("%Y%m%dT%H%M%S")
    else:
        sent_date = etree.SubElement(header, 'SentDate')
        sent_date.text = datetime.now().strftime("%Y%m%d")

def process_product(product, accessibility_features, epub_isbn, is_onix3, publisher_data=None):
    """Process ONIX product"""
    new_product = etree.Element('Product')

    # Record Reference (mandatory)
    record_ref = product.find('RecordReference')
    if record_ref is not None:
        new_ref = etree.SubElement(new_product, 'RecordReference')
        new_ref.text = record_ref.text
    else:
        new_ref = etree.SubElement(new_product, 'RecordReference')
        new_ref.text = f"EPUB_{epub_isbn}"

    # Notification Type (mandatory)
    notif = etree.SubElement(new_product, 'NotificationType')
    notif.text = '03'  # New, confirmed

    # Product Identifiers
    process_identifiers(product, new_product, epub_isbn)

    # Descriptive Detail
    descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')
    process_descriptive_detail(product, descriptive_detail, accessibility_features, publisher_data)

    # Collateral Detail
    process_collateral_detail(product, new_product)

    # Publishing Detail
    process_publishing_detail(product, new_product)

    # Product Supply
    process_product_supply(product, new_product, publisher_data)

    return new_product
def process_identifiers(product, new_product, epub_isbn):
    """Process product identifiers"""
    for identifier in product.findall('.//ProductIdentifier'):
        new_identifier = etree.SubElement(new_product, 'ProductIdentifier')
        id_type = identifier.find('ProductIDType')
        if id_type is not None:
            new_type = etree.SubElement(new_identifier, 'ProductIDType')
            new_type.text = id_type.text
            
            id_value = etree.SubElement(new_identifier, 'IDValue')
            if id_type.text in ['03', '15']:  # ISBN-13
                id_value.text = epub_isbn
            else:
                old_value = identifier.find('IDValue')
                id_value.text = old_value.text if old_value is not None else ''

def process_descriptive_detail(product, descriptive_detail, accessibility_features, publisher_data):
    """Process descriptive detail section"""
    # Product composition
    if publisher_data and publisher_data.get('product_composition'):
        comp = etree.SubElement(descriptive_detail, 'ProductComposition')
        comp.text = publisher_data['product_composition']
    else:
        comp = etree.SubElement(descriptive_detail, 'ProductComposition')
        comp.text = '00'  # Single-item retail product

    # Product form
    if publisher_data and publisher_data.get('product_form'):
        form = etree.SubElement(descriptive_detail, 'ProductForm')
        form.text = publisher_data['product_form']
    else:
        form = etree.SubElement(descriptive_detail, 'ProductForm')
        form.text = 'EB'  # Digital download

    # Product form detail
    form_detail = etree.SubElement(descriptive_detail, 'ProductFormDetail')
    form_detail.text = 'E101'  # EPUB

    # Process accessibility features
    process_accessibility_features(descriptive_detail, accessibility_features)

    # Process title details
    process_title_details(product, descriptive_detail)

    # Process contributors
    process_contributors(product, descriptive_detail)

    # Process language
    process_language(product, descriptive_detail)

    # Process other elements
    process_additional_details(product, descriptive_detail)

def process_title_details(product, descriptive_detail):
    """Process title information"""
    for title in product.findall('.//Title'):
        title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
        title_type = title.find('TitleType')
        
        if title_type is not None:
            new_type = etree.SubElement(title_detail, 'TitleType')
            new_type.text = title_type.text
        else:
            new_type = etree.SubElement(title_detail, 'TitleType')
            new_type.text = '01'  # Distinctive title
        
        title_element = etree.SubElement(title_detail, 'TitleElement')
        level = etree.SubElement(title_element, 'TitleElementLevel')
        level.text = '01'  # Product level
        
        title_text = title.find('TitleText')
        if title_text is not None:
            new_text = etree.SubElement(title_element, 'TitleText')
            new_text.text = title_text.text
        
        subtitle = title.find('Subtitle')
        if subtitle is not None:
            new_subtitle = etree.SubElement(title_element, 'Subtitle')
            new_subtitle.text = subtitle.text

def process_accessibility_features(descriptive_detail, accessibility_features):
    """Process accessibility features"""
    logger.info("Adding accessibility features")
    for code, is_present in accessibility_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            feature_type = etree.SubElement(feature, 'ProductFormFeatureType')
            feature_type.text = '09'  # Accessibility feature
            
            feature_value = etree.SubElement(feature, 'ProductFormFeatureValue')
            feature_value.text = code
            
            feature_desc = etree.SubElement(feature, 'ProductFormFeatureDescription')
            feature_desc.text = CODELIST_196[code]
            
            logger.debug(f"Added accessibility feature: {code} - {CODELIST_196[code]}")

def process_contributors(product, descriptive_detail):
    """Process contributor information"""
    for contributor in product.findall('.//Contributor'):
        new_contributor = etree.SubElement(descriptive_detail, 'Contributor')
        
        # Sequence number if present
        sequence = contributor.find('SequenceNumber')
        if sequence is not None:
            new_seq = etree.SubElement(new_contributor, 'SequenceNumber')
            new_seq.text = sequence.text
        
        # Contributor role
        role = contributor.find('ContributorRole')
        if role is not None:
            new_role = etree.SubElement(new_contributor, 'ContributorRole')
            new_role.text = role.text
        
        # Personal name
        name = contributor.find('PersonName')
        if name is not None:
            new_name = etree.SubElement(new_contributor, 'PersonName')
            new_name.text = name.text

def process_language(product, descriptive_detail):
    """Process language information"""
    for language in product.findall('.//Language'):
        new_language = etree.SubElement(descriptive_detail, 'Language')
        
        role = language.find('LanguageRole')
        if role is not None:
            new_role = etree.SubElement(new_language, 'LanguageRole')
            new_role.text = role.text
        
        code = language.find('LanguageCode')
        if code is not None:
            new_code = etree.SubElement(new_language, 'LanguageCode')
            new_code.text = code.text

def process_additional_details(product, descriptive_detail):
    """Process additional descriptive details"""
    # Audiences
    for audience in product.findall('.//Audience'):
        new_audience = etree.SubElement(descriptive_detail, 'Audience')
        
        type_code = audience.find('AudienceCodeType')
        if type_code is not None:
            new_type = etree.SubElement(new_audience, 'AudienceCodeType')
            new_type.text = type_code.text
        
        code_value = audience.find('AudienceCodeValue')
        if code_value is not None:
            new_value = etree.SubElement(new_audience, 'AudienceCodeValue')
            new_value.text = code_value.text

def process_collateral_detail(product, new_product):
    """Process collateral detail section"""
    collateral_detail = etree.SubElement(new_product, 'CollateralDetail')
    
    # Text content (from OtherText)
    for text in product.findall('.//OtherText'):
        text_content = etree.SubElement(collateral_detail, 'TextContent')
        
        text_type = text.find('TextTypeCode')
        if text_type is not None:
            new_type = etree.SubElement(text_content, 'TextType')
            new_type.text = text_type.text
        
        content_audience = etree.SubElement(text_content, 'ContentAudience')
        content_audience.text = '00'  # Unrestricted
        
        text_value = text.find('Text')
        if text_value is not None:
            new_text = etree.SubElement(text_content, 'Text')
            new_text.text = text_value.text
    
    # Supporting resources (from MediaFile)
    process_supporting_resources(product, collateral_detail)

def process_supporting_resources(product, collateral_detail):
    """Process supporting resources"""
    for media in product.findall('.//MediaFile'):
        resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        # Resource content type
        content_type = etree.SubElement(resource, 'ResourceContentType')
        media_type = media.find('MediaFileTypeCode')
        content_type.text = media_type.text if media_type is not None else '01'
        
        # Resource mode
        mode = etree.SubElement(resource, 'ResourceMode')
        mode.text = '03'  # Image
        
        # Resource version
        version = etree.SubElement(resource, 'ResourceVersion')
        form = etree.SubElement(version, 'ResourceForm')
        form.text = '02'  # Downloadable file
        
        link = media.find('MediaFileLink')
        if link is not None:
            resource_link = etree.SubElement(version, 'ResourceLink')
            resource_link.text = link.text

def process_publishing_detail(product, new_product):
    """Process publishing detail section"""
    publishing_detail = etree.SubElement(new_product, 'PublishingDetail')
    
    # Imprint
    imprint = product.find('.//Imprint/ImprintName')
    if imprint is not None:
        new_imprint = etree.SubElement(publishing_detail, 'Imprint')
        imprint_name = etree.SubElement(new_imprint, 'ImprintName')
        imprint_name.text = imprint.text
    
    # Publisher
    publisher = product.find('.//Publisher/PublisherName')
    if publisher is not None:
        new_publisher = etree.SubElement(publishing_detail, 'Publisher')
        pub_name = etree.SubElement(new_publisher, 'PublisherName')
        pub_name.text = publisher.text
    
    # Publishing status
    status = product.find('.//PublishingStatus')
    new_status = etree.SubElement(publishing_detail, 'PublishingStatus')
    new_status.text = status.text if status is not None else '04'  # Active
    
    # Publication date
    pub_date = product.find('.//PublicationDate')
    if pub_date is not None:
        publishing_date = etree.SubElement(publishing_detail, 'PublishingDate')
        date_role = etree.SubElement(publishing_date, 'PublishingDateRole')
        date_role.text = '01'  # Nominal publication date
        date = etree.SubElement(publishing_date, 'Date')
        date.text = pub_date.text

def process_product_supply(product, new_product, publisher_data):
    """Process product supply section"""
    product_supply = etree.SubElement(new_product, 'ProductSupply')
    supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
    
    # Supplier
    supplier = etree.SubElement(supply_detail, 'Supplier')
    supplier_role = etree.SubElement(supplier, 'SupplierRole')
    supplier_role.text = '01'  # Publisher
    
    if publisher_data and publisher_data.get('sender_name'):
        supplier_name = etree.SubElement(supplier, 'SupplierName')
        supplier_name.text = publisher_data['sender_name']
    
    # Availability
    availability = etree.SubElement(supply_detail, 'ProductAvailability')
    availability.text = '20'  # Available
    
    # Process prices if provided
    if publisher_data and 'prices' in publisher_data:
        process_prices(supply_detail, publisher_data['prices'])

def process_prices(supply_detail, prices):
    """Process price information"""
    for currency, amount in prices.items():
        if amount:
            price = etree.SubElement(supply_detail, 'Price')
            
            price_type = etree.SubElement(price, 'PriceType')
            price_type.text = '02'  # RRP including tax
            
            currency_code = etree.SubElement(price, 'CurrencyCode')
            currency_code.text = currency.upper()
            
            price_amount = etree.SubElement(price, 'PriceAmount')
            price_amount.text = str(Decimal(amount))

            territory = etree.SubElement(price, 'Territory')
            if currency.upper() == 'CAD':
                countries = 'CA'
            elif currency.upper() == 'GBP':
                countries = 'GB'
            elif currency.upper() == 'USD':
                countries = 'US'
            else:
                countries = 'ROW'  # Rest of World
            etree.SubElement(territory, 'CountriesIncluded').text = countries