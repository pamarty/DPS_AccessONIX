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

        # Create new root with appropriate namespace
        new_root = etree.Element('ONIXMessage', nsmap=NSMAP if is_reference else {})
        if is_reference:
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

        # Generate output with appropriate format
        output_xml = etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8')
        
        # Convert to short tags if needed
        if not is_reference:
            output_xml = output_xml.replace(b'<ONIXMessage>', b'<ONIXmessage>')
            output_xml = output_xml.replace(b'</ONIXMessage>', b'</ONIXmessage>')

        return output_xml

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def process_header(root, new_root, original_version):
    """Process header elements"""
    header = etree.SubElement(new_root, 'Header')

    # Sender info
    sender = etree.SubElement(header, 'Sender')
    from_company = root.xpath('.//*[local-name() = "FromCompany"]/text()')
    company_element = etree.SubElement(sender, 'SenderName')
    company_element.text = from_company[0] if from_company else "Default Company Name"

    contact_name = root.xpath('.//*[local-name() = "ContactName"]/text()')
    if contact_name:
        contact_element = etree.SubElement(sender, 'ContactName')
        contact_element.text = contact_name[0]

    email = root.xpath('.//*[local-name() = "EmailAddress"]/text()')
    if email:
        email_element = etree.SubElement(sender, 'EmailAddress')
        email_element.text = email[0]

    # SentDateTime
    if original_version.startswith('3'):
        sent_date_time = etree.SubElement(header, 'SentDateTime')
        sent_date_time.text = datetime.now().strftime("%Y%m%dT%H%M%S")
    else:
        sent_date = etree.SubElement(header, 'SentDate')
        sent_date.text = datetime.now().strftime("%Y%m%d")

    # MessageNote
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

    # Descriptive Detail
    descriptive_detail = process_descriptive_detail(new_product, old_product, epub_features)

    # Collateral Detail
    process_collateral_detail(new_product, old_product)

    # Publishing Detail
    process_publishing_detail(new_product, old_product)

    # Product Supply
    process_product_supply(new_product, old_product)

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

    # Product Form
    prod_comp = etree.SubElement(descriptive_detail, 'ProductComposition')
    prod_comp.text = '00'
    
    prod_form = etree.SubElement(descriptive_detail, 'ProductForm')
    prod_form.text = 'EB'
    
    form_detail = etree.SubElement(descriptive_detail, 'ProductFormDetail')
    form_detail.text = 'E101'

    # Accessibility Features
    for code, is_present in epub_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
            etree.SubElement(feature, 'ProductFormFeatureValue').text = code
            etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]

    # Title
    process_title(descriptive_detail, old_product)

    # Contributors
    process_contributors(descriptive_detail, old_product)

    # Language
    process_language(descriptive_detail, old_product)

    # Subjects
    process_subjects(descriptive_detail, old_product)

    # Audience
    process_audience(descriptive_detail, old_product)

    return descriptive_detail

def process_title(descriptive_detail, old_product):
    """Process title information"""
    for old_title in old_product.xpath('.//*[local-name() = "Title"]'):
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
        
        # Contributor Role
        role = old_contributor.xpath('.//*[local-name() = "ContributorRole"]/text()')
        if role:
            etree.SubElement(new_contributor, 'ContributorRole').text = role[0]

        # Person Name
        person_name = old_contributor.xpath('.//*[local-name() = "PersonName"]/text()')
        if person_name:
            etree.SubElement(new_contributor, 'PersonName').text = person_name[0]

        # Contributor Place
        country = old_contributor.xpath('.//*[local-name() = "CountryCode"]/text()')
        if country:
            place = etree.SubElement(new_contributor, 'ContributorPlace')
            etree.SubElement(place, 'ContributorPlaceRelator').text = '00'
            etree.SubElement(place, 'CountryCode').text = country[0]

def process_language(descriptive_detail, old_product):
    """Process language information"""
    for old_lang in old_product.xpath('.//*[local-name() = "Language"]'):
        language = etree.SubElement(descriptive_detail, 'Language')
        
        role = old_lang.xpath('.//*[local-name() = "LanguageRole"]/text()')
        etree.SubElement(language, 'LanguageRole').text = role[0] if role else '01'
        
        code = old_lang.xpath('.//*[local-name() = "LanguageCode"]/text()')
        etree.SubElement(language, 'LanguageCode').text = code[0] if code else 'eng'

def process_subjects(descriptive_detail, old_product):
    """Process subject information"""
    for old_subject in old_product.xpath('.//*[local-name() = "Subject"]'):
        new_subject = etree.SubElement(descriptive_detail, 'Subject')
        
        scheme = old_subject.xpath('.//*[local-name() = "SubjectSchemeIdentifier"]/text()')
        if scheme:
            etree.SubElement(new_subject, 'SubjectSchemeIdentifier').text = scheme[0]
        
        code = old_subject.xpath('.//*[local-name() = "SubjectCode"]/text()')
        if code:
            etree.SubElement(new_subject, 'SubjectCode').text = code[0]

def process_audience(descriptive_detail, old_product):
    """Process audience information"""
    for old_audience in old_product.xpath('.//*[local-name() = "Audience"]'):
        new_audience = etree.SubElement(descriptive_detail, 'Audience')
        
        type_code = old_audience.xpath('.//*[local-name() = "AudienceCodeType"]/text()')
        if type_code:
            etree.SubElement(new_audience, 'AudienceCodeType').text = type_code[0]
        
        code_value = old_audience.xpath('.//*[local-name() = "AudienceCodeValue"]/text()')
        if code_value:
            etree.SubElement(new_audience, 'AudienceCodeValue').text = code_value[0]

