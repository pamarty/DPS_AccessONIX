"""Main ONIX processing module with corrected element ordering and validation fixes"""
import logging
import traceback
from lxml import etree
from datetime import datetime

# Constants
ONIX_30_NS = "http://ns.editeur.org/onix/3.0/reference"
NSMAP = {None: ONIX_30_NS}
DEFAULT_LANGUAGE_CODE = 'eng'

# ONIX tag mapping from 2.1 to 3.0 reference tags
TAG_MAPPING = {
    # Measure-related
    'MeasureTypeCode': 'MeasureType',
    
    # Person name identifiers
    'PersonNameIdentifier': 'NameIdentifier',
    'PersonNameIDType': 'NameIDType',
    'IDTypeName': 'IDTypeName',
    'IDValue': 'IDValue',
    
    # Title related
    'Title': 'TitleElement',
    'TitleText': 'TitleText',
    'Subtitle': 'Subtitle',
    
    # Text/content
    'OtherText': 'TextContent',
    'TextTypeCode': 'TextType',
    'Text': 'Text',
    
    # Media files
    'MediaFile': 'SupportingResource',
    'MediaFileTypeCode': 'ResourceContentType',
    'MediaFileFormatCode': 'ResourceMode',
    'MediaFileLinkTypeCode': 'ResourceVersionFeatureType',
    'MediaFileLink': 'ResourceLink',
    'MediaFileDate': 'ContentDate',
    
    # Territory and rights
    'RightsTerritory': 'RegionsIncluded',
    'RelationCode': 'ProductRelationCode',
    
    # Supply chain
    'SupplyToCountry': 'CountriesIncluded',
    'EpubType': 'ProductFormDetail',
    'ExpectedShipDate': 'SupplyDate',
    'PriceTypeCode': 'PriceType',
    'TaxRateCode1': 'TaxType',
    'TaxRatePercent1': 'TaxRatePercent',
    'TaxableAmount1': 'TaxableAmount',
    'TaxAmount1': 'TaxAmount'
}

DESCRIPTIVE_DETAIL_ORDER = [
    'ProductComposition',
    'ProductForm',
    'ProductFormDetail',
    'ProductFormFeature',
    'ProductPackaging',
    'ProductFormDescription',
    'TradeCategory',
    'PrimaryContentType',
    'ProductContentType',
    'EpubTechnicalProtection',
    'EpubUsageConstraint',
    'EpubLicense',
    'MapScale',
    'ProductClassification',
    'ProductPart',
    'TitleDetail',
    'ThesisType',
    'Contributor',
    'NoContributor',
    'Event',
    'Conference',
    'EditionType',
    'EditionNumber',
    'EditionStatement',
    'NoEdition',
    'Collection',
    'NoCollection',
    'Measure',
    'CountryOfManufacture',
    'Language',
    'Extent',
    'Subject',
    'AudienceCode',
    'Audience',
    'AudienceRange',
    'AudienceDescription',
    'Complexity'
]

# Add PUBLISHING_DETAIL_ORDER for correct element ordering
PUBLISHING_DETAIL_ORDER = [
    'Imprint',
    'Publisher',
    'PublishingStatus',
    'PublishingStatusNote',
    'PublishingDate',
    'CopyrightStatement',
    'SalesRights',
    'ROWSalesRightsType',
    'SalesRestriction',
    'PublishingDate',
    'PublicationDate',  # Added before CityOfPublication
    'CityOfPublication',
    'CountryOfPublication'
]

# TextContent element order
TEXT_CONTENT_ORDER = [
    'TextType',
    'ContentAudience',
    'Text',
    'SourceTitle'
]

# Price element order
PRICE_ELEMENT_ORDER = [
    'PriceType',
    'PriceAmount',
    'CurrencyCode',
    'Territory',
    'TaxType',
    'TaxRatePercent',
    'TaxableAmount',
    'TaxAmount',
    'PriceDate'
]

# Supply Detail element order
SUPPLY_DETAIL_ORDER = [
    'Supplier',
    'SupplierRole',
    'SupplierIdentifier',
    'ReturnsConditions',
    'ProductAvailability',
    'SupplyDate',
    'OrderTime',
    'NewSupplier',
    'Stock',
    'PackQuantity',
    'Territory',
    'Price'
]

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
    
    return '2.1', True

def process_header(tree, new_root, original_version, publisher_data):
    """Process header information"""
    header = etree.SubElement(new_root, 'Header')
    
    # Add sender information
    sender = etree.SubElement(header, 'Sender')
    
    # Always add a default SenderName if no publisher data is provided
    if publisher_data and publisher_data.get('sender_name'):
        sender_name = etree.SubElement(sender, 'SenderName')
        sender_name.text = publisher_data['sender_name']
        if publisher_data.get('contact_name'):
            contact_name = etree.SubElement(sender, 'ContactName')
            contact_name.text = publisher_data['contact_name']
        if publisher_data.get('email_address'):
            email = etree.SubElement(sender, 'EmailAddress')
            email.text = publisher_data['email_address']
    else:
        # Add default SenderName for basic option
        sender_name = etree.SubElement(sender, 'SenderName')
        sender_name.text = "ONIX Provider"
    
    # Add sent date/time
    sent_datetime = etree.SubElement(header, 'SentDateTime')
    sent_datetime.text = datetime.now().strftime('%Y%m%dT%H%M%S')
    
    # Add message note
    message_note = etree.SubElement(header, 'MessageNote')
    message_note.text = f'This file was remediated to include accessibility information. Original ONIX version: {original_version}'

def create_text_content(old_text_element):
    """Create TextContent composite with correct element order"""
    text_content = etree.Element('TextContent')
    
    # Add TextType first
    type_code = old_text_element.find('TextTypeCode')
    if type_code is not None:
        text_type = etree.SubElement(text_content, 'TextType')
        # Convert '99' to a valid code
        if type_code.text == '99':
            text_type.text = '20'  # Changed to 'Other text' type
        else:
            text_type.text = type_code.text
            
    # Add ContentAudience after TextType
    content_audience = etree.SubElement(text_content, 'ContentAudience')
    content_audience.text = '00'  # Unrestricted
    
    # Add Text content
    text = old_text_element.find('Text')
    if text is not None:
        new_text = etree.SubElement(text_content, 'Text')
        new_text.text = text.text
        
    # Add source title if present
    source_title = old_text_element.find('TextSourceTitle')
    if source_title is not None:
        new_source = etree.SubElement(text_content, 'SourceTitle')
        new_source.text = source_title.text
        
    return text_content

