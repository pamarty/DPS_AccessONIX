import xml.etree.ElementTree as ET
from lxml import etree
import logging
from datetime import datetime
import traceback
from decimal import Decimal
from .epub_analyzer import CODELIST_196

logger = logging.getLogger(__name__)

ONIX_30_NS = "http://ns.editeur.org/onix/3.0/reference"
NSMAP = {None: ONIX_30_NS}

def get_publisher_value(publisher_data, key, default_value):
    """Safely get publisher data value with fallback"""
    if publisher_data is None:
        return default_value
    return publisher_data.get(key, default_value)

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
    """Main function to process ONIX content"""
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(xml_content, parser)
        logger.info(f"XML parsed successfully. Root tag: {tree.tag}")

        original_version, is_reference = get_original_version(tree)

        # Create new ONIX 3.0 document
        new_root = etree.Element('ONIXMessage', nsmap=NSMAP)
        new_root.set("release", "3.0")

        # Process header while preserving original information
        process_header(tree, new_root, original_version, publisher_data)

        # Process products based on input type
        if tree.tag.endswith('Product') or tree.tag == 'Product':
            process_single_product(tree, new_root, epub_features, epub_isbn, publisher_data)
        else:
            products = tree.xpath('.//*[local-name() = "Product"]')
            if products:
                for old_product in products:
                    process_single_product(old_product, new_root, epub_features, epub_isbn, publisher_data)
            else:
                create_new_product(new_root, epub_features, epub_isbn, publisher_data)

        return etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8')

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def process_header(root, new_root, original_version, publisher_data):
    """Process header elements in correct order with fallback values"""
    header = etree.SubElement(new_root, 'Header')
    
    # Sender information (required first)
    sender = etree.SubElement(header, 'Sender')
    
    # Get original sender info or use publisher data with proper fallbacks
    from_company = root.xpath('.//*[local-name() = "FromCompany"]/text()')
    sender_name = None
    if publisher_data:
        sender_name = publisher_data.get('sender_name')
    if not sender_name and from_company:
        sender_name = from_company[0]
    if not sender_name:
        sender_name = "Default Company Name"
    etree.SubElement(sender, 'SenderName').text = sender_name

    # Handle contact name with fallback
    contact_name = None
    if publisher_data:
        contact_name = publisher_data.get('contact_name')
    if contact_name:
        etree.SubElement(sender, 'ContactName').text = contact_name
    
    # Handle email with fallback
    email = None
    if publisher_data:
        email = publisher_data.get('email')
    if email:
        etree.SubElement(sender, 'EmailAddress').text = email

    # SentDateTime (required)
    etree.SubElement(header, 'SentDateTime').text = datetime.now().strftime("%Y%m%dT%H%M%S")

    # Optional header elements
    message_note = root.xpath('.//*[local-name() = "MessageNote"]/text()')
    note_text = f"This file was remediated to include accessibility information. Original ONIX version: {original_version}"
    etree.SubElement(header, 'MessageNote').text = message_note[0] if message_note else note_text

def process_single_product(old_product, new_root, epub_features, epub_isbn, publisher_data):
    """Process a single product with correct element ordering"""
    new_product = etree.SubElement(new_root, "Product")
    
    # Required first elements
    record_ref = old_product.xpath('.//*[local-name() = "RecordReference"]/text()')
    etree.SubElement(new_product, 'RecordReference').text = record_ref[0] if record_ref else f"EPUB_{epub_isbn}"
    etree.SubElement(new_product, 'NotificationType').text = '03'
    
    # Process identifiers
    process_identifiers(new_product, old_product, epub_isbn)
    
    # Process main sections in correct order
    descriptive_detail = process_descriptive_detail(new_product, old_product, epub_features, publisher_data)
    collateral_detail = process_collateral_detail(new_product, old_product)
    publishing_detail = process_publishing_detail(new_product, old_product, publisher_data)
    process_product_supply(new_product, old_product, publisher_data)

