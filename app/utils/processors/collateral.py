"""Collateral detail processing module"""
import logging
from lxml import etree
from ..onix_constants import DEFAULT_CONTENT_AUDIENCE

logger = logging.getLogger(__name__)

def process_collateral_detail(new_product, old_product):
    """Process collateral detail section"""
    collateral_detail = etree.SubElement(new_product, 'CollateralDetail')

    # Process text content
    process_text_content(collateral_detail, old_product)

    # Process supporting resources
    process_supporting_resources(collateral_detail, old_product)

    return collateral_detail

[Rest of the collateral.py file with all the processing functions]