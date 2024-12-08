"""Descriptive detail processing module"""
import logging
from lxml import etree
from ..onix_constants import (
    DEFAULT_PRODUCT_COMPOSITION,
    DEFAULT_PRODUCT_FORM,
    DEFAULT_PRODUCT_FORM_DETAIL,
    DEFAULT_LANGUAGE_CODE,
    DEFAULT_LANGUAGE_ROLE
)
from ..epub_analyzer import CODELIST_196

logger = logging.getLogger(__name__)

def process_descriptive_detail(new_product, old_product, epub_features, publisher_data=None):
    """Process descriptive detail section"""
    descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')

    # Required elements in correct order
    product_comp = etree.SubElement(descriptive_detail, 'ProductComposition')
    if publisher_data and publisher_data.get('product_composition'):
        product_comp.text = publisher_data['product_composition']
    else:
        product_comp.text = DEFAULT_PRODUCT_COMPOSITION
    
    product_form = etree.SubElement(descriptive_detail, 'ProductForm')
    if publisher_data and publisher_data.get('product_form'):
        product_form.text = publisher_data['product_form']
    else:
        old_form = old_product.xpath('.//*[local-name() = "ProductForm"]/text()')
        product_form.text = old_form[0] if old_form else DEFAULT_PRODUCT_FORM
    
    product_form_detail = etree.SubElement(descriptive_detail, 'ProductFormDetail')
    old_detail = old_product.xpath('.//*[local-name() = "ProductFormDetail"]/text()')
    product_form_detail.text = old_detail[0] if old_detail else DEFAULT_PRODUCT_FORM_DETAIL

    # Process existing product form features
    process_form_features(descriptive_detail, old_product, epub_features)

    # Process other elements
    process_titles(descriptive_detail, old_product)
    process_contributors(descriptive_detail, old_product)
    process_language(descriptive_detail, old_product, publisher_data)
    process_subjects(descriptive_detail, old_product)
    process_audience(descriptive_detail, old_product)
    process_extent(descriptive_detail, old_product)

    return descriptive_detail

[Rest of the descriptive.py file with all the processing functions]