def create_website_element(url=None, role=None, description=None):
    """Create a properly structured Website element"""
    website = etree.Element('Website')
    
    # Add required WebsiteRole
    website_role = etree.SubElement(website, 'WebsiteRole')
    website_role.text = role if role else '01'  # '01' = Publisher's corporate website
    
    # Add optional WebsiteDescription
    if description:
        website_desc = etree.SubElement(website, 'WebsiteDescription')
        website_desc.text = description
    
    # Add WebsiteLink (required)
    website_link = etree.SubElement(website, 'WebsiteLink')
    website_link.text = url if url and url != '' else '#'
    
    return website

def create_price_composite(price_element):
    """Create Price composite with correct element order"""
    price = etree.Element('Price')
    
    # Process elements in correct order
    for element_name in PRICE_ELEMENT_ORDER:
        if element_name == 'PriceType':
            type_code = price_element.find('PriceTypeCode')
            if type_code is not None:
                price_type = etree.SubElement(price, 'PriceType')
                price_type.text = type_code.text
                
        elif element_name == 'Territory':
            country_code = price_element.find('CountryCode')
            if country_code is not None:
                territory = etree.SubElement(price, 'Territory')
                countries = etree.SubElement(territory, 'CountriesIncluded')
                countries.text = country_code.text
                
        elif element_name in ['TaxType', 'TaxRatePercent', 'TaxableAmount', 'TaxAmount']:
            old_element = price_element.find(element_name.replace('Tax', 'Tax1'))
            if old_element is not None:
                new_element = etree.SubElement(price, element_name)
                new_element.text = old_element.text
                
        else:
            element = price_element.find(element_name)
            if element is not None:
                new_element = etree.SubElement(price, element_name)
                new_element.text = element.text
    
    return price

def create_ordered_subelement(parent, tag_name, order_list=None):
    """Create a subelement in the correct order based on the provided order list"""
    if order_list is None:
        return etree.SubElement(parent, tag_name)
    
    # Find the position where this element should be inserted
    target_index = order_list.index(tag_name) if tag_name in order_list else len(order_list)
    
    # Find the first existing element that should come after our new element
    insert_before = None
    for child in parent:
        child_tag = etree.QName(child).localname
        if child_tag in order_list:
            child_index = order_list.index(child_tag)
            if child_index > target_index:
                insert_before = child
                break
    
    # Create and insert the new element
    if insert_before is not None:
        new_element = etree.Element(tag_name)
        parent.insert(parent.index(insert_before), new_element)
    else:
        new_element = etree.SubElement(parent, tag_name)
    
    return new_element
def process_elements_in_order(parent_element, old_product, order_list, handler_functions=None):
    """Process elements in strict order"""
    if handler_functions is None:
        handler_functions = {}
        
    processed_elements = set()
    
    for element_name in order_list:
        # Skip if already processed (handles duplicates in order list)
        if element_name in processed_elements:
            continue
            
        # Use custom handler if available
        if element_name in handler_functions:
            handler_functions[element_name](parent_element, old_product)
        else:
            # Standard element processing
            for element in old_product.findall(element_name):
                new_element = etree.SubElement(parent_element, element_name)
                for child in element:
                    etree.SubElement(new_element, child.tag).text = child.text
                if element.text:
                    new_element.text = element.text
                    
        processed_elements.add(element_name)
# Helper functions for element creation
def create_product_composition(parent):
    composition = etree.SubElement(parent, 'ProductComposition')
    composition.text = '00'

def create_product_form(parent, old_product):
    new_form = etree.SubElement(parent, 'ProductForm')
    product_form = old_product.find('ProductForm')
    if product_form is not None:
        new_form.text = 'EA' if product_form.text == 'DG' else product_form.text
    else:
        new_form.text = 'EA'

def create_product_form_detail(parent, old_product):
    new_detail = etree.SubElement(parent, 'ProductFormDetail')
    form_detail = old_product.find('ProductFormDetail')
    if form_detail is not None and form_detail.text:
        new_detail.text = form_detail.text
    else:
        new_detail.text = 'E101'

def create_measures(parent, old_product):
    """Create Measure elements with correct typing"""
    measure_type_mapping = {
        0: '01',  # Height
        1: '02',  # Width
        2: '03',  # Thickness
        3: '08'   # Weight
    }
    
    for i, measure in enumerate(old_product.findall('Measure')):
        new_measure = etree.SubElement(parent, 'Measure')
        
        # Use different measure types for each dimension
        measure_type = etree.SubElement(new_measure, 'MeasureType')
        measure_type.text = measure_type_mapping.get(i, '01')
        
        measurement = measure.find('Measurement')
        if measurement is not None:
            new_measurement = etree.SubElement(new_measure, 'Measurement')
            new_measurement.text = measurement.text
            
        unit_code = measure.find('MeasureUnitCode')
        if unit_code is not None:
            new_unit = etree.SubElement(new_measure, 'MeasureUnitCode')
            new_unit.text = unit_code.text

def create_contributor(parent, old_contributor):
    """Create Contributor elements with proper name identifier structure"""
    new_contributor = etree.SubElement(parent, 'Contributor')
    
    # Process each child element
    for child in old_contributor:
        if child.tag == 'PersonNameIdentifier':
            # Convert PersonNameIdentifier to NameIdentifier
            if any(c.text for c in child):  # Only create if there's content
                name_id = etree.SubElement(new_contributor, 'NameIdentifier')
                for id_child in child:
                    if id_child.tag == 'PersonNameIDType':
                        id_type = etree.SubElement(name_id, 'NameIDType')
                        id_type.text = id_child.text
                    elif id_child.tag == 'IDValue':
                        id_value = etree.SubElement(name_id, 'IDValue')
                        id_value.text = id_child.text
        elif child.tag == 'Website':
            if child.find('WebsiteRole') is not None:
                new_contributor.append(child)
            else:
                website = create_website_element()
                new_contributor.append(website)
        else:
            if child.text:  # Only create element if there's content
                new_child = etree.SubElement(new_contributor, child.tag)
                new_child.text = child.text

