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

def process_text_content(collateral_detail, old_product):
    """Process text content"""
    for old_text in old_product.xpath('.//*[local-name() = "OtherText"]'):
        text_content = etree.SubElement(collateral_detail, 'TextContent')
        
        text_type = old_text.xpath('.//*[local-name() = "TextTypeCode"]/text()')
        type_value = text_type[0] if text_type else "03"
        if type_value == "99":
            type_value = "03"  # Map unknown to description
        etree.SubElement(text_content, 'TextType').text = type_value
        
        etree.SubElement(text_content, 'ContentAudience').text = DEFAULT_CONTENT_AUDIENCE
        
        text = old_text.xpath('.//*[local-name() = "Text"]/text()')
        if text:
            text_elem = etree.SubElement(text_content, 'Text')
            text_elem.text = text[0]
            
            text_format = old_text.xpath('.//*[local-name() = "TextFormat"]/text()')
            if text_format:
                text_elem.set('textformat', text_format[0].lower())

def process_supporting_resources(collateral_detail, old_product):
    """Process supporting resources"""
    for old_resource in old_product.xpath('.//*[local-name() = "SupportingResource"]'):
        resource = etree.SubElement(collateral_detail, 'SupportingResource')
        
        # ResourceContentType
        content_type = old_resource.xpath('.//*[local-name() = "ResourceContentType"]/text()')
        if content_type:
            etree.SubElement(resource, 'ResourceContentType').text = content_type[0]
        
        # ResourceMode
        mode = old_resource.xpath('.//*[local-name() = "ResourceMode"]/text()')
        if mode:
            etree.SubElement(resource, 'ResourceMode').text = mode[0]
        
        # ResourceVersion
        process_resource_version(resource, old_resource)

def process_resource_version(resource, old_resource):
    """Process resource version information"""
    version = etree.SubElement(resource, 'ResourceVersion')
    
    # ResourceForm
    form = old_resource.xpath('.//*[local-name() = "ResourceForm"]/text()')
    if form:
        etree.SubElement(version, 'ResourceForm').text = form[0]
    
    # ResourceLink
    link = old_resource.xpath('.//*[local-name() = "ResourceLink"]/text()')
    if link:
        etree.SubElement(version, 'ResourceLink').text = link[0]
    
    # ContentDate
    date = old_resource.xpath('.//*[local-name() = "ContentDate"]/text()')
    if date:
        content_date = etree.SubElement(version, 'ContentDate')
        etree.SubElement(content_date, 'ContentDateRole').text = '01'
        etree.SubElement(content_date, 'Date').text = date[0]