def process_collateral_detail(new_product, old_product):
    """Process collateral detail section"""
    collateral_detail = etree.SubElement(new_product, 'CollateralDetail')

    # Text Content
    for old_text in old_product.xpath('.//*[local-name() = "OtherText"]'):
        text_content = etree.SubElement(collateral_detail, 'TextContent')
        
        text_type = old_text.xpath('.//*[local-name() = "TextTypeCode"]/text()')
        type_value = text_type[0] if text_type else "03"
        # Map text type 99 to 03 (description)
        if type_value == "99":
            type_value = "03"
        etree.SubElement(text_content, 'TextType').text = type_value
        
        etree.SubElement(text_content, 'ContentAudience').text = '00'
        
        text = old_text.xpath('.//*[local-name() = "Text"]/text()')
        if text:
            etree.SubElement(text_content, 'Text').text = text[0]

    # Supporting Resource
    for old_media in old_product.xpath('.//*[local-name() = "MediaFile"]'):
        resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        # Required order: ResourceContentType, ContentAudience, ResourceMode
        media_type = old_media.xpath('.//*[local-name() = "MediaFileTypeCode"]/text()')
        etree.SubElement(resource, 'ResourceContentType').text = media_type[0] if media_type else '01'
        etree.SubElement(resource, 'ContentAudience').text = '00'
        etree.SubElement(resource, 'ResourceMode').text = '03'
        
        version = etree.SubElement(resource, 'ResourceVersion')
        etree.SubElement(version, 'ResourceForm').text = '02'
        
        link = old_media.xpath('.//*[local-name() = "MediaFileLink"]/text()')
        if link:
            etree.SubElement(version, 'ResourceLink').text = link[0]

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
    
    # Publishing Date
    pub_date = old_product.xpath('.//*[local-name() = "PublicationDate"]/text()')
    if pub_date:
        publishing_date = etree.SubElement(publishing_detail, 'PublishingDate')
        etree.SubElement(publishing_date, 'PublishingDateRole').text = '01'
        etree.SubElement(publishing_date, 'Date').text = format_date(pub_date[0])
    
    # Sales Rights
    process_sales_rights(publishing_detail, old_product)

def process_sales_rights(publishing_detail, old_product):
    """Process sales rights information"""
    for old_rights in old_product.xpath('.//*[local-name() = "SalesRights"]'):
        new_rights = etree.SubElement(publishing_detail, 'SalesRights')
        
        rights_type = old_rights.xpath('.//*[local-name() = "SalesRightsType"]/text()')
        etree.SubElement(new_rights, 'SalesRightsType').text = rights_type[0] if rights_type else '01'
        
        territory = etree.SubElement(new_rights, 'Territory')
        
        countries = old_rights.xpath('.//*[local-name() = "RightsCountry"]/text()')
        if countries:
            etree.SubElement(territory, 'CountriesIncluded').text = countries[0]
        else:
            regions = old_rights.xpath('.//*[local-name() = "RightsTerritory"]/text()')
            if regions:
                etree.SubElement(territory, 'RegionsIncluded').text = regions[0]
            else:
                etree.SubElement(territory, 'CountriesIncluded').text = 'US'

def process_product_supply(new_product, old_product):
    """Process product supply section"""
    product_supply = etree.SubElement(new_product, 'ProductSupply')
    
    # Process each SupplyDetail
    supply_details = old_product.xpath('.//*[local-name() = "SupplyDetail"]')
    if supply_details:
        for old_supply in supply_details:
            process_supply_detail(product_supply, old_supply)
    else:
        create_default_supply_detail(product_supply)

def process_supply_detail(product_supply, old_supply):
    """Process individual supply detail"""
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
    
    # Supply Dates
    process_supply_dates(supply_detail, old_supply)
    
    # Prices
    process_prices(supply_detail, old_supply)

def process_supply_dates(supply_detail, old_supply):
    """Process supply dates"""
    # Map date types to roles
    date_mapping = {
        'ExpectedShipDate': '08',  # Expected availability date
        'OnSaleDate': '01'         # Publication date
    }
    
    for date_type, role in date_mapping.items():
        date_value = old_supply.xpath(f'.//*[local-name() = "{date_type}"]/text()')
        if date_value:
            supply_date = etree.SubElement(supply_detail, 'SupplyDate')
            etree.SubElement(supply_date, 'SupplyDateRole').text = role
            etree.SubElement(supply_date, 'Date').text = format_date(date_value[0])

def process_prices(supply_detail, old_supply):
    """Process price information"""
    prices = old_supply.xpath('.//*[local-name() = "Price"]')
    if prices:
        for old_price in prices:
            price = etree.SubElement(supply_detail, 'Price')
            
            # Required elements in correct order
            price_type = old_price.xpath('.//*[local-name() = "PriceTypeCode"]/text()')
            etree.SubElement(price, 'PriceType').text = price_type[0] if price_type else '02'
            
            # Price Amount (required)
            amount = old_price.xpath('.//*[local-name() = "PriceAmount"]/text()')
            if amount:
                etree.SubElement(price, 'PriceAmount').text = amount[0]
            else:
                etree.SubElement(price, 'PriceAmount').text = '0.00'
            
            # Territory handling
            territory = etree.SubElement(price, 'Territory')
            countries = old_price.xpath('.//*[local-name() = "CountryCode"]/text()')
            if countries:
                etree.SubElement(territory, 'CountriesIncluded').text = countries[0]
            else:
                etree.SubElement(territory, 'CountriesIncluded').text = 'US'
    else:
        # Create default price if none exist
        create_default_price(supply_detail)

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