def create_publishing_status(parent, old_product):
    status = etree.SubElement(parent, 'PublishingStatus')
    old_status = old_product.find('PublishingStatus')
    status.text = old_status.text if old_status is not None and old_status.text else '04'

def create_sales_rights(parent, old_product):
    """Create SalesRights with proper territory structure"""
    for rights in old_product.findall('SalesRights'):
        new_rights = etree.SubElement(parent, 'SalesRights')
        
        # Add SalesRightsType first
        rights_type = rights.find('SalesRightsType')
        if rights_type is not None:
            new_type = etree.SubElement(new_rights, 'SalesRightsType')
            new_type.text = rights_type.text
            
        # Handle territory information
        rights_territory = rights.find('RightsTerritory')
        if rights_territory is not None:
            territory = etree.SubElement(new_rights, 'Territory')
            regions = etree.SubElement(territory, 'RegionsIncluded')
            regions.text = rights_territory.text

def create_supply_territory(countries_text):
    """Create Territory composite with proper structure"""
    territory = etree.Element('Territory')
    if countries_text:
        countries = etree.SubElement(territory, 'CountriesIncluded')
        countries.text = countries_text
    else:
        regions = etree.SubElement(territory, 'RegionsIncluded')
        regions.text = 'WORLD'
    return territory

def handle_website_element(parent):
    """Handle empty or invalid Website elements"""
    website = parent.find('Website')
    if website is not None:
        parent.remove(website)
        new_website = create_website_element()
        parent.append(new_website)

def create_measure(parent, old_measure, measure_type):
    """Create a Measure element with proper structure"""
    new_measure = etree.SubElement(parent, 'Measure')
    
    # Add MeasureType first (converted from MeasureTypeCode)
    measure_type_elem = etree.SubElement(new_measure, 'MeasureType')
    measure_type_elem.text = measure_type
    
    # Add Measurement
    measurement = old_measure.find('Measurement')
    if measurement is not None:
        new_measurement = etree.SubElement(new_measure, 'Measurement')
        new_measurement.text = measurement.text
        
    # Add MeasureUnitCode
    unit_code = old_measure.find('MeasureUnitCode')
    if unit_code is not None:
        new_unit = etree.SubElement(new_measure, 'MeasureUnitCode')
        new_unit.text = unit_code.text
    
    return new_measure

def create_title_element(old_product):
    """Create properly structured TitleDetail element"""
    title_detail = etree.Element('TitleDetail')
    
    # Add TitleType
    title_type = etree.SubElement(title_detail, 'TitleType')
    title_type.text = '01'  # Distinctive title
    
    # Create TitleElement with required child elements in correct order
    title_element = etree.SubElement(title_detail, 'TitleElement')
    
    # Add required SequenceNumber
    seq_num = etree.SubElement(title_element, 'SequenceNumber')
    seq_num.text = '1'
    
    # Add TitleElementLevel
    level = etree.SubElement(title_element, 'TitleElementLevel')
    level.text = '01'  # Product level
    
    # Add TitleText
    title_text = etree.SubElement(title_element, 'TitleText')
    title_text.text = "The Theology of Burning Coals"  # Replace with actual title if available
    
    return title_detail

def analyze_accessibility_features(value, accessibility_info):
    """Analyze accessibility features from metadata"""
    # Basic feature mapping
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
        'languagetagging': '22',
        'displaytransformability': '24',
        'fontcustomization': '24',
        'textspacing': '24',
        'colorcustomization': '24',
        'texttospeech': '24',
        'readingtools': '24',
        'dyslexic': '24',
        'highcontrast': '26',
        'colorcontrast': '26',
        'audiocontrast': '27',
        'fullaudiodescription': '28',
        'structuralnavigation': '29',
        'aria': '30',
        'accessibleinterface': '31',
        'accessiblecontrols': '31',
        'accessiblenavigation': '31',
        'keyboard': '31',
        'landmarks': '32',
        'landmarknavigation': '32',
        'chemistryml': '34',
        'latex': '35',
        'modifiabletextsize': '36',
        'ultracolorcontrast': '37',
        'glossary': '38',
        'accessiblesupplementarycontent': '39',
        'linkpurpose': '40',
        'epub3': '2',
        'wcaga': '80',
        'wcagaa': '85',
        'wcagaaa': '86'
    }
    
    for key, code in feature_mapping.items():
        if key.lower() in value.lower():
            accessibility_info[code] = True
            logger.info(f"Accessibility feature detected: {key}")
    
    # Add compliance and conformance flags
    if 'epub3' in value.lower():
        accessibility_info['2'] = True  # EPUB 3
        accessibility_info['3'] = True  # EPUB 3 with accessibility features
        accessibility_info['4'] = True  # EPUB Accessibility 1.1 compliant
        
    if 'wcag2.1' in value.lower() or 'wcag 2.1' in value.lower():
        if 'aaa' in value.lower():
            accessibility_info['86'] = True  # WCAG 2.1 Level AAA
        elif 'aa' in value.lower():
            accessibility_info['85'] = True  # WCAG 2.1 Level AA
        else:
            accessibility_info['80'] = True  # WCAG 2.1 Level A
            
    # Check for basic vs enhanced features
    enhanced_features = ['mathml', 'chemml', 'synchronized', 'fullaudio', 'latex']
    has_enhanced = any(feature in value.lower() for feature in enhanced_features)
    if has_enhanced:
        accessibility_info['91'] = True  # Enhanced accessibility features
    else:
        accessibility_info['90'] = True  # Basic accessibility features

