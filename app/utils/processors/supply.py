"""Supply detail processing module"""
import logging
from lxml import etree
from ..onix_constants import DEFAULT_SUPPLIER_ROLE
from ..onix_utils import validate_price

logger = logging.getLogger(__name__)

def process_product_supply(new_product, old_product, publisher_data=None):
    """Process product supply section"""
    product_supply = etree.SubElement(new_product, 'ProductSupply')
    
    process_market(product_supply, old_product)
    process_supply_detail(product_supply, old_product, publisher_data)
    
    return product_supply

[Rest of the supply.py file with all the processing functions]