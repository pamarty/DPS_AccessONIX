"""Main ONIX processing module"""
import logging
import traceback
from lxml import etree
from datetime import datetime
from .onix_constants import ONIX_30_NS, NSMAP
from .processors import (
    process_header,
    process_product,
    process_descriptive_detail,
    process_collateral_detail,
    process_publishing_detail,
    process_product_supply
)

logger = logging.getLogger(__name__)

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

def process_work_identifier(old_product, work_id):
    """Process WorkIdentifier composite"""
    work_id_type = etree.SubElement(work_id, 'WorkIDType')
    work_id_type.text = old_product.findtext('.//WorkIDType')
    id_value = etree.SubElement(work_id, 'IDValue') 
    id_value.text = old_product.findtext('.//IDValue')

def process_product_website(old_product, website):
    """Process ProductWebsite composite"""
    role = etree.SubElement(website, 'WebsiteRole')
    role.text = old_product.findtext('.//WebsiteRole')
    link = etree.SubElement(website, 'ProductWebsiteLink')
    link.text = old_product.findtext('.//ProductWebsiteLink')

def process_media_file(old_media, product):
    """Process MediaFile composite"""
    media = etree.SubElement(product, 'MediaFile')
    for element in old_media:
        new_element = etree.SubElement(media, element.tag)
        new_element.text = element.text
        for attr, value in element.attrib.items():
            new_element.set(attr, value)

def process_supply_detail(old_supply, product_supply):
    """Process SupplyDetail composite"""
    supply = etree.SubElement(product_supply, 'SupplyDetail')
    
    # Process supplier info
    if old_supply.find('.//SupplierName') is not None:
        supplier_name = etree.SubElement(supply, 'SupplierName')
        supplier_name.text = old_supply.findtext('.//SupplierName')
    
    if old_supply.find('.//SupplierRole') is not None:
        supplier_role = etree.SubElement(supply, 'SupplierRole')
        supplier_role.text = old_supply.findtext('.//SupplierRole')
    
    # Process availability
    if old_supply.find('.//ProductAvailability') is not None:
        availability = etree.SubElement(supply, 'ProductAvailability')
        availability.text = old_supply.findtext('.//ProductAvailability')
    
    # Process prices
    prices = old_supply.findall('.//Price')
    if prices:
        for old_price in prices:
            price = etree.SubElement(supply, 'Price')
            
            # Price type
            if old_price.find('.//PriceTypeCode') is not None:
                price_type = etree.SubElement(price, 'PriceTypeCode')
                price_type.text = old_price.findtext('.//PriceTypeCode')
            
            # Price amount
            if old_price.find('.//PriceAmount') is not None:
                amount = etree.SubElement(price, 'PriceAmount')
                amount.text = old_price.findtext('.//PriceAmount')
            
            # Currency
            if old_price.find('.//CurrencyCode') is not None:
                currency = etree.SubElement(price, 'CurrencyCode')
                currency.text = old_price.findtext('.//CurrencyCode')

def process_related_product(old_related, product):
    """Process RelatedProduct composite"""
    related = etree.SubElement(product, 'RelatedProduct')
    
    # Relation code
    if old_related.find('.//RelationCode') is not None:
        relation = etree.SubElement(related, 'RelationCode')
        relation.text = old_related.findtext('.//RelationCode')
    
    # Product identifiers
    identifiers = old_related.findall('.//ProductIdentifier')
    if identifiers:
        for old_id in identifiers:
            pid = etree.SubElement(related, 'ProductIdentifier')
            
            id_type = etree.SubElement(pid, 'ProductIDType')
            id_type.text = old_id.findtext('.//ProductIDType')
            
            id_value = etree.SubElement(pid, 'IDValue')
            id_value.text = old_id.findtext('.//IDValue')