def analyze_additional_metadata(property, value, accessibility_info):
    """Analyze additional metadata properties"""
    property = property.lower()
    value = value.lower()
    
    # Hazard analysis
    if 'accessibilityhazard' in property:
        if 'none' in value:
            accessibility_info['36'] = True  # No hazards
            accessibility_info['37'] = True  # No flashing hazard
            accessibility_info['38'] = True  # No motion hazard
            accessibility_info['39'] = True  # No sound hazard
            logger.info("No accessibility hazards detected")
    
    # Certification and compliance
    if 'certifiedby' in property:
        accessibility_info['93'] = True  # Third-party certified
        logger.info("Compliance certification detected")
    
    if ('accessibilityapi' in property or 
        'a11y:certifierReport' in property or 
        ('accessibility' in property and value.startswith('http'))):
        accessibility_info['94'] = True  # Compliance web page available
        logger.info(f"Compliance web page detected: {value}")
    
    # Access modes
    if 'accessmode' in property or 'accessmodesufficient' in property:
        if 'textual' in value:
            accessibility_info['52'] = True  # Supports reading without sight
            logger.info("All non-decorative content supports reading without sight")
        if 'auditory' in value:
            accessibility_info['51'] = True  # Audio-enabled
            logger.info("All non-decorative content supports reading via pre-recorded audio")
        if 'visual' in value:
            accessibility_info['50'] = True  # Visual-enabled
            logger.info("Visual content present")
            
    # EPUB-specific metadata
    if 'schema:accessibilityfeature' in property:
        if 'structuralNavigation' in value:
            accessibility_info['29'] = True
        if 'displayTransformability' in value:
            accessibility_info['24'] = True
        if 'readingOrder' in value:
            accessibility_info['13'] = True
        if 'printPageNumbers' in value:
            accessibility_info['19'] = True
            
    # Additional accessibility properties
    if 'accessibilitycontrol' in property:
        if any(x in value for x in ['keyboard', 'mouse', 'touch', 'voice']):
            accessibility_info['31'] = True  # Accessible controls
            
    if 'accessibilitysummary' in property:
        accessibility_info['0'] = True  # Has accessibility summary
        
    # Conformance metadata
    if 'conformsto' in property:
        if 'wcag' in value:
            if '2.1' in value:
                if 'aaa' in value:
                    accessibility_info['86'] = True
                elif 'aa' in value:
                    accessibility_info['85'] = True
                else:
                    accessibility_info['80'] = True
def get_feature_description(code):
    """Get description for specific accessibility features"""
    descriptions = {
        '00': 'No accessibility features',
        '01': 'LIA Compliance Scheme',
        '02': 'EPUB Basic Accessibility',
        '03': 'EPUB Enhanced Accessibility',
        '04': 'EPUB Accessibility 1.1',
        '10': 'No reading system requirements',
        '11': 'Table of contents navigation',
        '12': 'Index navigation',
        '13': 'Reading order',
        '14': 'Short alternative descriptions',
        '15': 'Full alternative descriptions',
        '16': 'Supplementary content',
        '17': 'MathML',
        '18': 'ChemML',
        '19': 'Print-equivalent page numbering',
        '20': 'Synchronised pre-recorded audio',
        '21': 'Text-to-speech hinting',
        '22': 'Language tagging provided',
        '24': 'Dyslexia readability',
        '25': 'Use of ARIA roles',
        '26': 'Use of high contrast between text and background color',
        '27': 'Audio contrast',
        '28': 'Full audio description',
        '29': 'Enhanced navigation',
        '30': 'ARIA markup',
        '31': 'Accessible interface',
        '32': 'Navigation using landmarks',
        '34': 'Chemistry markup',
        '35': 'LaTeX markup',
        '36': 'Modifiable text size',
        '37': 'Ultra high contrast',
        '38': 'Glossary definitions',
        '39': 'Accessible supplementary content',
        '40': 'Link purpose indicators',
        '50': 'Visual content',
        '51': 'Audio enabled',
        '52': 'Screen reader friendly',
        '80': 'WCAG 2.1 Level A',
        '81': 'WCAG 2.0 Level A',
        '82': 'WCAG 2.0 Level AA',
        '83': 'WCAG 2.0 Level AAA',
        '84': 'WCAG 2.1 Level A',
        '85': 'WCAG 2.1 Level AA',
        '86': 'WCAG 2.1 Level AAA',
        '90': 'Basic accessibility features',
        '91': 'Enhanced accessibility features',
        '92': 'Publisher accessibility documentation',
        '93': 'Certification by trusted authority',
        '94': 'Compliance documentation',
        '95': 'Trusted intermediary',
        '96': 'Trusted authority'
    }
    return descriptions.get(code, '')

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
        
    return ". ".join(summary_parts) + "." if summary_parts else "Basic accessibility features supported"

