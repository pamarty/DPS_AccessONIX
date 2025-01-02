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

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
    """Process ONIX content"""
    try:
        # Create new ONIX 3.0 document
        root = etree.Element('ONIXMessage', nsmap=NSMAP)
        root.set('release', '3.0')

        # Process header
        header = etree.SubElement(root, 'Header')
        sender = etree.SubElement(header, 'Sender')
        
        if publisher_data:
            if publisher_data.get('sender_name'):
                etree.SubElement(sender, 'SenderName').text = publisher_data['sender_name']
            if publisher_data.get('contact_name'):
                etree.SubElement(sender, 'ContactName').text = publisher_data['contact_name']
            if publisher_data.get('email'):
                etree.SubElement(sender, 'EmailAddress').text = publisher_data['email']
        else:
            etree.SubElement(sender, 'SenderName').text = "Default Sender"
            
        etree.SubElement(header, 'SentDateTime').text = datetime.now().strftime("%Y%m%dT%H%M%S")
        etree.SubElement(header, 'MessageNote').text = "This file was remediated to include accessibility information"

        # Process product
        product = etree.SubElement(root, 'Product')
        
        # Add required product elements
        etree.SubElement(product, 'RecordReference').text = epub_isbn
        etree.SubElement(product, 'NotificationType').text = '03'
        
        # Add product identifiers
        identifier = etree.SubElement(product, 'ProductIdentifier')
        etree.SubElement(identifier, 'ProductIDType').text = '15'
        etree.SubElement(identifier, 'IDValue').text = epub_isbn
        
        # Process main sections
        descriptive_detail = process_descriptive_detail(product, epub_features, publisher_data)
        collateral_detail = process_collateral_detail(product)
        publishing_detail = process_publishing_detail(product, publisher_data)
        product_supply = process_product_supply(product, publisher_data)

        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8')

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        logger.error(traceback.format_exc())
        raise