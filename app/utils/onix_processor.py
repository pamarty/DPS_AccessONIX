"""Main ONIX processing module"""
import logging
import traceback
from lxml import etree
from datetime import datetime
from .onix_constants import ONIX_30_NS, NSMAP, DEFAULT_LANGUAGE_CODE
from .processors import (
    process_header
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

def copy_all_elements(old_element, new_element):
    """Copies all child elements from old to new along with attributes"""
    for element in old_element:
        new_child = etree.SubElement(new_element, element.tag)
        new_child.text = element.text
        for attr, value in element.attrib.items():
            new_child.set(attr, value)
        # Recursively copy child elements
        if len(element):
           copy_all_elements(element, new_child)

def process_product(old_product, new_root, epub_features, epub_isbn, publisher_data):
    """Process complete product composite"""
    try:
        product = etree.SubElement(new_root, 'Product')

        # Copy all elements from old_product to new product
        copy_all_elements(old_product, product)

        # Remove old descriptive detail
        old_descriptive_detail = product.find('DescriptiveDetail')
        if old_descriptive_detail is not None:
            product.remove(old_descriptive_detail)

        # Process descriptive detail with accessibility features
        descriptive_detail = etree.SubElement(product, 'DescriptiveDetail')
        process_accessibility_features(epub_features, descriptive_detail)

        # Add enhanced publisher data if available
        if publisher_data:
            product_composition = publisher_data.get('product_composition')
            product_form = publisher_data.get('product_form')
            language_code = publisher_data.get('language_code')
            price_cad = publisher_data.get('price_cad')
            price_gbp = publisher_data.get('price_gbp')
            price_usd = publisher_data.get('price_usd')

            if product_composition:
                product.find('DescriptiveDetail').insert(0, etree.Element('ProductComposition')).text = product_composition
            if product_form:
                 product.find('DescriptiveDetail').insert(1, etree.Element('ProductForm')).text = product_form
            if language_code:
                language = etree.SubElement(product.find('DescriptiveDetail'), 'Language')
                language_role = etree.SubElement(language, 'LanguageRole')
                language_role.text = '01'
                language_code_element = etree.SubElement(language, 'LanguageCode')
                language_code_element.text = language_code

            # Ensure a ProductSupply composite exists
            product_supply = product.find('ProductSupply')
            if product_supply is None:
               product_supply = etree.SubElement(product, 'ProductSupply')

            # Ensure a Market composite exists
            market = product_supply.find('Market')
            if market is None:
               market = etree.SubElement(product_supply, 'Market')

            # Ensure a Territory composite exists
            territory = market.find('Territory')
            if territory is None:
               territory = etree.SubElement(market, 'Territory')
            
            # Ensure a RegionsIncluded composite exists
            regions = territory.find('RegionsIncluded')
            if regions is None:
                regions = etree.SubElement(territory, 'RegionsIncluded')
            
            regions.text = 'WORLD'


            # Create a SupplyDetail composite
            supply_detail = etree.SubElement(product_supply, 'SupplyDetail')

            # Create a Supplier composite and its components
            supplier = etree.SubElement(supply_detail, 'Supplier')
            supplier_role = etree.SubElement(supplier, 'SupplierRole')
            supplier_role.text = '01' # default value

            # Add Sender name as supplier name
            supplier_name = etree.SubElement(supplier, 'SupplierName')
            supplier_name.text = publisher_data.get('sender_name', '')


            # Set product availability to 'Available'
            availability = etree.SubElement(supply_detail, 'ProductAvailability')
            availability.text = '10' # default value

            # Add prices if available
            if price_cad:
                 price = etree.SubElement(supply_detail, 'Price')
                 price_amount = etree.SubElement(price, 'PriceAmount')
                 price_amount.text = str(price_cad)
                 currency = etree.SubElement(price, 'CurrencyCode')
                 currency.text = 'CAD'

            if price_gbp:
                 price = etree.SubElement(supply_detail, 'Price')
                 price_amount = etree.SubElement(price, 'PriceAmount')
                 price_amount.text = str(price_gbp)
                 currency = etree.SubElement(price, 'CurrencyCode')
                 currency.text = 'GBP'

            if price_usd:
                price = etree.SubElement(supply_detail, 'Price')
                price_amount = etree.SubElement(price, 'PriceAmount')
                price_amount.text = str(price_usd)
                currency = etree.SubElement(price, 'CurrencyCode')
                currency.text = 'USD'
        
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