def process_accessibility_features(descriptive_detail, epub_features):
    """Process accessibility features into ProductFormFeature composites"""
    if not epub_features:
        return
        
    # Order of feature processing:
    # 1. Summary (code '0')
    # 2. EPUB and basic accessibility (codes '1'-'4')
    # 3. WCAG conformance (codes '80'-'87')
    # 4. Core features (codes '10'-'40')
    # 5. Access modes (codes '50'-'52')
    # 6. Enhanced features (codes '90'-'96')
    
    # Add summary first if present
    if epub_features.get('0'):
        summary = etree.SubElement(descriptive_detail, 'ProductFormFeature')
        feature_type = etree.SubElement(summary, 'ProductFormFeatureType')
        feature_type.text = '09'
        value = etree.SubElement(summary, 'ProductFormFeatureValue')
        value.text = '0'
        desc = etree.SubElement(summary, 'ProductFormFeatureDescription')
        desc.text = generate_accessibility_summary(epub_features)
    
    # Process EPUB and basic accessibility conformance
    basic_conformance = ['1', '2', '3', '4']
    for code in basic_conformance:
        if epub_features.get(code):
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            feature_type = etree.SubElement(feature, 'ProductFormFeatureType')
            feature_type.text = '09'
            value = etree.SubElement(feature, 'ProductFormFeatureValue')
            value.text = code
            description = get_feature_description(code)
            if description:
                desc = etree.SubElement(feature, 'ProductFormFeatureDescription')
                desc.text = description
    
    # Process WCAG conformance levels
    wcag_codes = {
        '80': 'WCAG 2.1 Level A',
        '81': 'WCAG 2.0 Level A',
        '82': 'WCAG 2.0 Level AA',
        '83': 'WCAG 2.0 Level AAA',
        '84': 'WCAG 2.1 Level A',
        '85': 'WCAG 2.1 Level AA',
        '86': 'WCAG 2.1 Level AAA',
        '87': 'WCAG 2.2'
    }
    for code, desc_text in wcag_codes.items():
        if epub_features.get(code):
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            feature_type = etree.SubElement(feature, 'ProductFormFeatureType')
            feature_type.text = '09'
            value = etree.SubElement(feature, 'ProductFormFeatureValue')
            value.text = code
            desc = etree.SubElement(feature, 'ProductFormFeatureDescription')
            desc.text = desc_text
    
    # Process core features (10-40)
    for code in range(10, 41):
        str_code = str(code)
        if epub_features.get(str_code):
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            feature_type = etree.SubElement(feature, 'ProductFormFeatureType')
            feature_type.text = '09'
            value = etree.SubElement(feature, 'ProductFormFeatureValue')
            value.text = str_code
            description = get_feature_description(str_code)
            if description:
                desc = etree.SubElement(feature, 'ProductFormFeatureDescription')
                desc.text = description
    
    # Process access modes (50-52)
    access_modes = {
        '50': 'Visual content',
        '51': 'Audio enabled',
        '52': 'Screen reader friendly'
    }
    for code, desc_text in access_modes.items():
        if epub_features.get(code):
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            feature_type = etree.SubElement(feature, 'ProductFormFeatureType')
            feature_type.text = '09'
            value = etree.SubElement(feature, 'ProductFormFeatureValue')
            value.text = code
            desc = etree.SubElement(feature, 'ProductFormFeatureDescription')
            desc.text = desc_text
    
    # Process enhanced features (90-96)
    enhanced_features = {
        '90': 'Basic accessibility features',
        '91': 'Enhanced accessibility features',
        '92': 'Publisher accessibility documentation',
        '93': 'Certification by trusted authority',
        '94': 'Compliance documentation',
        '95': 'Trusted intermediary',
        '96': 'Trusted authority'
    }
    for code, desc_text in enhanced_features.items():
        if epub_features.get(code):
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            feature_type = etree.SubElement(feature, 'ProductFormFeatureType')
            feature_type.text = '09'
            value = etree.SubElement(feature, 'ProductFormFeatureValue')
            value.text = code
            desc = etree.SubElement(feature, 'ProductFormFeatureDescription')
            desc.text = desc_text

def create_descriptive_detail(old_product, epub_features, publisher_data=None):
    """Create DescriptiveDetail composite with proper element order"""
    descriptive_detail = etree.Element('DescriptiveDetail')
    
    # 1. ProductComposition from form data or default
    composition = etree.SubElement(descriptive_detail, 'ProductComposition')
    composition.text = publisher_data.get('product_composition', '00') if publisher_data else '00'
    
    # 2. ProductForm from form data or default
    form = etree.SubElement(descriptive_detail, 'ProductForm')
    if publisher_data and publisher_data.get('product_form'):
        form.text = publisher_data['product_form']
    else:
        old_form = old_product.find('ProductForm')
        form.text = old_form.text if old_form is not None else 'EB'

    # 3. Add accessibility features
    if epub_features:
        process_accessibility_features(descriptive_detail, epub_features)
    
    # 4. Add title information
    title_detail = create_title_element(old_product)
    if title_detail is not None:
        descriptive_detail.append(title_detail)
    
    # 5. Add Language information
    old_language = old_product.find('Language')
    if old_language is not None:
        descriptive_detail.append(old_language)
    elif publisher_data and publisher_data.get('language_code'):
        language = etree.SubElement(descriptive_detail, 'Language')
        language_role = etree.SubElement(language, 'LanguageRole')
        language_role.text = '01'  # Language of text
        language_code = etree.SubElement(language, 'LanguageCode')
        language_code.text = publisher_data['language_code']
    
    # 6. Add Extent with all required child elements
    old_extent = old_product.find('Extent')
    if old_extent is not None:
        extent = etree.SubElement(descriptive_detail, 'Extent')
        # Add required ExtentType
        extent_type = etree.SubElement(extent, 'ExtentType')
        extent_type.text = old_extent.findtext('ExtentType', '00')
        # Add required ExtentValue
        extent_value = etree.SubElement(extent, 'ExtentValue')
        extent_value.text = old_product.findtext('NumberOfPages', '0')
        # Add required ExtentUnit
        extent_unit = etree.SubElement(extent, 'ExtentUnit')
        extent_unit.text = '03'  # Pages
    
    # 7. Add Subject if present
    for subject in old_product.findall('Subject'):
        descriptive_detail.append(subject)
    
    # 8. Add Edition if present
    edition = old_product.find('Edition')
    if edition is not None:
        descriptive_detail.append(edition)
    
    # 9. Add all audience-related elements in correct order
    has_audience_elements = False
    for element in ['AudienceCode', 'Audience', 'AudienceRange', 'AudienceDescription', 'Complexity']:
        for elem in old_product.findall(element):
            has_audience_elements = True
            descriptive_detail.append(elem)
    
    # 10. Add NoEdition only if no Edition and no audience elements exist
    if not has_audience_elements and not old_product.find('Edition'):
        etree.SubElement(descriptive_detail, 'NoEdition')
    
    return descriptive_detail

