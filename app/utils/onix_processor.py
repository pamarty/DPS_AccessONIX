"""Main ONIX processing module"""
import logging
from datetime import datetime
from .xml_builder import (
    create_onix_root,
    add_element,
    add_identifier,
    serialize_xml
)

logger = logging.getLogger(__name__)

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
    """Process ONIX content"""
    try:
        # Create root element
        root = create_onix_root()

        # Add header
        header = add_element(root, 'Header')
        sender = add_element(header, 'Sender')
        
        if publisher_data:
            if publisher_data.get('sender_name'):
                add_element(sender, 'SenderName', publisher_data['sender_name'])
            if publisher_data.get('contact_name'):
                add_element(sender, 'ContactName', publisher_data['contact_name'])
            if publisher_data.get('email'):
                add_element(sender, 'EmailAddress', publisher_data['email'])
        else:
            add_element(sender, 'SenderName', "Default Sender")
            
        add_element(header, 'SentDateTime', 
                   datetime.now().strftime("%Y%m%dT%H%M%S"))
        add_element(header, 'MessageNote', 
                   "This file was remediated to include accessibility information")

        # Add product
        product = add_element(root, 'Product')
        add_element(product, 'RecordReference', epub_isbn)
        add_element(product, 'NotificationType', '03')
        
        # Add ISBN identifier
        add_identifier(product, '15', epub_isbn)
        
        # Process main sections
        process_descriptive_detail(product, epub_features, publisher_data)
        process_collateral_detail(product)
        process_publishing_detail(product, publisher_data)
        process_product_supply(product, publisher_data)

        # Return serialized XML
        return serialize_xml(root)

    except Exception as e:
        logger.error(f"Error processing ONIX: {str(e)}")
        raise