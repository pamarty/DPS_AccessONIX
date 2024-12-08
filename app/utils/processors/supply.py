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

def process_market(product_supply, old_product):
    """Process market information"""
    market = etree.SubElement(product_supply, 'Market')
    territory = etree.SubElement(market, 'Territory')
    
    # Ensure at least one territory element is present
    countries = old_product.xpath('.//*[local-name() = "CountriesIncluded"]/text()')
    regions = old_product.xpath('.//*[local-name() = "RegionsIncluded"]/text()')
    
    if countries:
        countries_elem = etree.SubElement(territory, 'CountriesIncluded')
        countries_elem.text = countries[0]
    elif regions:
        regions_elem = etree.SubElement(territory, 'RegionsIncluded')
        regions_elem.text = regions[0]
    else:
        # Default to WORLD if no territory information is provided
        regions_elem = etree.SubElement(territory, 'RegionsIncluded')
        regions_elem.text = 'WORLD'

def process_supply_detail(product_supply, old_product, publisher_data=None):
    """Process supply detail information"""
    supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
    
    # Supplier
    supplier = etree.SubElement(supply_detail, 'Supplier')
    etree.SubElement(supplier, 'SupplierRole').text = DEFAULT_SUPPLIER_ROLE
    
    supplier_name = old_product.xpath('.//*[local-name() = "SupplierName"]/text()')
    if supplier_name:
        name_elem = etree.SubElement(supplier, 'SupplierName')
        name_elem.text = supplier_name[0]
    
    # Product Availability
    availability = old_product.xpath('.//*[local-name() = "ProductAvailability"]/text()')
    if availability:
        avail_elem = etree.SubElement(supply_detail, 'ProductAvailability')
        avail_elem.text = availability[0]
    
    # Process prices
    process_prices(supply_detail, old_product, publisher_data)

def process_prices(supply_detail, old_product, publisher_data=None):
    """Process price information"""
    if publisher_data:
        if publisher_data.get('price_cad'):
            price = etree.SubElement(supply_detail, 'Price')
            etree.SubElement(price, 'PriceAmount').text = validate_price(publisher_data['price_cad'])
            etree.SubElement(price, 'CurrencyCode').text = 'CAD'
        
        if publisher_data.get('price_gbp'):
            price = etree.SubElement(supply_detail, 'Price')
            etree.SubElement(price, 'PriceAmount').text = validate_price(publisher_data['price_gbp'])
            etree.SubElement(price, 'CurrencyCode').text = 'GBP'
        
        if publisher_data.get('price_usd'):
            price = etree.SubElement(supply_detail, 'Price')
            etree.SubElement(price, 'PriceAmount').text = validate_price(publisher_data['price_usd'])
            etree.SubElement(price, 'CurrencyCode').text = 'USD'
    else:
        # Process existing prices if no publisher data
        for old_price in old_product.xpath('.//*[local-name() = "Price"]'):
            price = etree.SubElement(supply_detail, 'Price')
            
            price_amount = old_price.xpath('.//*[local-name() = "PriceAmount"]/text()')
            if price_amount:
                amount_elem = etree.SubElement(price, 'PriceAmount')
                amount_elem.text = validate_price(price_amount[0])
            
            currency = old_price.xpath('.//*[local-name() = "CurrencyCode"]/text()')
            if currency:
                currency_elem = etree.SubElement(price, 'CurrencyCode')
                currency_elem.text = currency[0]