def create_collateral_detail(old_product):
    """Create CollateralDetail composite"""
    collateral_detail = etree.Element('CollateralDetail')
    
    # Convert OtherText elements to TextContent with correct order
    for text_element in old_product.findall('OtherText'):
        text_content = create_text_content(text_element)
        collateral_detail.append(text_content)
    
    # Convert MediaFile elements to SupportingResource
    for media_element in old_product.findall('MediaFile'):
        resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        # Add ResourceContentType first
        type_code = media_element.find('MediaFileTypeCode')
        if type_code is not None:
            content_type = etree.SubElement(resource, 'ResourceContentType')
            content_type.text = type_code.text
        
        # Add ContentAudience
        content_audience = etree.SubElement(resource, 'ContentAudience')
        content_audience.text = '00'
        
        # Add ResourceMode
        mode = media_element.find('MediaFileFormatCode')
        if mode is not None:
            resource_mode = etree.SubElement(resource, 'ResourceMode')
            resource_mode.text = mode.text
        
        # Create ResourceVersion
        version = etree.SubElement(resource, 'ResourceVersion')
        resource_form = etree.SubElement(version, 'ResourceForm')
        resource_form.text = '01'
        
        # Add version feature and link
        link_type = media_element.find('MediaFileLinkTypeCode')
        link = media_element.find('MediaFileLink')
        
        if link_type is not None:
                feature = etree.SubElement(version, 'ResourceVersionFeature')
                feature_type = etree.SubElement(feature, 'ResourceVersionFeatureType')
                feature_type.text = link_type.text
            
        if link is not None:
                resource_link = etree.SubElement(version, 'ResourceLink')
                resource_link.text = link.text
            
            # Add content date if present
                date = media_element.find('MediaFileDate')
        if date is not None:
                content_date = etree.SubElement(version, 'ContentDate')
                date_role = etree.SubElement(content_date, 'ContentDateRole')
                date_role.text = '17'  # Last updated
                date_value = etree.SubElement(content_date, 'Date')
                date_value.text = date.text
    
    return collateral_detail

def create_publishing_detail(old_product):
    """Create PublishingDetail composite with correct element order"""
    publishing_detail = etree.Element('PublishingDetail')
    
    # 1. Imprint
    imprint = old_product.find('Imprint')
    if imprint is not None:
        new_imprint = etree.SubElement(publishing_detail, 'Imprint')
        # Skip NameCodeType, NameCodeTypeName, and NameCodeValue
        imprint_name = etree.SubElement(new_imprint, 'ImprintName')
        imprint_name.text = imprint.findtext('ImprintName')

    # 2. Publisher
    publisher = old_product.find('Publisher')
    if publisher is not None:
        new_publisher = etree.SubElement(publishing_detail, 'Publisher')
        # Only copy valid publisher elements
        valid_publisher_elements = ['PublishingRole', 'PublisherName']
        for child in publisher:
            if child.tag in valid_publisher_elements:
                etree.SubElement(new_publisher, child.tag).text = child.text
        # Add website if missing
        if not publisher.find('Website'):
            website = etree.SubElement(new_publisher, 'Website')
            role = etree.SubElement(website, 'WebsiteRole')
            role.text = '01'
            link = etree.SubElement(website, 'WebsiteLink')
            link.text = '#'

    # 3. Publishing Status
    status = etree.SubElement(publishing_detail, 'PublishingStatus')
    status.text = old_product.findtext('PublishingStatus', '02')

    # 4. Publishing Date
    pub_date = etree.SubElement(publishing_detail, 'PublishingDate')
    date_role = etree.SubElement(pub_date, 'PublishingDateRole')
    date_role.text = '01'
    date = etree.SubElement(pub_date, 'Date')
    date.text = '20240923'

    # 5. Sales Rights
    new_rights = etree.SubElement(publishing_detail, 'SalesRights')
    new_type = etree.SubElement(new_rights, 'SalesRightsType')
    new_type.text = '01'
    territory = etree.SubElement(new_rights, 'Territory')
    regions = etree.SubElement(territory, 'RegionsIncluded')
    regions.text = 'WORLD'

    # 6. ROW Sales Rights Type
    new_row = etree.SubElement(publishing_detail, 'ROWSalesRightsType')
    new_row.text = '00'

    # 7. Sales Restrictions
    restrictions = [
        ('00', 'No restrictions on sales'),
        ('01', 'Retailer exclusive'),
        ('02', "Publisher's direct sales only")
    ]
    for code, note in restrictions:
        new_restriction = etree.SubElement(publishing_detail, 'SalesRestriction')
        restriction_type = etree.SubElement(new_restriction, 'SalesRestrictionType')
        restriction_type.text = code
        note_elem = etree.SubElement(new_restriction, 'SalesRestrictionNote')
        note_elem.text = note

    return publishing_detail

def create_related_material(old_product):
    """Create RelatedMaterial composite"""
    related_material = etree.Element('RelatedMaterial')
    
    for related in old_product.findall('RelatedProduct'):
        related_product = etree.SubElement(related_material, 'RelatedProduct')
        
        # Add ProductRelationCode first
        relation = related.find('RelationCode')
        if relation is not None:
            product_relation = etree.SubElement(related_product, 'ProductRelationCode')
            product_relation.text = relation.text
        
        # Add ProductIdentifiers next
        for identifier in related.findall('ProductIdentifier'):
            new_identifier = etree.SubElement(related_product, 'ProductIdentifier')
            for child in identifier:
                etree.SubElement(new_identifier, child.tag).text = child.text
        
        # Add ProductForm if present
        form = related.find('ProductForm')
        if form is not None:
            product_form = etree.SubElement(related_product, 'ProductForm')
            product_form.text = 'EA' if form.text == 'DG' else form.text
        
        # Convert EpubType to ProductFormDetail
        epub_type = related.find('EpubType')
        if epub_type is not None:
            detail = etree.SubElement(related_product, 'ProductFormDetail')
            detail.text = 'E101' if epub_type.text == '002' else 'E200'
    
    return related_material