def process_accessibility_features(epub_features, product):
    """Process accessibility features into ProductFormFeature composites"""
    for code, enabled in epub_features.items():
        if enabled:
            feature = etree.SubElement(product, 'ProductFormFeature')
            feature_type = etree.SubElement(feature, 'ProductFormFeatureType')
            feature_type.text = '09'  # Accessibility feature
            feature_value = etree.SubElement(feature, 'ProductFormFeatureValue')
            feature_value.text = code
            
            # Add description for specific features
            if code == '0':  # Accessibility summary
                desc = etree.SubElement(feature, 'ProductFormFeatureDescription')
                desc.text = generate_accessibility_summary(epub_features)
            elif code in ['22', '24', '26']:  # Special features needing description
                desc = etree.SubElement(feature, 'ProductFormFeatureDescription')
                desc.text = get_feature_description(code)

def generate_accessibility_summary(features):
    """Generate comprehensive accessibility summary"""
    summary_parts = []
    
    if features.get('4'):
        summary_parts.append("Meets EPUB Accessibility Specification 1.1")
    if features.get('85'):
        summary_parts.append("WCAG 2.1 Level AA compliant")
    if features.get('52'):
        summary_parts.append("Supports reading without sight")
    if features.get('24'):
        summary_parts.append("Includes dyslexia readability features")
    
    summary = ". ".join(summary_parts)
    return summary if summary else "Basic accessibility features supported"

def get_feature_description(code):
    """Get description for specific accessibility features"""
    descriptions = {
        '22': 'Language tagging provided',
        '24': 'Dyslexia readability',
        '26': 'Use of high contrast between text and background color'
    }
    return descriptions.get(code, '')

def validate_output(old_product, new_product):
    """Validate that no critical data is lost in conversion"""
    critical_fields = [
        'WorkIdentifier',
        'ProductWebsite',
        'SupplyDetail',
        'RelatedProduct',
        'MediaFile',
        'Barcode',
        'NumberOfPages',
        'Extent',
        'Illustrations',
        'MainSubject'
    ]
    
    for field in critical_fields:
        old_elements = old_product.findall(f'.//{field}')
        new_elements = new_product.findall(f'.//{field}')
        if len(old_elements) > len(new_elements):
            logger.warning(f'Missing {field} elements in output')
            return False
    return True

def process_product(old_product, new_root, epub_features, epub_isbn, publisher_data):
    """Process complete product composite"""
    try:
        product = etree.SubElement(new_root, 'Product')
        
        # Record Reference
        record_reference = etree.SubElement(product, 'RecordReference')
        record_reference.text = epub_isbn
        
        # Notification Type
        notification_type = etree.SubElement(product, 'NotificationType')
        notification_type.text = '03'  # Confirmed record
        
        # Product Identifiers
        process_product_identifiers(old_product, product, epub_isbn)
        
        # Work Identifier
        if old_product.find('.//WorkIdentifier') is not None:
            work_id = etree.SubElement(product, 'WorkIdentifier')
            process_work_identifier(old_product, work_id)
        
        # Product Website
        if old_product.find('.//ProductWebsite') is not None:
            website = etree.SubElement(product, 'ProductWebsite')
            process_product_website(old_product, website)
        
        # Process other details
        process_descriptive_detail(old_product, product, epub_features)
        process_collateral_detail(old_product, product)
        process_publishing_detail(old_product, product, publisher_data)
        
        # Product Supply
        product_supply = etree.SubElement(product, 'ProductSupply')
        
        # Market
        market = etree.SubElement(product_supply, 'Market')
        territory = etree.SubElement(market, 'Territory')
        regions = etree.SubElement(territory, 'RegionsIncluded')
        regions.text = 'WORLD'
        
        # Supply Details
        supply_details = old_product.findall('.//SupplyDetail')
        if supply_details:
            for supply in supply_details:
                process_supply_detail(supply, product_supply)
        
        # Related Products
        related_products = old_product.findall('.//RelatedProduct')
        if related_products:
            for related in related_products:
                process_related_product(related, product)
        
        # Media Files
        media_files = old_product.findall('.//MediaFile')
        if media_files:
            for media in media_files:
                process_media_file(media, product)
        
        # Validate output
        if not validate_output(old_product, product):
            logger.warning("Some data may have been lost in conversion")
        
        return product
        
    except Exception as e:
        logger.error(f"Error processing product: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
    """Process complete ONIX content"""
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