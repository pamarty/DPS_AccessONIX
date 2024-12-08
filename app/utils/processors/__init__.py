"""ONIX processors package"""
from .header import process_header
from .product import process_product
from .descriptive import process_descriptive_detail
from .collateral import process_collateral_detail
from .publishing import process_publishing_detail
from .supply import process_product_supply

__all__ = [
    'process_header',
    'process_product',
    'process_descriptive_detail',
    'process_collateral_detail',
    'process_publishing_detail',
    'process_product_supply'
]