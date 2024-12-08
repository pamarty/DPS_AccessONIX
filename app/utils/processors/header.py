"""Header processing module"""
import logging
from datetime import datetime
from lxml import etree

logger = logging.getLogger(__name__)

def process_header(root, new_root, original_version, publisher_data=None):
    """Process header elements"""
    header = etree.SubElement(new_root, 'Header')
    
    # Sender info
    sender = etree.SubElement(header, 'Sender')
    
    if publisher_data and publisher_data.get('sender_name'):
        name_elem = etree.SubElement(sender, 'SenderName')
        name_elem.text = publisher_data['sender_name']
    else:
        from_company = root.xpath('.//*[local-name() = "FromCompany"]/text()')
        if from_company:
            name_elem = etree.SubElement(sender, 'SenderName')
            name_elem.text = from_company[0]
        else:
            from_company = root.xpath('.//*[local-name() = "RecordSourceName"]/text()')
            name_elem = etree.SubElement(sender, 'SenderName')
            name_elem.text = from_company[0] if from_company else "Default Company Name"

    if publisher_data and publisher_data.get('contact_name'):
        contact_elem = etree.SubElement(sender, 'ContactName')
        contact_elem.text = publisher_data['contact_name']
    else:
        contact_name = root.xpath('.//*[local-name() = "ContactName"]/text()')
        if contact_name:
            contact_elem = etree.SubElement(sender, 'ContactName')
            contact_elem.text = contact_name[0]

    if publisher_data and publisher_data.get('email'):
        email_elem = etree.SubElement(sender, 'EmailAddress')
        email_elem.text = publisher_data['email']
    else:
        email = root.xpath('.//*[local-name() = "EmailAddress"]/text()')
        if email:
            email_elem = etree.SubElement(sender, 'EmailAddress')
            email_elem.text = email[0]

    sent_date_time = etree.SubElement(header, 'SentDateTime')
    sent_date_time.text = datetime.now().strftime("%Y%m%dT%H%M%S")

    message_note = root.xpath('.//*[local-name() = "MessageNote"]/text()')
    note_elem = etree.SubElement(header, 'MessageNote')
    note_elem.text = message_note[0] if message_note else f"This file was remediated to include accessibility information. Original ONIX version: {original_version}"