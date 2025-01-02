"""XML building utilities for ONIX generation"""
from lxml import etree

def create_onix_root():
    """Create the root ONIX message element"""
    root = etree.Element('ONIXMessage', 
                        nsmap={None: "http://ns.editeur.org/onix/3.0/reference"})
    root.set('release', '3.0')
    return root

def add_element(parent, name, text=None):
    """Add a child element with optional text content"""
    element = etree.SubElement(parent, name)
    if text is not None:
        element.text = str(text)
    return element

def add_identifier(parent, id_type, id_value):
    """Add a product identifier"""
    identifier = add_element(parent, 'ProductIdentifier')
    add_element(identifier, 'ProductIDType', id_type)
    add_element(identifier, 'IDValue', id_value)
    return identifier

def serialize_xml(root):
    """Serialize XML to string with proper formatting"""
    return etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding='utf-8'
    )