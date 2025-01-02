"""Product processing module"""
import logging
from lxml import etree
from ..onix_constants import DEFAULT_NOTIFICATION_TYPE
from .descriptive import process_descriptive_detail
from .collateral import process_collateral_detail
from .publishing import process_publishing_detail
from .supply import process_product_supply

logger = logging.getLogger(__name__)

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
    notify_element.text = notify_type[0] if notify_type else DEFAULT_NOTIFICATION_TYPE

    # Record Source Type and Name if present
    source_type = old_product.xpath('.//*[local-name() = "RecordSourceType"]/text()')
    if source_type:
        type_elem = etree.SubElement(new_product, 'RecordSourceType')
        type_elem.text = source_type[0]
        
    source_name = old_product.xpath('.//*[local-name() = "RecordSourceName"]/text()')
    if source_name:
        name_elem = etree.SubElement(new_product, 'RecordSourceName')
        name_elem.text = source_name[0]

    # Process identifiers without duplicates
    process_identifiers(new_product, old_product, epub_isbn)

    # Process barcode if present
    barcode = old_product.xpath('.//*[local-name() = "Barcode"]/text()')
    if barcode:
        barcode_elem = etree.SubElement(new_product, 'Barcode')
        barcode_elem.text = barcode[0]

    # Process main sections with publisher data
    descriptive_detail = process_descriptive_detail(new_product, old_product, epub_features, publisher_data)
    collateral_detail = process_collateral_detail(new_product, old_product)
    publishing_detail = process_publishing_detail(new_product, old_product, publisher_data)
    process_product_supply(new_product, old_product, publisher_data)

    # Process any remaining elements that should be within Product
    process_remaining_elements(new_product, old_product)

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

def process_remaining_elements(new_product, old_product):
    """Process any remaining elements that should be within Product"""
    # List of elements that should be processed within Product
    product_elements = [
        'RelatedProduct',
        'MediaFile',
        'ProductWebsite',
        'Imprint',
        'CityOfPublication',
        'CountryOfPublication',
        'PublicationDate',
        'CopyrightYear',
        'SalesRights',
        'Measure',
        'PromotionCampaign'
    ]
    
    for element_name in product_elements:
        for element in old_product.xpath(f'.//*[local-name() = "{element_name}"]'):
            # Deep copy the element and its children
            new_elem = etree.fromstring(etree.tostring(element))
            new_product.append(new_elem)