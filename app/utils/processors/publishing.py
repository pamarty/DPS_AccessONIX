"""Publishing detail processing module"""
import logging
from lxml import etree
from ..onix_constants import DEFAULT_PUBLISHER_ROLE
from ..onix_utils import format_date

logger = logging.getLogger(__name__)

def process_publishing_detail(new_product, old_product):
    """Process publishing detail section"""
    publishing_detail = etree.SubElement(new_product, 'PublishingDetail')

    # Publisher
    publisher = etree.SubElement(publishing_detail, 'Publisher')
    pub_role = etree.SubElement(publisher, 'PublishingRole')
    pub_role.text = DEFAULT_PUBLISHER_ROLE

    pub_name = old_product.xpath('.//*[local-name() = "PublisherName"]/text()')
    if pub_name:
        pub_name_elem = etree.SubElement(publisher, 'PublisherName')
        pub_name_elem.text = pub_name[0]

    # Publishing Status
    status = old_product.xpath('.//*[local-name() = "PublishingStatus"]/text()')
    if status:
        status_elem = etree.SubElement(publishing_detail, 'PublishingStatus')
        status_elem.text = status[0]

    # Publication Date
    pub_date = old_product.xpath('.//*[local-name() = "PublicationDate"]/text()')
    if pub_date:
        publishing_date = etree.SubElement(publishing_detail, 'PublishingDate')
        etree.SubElement(publishing_date, 'PublishingDateRole').text = '01'
        etree.SubElement(publishing_date, 'Date').text = format_date(pub_date[0])

    return publishing_detail