"""Main ONIX processing module with corrected element ordering and validation fixes"""
import logging
import traceback
import copy  # Add this at the top with other imports
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
    'Collection',
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
    'Language',
    'Extent',
    'Illustrations',
    'AncillaryContent',  # Moved before Subject
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

# Update the PRICE_ELEMENT_ORDER constant
PRICE_ELEMENT_ORDER = [
    'PriceType',
    'PriceAmount', 
    'CurrencyCode',
    'Territory',  # Territory must come before tax elements
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

def get_resource_mode(content_type):
    """
    Map content types to appropriate resource modes
    01 = website -> mode 04 (interactive)
    04 = front cover -> mode 03 (image)
    08 = product image -> mode 03 (image)
    """
    mode_mapping = {
        '01': '04',  # websites are interactive
        '04': '03',  # front cover is an image
        '08': '03',  # product image is an image
    }
    return mode_mapping.get(content_type, '03')  # default to '03' if not found

def convert_onix2_to_onix3(root):
    """Convert ONIX 2.1 XML to ONIX 3.0"""
    new_root = etree.Element("ONIXMessage", xmlns="http://ns.editeur.org/onix/3.0/reference", release="3.0")
    
    # Convert Header
    header = convert_header(root.find('Header'))
    new_root.append(header)
    
    # Convert each Product
    for product in root.findall('Product'):
        new_product = etree.SubElement(new_root, 'Product')
        
        # Convert basic elements
        for tag in ['RecordReference', 'NotificationType', 'RecordSourceType', 'RecordSourceName']:
            elem = product.find(tag)
            if elem is not None and elem.text:
                new_elem = etree.SubElement(new_product, tag)
                new_elem.text = elem.text
        
        # Convert ProductIdentifier elements
        for pid in product.findall('ProductIdentifier'):
            new_product.append(convert_product_identifier(pid))
            
        # Create DescriptiveDetail
        descriptive_detail = create_descriptive_detail(product)
        new_product.append(descriptive_detail)
        
        # Create CollateralDetail
        collateral_detail = create_collateral_detail(product)
        new_product.append(collateral_detail)
        
        # Create PublishingDetail
        publishing_detail = create_publishing_detail(product)
        new_product.append(publishing_detail)
        
        # Create RelatedMaterial
        related_material = create_related_material(product)
        new_product.append(related_material)
        
        # Create ProductSupply
        product_supply = create_product_supply(product)
        new_product.append(product_supply)
    
    return new_root


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
    # Add debug logging
    print("DEBUG: Processing header with publisher data:", publisher_data)
    
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
        if publisher_data.get('email'):  # Changed from email_address to email to match the data
            email = etree.SubElement(sender, 'EmailAddress')
            email.text = publisher_data['email']
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
    # If no price element was provided, create a default one
    if price_element is None:
        price_element = etree.Element('Price')
        # Add minimum required elements
        price_type = etree.SubElement(price_element, 'PriceTypeCode')
        price_type.text = '01'  # Default to RRP excluding tax
        price_amount = etree.SubElement(price_element, 'PriceAmount')
        price_amount.text = '0.00'  # Default to zero price
        currency = etree.SubElement(price_element, 'CurrencyCode')
        currency.text = 'USD'  # Default to USD
    
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
    new_contributor = etree.Element('Contributor')
    
    # Define the correct order of elements for ONIX 3.0
    element_order = [
        'SequenceNumber',
        'ContributorRole',
        'PersonName',
        'PersonNameInverted', 
        'NamesBeforeKey',
        'KeyNames',
        'BiographicalNote',
        'Website'
    ]
    
    # Create a temporary dictionary to store elements
    elements = {}
    
    # Process each child element
    for child in old_contributor:
        if child.tag == 'Website':
            website = etree.Element('Website')
            for web_child in child:
                if web_child.tag == 'WebsiteRole':
                    role = etree.SubElement(website, 'WebsiteRole')
                    role.text = web_child.text
                elif web_child.tag == 'WebsiteLink':
                    link = etree.SubElement(website, 'WebsiteLink')
                    link.text = web_child.text
            elements['Website'] = website
        elif child.tag not in ['PersonNameIdentifier', 'NameIdentifier', 'CountryCode']:  # Skip invalid elements
            if child.text:  # Only create element if there's content
                new_child = etree.Element(child.tag)
                new_child.text = child.text
                elements[child.tag] = new_child
    
    # Add elements in the correct order
    for tag in element_order:
        if tag in elements:
            new_contributor.append(elements[tag])
    
    return new_contributor

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
    
    # Get title from old product
    old_title = old_product.find('Title')
    if old_title is not None:
        # Add TitleText
        title_text = old_title.find('TitleText')
        if title_text is not None and title_text.text:
            new_title_text = etree.SubElement(title_element, 'TitleText')
            new_title_text.text = title_text.text
        
        # Add Subtitle if present
        subtitle = old_title.find('Subtitle')
        if subtitle is not None and subtitle.text:
            new_subtitle = etree.SubElement(title_element, 'Subtitle')
            new_subtitle.text = subtitle.text
    else:
        # Fallback to TitleText directly under Product
        title_text = old_product.find('TitleText')
        if title_text is not None and title_text.text:
            new_title_text = etree.SubElement(title_element, 'TitleText')
            new_title_text.text = title_text.text
    
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

def convert_header(old_header):
    """Convert Header from ONIX 2.1 to 3.0"""
    header = etree.Element('Header')
    
    if old_header is not None:
        # Convert sender information
        sender = old_header.find('FromCompany')
        if sender is not None:
            new_sender = etree.SubElement(header, 'Sender')
            company = etree.SubElement(new_sender, 'SenderName')
            company.text = sender.text
            
            # Add contact name if present
            contact = old_header.find('FromPerson')
            if contact is not None:
                contact_name = etree.SubElement(new_sender, 'ContactName')
                contact_name.text = contact.text
                
            # Add email if present
            email = old_header.find('FromEmail')
            if email is not None:
                email_addr = etree.SubElement(new_sender, 'EmailAddress')
                email_addr.text = email.text
                
        # Convert sent date
        sent_date = old_header.find('SentDate')
        if sent_date is not None:
            new_date = etree.SubElement(header, 'SentDateTime')
            new_date.text = sent_date.text + 'T000000'
            
    return header

def convert_product_identifier(old_identifier, existing_identifiers=None):
    """Convert ProductIdentifier from ONIX 2.1 to 3.0"""
    if existing_identifiers is None:
        existing_identifiers = set()
        
    identifier = etree.Element('ProductIdentifier')
    
    # Copy ID type
    id_type = old_identifier.find('ProductIDType')
    id_value = old_identifier.find('IDValue')
    
    if id_type is not None and id_value is not None:
        # Create identifier key for deduplication
        identifier_key = (id_type.text, id_value.text)
        
        # Skip if this identifier combination already exists
        if identifier_key in existing_identifiers:
            return None
            
        # Add to tracking set
        existing_identifiers.add(identifier_key)
        
        # Create new identifier elements
        new_type = etree.SubElement(identifier, 'ProductIDType')
        new_type.text = id_type.text
        
        new_value = etree.SubElement(identifier, 'IDValue')
        new_value.text = id_value.text
        
        return identifier
    
    return None

def create_descriptive_detail(old_product, epub_features, publisher_data=None):
    """Create DescriptiveDetail composite with proper element order"""
    descriptive_detail = etree.Element('DescriptiveDetail')
    
    # 1. ProductComposition
    composition = etree.SubElement(descriptive_detail, 'ProductComposition')
    composition.text = publisher_data.get('product_composition', '00') if publisher_data else '00'
    
    # 2. ProductForm 
    form = etree.SubElement(descriptive_detail, 'ProductForm')
    old_form = old_product.find('ProductForm')
    form.text = old_form.text if old_form is not None else 'BC'
    
    # 3. ProductFormDetail
    old_form_detail = old_product.find('ProductFormDetail')
    if old_form_detail is not None:
        form_detail = etree.SubElement(descriptive_detail, 'ProductFormDetail')
        form_detail.text = old_form_detail.text
    
    # 4. ProductFormFeature
    for old_feature in old_product.findall('ProductFormFeature'):
        feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
        for child in old_feature:
            etree.SubElement(feature, child.tag).text = child.text
            
    # 5. Add accessibility features
    if epub_features:
        process_accessibility_features(descriptive_detail, epub_features)
    
    # 6. ProductPackaging
    packaging = etree.SubElement(descriptive_detail, 'ProductPackaging')
    packaging.text = '00'
    
    # 7. ProductFormDescription
    desc = etree.SubElement(descriptive_detail, 'ProductFormDescription')
    desc.text = 'Trade paperback'
    
    # 8. TradeCategory
    trade = etree.SubElement(descriptive_detail, 'TradeCategory')
    trade.text = '01'
    
    # 9. PrimaryContentType
    primary = etree.SubElement(descriptive_detail, 'PrimaryContentType')
    primary.text = '10'
    
    # 10. Measure
    measure = etree.SubElement(descriptive_detail, 'Measure')
    measure_type = etree.SubElement(measure, 'MeasureType')
    measure_type.text = '01'
    measurement = etree.SubElement(measure, 'Measurement')
    measurement.text = '210'
    measure_unit = etree.SubElement(measure, 'MeasureUnitCode')
    measure_unit.text = 'mm'
    
    # 11. CountryOfManufacture
    country = etree.SubElement(descriptive_detail, 'CountryOfManufacture')
    country.text = 'CA'
    
    # 12. EpubTechnicalProtection
    protection = etree.SubElement(descriptive_detail, 'EpubTechnicalProtection')
    protection.text = '00'
    
    # 13. EpubUsageConstraint
    constraint = etree.SubElement(descriptive_detail, 'EpubUsageConstraint')
    constraint_type = etree.SubElement(constraint, 'EpubUsageType')
    constraint_type.text = '01'
    constraint_status = etree.SubElement(constraint, 'EpubUsageStatus')
    constraint_status.text = '01'
    
    # 14. EpubLicense
    license = etree.SubElement(descriptive_detail, 'EpubLicense')
    license_name = etree.SubElement(license, 'EpubLicenseName')
    license_name.text = 'Standard license'
    
    # 15. MapScale
    scale = etree.SubElement(descriptive_detail, 'MapScale')
    scale.text = '1000000'
    
    # 16. TitleDetail
    title_detail = create_title_element(old_product)
    if title_detail is not None:
        descriptive_detail.append(title_detail)
    
    # 17. Contributors (moved here after TitleDetail)
    for contributor in old_product.findall('Contributor'):
        new_contributor = create_contributor(descriptive_detail, contributor)
        descriptive_detail.append(new_contributor)
    
    # 18. NoEdition
    if not old_product.find('Edition'):
        etree.SubElement(descriptive_detail, 'NoEdition')
    
    # 19. Language
    old_language = old_product.find('Language')
    if old_language is not None:
        language = etree.SubElement(descriptive_detail, 'Language')
        language_role = etree.SubElement(language, 'LanguageRole')
        language_role.text = '01'
        language_code = etree.SubElement(language, 'LanguageCode')
        language_code.text = 'eng'
    
    # 20. Extent
    old_extent = old_product.find('Extent')
    if old_extent is not None:
        extent = etree.SubElement(descriptive_detail, 'Extent')
        extent_type = etree.SubElement(extent, 'ExtentType')
        extent_type.text = old_extent.findtext('ExtentType', '02')
        extent_value = etree.SubElement(extent, 'ExtentValue')
        extent_value.text = old_product.findtext('NumberOfPages', '320')
        extent_unit = etree.SubElement(extent, 'ExtentUnit')
        extent_unit.text = '03'
    
    # 21. Convert Illustrations to AncillaryContent
    illustrations = old_product.findall('.//Illustrations')
    for illustration in illustrations:
        illus_type = illustration.find('IllustrationType')
        illus_number = illustration.find('Number')
        illus_desc = illustration.find('IllustrationTypeDescription')
        
        ancillary = etree.SubElement(descriptive_detail, 'AncillaryContent')
        
        content_type = etree.SubElement(ancillary, 'AncillaryContentType')
        if illus_type is not None:
            if illus_type.text == '01':
                content_type.text = '01'  # Black and white illustrations
            elif illus_type.text == '02':
                content_type.text = '02'  # Color illustrations
            else:
                content_type.text = '00'  # Unspecified
        else:
            content_type.text = '00'
            
        if illus_number is not None:
            number = etree.SubElement(ancillary, 'Number')
            number.text = illus_number.text
            
        if illus_desc is not None:
            description = etree.SubElement(ancillary, 'AncillaryContentDescription')
            description.text = illus_desc.text
    
    # 22. Subject
    for subject in old_product.findall('Subject'):
        descriptive_detail.append(copy.deepcopy(subject))
    
    # 23. AudienceCode
    audience = etree.SubElement(descriptive_detail, 'AudienceCode')
    audience.text = '01'
    
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
        # Check URL before creating resource
        link = media_element.find('MediaFileLink')
        url = link.text if link is not None else None
            
        resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        # Add ResourceContentType first
        type_code = media_element.find('MediaFileTypeCode')
        if type_code is not None:
            # 1. ResourceContentType must be first
            content_type = etree.SubElement(resource, 'ResourceContentType')
            content_type.text = type_code.text
        else:
            # Default content type if none provided
            content_type = etree.SubElement(resource, 'ResourceContentType')
            content_type.text = '01'  # Default to website
            
        # 2. ContentAudience must come second
        content_audience = etree.SubElement(resource, 'ContentAudience')
        content_audience.text = '00'  # Unrestricted
            
        # 3. ResourceMode comes third
        resource_mode = etree.SubElement(resource, 'ResourceMode')
        resource_mode.text = get_resource_mode(type_code.text if type_code is not None else '01')
        
        # 4. ResourceVersion comes last
        version = etree.SubElement(resource, 'ResourceVersion')
        resource_form = etree.SubElement(version, 'ResourceForm')
        resource_form.text = '01'
        
        # Add version feature and link
        link_type = media_element.find('MediaFileLinkTypeCode')
        
        if link_type is not None:
            feature = etree.SubElement(version, 'ResourceVersionFeature')
            feature_type = etree.SubElement(feature, 'ResourceVersionFeatureType')
            feature_type.text = link_type.text
            
        if url:
            resource_link = etree.SubElement(version, 'ResourceLink')
            resource_link.text = url
            
        # Add content date if present
        date = media_element.find('MediaFileDate')
        if date is not None:
            content_date = etree.SubElement(version, 'ContentDate')
            date_role = etree.SubElement(content_date, 'ContentDateRole')
            date_role.text = '17'  # Last updated
            date_value = etree.SubElement(content_date, 'Date')
            date_value.text = date.text
    
    # Process ProductWebsite elements into SupportingResource
    for website in old_product.findall('ProductWebsite'):
        # Check URL before creating resource
        link = website.find('ProductWebsiteLink')
        url = link.text if link is not None else None
            
        resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        # Add required elements in correct order
        # 1. ResourceContentType must be first
        content_type = etree.SubElement(resource, 'ResourceContentType')
        content_type.text = '01'  # Website
        
        # 2. ContentAudience must come second
        content_audience = etree.SubElement(resource, 'ContentAudience')
        content_audience.text = '00'  # Unrestricted
        
        # 3. ResourceMode comes third
        resource_mode = etree.SubElement(resource, 'ResourceMode')
        resource_mode.text = '04'  # Interactive
        
        # 4. ResourceVersion comes last
        version = etree.SubElement(resource, 'ResourceVersion')
        resource_form = etree.SubElement(version, 'ResourceForm')
        resource_form.text = '01'
        
        # Add feature type if present
        feature = etree.SubElement(version, 'ResourceVersionFeature')
        feature_type = etree.SubElement(feature, 'ResourceVersionFeatureType')
        feature_type.text = '02'  # Link
        
        # Add website link
        if url:
            resource_link = etree.SubElement(version, 'ResourceLink')
            resource_link.text = url
    
    return collateral_detail

def create_publishing_detail(old_product):
    """Create PublishingDetail composite with correct element order"""
    publishing_detail = etree.Element('PublishingDetail')
    
    # 1. Imprint (MUST BE FIRST)
    imprint = old_product.find('Imprint')
    if imprint is not None:
        new_imprint = etree.SubElement(publishing_detail, 'Imprint')
        imprint_name = etree.SubElement(new_imprint, 'ImprintName')
        imprint_name.text = imprint.findtext('ImprintName')

    # 2. Publisher with Website
    publisher = old_product.find('Publisher')
    if publisher is not None:
        new_publisher = etree.SubElement(publishing_detail, 'Publisher')
        
        # Add PublishingRole first
        pub_role = etree.SubElement(new_publisher, 'PublishingRole')
        pub_role.text = publisher.findtext('PublishingRole', '01')
        
        # Add PublisherName
        pub_name = etree.SubElement(new_publisher, 'PublisherName')
        pub_name.text = publisher.findtext('PublisherName')
        
        # Add Website within Publisher
        website = etree.SubElement(new_publisher, 'Website')
        website_role = etree.SubElement(website, 'WebsiteRole')
        website_role.text = '01'
        website_link = etree.SubElement(website, 'WebsiteLink')
        website_link.text = 'http://www.dundurn.com'

    # 3. PublishingStatus
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
    
    # Add WorkIdentifier in RelatedWork
    work_identifier = old_product.find('WorkIdentifier')
    if work_identifier is not None:
        related_work = etree.SubElement(related_material, 'RelatedWork')
        work_relation = etree.SubElement(related_work, 'WorkRelationCode')
        work_relation.text = '01'  # Manifestation of
        new_work_id = etree.SubElement(related_work, 'WorkIdentifier')
        work_id_type = work_identifier.find('WorkIDType')
        id_value = work_identifier.find('IDValue')
        if work_id_type is not None:
            new_id_type = etree.SubElement(new_work_id, 'WorkIDType')
            new_id_type.text = work_id_type.text
        if id_value is not None:
            new_id_value = etree.SubElement(new_work_id, 'IDValue')
            new_id_value.text = id_value.text
    
    # Process related products
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
    has_price = False
    
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
            countries = old_supply.find('SupplyToCountry')
            if countries is not None:
                territory = create_supply_territory(countries.text)
                supply_detail.append(territory)
                
        elif element_name == 'Price':
            prices = old_supply.findall('Price')
            if prices:
                for price_element in prices:
                    price = create_price_composite(price_element)
                    supply_detail.append(price)
                    has_price = True
    
    # If no price elements were found, add UnpricedItemType
    if not has_price:
        unpriced = etree.SubElement(supply_detail, 'UnpricedItemType')
        unpriced.text = '01'  # Free of charge
    
    return supply_detail

def create_product_supply(old_product, publisher_data):
    """Create ProductSupply composite preserving existing data"""
    product_supply = etree.Element('ProductSupply')
    
    # Copy existing market information
    market = etree.SubElement(product_supply, 'Market')
    territory = etree.SubElement(market, 'Territory')
    
    # Get existing supply territories
    supply_countries = old_product.findall('.//SupplyToCountry')
    if supply_countries:
        countries = etree.SubElement(territory, 'CountriesIncluded')
        countries.text = ' '.join(country.text for country in supply_countries if country.text)
    else:
        regions = etree.SubElement(territory, 'RegionsIncluded')
        regions.text = 'WORLD'
    
    # Process existing supply details
    for old_supply in old_product.findall('SupplyDetail'):
        supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
        has_price = False
        
        # Copy supplier information
        supplier = etree.SubElement(supply_detail, 'Supplier')
        supplier_role = etree.SubElement(supplier, 'SupplierRole')
        supplier_role.text = old_supply.findtext('SupplierRole', '01')
        
        supplier_name = etree.SubElement(supplier, 'SupplierName')
        supplier_name.text = old_supply.findtext('SupplierName')
        
        # Copy returns conditions
        if old_supply.find('ReturnsCodeType') is not None:
            returns = etree.SubElement(supply_detail, 'ReturnsConditions')
            returns_type = etree.SubElement(returns, 'ReturnsCodeType')
            returns_type.text = old_supply.findtext('ReturnsCodeType')
            returns_code = etree.SubElement(returns, 'ReturnsCode')
            returns_code.text = old_supply.findtext('ReturnsCode')
        
        # Copy availability
        availability = etree.SubElement(supply_detail, 'ProductAvailability')
        availability.text = old_supply.findtext('ProductAvailability', '20')
        
        # Copy pack quantity
        if old_supply.find('PackQuantity') is not None:
            pack_qty = etree.SubElement(supply_detail, 'PackQuantity')
            pack_qty.text = old_supply.findtext('PackQuantity')
        
        # Add form prices if they exist, otherwise keep existing prices
        supplier_country = old_supply.findtext('SupplyToCountry')
        if supplier_country:
            if 'CA' in supplier_country and publisher_data and publisher_data.get('price_cad'):
                add_price(supply_detail, publisher_data['price_cad'], 'CAD', 'CA')
                has_price = True
            elif 'GB' in supplier_country and publisher_data and publisher_data.get('price_gbp'):
                add_price(supply_detail, publisher_data['price_gbp'], 'GBP', 'GB')
                has_price = True
            elif 'US' in supplier_country and publisher_data and publisher_data.get('price_usd'):
                add_price(supply_detail, publisher_data['price_usd'], 'USD', 'US')
                has_price = True
            else:
                # Copy existing prices
                for old_price in old_supply.findall('Price'):
                    copy_price(supply_detail, old_price)
                    has_price = True
        
        # If no price was added, add UnpricedItemType
        if not has_price:
            unpriced = etree.SubElement(supply_detail, 'UnpricedItemType')
            unpriced.text = '01'  # Free of charge
    
    return product_supply

def add_price(supply_detail, amount, currency, country):
    """Add a new price element"""
    price = etree.SubElement(supply_detail, 'Price')
    price_type = etree.SubElement(price, 'PriceType')
    price_type.text = '02'  # Suggested retail price
    
    price_amount = etree.SubElement(price, 'PriceAmount')
    price_amount.text = str(amount)
    
    currency_code = etree.SubElement(price, 'CurrencyCode')
    currency_code.text = currency
    
    territory = etree.SubElement(price, 'Territory')
    countries = etree.SubElement(territory, 'CountriesIncluded')
    countries.text = country

def copy_price(supply_detail, old_price):
    """Copy existing price element with proper ONIX 3.0 tag mapping"""
    price = etree.SubElement(supply_detail, 'Price')
    
    # Only include allowed elements in ONIX 3.0
    allowed_elements = {
        'PriceTypeCode': 'PriceType',
        'PriceAmount': 'PriceAmount',
        'CurrencyCode': 'CurrencyCode',
        'CountryCode': 'Territory'
    }
    
    # Process elements in correct order according to ONIX 3.0
    element_order = [
        'PriceType',
        'PriceAmount',
        'CurrencyCode',
        'Territory'  # Territory must come last
    ]
    
    # Process elements in correct order
    for element_name in element_order:
        # Handle special case for Territory
        if element_name == 'Territory':
            country_code = old_price.find('CountryCode')
            if country_code is not None:
                territory = etree.SubElement(price, 'Territory')
                countries = etree.SubElement(territory, 'CountriesIncluded')
                countries.text = country_code.text
            continue
            
        # Find old element using reverse mapping
        old_name = next((k for k, v in allowed_elements.items() if v == element_name), element_name)
        old_element = old_price.find(old_name)
        
        if old_element is not None and old_element.text:
            new_element = etree.SubElement(price, element_name)
            new_element.text = old_element.text

def process_product(old_product, new_root, epub_features, epub_isbn, publisher_data):
    """Process complete product composite"""
    try:
        # Create new product
        product = etree.SubElement(new_root, 'Product')
        
        # Add RecordReference first (REQUIRED)
        record_ref = old_product.find('RecordReference')
        if record_ref is not None:
            new_ref = etree.SubElement(product, 'RecordReference')
            new_ref.text = record_ref.text
            
        # Add NotificationType (REQUIRED)
        notif_type = old_product.find('NotificationType')
        if notif_type is not None:
            new_notif = etree.SubElement(product, 'NotificationType')
            new_notif.text = notif_type.text
            
        # Add RecordSourceType
        source_type = old_product.find('RecordSourceType')
        if source_type is not None:
            new_source_type = etree.SubElement(product, 'RecordSourceType')
            new_source_type.text = source_type.text
            
        # Add RecordSourceName
        source_name = old_product.find('RecordSourceName')
        if source_name is not None:
            new_source_name = etree.SubElement(product, 'RecordSourceName')
            new_source_name.text = source_name.text
            
        # Track existing identifiers
        existing_identifiers = set()
        
        # Copy product identifiers and validate them
        for identifier in old_product.findall('ProductIdentifier'):
            new_identifier = convert_product_identifier(identifier, existing_identifiers)
            if new_identifier is not None:
                product.append(new_identifier)
                
        # Validate identifiers after adding them
        validate_identifiers(product)
        
        # Handle WorkIdentifier first
        work_identifier = old_product.find('WorkIdentifier')
        if work_identifier is not None:
            work_id_type = work_identifier.find('WorkIDType')
            id_value = work_identifier.find('IDValue')
            if work_id_type is not None and id_value is not None:
                # Check if this identifier type/value combination already exists
                id_key = (work_id_type.text, id_value.text)
                if id_key not in existing_identifiers:
                    new_identifier = etree.SubElement(product, 'ProductIdentifier')
                    id_type = etree.SubElement(new_identifier, 'ProductIDType')
                    # Map WorkIDType to ProductIDType
                    if work_id_type.text == '15':  # ISBN-13
                        id_type.text = '15'
                    else:
                        id_type.text = '01'  # Proprietary
                    new_id_value = etree.SubElement(new_identifier, 'IDValue')
                    new_id_value.text = id_value.text
                    existing_identifiers.add(id_key)
        
        # Handle Barcode element properly - add it at Product level after ProductIdentifier elements
        old_barcode = old_product.find('Barcode')
        if old_barcode is not None:
            barcode = etree.SubElement(product, 'Barcode')
            barcode_type = etree.SubElement(barcode, 'BarcodeType')
            barcode_type.text = old_barcode.text
        
        # Create main blocks in correct order with publisher_data
        descriptive_detail = create_descriptive_detail(old_product, epub_features, publisher_data)
        if len(descriptive_detail) > 0:
            # Ensure this is an EPUB by setting ProductForm to EA
            product_form = descriptive_detail.find('ProductForm')
            if product_form is not None:
                product_form.text = 'EA'  # EA = EPUB
                
            # Add ProductFormDetail for EPUB3
            product_form_detail = descriptive_detail.find('ProductFormDetail')
            if product_form_detail is None:
                product_form_detail = etree.SubElement(descriptive_detail, 'ProductFormDetail')
            product_form_detail.text = 'E101'  # EPUB3
            
            # Ensure EPUB-specific elements exist
            if descriptive_detail.find('EpubTechnicalProtection') is None:
                epub_tech = etree.SubElement(descriptive_detail, 'EpubTechnicalProtection')
                epub_tech.text = '00'  # None
                
            if descriptive_detail.find('EpubUsageConstraint') is None:
                epub_usage = etree.SubElement(descriptive_detail, 'EpubUsageConstraint')
                usage_type = etree.SubElement(epub_usage, 'EpubUsageType')
                usage_type.text = '01'  # Preview
                usage_status = etree.SubElement(epub_usage, 'EpubUsageStatus')
                usage_status.text = '01'  # Permitted
                
            if descriptive_detail.find('EpubLicense') is None:
                epub_license = etree.SubElement(descriptive_detail, 'EpubLicense')
                license_name = etree.SubElement(epub_license, 'EpubLicenseName')
                license_name.text = 'Standard license'
            
            product.append(descriptive_detail)
        
        # Create CollateralDetail
        collateral_detail = create_collateral_detail(old_product)
        if len(collateral_detail) > 0:
            # Preserve product website in CollateralDetail
            website = old_product.find('ProductWebsite')
            if website is not None:
                # Create new supporting resource for website
                supporting_resource = etree.SubElement(collateral_detail, 'SupportingResource')
                
                # Add required elements in correct order
                content_type = etree.SubElement(supporting_resource, 'ResourceContentType')
                content_type.text = '01'  # Marketing
                
                content_audience = etree.SubElement(supporting_resource, 'ContentAudience')
                content_audience.text = '00'  # Unrestricted
                
                # Add ResourceMode (required before ResourceVersion)
                resource_mode = etree.SubElement(supporting_resource, 'ResourceMode')
                resource_mode.text = '04'  # Interactive
                
                # Add website role and link
                website_role = website.find('WebsiteRole')
                website_link = website.find('ProductWebsiteLink')
                if website_link is not None:
                    resource_version = etree.SubElement(supporting_resource, 'ResourceVersion')
                    resource_form = etree.SubElement(resource_version, 'ResourceForm')
                    resource_form.text = '01'  # Downloadable file
                    
                    if website_role is not None:
                        feature = etree.SubElement(resource_version, 'ResourceVersionFeature')
                        feature_type = etree.SubElement(feature, 'ResourceVersionFeatureType')
                        feature_type.text = website_role.text
                    
                    resource_link = etree.SubElement(resource_version, 'ResourceLink')
                    resource_link.text = website_link.text
            
            product.append(collateral_detail)
        
        # Add copyright year to PublishingDetail
        copyright_year = old_product.find('CopyrightYear')
        if copyright_year is not None:
            publishing_detail = product.find('PublishingDetail')
            if publishing_detail is not None:
                copyright = etree.SubElement(publishing_detail, 'CopyrightStatement')
                copyright_year_elem = etree.SubElement(copyright, 'CopyrightYear')
                copyright_year_elem.text = copyright_year.text
        
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

def validate_identifiers(product):
    """Validate product identifiers"""
    identifiers = product.findall('ProductIdentifier')
    
    # Check for required identifier types
    has_isbn13 = False
    has_isbn10 = False
    
    for identifier in identifiers:
        id_type = identifier.find('ProductIDType')
        if id_type is not None:
            if id_type.text == '15':  # ISBN-13
                has_isbn13 = True
            elif id_type.text == '02':  # ISBN-10 
                has_isbn10 = True
                
    if not (has_isbn13 or has_isbn10):
        raise ValueError("Product must have either ISBN-13 or ISBN-10")

def count_illustrations(old_product):
    """Count total illustrations from all sources"""
    total = 0
    
    # Count standard illustrations
    for illus in old_product.findall('Illustrations'):
        number = illus.find('Number')
        if number is not None and number.text:
            try:
                total += int(number.text)
            except ValueError:
                pass
                
    # Count figures from other sources
    for figure in old_product.findall('.//Figure'):
        total += 1
        
    return total

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

        # Add debug logging
        print("DEBUG: Publisher data received:", publisher_data)
    
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