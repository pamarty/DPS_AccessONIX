import xml.etree.ElementTree as ET
from lxml import etree
import logging
from datetime import datetime
import traceback
from decimal import Decimal
from .epub_analyzer import CODELIST_196

logger = logging.getLogger(__name__)

# ONIX namespaces
ONIX_30_NS = "http://ns.editeur.org/onix/3.0/reference"
NSMAP = {None: ONIX_30_NS}

def get_original_version(root):
    """Detect ONIX version from input file"""
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

def format_date(date_string):
    """Format date string to YYYYMMDD"""
    try:
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime("%Y%m%d")
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {date_string}")
    except Exception as e:
        logger.warning(f"Error formatting date {date_string}: {str(e)}")
        return date_string

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
    """Process ONIX content"""
    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(xml_content, parser)
        logger.info(f"XML parsed successfully. Root tag: {tree.tag}")

        original_version, is_reference = get_original_version(tree)

        # Create new ONIX 3.0 document
        new_root = etree.Element('ONIXMessage', nsmap=NSMAP)
        new_root.set("release", "3.0")

        # Process header
        process_header(tree, new_root, original_version)

        # Process products
        if tree.tag.endswith('Product') or tree.tag == 'Product':
            process_product(tree, new_root, epub_features, epub_isbn)
        else:
            products = tree.xpath('.//*[local-name() = "Product"]')
            if products:
                for old_product in products:
                    process_product(old_product, new_root, epub_features, epub_isbn)

        return etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8')

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def process_header(root, new_root, original_version):
    """Process header elements"""
    header = etree.SubElement(new_root, 'Header')
    
    # Sender info (required first)
    sender = etree.SubElement(header, 'Sender')
    from_company = root.xpath('.//*[local-name() = "FromCompany"]/text()')
    if from_company:
        name_elem = etree.SubElement(sender, 'SenderName')
        name_elem.text = from_company[0]
    else:
        from_company = root.xpath('.//*[local-name() = "RecordSourceName"]/text()')
        name_elem = etree.SubElement(sender, 'SenderName')
        name_elem.text = from_company[0] if from_company else "Default Company Name"

    contact_name = root.xpath('.//*[local-name() = "ContactName"]/text()')
    if contact_name:
        contact_elem = etree.SubElement(sender, 'ContactName')
        contact_elem.text = contact_name[0]

    email = root.xpath('.//*[local-name() = "EmailAddress"]/text()')
    if email:
        email_elem = etree.SubElement(sender, 'EmailAddress')
        email_elem.text = email[0]

    # Always use SentDateTime for ONIX 3.0
    sent_date_time = etree.SubElement(header, 'SentDateTime')
    sent_date_time.text = datetime.now().strftime("%Y%m%dT%H%M%S")

    # MessageNote with original version info
    message_note = root.xpath('.//*[local-name() = "MessageNote"]/text()')
    note_elem = etree.SubElement(header, 'MessageNote')
    note_elem.text = message_note[0] if message_note else f"This file was remediated to include accessibility information. Original ONIX version: {original_version}"

def process_product(old_product, new_root, epub_features, epub_isbn):
    """Process product elements"""
    new_product = etree.SubElement(new_root, "Product")
    
    # Record Reference
    record_ref = old_product.xpath('.//*[local-name() = "RecordReference"]/text()')
    ref_element = etree.SubElement(new_product, 'RecordReference')
    ref_element.text = record_ref[0] if record_ref else f"EPUB_{epub_isbn}"

    # Notification Type
    notify_element = etree.SubElement(new_product, 'NotificationType')
    notify_element.text = '03'

    # Product Identifiers
    process_identifiers(new_product, old_product, epub_isbn)

    # Process main sections in correct order
    descriptive_detail = process_descriptive_detail(new_product, old_product, epub_features)
    collateral_detail = process_collateral_detail(new_product, old_product)
    publishing_detail = process_publishing_detail(new_product, old_product)
    product_supply = process_product_supply(new_product, old_product)

