import xml.etree.ElementTree as ET
from lxml import etree
import logging
from datetime import datetime
import traceback
from decimal import Decimal
import re
from .epub_analyzer import CODELIST_196

logger = logging.getLogger(__name__)

# ONIX namespaces
ONIX_30_NS = "http://ns.editeur.org/onix/3.0/reference"
NSMAP = {None: ONIX_30_NS}

# Utility Functions
def format_date(date_string):
    """Format date string to YYYYMMDD"""
    try:
        if not date_string:
            return datetime.now().strftime("%Y%m%d")
        
        date_string = str(date_string).strip()
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime("%Y%m%d")
            except ValueError:
                continue
        return datetime.now().strftime("%Y%m%d")
    except Exception as e:
        logger.warning(f"Error formatting date {date_string}: {str(e)}")
        return datetime.now().strftime("%Y%m%d")

def clean_text(text):
    """Clean and format text content"""
    if not text:
        return ""
    # Remove any invalid XML characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', str(text))
    return text.strip()

def validate_price(price_str):
    """Validate and format price value"""
    try:
        if not price_str:
            return "0.00"
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

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
    """Process ONIX content"""
    try:
        parser = etree.XMLParser(remove_blank_text=True)
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
    notify_type = old_product.xpath('.//*[local-name() = "NotificationType"]/text()')
    notify_element.text = notify_type[0] if notify_type else '03'

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
    process_titles(descriptive_detail, old_product)

    # Process contributors
    process_contributors(descriptive_detail, old_product)

    # Process language
    process_language(descriptive_detail, old_product)

    # Process subjects
    process_subjects(descriptive_detail, old_product)

    # Process audience
    process_audience(descriptive_detail, old_product)

    # Process extent if present
    process_extent(descriptive_detail, old_product)

    return descriptive_detail

def process_titles(descriptive_detail, old_product):
    """Process title information"""
    for old_title in old_product.xpath('.//*[local-name() = "Title"]'):
        title_type = old_title.xpath('.//*[local-name() = "TitleType"]/text()')
        if not title_type or title_type[0] == "01":  # Main title
            title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
            etree.SubElement(title_detail, 'TitleType').text = '01'
            
            title_element = etree.SubElement(title_detail, 'TitleElement')
            etree.SubElement(title_element, 'TitleElementLevel').text = '01'
            
            title_text = old_title.xpath('.//*[local-name() = "TitleText"]/text()')
            etree.SubElement(title_element, 'TitleText').text = title_text[0] if title_text else 'Unknown Title'

            subtitle = old_title.xpath('.//*[local-name() = "Subtitle"]/text()')
            if subtitle:
                etree.SubElement(title_element, 'Subtitle').text = subtitle[0]
def process_contributors(descriptive_detail, old_product):
    """Process contributor information with correct element ordering"""
    for old_contributor in old_product.xpath('.//*[local-name() = "Contributor"]'):
        new_contributor = etree.SubElement(descriptive_detail, 'Contributor')
        
        # ContributorRole must come first
        role = old_contributor.xpath('.//*[local-name() = "ContributorRole"]/text()')
        if role:
            etree.SubElement(new_contributor, 'ContributorRole').text = role[0]

        # Personal name elements in correct order
        person_name = old_contributor.xpath('.//*[local-name() = "PersonName"]/text()')
        if person_name:
            etree.SubElement(new_contributor, 'PersonName').text = person_name[0]

        inverted_name = old_contributor.xpath('.//*[local-name() = "PersonNameInverted"]/text()')
        if inverted_name:
            etree.SubElement(new_contributor, 'PersonNameInverted').text = inverted_name[0]

        names_before = old_contributor.xpath('.//*[local-name() = "NamesBeforeKey"]/text()')
        if names_before:
            etree.SubElement(new_contributor, 'NamesBeforeKey').text = names_before[0]

        key_names = old_contributor.xpath('.//*[local-name() = "KeyNames"]/text()')
        if key_names:
            etree.SubElement(new_contributor, 'KeyNames').text = key_names[0]

        # Biographical note comes after name components
        bio = old_contributor.xpath('.//*[local-name() = "BiographicalNote"]/text()')
        if bio:
            etree.SubElement(new_contributor, 'BiographicalNote').text = bio[0]

        # ContributorPlace with proper structure
        country = old_contributor.xpath('.//*[local-name() = "CountryCode"]/text()')
        if country:
            place = etree.SubElement(new_contributor, 'ContributorPlace')
            etree.SubElement(place, 'ContributorPlaceRelator').text = '00'
            etree.SubElement(place, 'CountryCode').text = country[0]

