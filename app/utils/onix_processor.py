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
        process_header(tree, new_root, original_version, publisher_data)

        # Process products
        if tree.tag.endswith('Product') or tree.tag == 'Product':
            process_product(tree, new_root, epub_features, epub_isbn, publisher_data)
        else:
            products = tree.xpath('.//*[local-name() = "Product"]')
            if products:
                for old_product in products:
                    process_product(old_product, new_root, epub_features, epub_isbn, publisher_data)

        return etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8')

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def process_header(root, new_root, original_version, publisher_data=None):
    """Process header elements"""
    header = etree.SubElement(new_root, 'Header')
    
    # Sender info
    sender = etree.SubElement(header, 'Sender')
    
    if publisher_data and publisher_data.get('sender_name'):
        name_elem = etree.SubElement(sender, 'SenderName')
        name_elem.text = publisher_data['sender_name']
    else:
        from_company = root.xpath('.//*[local-name() = "FromCompany"]/text()')
        if from_company:
            name_elem = etree.SubElement(sender, 'SenderName')
            name_elem.text = from_company[0]
        else:
            from_company = root.xpath('.//*[local-name() = "RecordSourceName"]/text()')
            name_elem = etree.SubElement(sender, 'SenderName')
            name_elem.text = from_company[0] if from_company else "Default Company Name"

    if publisher_data and publisher_data.get('contact_name'):
        contact_elem = etree.SubElement(sender, 'ContactName')
        contact_elem.text = publisher_data['contact_name']
    else:
        contact_name = root.xpath('.//*[local-name() = "ContactName"]/text()')
        if contact_name:
            contact_elem = etree.SubElement(sender, 'ContactName')
            contact_elem.text = contact_name[0]

    if publisher_data and publisher_data.get('email'):
        email_elem = etree.SubElement(sender, 'EmailAddress')
        email_elem.text = publisher_data['email']
    else:
        email = root.xpath('.//*[local-name() = "EmailAddress"]/text()')
        if email:
            email_elem = etree.SubElement(sender, 'EmailAddress')
            email_elem.text = email[0]

    sent_date_time = etree.SubElement(header, 'SentDateTime')
    sent_date_time.text = datetime.now().strftime("%Y%m%dT%H%M%S")

    message_note = root.xpath('.//*[local-name() = "MessageNote"]/text()')
    note_elem = etree.SubElement(header, 'MessageNote')
    note_elem.text = message_note[0] if message_note else f"This file was remediated to include accessibility information. Original ONIX version: {original_version}"

def process_product(old_product, new_root, epub_features, epub_isbn, publisher_data=None):
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

    # Process identifiers without duplicates
    process_identifiers(new_product, old_product, epub_isbn)

    # Process main sections
    descriptive_detail = process_descriptive_detail(new_product, old_product, epub_features, publisher_data)
    collateral_detail = process_collateral_detail(new_product, old_product)
    publishing_detail = process_publishing_detail(new_product, old_product)
    process_product_supply(new_product, old_product, publisher_data)

def process_identifiers(new_product, old_product, epub_isbn):
    """Process product identifiers without duplicates"""
    processed_types = set()
    
    for old_identifier in old_product.xpath('.//*[local-name() = "ProductIdentifier"]'):
        id_type = old_identifier.xpath('.//*[local-name() = "ProductIDType"]/text()')
        if id_type and id_type[0] not in processed_types:
            new_identifier = etree.SubElement(new_product, 'ProductIdentifier')
            type_elem = etree.SubElement(new_identifier, 'ProductIDType')
            type_elem.text = id_type[0]
            
            value_elem = etree.SubElement(new_identifier, 'IDValue')
            if id_type[0] in ["03", "15"]:  # ISBN-13
                value_elem.text = epub_isbn
            else:
                old_value = old_identifier.xpath('.//*[local-name() = "IDValue"]/text()')
                value_elem.text = old_value[0] if old_value else ''
            
            processed_types.add(id_type[0])