def process_identifiers(new_product, old_product, epub_isbn):
    """Process product identifiers"""
    for old_identifier in old_product.xpath('.//*[local-name() = "ProductIdentifier"]'):
        new_identifier = etree.SubElement(new_product, 'ProductIdentifier')
        
        id_type = old_identifier.xpath('.//*[local-name() = "ProductIDType"]/text()')
        if id_type:
            type_elem = etree.SubElement(new_identifier, 'ProductIDType')
            type_elem.text = id_type[0]
            
            value_elem = etree.SubElement(new_identifier, 'IDValue')
            if id_type[0] in ["03", "15"]:  # ISBN-13
                value_elem.text = epub_isbn
            else:
                old_value = old_identifier.xpath('.//*[local-name() = "IDValue"]/text()')
                value_elem.text = old_value[0] if old_value else ''
def process_descriptive_detail(new_product, old_product, epub_features):
    """Process descriptive detail section"""
    descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')

    # Required elements in correct order
    product_comp = etree.SubElement(descriptive_detail, 'ProductComposition')
    product_comp.text = '00'
    
    product_form = etree.SubElement(descriptive_detail, 'ProductForm')
    old_form = old_product.xpath('.//*[local-name() = "ProductForm"]/text()')
    product_form.text = old_form[0] if old_form else 'EB'
    
    product_form_detail = etree.SubElement(descriptive_detail, 'ProductFormDetail')
    old_detail = old_product.xpath('.//*[local-name() = "ProductFormDetail"]/text()')
    product_form_detail.text = old_detail[0] if old_detail else 'E101'

    # Process existing product form features
    old_features = old_product.xpath('.//*[local-name() = "ProductFormFeature"]')
    for old_feature in old_features:
        feature_type = old_feature.xpath('.//*[local-name() = "ProductFormFeatureType"]/text()')
        if feature_type and feature_type[0] != "09":  # Skip accessibility features
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = feature_type[0]
            
            feature_value = old_feature.xpath('.//*[local-name() = "ProductFormFeatureValue"]/text()')
            if feature_value:
                etree.SubElement(feature, 'ProductFormFeatureValue').text = feature_value[0]

    # Add accessibility features
    for code, is_present in epub_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
            etree.SubElement(feature, 'ProductFormFeatureValue').text = code
            etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]

    # Process titles
    for old_title in old_product.xpath('.//*[local-name() = "Title"]'):
        title_type = old_title.xpath('.//*[local-name() = "TitleType"]/text()')
        if not title_type or title_type[0] == "01":  # Main title
            title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
            etree.SubElement(title_detail, 'TitleType').text = '01'
            
            title_element = etree.SubElement(title_detail, 'TitleElement')
            etree.SubElement(title_element, 'TitleElementLevel').text = '01'
            
            title_text = old_title.xpath('.//*[local-name() = "TitleText"]/text()')
            etree.SubElement(title_element, 'TitleText').text = title_text[0] if title_text else 'Unknown Title'

    # Process contributors
    for old_contributor in old_product.xpath('.//*[local-name() = "Contributor"]'):
        new_contributor = etree.SubElement(descriptive_detail, 'Contributor')
        
        role = old_contributor.xpath('.//*[local-name() = "ContributorRole"]/text()')
        if role:
            etree.SubElement(new_contributor, 'ContributorRole').text = role[0]

        sequence = old_contributor.xpath('.//*[local-name() = "SequenceNumber"]/text()')
        if sequence:
            etree.SubElement(new_contributor, 'SequenceNumber').text = sequence[0]

        person_name = old_contributor.xpath('.//*[local-name() = "PersonName"]/text()')
        if person_name:
            etree.SubElement(new_contributor, 'PersonName').text = person_name[0]

        inverted_name = old_contributor.xpath('.//*[local-name() = "PersonNameInverted"]/text()')
        if inverted_name:
            etree.SubElement(new_contributor, 'PersonNameInverted').text = inverted_name[0]

        country = old_contributor.xpath('.//*[local-name() = "CountryCode"]/text()')
        if country:
            place = etree.SubElement(new_contributor, 'ContributorPlace')
            etree.SubElement(place, 'ContributorPlaceRelator').text = '00'
            etree.SubElement(place, 'CountryCode').text = country[0]

        bio = old_contributor.xpath('.//*[local-name() = "BiographicalNote"]/text()')
        if bio:
            etree.SubElement(new_contributor, 'BiographicalNote').text = bio[0]

    # Process language
    language = etree.SubElement(descriptive_detail, 'Language')
    lang_role = old_product.xpath('.//*[local-name() = "LanguageRole"]/text()')
    etree.SubElement(language, 'LanguageRole').text = lang_role[0] if lang_role else '01'
    
    lang_code = old_product.xpath('.//*[local-name() = "LanguageCode"]/text()')
    etree.SubElement(language, 'LanguageCode').text = lang_code[0] if lang_code else 'eng'

    # Process subjects
    for old_subject in old_product.xpath('.//*[local-name() = "Subject"]'):
        new_subject = etree.SubElement(descriptive_detail, 'Subject')
        
        scheme = old_subject.xpath('.//*[local-name() = "SubjectSchemeIdentifier"]/text()')
        if scheme:
            etree.SubElement(new_subject, 'SubjectSchemeIdentifier').text = scheme[0]
        
        code = old_subject.xpath('.//*[local-name() = "SubjectCode"]/text()')
        if code:
            etree.SubElement(new_subject, 'SubjectCode').text = code[0]

    # Process audience if present
    audience = old_product.xpath('.//*[local-name() = "AudienceCode"]/text()')
    if audience:
        etree.SubElement(descriptive_detail, 'Audience').text = audience[0]

    return descriptive_detail