def process_identifiers(new_product, old_product, epub_isbn):
    """Process product identifiers"""
    for old_identifier in old_product.xpath('.//*[local-name() = "ProductIdentifier"]'):
        new_identifier = etree.SubElement(new_product, 'ProductIdentifier')
        id_type = old_identifier.xpath('.//*[local-name() = "ProductIDType"]/text()')
        if id_type:
            etree.SubElement(new_identifier, 'ProductIDType').text = id_type[0]
            id_value = etree.SubElement(new_identifier, 'IDValue')
            if id_type[0] in ["03", "15"]:  # ISBN-13
                id_value.text = epub_isbn
            else:
                old_value = old_identifier.xpath('.//*[local-name() = "IDValue"]/text()')
                id_value.text = old_value[0] if old_value else ''

def process_descriptive_detail(new_product, old_product, epub_features, publisher_data):
    """Process DescriptiveDetail section with correct element ordering"""
    descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')
    
    # Required elements in strict order
    etree.SubElement(descriptive_detail, 'ProductComposition').text = get_publisher_value(
        publisher_data, 'product_composition', '00')
    etree.SubElement(descriptive_detail, 'ProductForm').text = get_publisher_value(
        publisher_data, 'product_form', 'EB')
    etree.SubElement(descriptive_detail, 'ProductFormDetail').text = 'E101'
    
    # Process accessibility features
    for code, is_present in epub_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
            etree.SubElement(feature, 'ProductFormFeatureValue').text = code
            etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]
    
    # Process other elements in correct order
    process_titles(descriptive_detail, old_product)
    process_contributors(descriptive_detail, old_product)
    process_language(descriptive_detail, old_product, publisher_data)
    process_extent(descriptive_detail, old_product)
    
    return descriptive_detail

def process_titles(descriptive_detail, old_product):
    """Process title information"""
    title_found = False
    for old_title in old_product.xpath('.//*[local-name() = "Title"]'):
        title_found = True
        title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
        title_type = old_title.xpath('.//*[local-name() = "TitleType"]/text()')
        etree.SubElement(title_detail, 'TitleType').text = title_type[0] if title_type else "01"
        
        title_element = etree.SubElement(title_detail, 'TitleElement')
        etree.SubElement(title_element, 'TitleElementLevel').text = "01"
        
        title_text = old_title.xpath('.//*[local-name() = "TitleText"]/text()')
        etree.SubElement(title_element, 'TitleText').text = title_text[0] if title_text else "Unknown Title"
        
        subtitle = old_title.xpath('.//*[local-name() = "Subtitle"]/text()')
        if subtitle:
            etree.SubElement(title_element, 'Subtitle').text = subtitle[0]
    
    # Ensure at least one title exists
    if not title_found:
        title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
        etree.SubElement(title_detail, 'TitleType').text = "01"
        title_element = etree.SubElement(title_detail, 'TitleElement')
        etree.SubElement(title_element, 'TitleElementLevel').text = "01"
        etree.SubElement(title_element, 'TitleText').text = "Unknown Title"

def process_contributors(descriptive_detail, old_product):
    """Process contributor information"""
    excluded_tags = ["NameCodeType", "NameCodeTypeName", "NameCodeValue", "PersonNameIdentifier", "Website"]
    
    for old_contributor in old_product.xpath('.//*[local-name() = "Contributor"]'):
        new_contributor = etree.SubElement(descriptive_detail, 'Contributor')
        for child in old_contributor:
            child_tag = etree.QName(child).localname
            if child_tag not in excluded_tags:
                etree.SubElement(new_contributor, child_tag).text = child.text

