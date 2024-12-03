import xml.etree.ElementTree as ET
from lxml import etree
import logging
from datetime import datetime
import traceback
import re
from decimal import Decimal

logger = logging.getLogger(__name__)

ONIX_30_NS = "http://ns.editeur.org/onix/3.0/reference"
NSMAP = {None: ONIX_30_NS}

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
    """
    Process ONIX XML with accessibility features and publisher data
    Returns: bytes (processed XML content)
    """
    try:
        # Parse XML with recovery mode enabled
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(xml_content, parser=parser)
        logger.info(f"XML parsed successfully. Root tag: {tree.tag}")

        # Define namespaces and helper functions
        def create_element(tag):
            return etree.Element(f"{{{ONIX_30_NS}}}{tag}", nsmap=NSMAP)

        def subelement(parent, tag, text=None):
            elem = etree.SubElement(parent, f"{{{ONIX_30_NS}}}{tag}")
            if text is not None:
                elem.text = text
            return elem

        # Create new root if needed
        new_root = ensure_valid_root(tree)

        # Process header
        process_header(new_root, epub_isbn, publisher_data)

        # Process products
        process_products(new_root, epub_features, epub_isbn, publisher_data)

        # Transform to string
        transformed_xml = etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8')
        logger.info("ONIX processing completed successfully")
        return transformed_xml

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def ensure_valid_root(tree):
    """Ensure valid ONIX root element"""
    if tree.tag != 'ONIXMessage':
        new_root = etree.Element('ONIXMessage', nsmap=NSMAP)
        new_root.set("release", "3.0")
        if tree.tag == 'Product':
            new_root.append(tree)
        else:
            for child in tree:
                if child.tag == 'Product':
                    new_root.append(child)
        return new_root
    return tree

def process_header(root, epub_isbn, publisher_data):
    """Process ONIX header"""
    header = root.find('.//Header')
    if header is None:
        header = etree.SubElement(root, 'Header')

    # Update sender information if publisher data is provided
    if publisher_data:
        sender = header.find('.//Sender')
        if sender is None:
            sender = etree.SubElement(header, 'Sender')
        
        update_sender_info(sender, publisher_data)

    # Update sent date/time
    sent_datetime = etree.SubElement(header, 'SentDateTime')
    sent_datetime.text = datetime.now().strftime("%Y%m%dT%H%M%S")

def update_sender_info(sender, publisher_data):
    """Update sender information with publisher data"""
    elements = {
        'SenderName': publisher_data.get('sender_name', ''),
        'ContactName': publisher_data.get('contact_name', ''),
        'EmailAddress': publisher_data.get('email', '')
    }
    
    for tag, value in elements.items():
        elem = sender.find(f'.//{tag}')
        if elem is None:
            elem = etree.SubElement(sender, tag)
        elem.text = value

def process_products(root, epub_features, epub_isbn, publisher_data):
    """Process all products in the ONIX file"""
    for product in root.findall('.//Product'):
        # Process basic product information
        process_product_identifiers(product, epub_isbn)
        
        # Process descriptive detail
        descriptive_detail = ensure_descriptive_detail(product)
        process_descriptive_detail(descriptive_detail, epub_features, publisher_data)
        
        # Process collateral detail
        process_collateral_detail(product)
        
        # Process publishing detail
        process_publishing_detail(product)
        
        # Process product supply
        if publisher_data:
            process_product_supply(product, publisher_data)

def process_product_identifiers(product, epub_isbn):
    """Process product identifiers"""
    for identifier in product.findall('.//ProductIdentifier'):
        id_type = identifier.find('.//ProductIDType')
        if id_type is not None and id_type.text in ['03', '15']:  # ISBN-13
            id_value = identifier.find('.//IDValue')
            if id_value is not None:
                id_value.text = epub_isbn

def ensure_descriptive_detail(product):
    """Ensure DescriptiveDetail section exists"""
    descriptive_detail = product.find('.//DescriptiveDetail')
    if descriptive_detail is None:
        descriptive_detail = etree.SubElement(product, 'DescriptiveDetail')
    return descriptive_detail

def process_descriptive_detail(descriptive_detail, epub_features, publisher_data):
    """Process descriptive detail section"""
    # Add product composition
    if publisher_data and publisher_data.get('product_composition'):
        composition = descriptive_detail.find('.//ProductComposition')
        if composition is None:
            composition = etree.SubElement(descriptive_detail, 'ProductComposition')
        composition.text = publisher_data['product_composition']

    # Add product form
    if publisher_data and publisher_data.get('product_form'):
        form = descriptive_detail.find('.//ProductForm')
        if form is None:
            form = etree.SubElement(descriptive_detail, 'ProductForm')
        form.text = publisher_data['product_form']

    # Process accessibility features
    process_accessibility_features(descriptive_detail, epub_features)

def process_accessibility_features(descriptive_detail, epub_features):
    """Process accessibility features"""
    # Remove existing accessibility features
    for feature in descriptive_detail.findall('.//ProductFormFeature'):
        feature_type = feature.find('.//ProductFormFeatureType')
        if feature_type is not None and feature_type.text == "09":
            descriptive_detail.remove(feature)

    # Add new accessibility features
    for code, is_present in epub_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            feature_type = etree.SubElement(feature, 'ProductFormFeatureType')
            feature_type.text = "09"
            
            feature_value = etree.SubElement(feature, 'ProductFormFeatureValue')
            feature_value.text = code
            
            feature_description = etree.SubElement(feature, 'ProductFormFeatureDescription')
            feature_description.text = CODELIST_196[code]

def process_collateral_detail(product):
    """Process collateral detail section"""
    collateral_detail = product.find('.//CollateralDetail')
    if collateral_detail is None:
        collateral_detail = etree.SubElement(product, 'CollateralDetail')

def process_publishing_detail(product):
    """Process publishing detail section"""
    publishing_detail = product.find('.//PublishingDetail')
    if publishing_detail is None:
        publishing_detail = etree.SubElement(product, 'PublishingDetail')

def process_product_supply(product, publisher_data):
    """Process product supply section"""
    product_supply = product.find('.//ProductSupply')
    if product_supply is None:
        product_supply = etree.SubElement(product, 'ProductSupply')
    
    # Process pricing information
    if 'prices' in publisher_data:
        process_pricing(product_supply, publisher_data['prices'])

def process_pricing(product_supply, prices):
    """Process pricing information"""
    for currency, amount in prices.items():
        if amount:
            supply_detail = ensure_supply_detail(product_supply)
            price = etree.SubElement(supply_detail, 'Price')
            
            price_type = etree.SubElement(price, 'PriceType')
            price_type.text = '02'  # RRP including tax
            
            currency_code = etree.SubElement(price, 'CurrencyCode')
            currency_code.text = currency.upper()
            
            price_amount = etree.SubElement(price, 'PriceAmount')
            price_amount.text = str(Decimal(amount))

def ensure_supply_detail(product_supply):
    """Ensure SupplyDetail section exists"""
    supply_detail = product_supply.find('.//SupplyDetail')
    if supply_detail is None:
        supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
        
        # Add default supplier
        supplier = etree.SubElement(supply_detail, 'Supplier')
        supplier_role = etree.SubElement(supplier, 'SupplierRole')
        supplier_role.text = '01'  # Publisher
        
        # Add default availability
        availability = etree.SubElement(supply_detail, 'ProductAvailability')
        availability.text = '20'  # Available
        
    return supply_detail