def process_collateral_detail(new_product, old_product):
    """Process collateral detail section"""
    collateral_detail = etree.SubElement(new_product, 'CollateralDetail')

    # Process text content
    for old_text in old_product.xpath('.//*[local-name() = "OtherText"]'):
        text_content = etree.SubElement(collateral_detail, 'TextContent')
        
        text_type = old_text.xpath('.//*[local-name() = "TextTypeCode"]/text()')
        # Map text type 99 to 03 (description)
        type_value = text_type[0] if text_type else "03"
        if type_value == "99":
            type_value = "03"
        etree.SubElement(text_content, 'TextType').text = type_value
        
        etree.SubElement(text_content, 'ContentAudience').text = '00'
        
        text = old_text.xpath('.//*[local-name() = "Text"]/text()')
        if text:
            formatted_text = etree.SubElement(text_content, 'Text')
            formatted_text.text = text[0]
            
            text_format = old_text.xpath('.//*[local-name() = "TextFormat"]/text()')
            if text_format:
                formatted_text.set('textformat', text_format[0].lower())

    # Process supporting resources
    for old_media in old_product.xpath('.//*[local-name() = "MediaFile"]'):
        resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        # Required order: ResourceContentType, ContentAudience, ResourceMode
        media_type = old_media.xpath('.//*[local-name() = "MediaFileTypeCode"]/text()')
        etree.SubElement(resource, 'ResourceContentType').text = media_type[0] if media_type else '01'
        
        etree.SubElement(resource, 'ContentAudience').text = '00'
        
        # Default to Image mode for most resources
        etree.SubElement(resource, 'ResourceMode').text = '03'
        
        # ResourceVersion must contain at least ResourceForm and optionally ResourceLink
        version = etree.SubElement(resource, 'ResourceVersion')
        etree.SubElement(version, 'ResourceForm').text = '02'
        
        link = old_media.xpath('.//*[local-name() = "MediaFileLink"]/text()')
        if link:
            etree.SubElement(version, 'ResourceLink').text = link[0]

    return collateral_detail