def process_language(descriptive_detail, old_product, publisher_data):
    """Process language information"""
    languages = old_product.xpath('.//*[local-name() = "Language"]')
    if languages:
        for old_lang in languages:
            new_lang = etree.SubElement(descriptive_detail, 'Language')
            role = old_lang.xpath('.//*[local-name() = "LanguageRole"]/text()')
            etree.SubElement(new_lang, 'LanguageRole').text = role[0] if role else '01'
            code = old_lang.xpath('.//*[local-name() = "LanguageCode"]/text()')
            etree.SubElement(new_lang, 'LanguageCode').text = code[0] if code else get_publisher_value(
                publisher_data, 'language_code', 'eng')
    else:
        new_lang = etree.SubElement(descriptive_detail, 'Language')
        etree.SubElement(new_lang, 'LanguageRole').text = '01'
        etree.SubElement(new_lang, 'LanguageCode').text = get_publisher_value(
            publisher_data, 'language_code', 'eng')

def process_extent(descriptive_detail, old_product):
    """Process extent information"""
    for extent in old_product.findall('.//Extent'):
        new_extent = etree.SubElement(descriptive_detail, 'Extent')
        extent_type = extent.find('ExtentType')
        etree.SubElement(new_extent, 'ExtentType').text = extent_type.text if extent_type is not None else '00'
        extent_value = extent.find('ExtentValue')
        etree.SubElement(new_extent, 'ExtentValue').text = extent_value.text if extent_value is not None else '0'
        extent_unit = extent.find('ExtentUnit')
        etree.SubElement(new_extent, 'ExtentUnit').text = extent_unit.text if extent_unit is not None else '03'

def process_collateral_detail(new_product, old_product):
    """Process CollateralDetail section"""
    collateral_detail = etree.SubElement(new_product, 'CollateralDetail')
    
    # Process TextContent
    for old_text in old_product.xpath('.//*[local-name() = "OtherText"]'):
        text_content = etree.SubElement(collateral_detail, 'TextContent')
        # ResourceContentType must come first
        text_type = old_text.xpath('.//*[local-name() = "TextTypeCode"]/text()')
        etree.SubElement(text_content, 'TextType').text = text_type[0] if text_type else "03"
        etree.SubElement(text_content, 'ContentAudience').text = '00'
        
        text = old_text.xpath('.//*[local-name() = "Text"]/text()')
        if text:
            text_elem = etree.SubElement(text_content, 'Text')
            text_elem.text = text[0]

    # Process SupportingResource
    for old_media in old_product.xpath('.//*[local-name() = "MediaFile"]'):
        supporting_resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        # ResourceContentType must come first
        media_type = old_media.xpath('.//*[local-name() = "MediaFileTypeCode"]/text()')
        etree.SubElement(supporting_resource, 'ResourceContentType').text = media_type[0] if media_type else '01'
        
        # Then ContentAudience
        etree.SubElement(supporting_resource, 'ContentAudience').text = '00'
        
        # Then ResourceMode
        etree.SubElement(supporting_resource, 'ResourceMode').text = '03'
        
        # ResourceVersion must be last
        resource_version = etree.SubElement(supporting_resource, 'ResourceVersion')
        etree.SubElement(resource_version, 'ResourceForm').text = '02'
        
        link = old_media.xpath('.//*[local-name() = "MediaFileLink"]/text()')
        if link:
            etree.SubElement(resource_version, 'ResourceLink').text = link[0]
    
    return collateral_detail

def process_publishing_detail(new_product, old_product, publisher_data):
    """Process PublishingDetail section"""
    publishing_detail = etree.SubElement(new_product, 'PublishingDetail')
    
    # Process Imprint
    imprints = old_product.xpath('.//*[local-name() = "Imprint"]')
    if imprints:
        imprint = etree.SubElement(publishing_detail, 'Imprint')
        imprint_name = imprints[0].xpath('.//*[local-name() = "ImprintName"]/text()')
        if imprint_name:
            etree.SubElement(imprint, 'ImprintName').text = imprint_name[0]
    
    # Process Publisher
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
    
    # Publishing Date
    pub_date = old_product.xpath('.//*[local-name() = "PublicationDate"]/text()')
    if pub_date:
        publishing_date = etree.SubElement(publishing_detail, 'PublishingDate')
        etree.SubElement(publishing_date, 'PublishingDateRole').text = '01'
        etree.SubElement(publishing_date, 'Date').text = format_date(pub_date[0])
    
    # Process Sales Rights
    process_sales_rights(publishing_detail, old_product)
    
    return publishing_detail