def process_descriptive_detail(new_product, old_product, epub_features, publisher_data=None):
    """Process descriptive detail section"""
    descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')

    # Product Composition
    product_comp = etree.SubElement(descriptive_detail, 'ProductComposition')
    if publisher_data and publisher_data.get('product_composition'):
        product_comp.text = publisher_data['product_composition']
    else:
        product_comp.text = '00'
    
    # Product Form
    product_form = etree.SubElement(descriptive_detail, 'ProductForm')
    if publisher_data and publisher_data.get('product_form'):
        product_form.text = publisher_data['product_form']
    else:
        old_form = old_product.xpath('.//*[local-name() = "ProductForm"]/text()')
        product_form.text = old_form[0] if old_form else 'EB'
    
    # Product Form Detail
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

    # Process other elements
    process_titles(descriptive_detail, old_product)
    process_contributors(descriptive_detail, old_product)
    process_language(descriptive_detail, old_product, publisher_data)
    process_subjects(descriptive_detail, old_product)
    process_audience(descriptive_detail, old_product)
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
    """Process contributor information"""
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

        bio = old_contributor.xpath('.//*[local-name() = "BiographicalNote"]/text()')
        if bio:
            etree.SubElement(new_contributor, 'BiographicalNote').text = bio[0]

        country = old_contributor.xpath('.//*[local-name() = "CountryCode"]/text()')
        if country:
            place = etree.SubElement(new_contributor, 'ContributorPlace')
            etree.SubElement(place, 'ContributorPlaceRelator').text = '00'
            etree.SubElement(place, 'CountryCode').text = country[0]

def process_language(descriptive_detail, old_product, publisher_data=None):
    """Process language information"""
    language = etree.SubElement(descriptive_detail, 'Language')
    
    # Language role
    etree.SubElement(language, 'LanguageRole').text = '01'
    
    # Language code
    if publisher_data and publisher_data.get('language_code'):
        etree.SubElement(language, 'LanguageCode').text = publisher_data['language_code']
    else:
        lang_code = old_product.xpath('.//*[local-name() = "LanguageCode"]/text()')
        etree.SubElement(language, 'LanguageCode').text = lang_code[0] if lang_code else 'eng'

def process_subjects(descriptive_detail, old_product):
    """Process subject information"""
    for old_subject in old_product.xpath('.//*[local-name() = "Subject"]'):
        scheme = old_subject.xpath('.//*[local-name() = "SubjectSchemeIdentifier"]/text()')
        code = old_subject.xpath('.//*[local-name() = "SubjectCode"]/text()')
        heading = old_subject.xpath('.//*[local-name() = "SubjectHeadingText"]/text()')
        
        if scheme and (code or heading):
            new_subject = etree.SubElement(descriptive_detail, 'Subject')
            etree.SubElement(new_subject, 'SubjectSchemeIdentifier').text = scheme[0]
            
            scheme_name = old_subject.xpath('.//*[local-name() = "SubjectSchemeName"]/text()')
            if scheme_name:
                etree.SubElement(new_subject, 'SubjectSchemeName').text = scheme_name[0]
            
            if code:
                etree.SubElement(new_subject, 'SubjectCode').text = code[0]
            
            if heading:
                etree.SubElement(new_subject, 'SubjectHeadingText').text = heading[0]

def process_audience(descriptive_detail, old_product):
    """Process audience information"""
    audience_code = old_product.xpath('.//*[local-name() = "AudienceCode"]/text()')
    if audience_code:
        audience = etree.SubElement(descriptive_detail, 'Audience')
        etree.SubElement(audience, 'AudienceCodeType').text = '01'
        etree.SubElement(audience, 'AudienceCodeValue').text = audience_code[0]

def process_extent(descriptive_detail, old_product):
    """Process extent information"""
    for old_extent in old_product.xpath('.//*[local-name() = "Extent"]'):
        extent_type = old_extent.xpath('.//*[local-name() = "ExtentType"]/text()')
        extent_value = old_extent.xpath('.//*[local-name() = "ExtentValue"]/text()')
        extent_unit = old_extent.xpath('.//*[local-name() = "ExtentUnit"]/text()')
        
        if extent_type and extent_value and extent_unit:
            try:
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
    process_text_content(collateral_detail, old_product)
    process_supporting_resources(collateral_detail, old_product)
    return collateral_detail

def process_text_content(collateral_detail, old_product):
    """Process text content"""
    for old_text in old_product.xpath('.//*[local-name() = "OtherText"]'):
        text_content = etree.SubElement(collateral_detail, 'TextContent')
        
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

