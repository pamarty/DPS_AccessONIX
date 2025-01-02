"""Descriptive detail processing module"""
import logging
from ..xml_builder import add_element

logger = logging.getLogger(__name__)

def process_descriptive_detail(product, epub_features, publisher_data=None):
    """Process descriptive detail section"""
    detail = add_element(product, 'DescriptiveDetail')
    
    # Add product composition
    composition = publisher_data.get('product_composition', '00')
    add_element(detail, 'ProductComposition', composition)
    
    # Add product form
    form = publisher_data.get('product_form', 'EB')
    add_element(detail, 'ProductForm', form)
    
    # Add accessibility features
    for code, is_present in epub_features.items():
        if is_present:
            feature = add_element(detail, 'ProductFormFeature')
            add_element(feature, 'ProductFormFeatureType', '09')
            add_element(feature, 'ProductFormFeatureValue', code)
    
    return detail