def process_publishing_detail(new_product, old_product):
    """Process publishing detail section"""
    publishing_detail = etree.SubElement(new_product, 'PublishingDetail')

    # Imprint
    imprints = old_product.xpath('.//*[local-name() = "Imprint"]')
    if imprints:
        imprint = etree.SubElement(publishing_detail, 'Imprint')
        imprint_name = imprints[0].xpath('.//*[local-name() = "ImprintName"]/text()')
        if imprint_name:
            etree.SubElement(imprint, 'ImprintName').text = imprint_name[0]

    # Publisher
    publishers = old_product.xpath('.//*[local-name() = "Publisher"]')
    if publishers:
        publisher = etree.SubElement(publishing_detail, 'Publisher')
        etree.SubElement(publisher, 'PublishingRole').text = '01'
        publisher_name = publishers[0].xpath('.//*[local-name() = "PublisherName"]/text()')
        if publisher_name:
            etree.SubElement(publisher, 'PublisherName').text = publisher_name[0]

    # Publishing Status
    status = old_product.xpath('.//*[local-name() = "PublishingStatus"]/text()')
    etree.SubElement(publishing_detail, 'PublishingStatus').text = status[0] if status else '04'

    # Publication Date
    pub_date = old_product.xpath('.//*[local-name() = "PublicationDate"]/text()')
    if pub_date:
        publishing_date = etree.SubElement(publishing_detail, 'PublishingDate')
        etree.SubElement(publishing_date, 'PublishingDateRole').text = '01'
        etree.SubElement(publishing_date, 'Date').text = format_date(pub_date[0])

    # Sales Rights
    for old_rights in old_product.xpath('.//*[local-name() = "SalesRights"]'):
        new_rights = etree.SubElement(publishing_detail, 'SalesRights')
        rights_type = old_rights.xpath('.//*[local-name() = "SalesRightsType"]/text()')
        etree.SubElement(new_rights, 'SalesRightsType').text = rights_type[0] if rights_type else '01'
        
        territory = etree.SubElement(new_rights, 'Territory')
        
        countries = old_rights.xpath('.//*[local-name() = "RightsCountry"]/text()')
        if countries:
            etree.SubElement(territory, 'CountriesIncluded').text = countries[0]
        
        regions = old_rights.xpath('.//*[local-name() = "RightsTerritory"]/text()')
        if regions:
            etree.SubElement(territory, 'RegionsIncluded').text = regions[0]

    return publishing_detail

def process_product_supply(new_product, old_product):
    """Process product supply section"""
    product_supply = etree.SubElement(new_product, 'ProductSupply')
    
    supply_details = old_product.xpath('.//*[local-name() = "SupplyDetail"]')
    if supply_details:
        for old_supply in supply_details:
            supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
            
            # Supplier (required first)
            supplier = etree.SubElement(supply_detail, 'Supplier')
            supplier_role = old_supply.xpath('.//*[local-name() = "SupplierRole"]/text()')
            etree.SubElement(supplier, 'SupplierRole').text = supplier_role[0] if supplier_role else '01'
            
            supplier_name = old_supply.xpath('.//*[local-name() = "SupplierName"]/text()')
            etree.SubElement(supplier, 'SupplierName').text = supplier_name[0] if supplier_name else "Default Supplier"
            
            # Product Availability (required before Price)
            availability = old_supply.xpath('.//*[local-name() = "ProductAvailability"]/text()')
            etree.SubElement(supply_detail, 'ProductAvailability').text = availability[0] if availability else '20'
            
            # Supply dates
            process_supply_dates(supply_detail, old_supply)
            
            # Prices
            process_prices(supply_detail, old_supply)
    else:
        # Create default supply detail if none exists
        create_default_supply_detail(product_supply)

    return product_supply

def process_supply_dates(supply_detail, old_supply):
    """Process supply dates"""
    date_mapping = {
        'ExpectedShipDate': '08',
        'OnSaleDate': '01'
    }
    
    for date_type, role in date_mapping.items():
        date_value = old_supply.xpath(f'.//*[local-name() = "{date_type}"]/text()')
        if date_value:
            supply_date = etree.SubElement(supply_detail, 'SupplyDate')
            etree.SubElement(supply_date, 'SupplyDateRole').text = role
            etree.SubElement(supply_date, 'Date').text = format_date(date_value[0])