def process_supporting_resources(collateral_detail, old_product):
    """Process supporting resources"""
    for old_resource in old_product.xpath('.//*[local-name() = "SupportingResource"]'):
        new_resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        content_type = old_resource.xpath('.//*[local-name() = "ResourceContentType"]/text()')
        if content_type:
            etree.SubElement(new_resource, 'ResourceContentType').text = content_type[0]
        
        mode = old_resource.xpath('.//*[local-name() = "ResourceMode"]/text()')
        if mode:
            etree.SubElement(new_resource, 'ResourceMode').text = mode[0]
        
        version = etree.SubElement(new_resource, 'ResourceVersion')
        
        form = old_resource.xpath('.//*[local-name() = "ResourceForm"]/text()')
        if form:
            etree.SubElement(version, 'ResourceForm').text = form[0]
        
        link = old_resource.xpath('.//*[local-name() = "ResourceLink"]/text()')
        if link:
            etree.SubElement(version, 'ResourceLink').text = link[0]

def process_publishing_detail(new_product, old_product):
    """Process publishing detail section"""
    publishing_detail = etree.SubElement(new_product, 'PublishingDetail')

    # Publisher
    publisher = etree.SubElement(publishing_detail, 'Publisher')
    pub_role = etree.SubElement(publisher, 'PublishingRole')
    pub_role.text = '01'

    pub_name = old_product.xpath('.//*[local-name() = "PublisherName"]/text()')
    if pub_name:
        pub_name_elem = etree.SubElement(publisher, 'PublisherName')
        pub_name_elem.text = pub_name[0]

    # Publishing Status
    status = old_product.xpath('.//*[local-name() = "PublishingStatus"]/text()')
    if status:
        status_elem = etree.SubElement(publishing_detail, 'PublishingStatus')
        status_elem.text = status[0]

    # Publication Date
    pub_date = old_product.xpath('.//*[local-name() = "PublicationDate"]/text()')
    if pub_date:
        publishing_date = etree.SubElement(publishing_detail, 'PublishingDate')
        etree.SubElement(publishing_date, 'PublishingDateRole').text = '01'
        etree.SubElement(publishing_date, 'Date').text = format_date(pub_date[0])

    return publishing_detail

def process_product_supply(new_product, old_product, publisher_data=None):
    """Process product supply section"""
    product_supply = etree.SubElement(new_product, 'ProductSupply')
    
    # Market
    market = etree.SubElement(product_supply, 'Market')
    territory = etree.SubElement(market, 'Territory')
    
    countries = old_product.xpath('.//*[local-name() = "CountriesIncluded"]/text()')
    regions = old_product.xpath('.//*[local-name() = "RegionsIncluded"]/text()')
    
    if countries:
        countries_elem = etree.SubElement(territory, 'CountriesIncluded')
        countries_elem.text = countries[0]
    elif regions:
        regions_elem = etree.SubElement(territory, 'RegionsIncluded')
        regions_elem.text = regions[0]
    else:
        regions_elem = etree.SubElement(territory, 'RegionsIncluded')
        regions_elem.text = 'WORLD'
    
    # Supply Detail
    supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
    
    supplier = etree.SubElement(supply_detail, 'Supplier')
    etree.SubElement(supplier, 'SupplierRole').text = '01'
    
    supplier_name = old_product.xpath('.//*[local-name() = "SupplierName"]/text()')
    if supplier_name:
        name_elem = etree.SubElement(supplier, 'SupplierName')
        name_elem.text = supplier_name[0]
    
    # Product Availability
    availability = old_product.xpath('.//*[local-name() = "ProductAvailability"]/text()')
    if availability:
        avail_elem = etree.SubElement(supply_detail, 'ProductAvailability')
        avail_elem.text = availability[0]
    
    # Process prices
    if publisher_data and any(publisher_data.get(f'price_{curr.lower()}') for curr in ['CAD', 'GBP', 'USD']):
        for currency in ['CAD', 'GBP', 'USD']:
            price_value = publisher_data.get(f'price_{currency.lower()}')
            if price_value:
                price = etree.SubElement(supply_detail, 'Price')
                price_amount = etree.SubElement(price, 'PriceAmount')
                price_amount.text = validate_price(price_value)
                currency_elem = etree.SubElement(price, 'CurrencyCode')
                currency_elem.text = currency
    else:
        # Process existing prices
        for old_price in old_product.xpath('.//*[local-name() = "Price"]'):
            price_amount = old_price.xpath('.//*[local-name() = "PriceAmount"]/text()')
            if price_amount:
                price = etree.SubElement(supply_detail, 'Price')
                amount_elem = etree.SubElement(price, 'PriceAmount')
                amount_elem.text = validate_price(price_amount[0])
                
                currency = old_price.xpath('.//*[local-name() = "CurrencyCode"]/text()')
                if currency:
                    currency_elem = etree.SubElement(price, 'CurrencyCode')
                    currency_elem.text = currency[0]
    
    return product_supply