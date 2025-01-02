"""Product processing module"""
import logging
from lxml import etree
from ..onix_constants import DEFAULT_NOTIFICATION_TYPE

logger = logging.getLogger(__name__)

def process_product(product, epub_features, epub_isbn, publisher_data=None):
    """Process product elements"""
    # Record Reference
    etree.SubElement(product, 'RecordReference').text = epub_isbn

    # Notification Type
    etree.SubElement(product, 'NotificationType').text = DEFAULT_NOTIFICATION_TYPE

    # Process identifiers
    identifier = etree.SubElement(product, 'ProductIdentifier')
    etree.SubElement(identifier, 'ProductIDType').text = '15'
    etree.SubElement(identifier, 'IDValue').text = epub_isbn

    # Process descriptive detail
    descriptive_detail = etree.SubElement(product, 'DescriptiveDetail')
    process_descriptive_detail(descriptive_detail, epub_features, publisher_data)

    # Process collateral detail
    collateral_detail = etree.SubElement(product, 'CollateralDetail')
    process_collateral_detail(collateral_detail)

    # Process publishing detail
    publishing_detail = etree.SubElement(product, 'PublishingDetail')
    process_publishing_detail(publishing_detail, publisher_data)

    # Process product supply
    product_supply = etree.SubElement(product, 'ProductSupply')
    process_product_supply(product_supply, publisher_data)

    return product