def process_language(descriptive_detail, old_product):
    """Process language information"""
    for old_lang in old_product.xpath('.//*[local-name() = "Language"]'):
        language = etree.SubElement(descriptive_detail, 'Language')
        
        # LanguageRole must come first
        lang_role = old_lang.xpath('.//*[local-name() = "LanguageRole"]/text()')
        etree.SubElement(language, 'LanguageRole').text = lang_role[0] if lang_role else '01'
        
        # Then LanguageCode
        lang_code = old_lang.xpath('.//*[local-name() = "LanguageCode"]/text()')
        etree.SubElement(language, 'LanguageCode').text = lang_code[0] if lang_code else 'eng'

def process_subjects(descriptive_detail, old_product):
    """Process subject information with required elements"""
    for old_subject in old_product.xpath('.//*[local-name() = "Subject"]'):
        scheme = old_subject.xpath('.//*[local-name() = "SubjectSchemeIdentifier"]/text()')
        code = old_subject.xpath('.//*[local-name() = "SubjectCode"]/text()')
        heading = old_subject.xpath('.//*[local-name() = "SubjectHeadingText"]/text()')
        
        # Only create Subject if we have required elements
        if scheme and (code or heading):
            new_subject = etree.SubElement(descriptive_detail, 'Subject')
            etree.SubElement(new_subject, 'SubjectSchemeIdentifier').text = scheme[0]
            
            # Add SubjectSchemeName if present
            scheme_name = old_subject.xpath('.//*[local-name() = "SubjectSchemeName"]/text()')
            if scheme_name:
                etree.SubElement(new_subject, 'SubjectSchemeName').text = scheme_name[0]
            
            # Add SubjectCode if present
            if code:
                etree.SubElement(new_subject, 'SubjectCode').text = code[0]
            
            # Add SubjectHeadingText if present
            if heading:
                etree.SubElement(new_subject, 'SubjectHeadingText').text = heading[0]

def process_audience(descriptive_detail, old_product):
    """Process audience information with required elements"""
    audience_code = old_product.xpath('.//*[local-name() = "AudienceCode"]/text()')
    if audience_code:
        audience = etree.SubElement(descriptive_detail, 'Audience')
        etree.SubElement(audience, 'AudienceCodeType').text = '01'
        etree.SubElement(audience, 'AudienceCodeValue').text = audience_code[0]

def process_extent(descriptive_detail, old_product):
    """Process extent information with validation"""
    for old_extent in old_product.xpath('.//*[local-name() = "Extent"]'):
        extent_type = old_extent.xpath('.//*[local-name() = "ExtentType"]/text()')
        extent_value = old_extent.xpath('.//*[local-name() = "ExtentValue"]/text()')
        extent_unit = old_extent.xpath('.//*[local-name() = "ExtentUnit"]/text()')
        
        # Only create Extent if we have valid values
        if extent_type and extent_value and extent_unit:
            try:
                # Validate extent value is greater than 0
                value = int(extent_value[0])
                if value > 0:
                    new_extent = etree.SubElement(descriptive_detail, 'Extent')
                    etree.SubElement(new_extent, 'ExtentType').text = extent_type[0]
                    etree.SubElement(new_extent, 'ExtentValue').text = str(value)
                    etree.SubElement(new_extent, 'ExtentUnit').text = extent_unit[0]
            except (ValueError, TypeError):
                logger.warning(f"Invalid extent value: {extent_value[0]}")
                continue

def process_collateral_detail(new_product, old_product):
    """Process collateral detail section"""
    collateral_detail = etree.SubElement(new_product, 'CollateralDetail')

    # Process text content
    process_text_content(collateral_detail, old_product)

    # Process supporting resources
    process_supporting_resources(collateral_detail, old_product)

    return collateral_detail

def process_text_content(collateral_detail, old_product):
    """Process text content with proper type mapping"""
    for old_text in old_product.xpath('.//*[local-name() = "OtherText"]'):
        text_content = etree.SubElement(collateral_detail, 'TextContent')
        
        # Get and map text type
        text_type = old_text.xpath('.//*[local-name() = "TextTypeCode"]/text()')
        type_value = text_type[0] if text_type else "03"
        if type_value == "99":
            type_value = "03"  # Map unknown to description
        etree.SubElement(text_content, 'TextType').text = type_value
        
        etree.SubElement(text_content, 'ContentAudience').text = '00'
        
        text = old_text.xpath('.//*[local-name() = "Text"]/text()')
        if text:
            text_elem = etree.SubElement(text_content, 'Text')
            text_elem.text = text[0]
            
            text_format = old_text.xpath('.//*[local-name() = "TextFormat"]/text()')
            if text_format:
                text_elem.set('textformat', text_format[0].lower())