def process_sales_rights(publishing_detail, old_product):
    """Process sales rights information"""
    for old_rights in old_product.xpath('.//*[local-name() = "SalesRights"]'):
        new_rights = etree.SubElement(publishing_detail, 'SalesRights')
        rights_type = old_rights.xpath('.//*[local-name() = "SalesRightsType"]/text()')
        etree.SubElement(new_rights, 'SalesRightsType').text = rights_type[0] if rights_type else '01'
        
        territory = etree.SubElement(new_rights, 'Territory')
        countries = old_rights.xpath('.//*[local-name() = "RightsCountry"]/text()')
        regions = old_rights.xpath('.//*[local-name() = "RightsTerritory"]/text()')
        
        if countries:
            etree.SubElement(territory, 'CountriesIncluded').text = countries[0]
        elif regions:
            etree.SubElement(territory, 'RegionsIncluded').text = regions[0]

def process_product_supply(new_product, old_product, publisher_data):
    """Process ProductSupply section with fallbacks"""
    product_supply = etree.SubElement(new_product, 'ProductSupply')
    
    # Process each SupplyDetail
    supply_details = old_product.xpath('.//*[local-name() = "SupplyDetail"]')
    if supply_details:
        for old_supply in supply_details:
            process_supply_detail(product_supply, old_supply, publisher_data)
    else:
        # Create default supply detail if none exists
        create_default_supply_detail(product_supply, publisher_data)

def process_supply_detail(product_supply, old_supply, publisher_data):
    """Process individual SupplyDetail section"""
    supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
    
    # Supplier information (must come first)
    supplier = etree.SubElement(supply_detail, 'Supplier')
    supplier_role = old_supply.xpath('.//*[local-name() = "SupplierRole"]/text()')
    etree.SubElement(supplier, 'SupplierRole').text = supplier_role[0] if supplier_role else '01'
    
    supplier_name = old_supply.xpath('.//*[local-name() = "SupplierName"]/text()')
    etree.SubElement(supplier, 'SupplierName').text = supplier_name[0] if supplier_name else get_publisher_value(
        publisher_data, 'sender_name', 'Default Supplier')
    
    # ProductAvailability (must come before SupplyDate)
    availability = old_supply.xpath('.//*[local-name() = "ProductAvailability"]/text()')
    etree.SubElement(supply_detail, 'ProductAvailability').text = availability[0] if availability else '20'
    
    # Process supply dates
    process_supply_dates(supply_detail, old_supply)
    
    # Process prices
    process_prices(supply_detail, old_supply, publisher_data)

def process_supply_dates(supply_detail, old_supply):
    """Process supply dates"""
    date_mapping = {
        'ExpectedShipDate': '08',  # Expected availability date
        'OnSaleDate': '01'         # Publication date
    }
    
    date_found = False
    for date_type, role in date_mapping.items():
        date_value = old_supply.xpath(f'.//*[local-name() = "{date_type}"]/text()')
        if date_value:
            date_found = True
            supply_date = etree.SubElement(supply_detail, 'SupplyDate')
            etree.SubElement(supply_date, 'SupplyDateRole').text = role
            etree.SubElement(supply_date, 'Date').text = format_date(date_value[0])
    
    # Add default date if none found
    if not date_found:
        supply_date = etree.SubElement(supply_detail, 'SupplyDate')
        etree.SubElement(supply_date, 'SupplyDateRole').text = '08'
        etree.SubElement(supply_date, 'Date').text = datetime.now().strftime("%Y%m%d")