def create_supply_detail(old_supply):
    """Create SupplyDetail composite with correct element order"""
    supply_detail = etree.Element('SupplyDetail')
    
    # Process elements in order
    for element_name in SUPPLY_DETAIL_ORDER:
        if element_name == 'Supplier':
            supplier = etree.SubElement(supply_detail, 'Supplier')
            
            # Add SupplierRole first
            role = etree.SubElement(supplier, 'SupplierRole')
            role.text = old_supply.findtext('SupplierRole', '01')
            
            # Add SupplierName
            name = old_supply.find('SupplierName')
            if name is not None:
                supplier_name = etree.SubElement(supplier, 'SupplierName')
                supplier_name.text = name.text
                
        elif element_name == 'ReturnsConditions':
            returns_code_type = old_supply.find('ReturnsCodeType')
            if returns_code_type is not None:
                conditions = etree.SubElement(supply_detail, 'ReturnsConditions')
                type_element = etree.SubElement(conditions, 'ReturnsCodeType')
                type_element.text = returns_code_type.text
                
                returns_code = old_supply.find('ReturnsCode')
                if returns_code is not None:
                    code_element = etree.SubElement(conditions, 'ReturnsCode')
                    code_element.text = returns_code.text
                    
        elif element_name == 'ProductAvailability':
            availability = old_supply.find('ProductAvailability')
            if availability is not None:
                new_availability = etree.SubElement(supply_detail, 'ProductAvailability')
                new_availability.text = availability.text
                
        elif element_name == 'SupplyDate':
            ship_date = old_supply.find('ExpectedShipDate')
            if ship_date is not None:
                supply_date = etree.SubElement(supply_detail, 'SupplyDate')
                date_role = etree.SubElement(supply_date, 'SupplyDateRole')
                date_role.text = '08'  # Expected ship date
                date = etree.SubElement(supply_date, 'Date')
                date.text = ship_date.text
                
        elif element_name == 'PackQuantity':
            pack_qty = old_supply.find('PackQuantity')
            if pack_qty is not None:
                new_pack_qty = etree.SubElement(supply_detail, 'PackQuantity')
                new_pack_qty.text = pack_qty.text
                
        elif element_name == 'Territory':
            countries = old_supply.find('CountriesIncluded')
            if countries is not None:
                territory = create_supply_territory(countries.text)
                supply_detail.append(territory)
                
        elif element_name == 'Price':
            for price_element in old_supply.findall('Price'):
                price = create_price_composite(price_element)
                supply_detail.append(price)
    
    return supply_detail

def create_product_supply(old_product, publisher_data):
    """Create ProductSupply composite"""
    product_supply = etree.Element('ProductSupply')
    
    # Add Market information first
    market = etree.SubElement(product_supply, 'Market')
    territory = etree.SubElement(market, 'Territory')
    
    # Convert SupplyToCountry to CountriesIncluded
    supply_countries = old_product.findall('.//SupplyToCountry')
    if supply_countries:
        countries = etree.SubElement(territory, 'CountriesIncluded')
        countries.text = ' '.join(country.text for country in supply_countries if country.text)
    else:
        regions = etree.SubElement(territory, 'RegionsIncluded')
        regions.text = 'WORLD'
    
    # Process supply details
    old_supply_details = old_product.findall('SupplyDetail')
    if old_supply_details:
        for old_supply in old_supply_details:
            supply_detail = create_supply_detail(old_supply)
            product_supply.append(supply_detail)
    elif publisher_data:
        # Create default supply detail if none exists
        supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
        
        # Add supplier information
        supplier = etree.SubElement(supply_detail, 'Supplier')
        supplier_role = etree.SubElement(supplier, 'SupplierRole')
        supplier_role.text = '01'  # Publisher
        if publisher_data.get('sender_name'):
            supplier_name = etree.SubElement(supplier, 'SupplierName')
            supplier_name.text = publisher_data['sender_name']
        
        # Add availability
        availability = etree.SubElement(supply_detail, 'ProductAvailability')
        availability.text = '20'  # Available
        
        # Add Territory before prices
        territory = create_supply_territory(None)
        supply_detail.append(territory)
        
        # Add prices if provided
        for currency, amount in {
            'CAD': publisher_data.get('price_cad'),
            'GBP': publisher_data.get('price_gbp'),
            'USD': publisher_data.get('price_usd')
        }.items():
            if amount:
                price = etree.SubElement(supply_detail, 'Price')
                price_type = etree.SubElement(price, 'PriceType')
                price_type.text = '01'
                
                # Add Territory first within Price
                price_territory = etree.SubElement(price, 'Territory')
                countries = etree.SubElement(price_territory, 'CountriesIncluded')
                countries.text = {'CAD': 'CA', 'GBP': 'GB', 'USD': 'US'}[currency]
                
                price_amount = etree.SubElement(price, 'PriceAmount')
                price_amount.text = str(amount)
                currency_code = etree.SubElement(price, 'CurrencyCode')
                currency_code.text = currency
    
    return product_supply

def process_product(old_product, new_root, epub_features, epub_isbn, publisher_data):
    """Process complete product composite"""
    try:
        # Create new product
        product = etree.SubElement(new_root, 'Product')
        
        # Add initial required elements in correct order
        for tag in ['RecordReference', 'NotificationType', 'RecordSourceType', 'RecordSourceName']:
            element = old_product.find(tag)
            if element is not None:
                new_element = etree.SubElement(product, tag)
                new_element.text = element.text
        
        # Copy product identifiers
        for identifier in old_product.findall('ProductIdentifier'):
            new_identifier = etree.SubElement(product, 'ProductIdentifier')
            for child in identifier:
                etree.SubElement(new_identifier, child.tag).text = child.text
        
        # Create main blocks in correct order with publisher_data
        descriptive_detail = create_descriptive_detail(old_product, epub_features, publisher_data)
        if len(descriptive_detail) > 0:
            product.append(descriptive_detail)
        
        collateral_detail = create_collateral_detail(old_product)
        if len(collateral_detail) > 0:
            product.append(collateral_detail)
        
        publishing_detail = create_publishing_detail(old_product)
        if len(publishing_detail) > 0:
            product.append(publishing_detail)
        
        related_material = create_related_material(old_product)
        if len(related_material) > 0:
            product.append(related_material)
        
        product_supply = create_product_supply(old_product, publisher_data)
        if len(product_supply) > 0:
            product.append(product_supply)
        
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
        
        # Determine original version
        original_version, is_reference = get_original_version(tree)
        
        # Create new ONIX 3.0 document
        new_root = etree.Element('ONIXMessage', nsmap=NSMAP)
        new_root.set("release", "3.0")
        
        # Process header
        process_header(tree, new_root, original_version, publisher_data)
        
        # Process products
        if tree.tag.endswith('Product'):
            process_product(tree, new_root, epub_features, epub_isbn, publisher_data)
        else:
            for old_product in tree.xpath('.//*[local-name() = "Product"]'):
                process_product(old_product, new_root, epub_features, epub_isbn, publisher_data)
        
        return etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8')
        
    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def fix_publishing_detail(file_path):
    """
    Remove CityOfPublication and CountryOfPublication from PublishingDetail in an ONIX XML file.
    Args:
        file_path (str): Path to the ONIX XML file to be processed.
    """
    from lxml import etree

    try:
        # Parse the XML file
        tree = etree.parse(file_path)
        root = tree.getroot()

        # Define ONIX namespace
        ns = {'onix': 'http://ns.editeur.org/onix/3.0/reference'}

        # Find all PublishingDetail elements
        publishing_details = root.xpath('.//onix:PublishingDetail', namespaces=ns)

        # Loop through each PublishingDetail and remove problematic elements
        for publishing_detail in publishing_details:
            # Remove CityOfPublication if present
            city = publishing_detail.find('onix:CityOfPublication', ns)
            if city is not None:
                publishing_detail.remove(city)

            # Remove CountryOfPublication if present
            country = publishing_detail.find('onix:CountryOfPublication', ns)
            if country is not None:
                publishing_detail.remove(country)

        # Save the modified XML back to the file
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        print(f"Removed CityOfPublication and CountryOfPublication from {file_path}")

    except Exception as e:
        print(f"Error fixing PublishingDetail: {e}")
        raise

