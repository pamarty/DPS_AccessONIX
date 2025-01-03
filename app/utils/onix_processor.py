"""Main ONIX processing module"""
import logging
import traceback
from lxml import etree
from datetime import datetime
from .onix_constants import ONIX_30_NS, NSMAP, DEFAULT_LANGUAGE_CODE
from .processors import (
    process_header,
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

def process_product_identifiers(old_product, product, epub_isbn):
    """Process product identifiers including ISBN-13, ISBN-10, etc."""
    try:
        # Add main ISBN-13 first
        identifier = etree.SubElement(product, 'ProductIdentifier')
        id_type = etree.SubElement(identifier, 'ProductIDType')
        id_type.text = '03'  # GTIN-13/ISBN-13
        id_value = etree.SubElement(identifier, 'IDValue')
        id_value.text = epub_isbn
        
        # Process original ISBN-10 if exists
        isbn_10 = old_product.findtext('.//ProductIdentifier[ProductIDType="02"]/IDValue')
        if isbn_10:
            identifier = etree.SubElement(product, 'ProductIdentifier')
            id_type = etree.SubElement(identifier, 'ProductIDType')
            id_type.text = '02'  # ISBN-10
            id_value = etree.SubElement(identifier, 'IDValue')
            id_value.text = isbn_10
        
        # Preserve any other identifiers from original
        for old_id in old_product.findall('.//ProductIdentifier'):
            id_type_text = old_id.findtext('ProductIDType')
            id_value_text = old_id.findtext('IDValue')
            
            # Skip if already processed or empty
            if not id_value_text or id_type_text in ['02', '03']:
                continue
                
            identifier = etree.SubElement(product, 'ProductIdentifier')
            id_type = etree.SubElement(identifier, 'ProductIDType')
            id_type.text = id_type_text
            id_value = etree.SubElement(identifier, 'IDValue')
            id_value.text = id_value_text
                
    except Exception as e:
        logger.error(f"Error processing product identifiers: {str(e)}")
        raise

def process_work_identifier(old_product, work_id):
    """Process WorkIdentifier composite"""
    try:
        work_id_type = etree.SubElement(work_id, 'WorkIDType')
        work_id_type.text = old_product.findtext('.//WorkIDType')
        id_value = etree.SubElement(work_id, 'IDValue')
        id_value.text = old_product.findtext('.//IDValue')
    except Exception as e:
        logger.error(f"Error processing work identifier: {str(e)}")
        raise

def process_product_website(old_product, website):
    """Process ProductWebsite composite"""
    try:
        if old_product.find('.//WebsiteRole') is not None:
            role = etree.SubElement(website, 'WebsiteRole')
            role.text = old_product.findtext('.//WebsiteRole')
        
        if old_product.find('.//ProductWebsiteLink') is not None:
            link = etree.SubElement(website, 'ProductWebsiteLink')
            link.text = old_product.findtext('.//ProductWebsiteLink')
    except Exception as e:
        logger.error(f"Error processing product website: {str(e)}")
        raise

def process_media_file(old_media, product):
    """Process MediaFile composite"""
    try:
        media = etree.SubElement(product, 'MediaFile')
        for element in old_media:
            new_element = etree.SubElement(media, element.tag)
            new_element.text = element.text
            for attr, value in element.attrib.items():
                new_element.set(attr, value)
    except Exception as e:
        logger.error(f"Error processing media file: {str(e)}")
        raise

def process_supply_detail(old_supply, product_supply):
    """Process SupplyDetail composite"""
    try:
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
                
                if old_price.find('.//PriceTypeCode') is not None:
                    price_type = etree.SubElement(price, 'PriceTypeCode')
                    price_type.text = old_price.findtext('.//PriceTypeCode')
                
                if old_price.find('.//PriceAmount') is not None:
                    amount = etree.SubElement(price, 'PriceAmount')
                    amount.text = old_price.findtext('.//PriceAmount')
                
                if old_price.find('.//CurrencyCode') is not None:
                    currency = etree.SubElement(price, 'CurrencyCode')
                    currency.text = old_price.findtext('.//CurrencyCode')
    except Exception as e:
        logger.error(f"Error processing supply detail: {str(e)}")
        raise

def process_accessibility_features(epub_features, descriptive_detail):
    """Process accessibility features into ProductFormFeature composites"""
    for code, enabled in epub_features.items():
        if enabled:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
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

def analyze_accessibility_features(value, accessibility_info):
    """Analyze accessibility features from metadata"""
    feature_mapping = {
        'tableofcontents': '11',
        'index': '12',
        'readingorder': '13',
        'alternativetext': '14',
        'longdescription': '15',
        'alternativerepresentation': '16',
        'mathml': '17',
        'chemml': '18',
        'printpagenumbers': '19',
        'pagenumbers': '19',
        'pagebreaks': '19',
        'synchronizedaudiotext': '20',
        'ttsmarkup': '21',
        'displaytransformability': '24',
        'fontcustomization': '24',
        'textspacing': '24',
        'colorcustomization': '24',
        'texttospeech': '24',
        'readingtools': '24',
        'highcontrast': '26',
        'colorcontrast': '26',
        'audiocontrast': '27',
        'fullaudiodescription': '28',
        'structuralnavigation': '29',
        'aria': '30',
        'accessibleinterface': '31',
        'accessiblecontrols': '31',
        'accessiblenavigation': '31',
        'landmarks': '32',
        'landmarknavigation': '32',
        'chemistryml': '34',
        'latex': '35',
        'modifiabletextsize': '36',
        'ultracolorcontrast': '37',
        'glossary': '38',
        'accessiblesupplementarycontent': '39',
        'linkpurpose': '40'
    }
    
    for key, code in feature_mapping.items():
        if key in value:
            accessibility_info[code] = True
            logger.info(f"Accessibility feature detected: {key}")

def analyze_additional_metadata(property, value, accessibility_info):
    """Analyze additional metadata properties"""
    if 'accessibilityhazard' in property and 'none' in value:
        accessibility_info['36'] = True
        logger.info("All textual content can be modified")
    
    if 'certifiedby' in property:
        accessibility_info['93'] = True
        logger.info("Compliance certification detected")
    
    if ('accessibilityapi' in property or 
        'a11y:certifierReport' in property or 
        ('accessibility' in property and value.startswith('http'))):
        accessibility_info['94'] = True
        logger.info(f"Compliance web page detected: {value}")
    
    if 'accessmode' in property or 'accessmodesufficient' in property:
        if 'textual' in value:
            accessibility_info['52'] = True
            logger.info("All non-decorative content supports reading without sight")
        if 'auditory' in value:
            accessibility_info['51'] = True
            logger.info("All non-decorative content supports reading via pre-recorded audio")

def process_product(old_product, new_root, epub_features, epub_isbn, publisher_data):
    """Process complete product composite"""
    try:
        product = etree.SubElement(new_root, 'Product')
        
        # Record Reference (required)
        record_reference = etree.SubElement(product, 'RecordReference')
        record_reference.text = epub_isbn
        
        # Notification Type (required)
        notification_type = etree.SubElement(product, 'NotificationType')
        notification_type.text = '03'  # Confirmed record
        
        # Product Identifiers
        process_product_identifiers(old_product, product, epub_isbn)
        
        # Work Identifier if exists
        if old_product.find('.//WorkIdentifier') is not None:
            work_id = etree.SubElement(product, 'WorkIdentifier')
            process_work_identifier(old_product, work_id)
        
        # Product Website if exists
        if old_product.find('.//ProductWebsite') is not None:
            website = etree.SubElement(product, 'ProductWebsite')
            process_product_website(old_product, website)

        # Process descriptive detail with accessibility features
        descriptive_detail = etree.SubElement(product, 'DescriptiveDetail')
        process_descriptive_detail(old_product, descriptive_detail)
        process_accessibility_features(epub_features, descriptive_detail)
        
        # Process other core details
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

def validate_output(old_product, new_product):
    """Validate that no critical data is lost in conversion"""
    critical_fields = [
        'WorkIdentifier',
        'ProductWebsite',
        'SupplyDetail',
        'MediaFile',
        'Barcode',
        'NumberOfPages',
        'Extent',
        'Illustrations',
        'MainSubject',
        'DescriptiveDetail',
        'CollateralDetail',
        'PublishingDetail'
    ]
    
    for field in critical_fields:
        old_elements = old_product.findall(f'.//{field}')
        new_elements = new_product.findall(f'.//{field}')
        if len(old_elements) > len(new_elements):
            logger.warning(f'Missing {field} elements in output')
            return False
    return True

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
    """Process complete ONIX content"""
    try:
        parser = etree.XMLParser(remove_blank_text=True, recover=True)
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