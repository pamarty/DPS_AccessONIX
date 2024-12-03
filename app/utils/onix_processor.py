```python
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

        # Process the product(s)
        if root.tag.endswith('Product'):
            # If root is a Product element
            process_single_product(root, new_root, epub_features, epub_isbn, publisher_data)
        else:
            # Look for Product elements
            products = root.xpath('.//*[local-name() = "Product"]')
            if products:
                for old_product in products:
                    process_single_product(old_product, new_root, epub_features, epub_isbn, publisher_data)
            else:
                # Create a new product if none found
                create_new_product(new_root, epub_features, epub_isbn, publisher_data)

        # Return processed XML
        return etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8')

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def process_single_product(old_product, new_root, epub_features, epub_isbn, publisher_data):
    """Process a single product element"""
    new_product = etree.SubElement(new_root, "Product")
    
    # Record Reference
    record_ref = old_product.xpath('.//*[local-name() = "RecordReference"]/text()')
    etree.SubElement(new_product, 'RecordReference').text = record_ref[0] if record_ref else f"EPUB_{epub_isbn}"
    
    # Notification Type
    etree.SubElement(new_product, 'NotificationType').text = '03'
    
    # Process identifiers
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
    
    # Descriptive Detail
    descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')
    
    # Product Form
    etree.SubElement(descriptive_detail, 'ProductComposition').text = publisher_data.get('product_composition', '00')
    etree.SubElement(descriptive_detail, 'ProductForm').text = publisher_data.get('product_form', 'EB')
    etree.SubElement(descriptive_detail, 'ProductFormDetail').text = 'E101'
    
    # Process accessibility features
    for code, is_present in epub_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
            etree.SubElement(feature, 'ProductFormFeatureValue').text = code
            etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]
    
    # Add minimum required elements
    add_minimum_elements(new_product, publisher_data)

def add_minimum_elements(product, publisher_data):
    """Add minimum required elements to a product"""
    desc_detail = product.find('DescriptiveDetail')
    if desc_detail is not None:
        # Add title
        title_detail = etree.SubElement(desc_detail, 'TitleDetail')
        etree.SubElement(title_detail, 'TitleType').text = '01'
        title_element = etree.SubElement(title_detail, 'TitleElement')
        etree.SubElement(title_element, 'TitleElementLevel').text = '01'
        etree.SubElement(title_element, 'TitleText').text = "Title Not Available"
        
        # Add language
        language = etree.SubElement(desc_detail, 'Language')
        etree.SubElement(language, 'LanguageRole').text = '01'
        etree.SubElement(language, 'LanguageCode').text = publisher_data.get('language_code', 'eng')
    
    # Add publishing detail
    pub_detail = etree.SubElement(product, 'PublishingDetail')
    etree.SubElement(pub_detail, 'PublishingStatus').text = '04'  # Active
    
    # Add product supply
    prod_supply = etree.SubElement(product, 'ProductSupply')
    supply_detail = etree.SubElement(prod_supply, 'SupplyDetail')
    supplier = etree.SubElement(supply_detail, 'Supplier')
    etree.SubElement(supplier, 'SupplierRole').text = '01'
    etree.SubElement(supply_detail, 'ProductAvailability').text = '20'  # Available
def process_identifiers(old_product, new_product, epub_isbn):
    """Process product identifiers"""
    found_isbn = False
    
    # Process existing identifiers
    for identifier in old_product.xpath('.//*[local-name() = "ProductIdentifier"]'):
        new_identifier = etree.SubElement(new_product, 'ProductIdentifier')
        id_type = identifier.xpath('.//*[local-name() = "ProductIDType"]/text()')
        if id_type:
            etree.SubElement(new_identifier, 'ProductIDType').text = id_type[0]
            id_value = etree.SubElement(new_identifier, 'IDValue')
            if id_type[0] in ["03", "15"]:  # ISBN-13
                id_value.text = epub_isbn
                found_isbn = True
            else:
                old_value = identifier.xpath('.//*[local-name() = "IDValue"]/text()')
                id_value.text = old_value[0] if old_value else ''
    
    # Add ISBN if not found
    if not found_isbn:
        new_identifier = etree.SubElement(new_product, 'ProductIdentifier')
        etree.SubElement(new_identifier, 'ProductIDType').text = '15'
        etree.SubElement(new_identifier, 'IDValue').text = epub_isbn

def process_descriptive_detail(old_product, descriptive_detail, epub_features, publisher_data):
    """Process descriptive detail section"""
    # Product composition and form
    etree.SubElement(descriptive_detail, 'ProductComposition').text = publisher_data.get('product_composition', '00')
    etree.SubElement(descriptive_detail, 'ProductForm').text = publisher_data.get('product_form', 'EB')
    etree.SubElement(descriptive_detail, 'ProductFormDetail').text = 'E101'
    
    # Accessibility features
    for code, is_present in epub_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
            etree.SubElement(feature, 'ProductFormFeatureValue').text = code
            etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]
    
    # Process titles
    process_titles(old_product, descriptive_detail)
    
    # Process contributors
    process_contributors(old_product, descriptive_detail)
    
    # Process language
    process_language(old_product, descriptive_detail, publisher_data)

def process_titles(old_product, descriptive_detail):
    """Process title information"""
    titles = old_product.xpath('.//*[local-name() = "Title"]')
    if not titles:
        # Create default title if none exists
        title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
        etree.SubElement(title_detail, 'TitleType').text = '01'
        title_element = etree.SubElement(title_detail, 'TitleElement')
        etree.SubElement(title_element, 'TitleElementLevel').text = '01'
        etree.SubElement(title_element, 'TitleText').text = 'Title Not Available'
        return
    
    for old_title in titles:
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

def process_contributors(old_product, descriptive_detail):
    """Process contributor information"""
    for old_contributor in old_product.xpath('.//*[local-name() = "Contributor"]'):
        contributor = etree.SubElement(descriptive_detail, 'Contributor')
        
        # Contributor role
        role = old_contributor.xpath('.//*[local-name() = "ContributorRole"]/text()')
        if role:
            etree.SubElement(contributor, 'ContributorRole').text = role[0]
        
        # Person name variants
        for name_type in ['PersonName', 'PersonNameInverted', 'CorporateName']:
            name = old_contributor.xpath(f'.//*[local-name() = "{name_type}"]/text()')
            if name:
                etree.SubElement(contributor, name_type).text = name[0]
        
        # Biographical note
        bio = old_contributor.xpath('.//*[local-name() = "BiographicalNote"]/text()')
        if bio:
            etree.SubElement(contributor, 'BiographicalNote').text = bio[0]

def process_language(old_product, descriptive_detail, publisher_data):
    """Process language information"""
    languages = old_product.xpath('.//*[local-name() = "Language"]')
    if not languages:
        # Create default language if none exists
        language = etree.SubElement(descriptive_detail, 'Language')
        etree.SubElement(language, 'LanguageRole').text = '01'
        etree.SubElement(language, 'LanguageCode').text = publisher_data.get('language_code', 'eng')
        return
    
    for old_language in languages:
        language = etree.SubElement(descriptive_detail, 'Language')
        
        role = old_language.xpath('.//*[local-name() = "LanguageRole"]/text()')
        etree.SubElement(language, 'LanguageRole').text = role[0] if role else '01'
        
        code = old_language.xpath('.//*[local-name() = "LanguageCode"]/text()')
        etree.SubElement(language, 'LanguageCode').text = code[0] if code else publisher_data.get('language_code', 'eng')

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
            text_elem = etree.SubElement(text_content, 'Text')
            text_elem.text = text[0]
            
            text_format = old_text.xpath('.//*[local-name() = "TextFormat"]/text()')
            if text_format:
                text_elem.set('textformat', text_format[0].lower())
    
    # Convert MediaFile to SupportingResource
    process_supporting_resources(old_product, collateral_detail)

def process_supporting_resources(old_product, collateral_detail):
    """Process supporting resources"""
    for old_media in old_product.xpath('.//*[local-name() = "MediaFile"]'):
        resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        media_type = old_media.xpath('.//*[local-name() = "MediaFileTypeCode"]/text()')
        etree.SubElement(resource, 'ResourceContentType').text = media_type[0] if media_type else '01'
        
        etree.SubElement(resource, 'ResourceMode').text = '03'
        
        resource_version = etree.SubElement(resource, 'ResourceVersion')
        etree.SubElement(resource_version, 'ResourceForm').text = '02'
        
        link = old_media.xpath('.//*[local-name() = "MediaFileLink"]/text()')
        if link:
            etree.SubElement(resource_version, 'ResourceLink').text = link[0]

def process_publishing_detail(old_product, publishing_detail):
    """Process publishing detail section"""
    # Imprint
    imprint = old_product.xpath('.//*[local-name() = "ImprintName"]/text()')
    if imprint:
        imprint_detail = etree.SubElement(publishing_detail, 'Imprint')
        etree.SubElement(imprint_detail, 'ImprintName').text = imprint[0]
    
    # Publisher
    publisher = old_product.xpath('.//*[local-name() = "PublisherName"]/text()')
    if publisher:
        publisher_detail = etree.SubElement(publishing_detail, 'Publisher')
        etree.SubElement(publisher_detail, 'PublisherName').text = publisher[0]
    
    # Publishing status
    status = old_product.xpath('.//*[local-name() = "PublishingStatus"]/text()')
    etree.SubElement(publishing_detail, 'PublishingStatus').text = status[0] if status else '04'
    
    # Publication date
    pub_date = old_product.xpath('.//*[local-name() = "PublicationDate"]/text()')
    if pub_date:
        publishing_date = etree.SubElement(publishing_detail, 'PublishingDate')
        etree.SubElement(publishing_date, 'PublishingDateRole').text = '01'
        etree.SubElement(publishing_date, 'Date').text = pub_date[0]

def process_product_supply(old_product, product_supply, publisher_data):
    """Process product supply section"""
    supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
    
    # Supplier
    supplier = etree.SubElement(supply_detail, 'Supplier')
    etree.SubElement(supplier, 'SupplierRole').text = '01'
    if publisher_data and publisher_data.get('sender_name'):
        etree.SubElement(supplier, 'SupplierName').text = publisher_data['sender_name']
    
    # Product availability
    availability = old_product.xpath('.//*[local-name() = "ProductAvailability"]/text()')
    etree.SubElement(supply_detail, 'ProductAvailability').text = availability[0] if availability else '20'
    
    # Process prices
    if publisher_data and 'prices' in publisher_data:
        for currency, amount in publisher_data['prices'].items():
            if amount:
                price = etree.SubElement(supply_detail, 'Price')
                etree.SubElement(price, 'PriceType').text = '02'
                etree.SubElement(price, 'CurrencyCode').text = currency.upper()
                etree.SubElement(price, 'PriceAmount').text = str(Decimal(amount))