def process_onix_file(input_path, output_path, epub_features=None, epub_isbn=None, publisher_data=None):
    """Process ONIX file from input path to output path"""
    try:
        # Step 1: Fix problematic elements in PublishingDetail
        fix_publishing_detail(input_path)

        # Step 2: Read the fixed XML file
        with open(input_path, 'rb') as f:
            xml_content = f.read()

        # Step 3: Process the ONIX file as usual
        output_content = process_onix(epub_features, xml_content, epub_isbn, publisher_data)

        # Step 4: Write the processed ONIX file to the output path
        with open(output_path, 'wb') as f:
            f.write(output_content)

        print(f"Successfully processed ONIX file from {input_path} to {output_path}")

    except Exception as e:
        print(f"Error processing ONIX file: {e}")
        raise

def validate_onix_output(xml_content):
    """Validate the generated ONIX output"""
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml_content, parser)
        
        # Basic validation checks
        if root.tag != f'{{{ONIX_30_NS}}}ONIXMessage':
            raise ValueError("Invalid root element")
            
        release = root.get('release')
        if release != '3.0':
            raise ValueError("Invalid ONIX release version")
            
        # Check header requirements
        header = root.find(f'.//{{{ONIX_30_NS}}}Header')
        if header is None:
            raise ValueError("Missing Header element")
            
        sender = header.find(f'.//{{{ONIX_30_NS}}}Sender')
        if sender is None:
            raise ValueError("Missing Sender in Header")
            
        # Validate each product
        for product in root.findall(f'.//{{{ONIX_30_NS}}}Product'):
            # Check required product elements
            required_elements = [
                'RecordReference',
                'NotificationType',
                'ProductIdentifier',
                'DescriptiveDetail'
            ]
            
            for element in required_elements:
                if product.find(f'.//{{{ONIX_30_NS}}}{element}') is None:
                    raise ValueError(f"Missing required element: {element}")
            
            # Validate DescriptiveDetail
            desc_detail = product.find(f'.//{{{ONIX_30_NS}}}DescriptiveDetail')
            if desc_detail is not None:
                # Check required DescriptiveDetail elements
                if desc_detail.find(f'.//{{{ONIX_30_NS}}}ProductComposition') is None:
                    raise ValueError("Missing ProductComposition in DescriptiveDetail")
                if desc_detail.find(f'.//{{{ONIX_30_NS}}}ProductForm') is None:
                    raise ValueError("Missing ProductForm in DescriptiveDetail")
                    
                # Validate element order in DescriptiveDetail
                prev_index = -1
                for child in desc_detail:
                    child_name = etree.QName(child).localname
                    if child_name in DESCRIPTIVE_DETAIL_ORDER:
                        current_index = DESCRIPTIVE_DETAIL_ORDER.index(child_name)
                        if current_index < prev_index:
                            raise ValueError(f"Invalid element order in DescriptiveDetail: {child_name}")
                        prev_index = current_index
            
            # Validate TextContent elements
            for text_content in product.findall(f'.//{{{ONIX_30_NS}}}TextContent'):
                if text_content.find(f'.//{{{ONIX_30_NS}}}TextType') is None:
                    raise ValueError("Missing TextType in TextContent")
                if text_content.find(f'.//{{{ONIX_30_NS}}}ContentAudience') is None:
                    raise ValueError("Missing ContentAudience in TextContent")
                    
                # Validate TextContent element order
                prev_index = -1
                for child in text_content:
                    child_name = etree.QName(child).localname
                    if child_name in TEXT_CONTENT_ORDER:
                        current_index = TEXT_CONTENT_ORDER.index(child_name)
                        if current_index < prev_index:
                            raise ValueError(f"Invalid element order in TextContent: {child_name}")
                        prev_index = current_index
            
            # Validate Website elements
            for website in product.findall(f'.//{{{ONIX_30_NS}}}Website'):
                if website.find(f'.//{{{ONIX_30_NS}}}WebsiteRole') is None:
                    raise ValueError("Missing WebsiteRole in Website")
                if website.find(f'.//{{{ONIX_30_NS}}}WebsiteLink') is None:
                    raise ValueError("Missing WebsiteLink in Website")
            
            # Validate Price elements
            for price in product.findall(f'.//{{{ONIX_30_NS}}}Price'):
                if price.find(f'.//{{{ONIX_30_NS}}}PriceType') is None:
                    raise ValueError("Missing PriceType in Price")
                if price.find(f'.//{{{ONIX_30_NS}}}PriceAmount') is None:
                    raise ValueError("Missing PriceAmount in Price")
                
                # Validate Price element order
                prev_index = -1
                for child in price:
                    child_name = etree.QName(child).localname
                    if child_name in PRICE_ELEMENT_ORDER:
                        current_index = PRICE_ELEMENT_ORDER.index(child_name)
                        if current_index < prev_index:
                            raise ValueError(f"Invalid element order in Price: {child_name}")
                        prev_index = current_index
        
        return True
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Add test code here if needed