def process_prices(supply_detail, old_supply):
    """Process price information"""
    for old_price in old_supply.xpath('.//*[local-name() = "Price"]'):
        price = etree.SubElement(supply_detail, 'Price')
        
        # PriceType required first
        price_type = old_price.xpath('.//*[local-name() = "PriceTypeCode"]/text()')
        etree.SubElement(price, 'PriceType').text = price_type[0] if price_type else '02'
        
        # Price Amount
        amount = old_price.xpath('.//*[local-name() = "PriceAmount"]/text()')
        if amount:
            etree.SubElement(price, 'PriceAmount').text = amount[0]
        
        # Territory handling
        territory = etree.SubElement(price, 'Territory')
        countries = old_price.xpath('.//*[local-name() = "CountryCode"]/text()')
        if countries:
            etree.SubElement(territory, 'CountriesIncluded').text = countries[0]

def create_default_supply_detail(product_supply):
    """Create default supply detail section"""
    supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
    
    # Required supplier info
    supplier = etree.SubElement(supply_detail, 'Supplier')
    etree.SubElement(supplier, 'SupplierRole').text = '01'
    etree.SubElement(supplier, 'SupplierName').text = 'Default Supplier'
    
    # Required availability
    etree.SubElement(supply_detail, 'ProductAvailability').text = '20'
    
    # Add default price
    create_default_price(supply_detail)

def create_default_price(supply_detail):
    """Create default price section"""
    price = etree.SubElement(supply_detail, 'Price')
    etree.SubElement(price, 'PriceType').text = '02'
    etree.SubElement(price, 'PriceAmount').text = '0.00'
    territory = etree.SubElement(price, 'Territory')
    etree.SubElement(territory, 'CountriesIncluded').text = 'US'

def map_product_form(old_form):
    """Map product form codes between versions"""
    form_mapping = {
        'BC': 'BB',  # Paperback -> Paperback
        'BB': 'BB',  # Hardback -> Hardback
        'BZ': 'BZ',  # Other book format -> Other book format
        'DG': 'EA',  # Electronic -> Digital download
        'EB': 'EB',  # Digital -> Digital
        'EC': 'EC'   # HTML -> HTML
    }
    return form_mapping.get(old_form, 'EB')  # Default to 'EB' if unknown

def map_text_type(old_type):
    """Map text type codes between versions"""
    if old_type == "99":
        return "03"  # Map unknown to description
    return old_type if old_type in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"] else "03"

def clean_text(text):
    """Clean and format text content"""
    if not text:
        return ""
    # Remove any invalid XML characters
    import re
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return text.strip()

def validate_date(date_str):
    """Validate and format date string"""
    try:
        if not date_str:
            return None
        date_str = str(date_str).strip()
        # Try different date formats
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y%m%d")
            except ValueError:
                continue
        return None
    except Exception as e:
        logger.warning(f"Date validation error for {date_str}: {str(e)}")
        return None

def validate_price(price_str):
    """Validate and format price value"""
    try:
        if not price_str:
            return "0.00"
        # Remove currency symbols and whitespace
        price_str = re.sub(r'[^\d.]', '', str(price_str))
        price = Decimal(price_str)
        return str(price.quantize(Decimal('0.01')))
    except Exception as e:
        logger.warning(f"Price validation error for {price_str}: {str(e)}")
        return "0.00"

def get_element_text(parent, xpath, default=""):
    """Safely get element text using xpath"""
    try:
        elements = parent.xpath(xpath)
        return clean_text(elements[0]) if elements else default
    except Exception as e:
        logger.warning(f"Error getting element text for xpath {xpath}: {str(e)}")
        return default

def create_element_with_text(parent, tag, text=None):
    """Create element with optional text content"""
    element = etree.SubElement(parent, tag)
    if text is not None:
        element.text = clean_text(text)
    return element

def log_missing_required(element_name, parent_name):
    """Log missing required element"""
    logger.warning(f"Missing required element '{element_name}' in {parent_name}")

def handle_processing_error(e, context):
    """Handle processing errors with context"""
    logger.error(f"Error processing {context}: {str(e)}")
    logger.error(traceback.format_exc())
    raise