def process_prices(supply_detail, old_supply, publisher_data):
    """Process pricing information"""
    # Process existing prices
    prices_found = False
    for old_price in old_supply.xpath('.//*[local-name() = "Price"]'):
        prices_found = True
        price = etree.SubElement(supply_detail, 'Price')
        
        # PriceType (required first)
        price_type = old_price.xpath('.//*[local-name() = "PriceTypeCode"]/text()')
        etree.SubElement(price, 'PriceType').text = price_type[0] if price_type else '02'
        
        # Process currency and amount
        currency = old_price.xpath('.//*[local-name() = "CurrencyCode"]/text()')
        if currency:
            etree.SubElement(price, 'CurrencyCode').text = currency[0]
        
        amount = old_price.xpath('.//*[local-name() = "PriceAmount"]/text()')
        if amount:
            etree.SubElement(price, 'PriceAmount').text = amount[0]
    
    # Add new prices from publisher data
    if publisher_data and publisher_data.get('prices'):
        for currency, amount in publisher_data['prices'].items():
            if amount:
                price = etree.SubElement(supply_detail, 'Price')
                etree.SubElement(price, 'PriceType').text = '02'
                etree.SubElement(price, 'CurrencyCode').text = currency.upper()
                etree.SubElement(price, 'PriceAmount').text = str(Decimal(amount))
                prices_found = True
    
    # Add default price if no prices found
    if not prices_found:
        price = etree.SubElement(supply_detail, 'Price')
        etree.SubElement(price, 'PriceType').text = '02'
        etree.SubElement(price, 'CurrencyCode').text = 'USD'
        etree.SubElement(price, 'PriceAmount').text = '0.00'

def create_default_supply_detail(product_supply, publisher_data):
    """Create default supply detail section"""
    supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
    
    # Add required supplier info
    supplier = etree.SubElement(supply_detail, 'Supplier')
    etree.SubElement(supplier, 'SupplierRole').text = '01'
    etree.SubElement(supplier, 'SupplierName').text = get_publisher_value(
        publisher_data, 'sender_name', 'Default Supplier')
    
    # Add required availability
    etree.SubElement(supply_detail, 'ProductAvailability').text = '20'
    
    # Add default supply date
    supply_date = etree.SubElement(supply_detail, 'SupplyDate')
    etree.SubElement(supply_date, 'SupplyDateRole').text = '08'
    etree.SubElement(supply_date, 'Date').text = datetime.now().strftime("%Y%m%d")
    
    # Add default price
    price = etree.SubElement(supply_detail, 'Price')
    etree.SubElement(price, 'PriceType').text = '02'
    etree.SubElement(price, 'CurrencyCode').text = 'USD'
    etree.SubElement(price, 'PriceAmount').text = '0.00'

def create_new_product(new_root, epub_features, epub_isbn, publisher_data):
    """Create a new product when none exists"""
    new_product = etree.SubElement(new_root, "Product")
    
    # Basic product information
    etree.SubElement(new_product, 'RecordReference').text = f"EPUB_{epub_isbn}"
    etree.SubElement(new_product, 'NotificationType').text = '03'
    
    # Product Identifier
    identifier = etree.SubElement(new_product, 'ProductIdentifier')
    etree.SubElement(identifier, 'ProductIDType').text = '15'  # ISBN-13
    etree.SubElement(identifier, 'IDValue').text = epub_isbn
    
    # DescriptiveDetail
    descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')
    etree.SubElement(descriptive_detail, 'ProductComposition').text = get_publisher_value(
        publisher_data, 'product_composition', '00')
    etree.SubElement(descriptive_detail, 'ProductForm').text = get_publisher_value(
        publisher_data, 'product_form', 'EB')
    etree.SubElement(descriptive_detail, 'ProductFormDetail').text = 'E101'
    
    # Add accessibility features
    for code, is_present in epub_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
            etree.SubElement(feature, 'ProductFormFeatureValue').text = code
            etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]
    
    # Add minimum required elements
    add_minimum_elements(new_product, publisher_data)