import xml.etree.ElementTree as ET
from lxml import etree
import logging
from datetime import datetime
import traceback
from decimal import Decimal
from .epub_analyzer import CODELIST_196

logger = logging.getLogger(__name__)

ONIX_30_NS = "http://ns.editeur.org/onix/3.0/reference"
NSMAP = {None: ONIX_30_NS}

def process_onix(epub_features, xml_content, epub_isbn, publisher_data=None):
   try:
       parser = etree.XMLParser(recover=True)
       root = etree.fromstring(xml_content, parser=parser)
       logger.info(f"XML parsed successfully. Root tag: {root.tag}")

       new_root = etree.Element('ONIXMessage', nsmap=NSMAP)
       new_root.set("release", "3.0")

       new_header = etree.SubElement(new_root, 'Header')
       sender = etree.SubElement(new_header, 'Sender')
       
       if publisher_data and publisher_data.get('sender_name'):
           etree.SubElement(sender, 'SenderName').text = publisher_data.get('sender_name')
       else:
           from_company = root.xpath('.//*[local-name() = "FromCompany"]/text()')
           etree.SubElement(sender, 'SenderName').text = from_company[0] if from_company else "Default Company Name"

       if publisher_data and publisher_data.get('contact_name'):
           etree.SubElement(sender, 'ContactName').text = publisher_data.get('contact_name')
       else:
           contact_name = root.xpath('.//*[local-name() = "ContactName"]/text()')
           if contact_name:
               etree.SubElement(sender, 'ContactName').text = contact_name[0]

       if publisher_data and publisher_data.get('email'):
           etree.SubElement(sender, 'EmailAddress').text = publisher_data.get('email')
       else:
           email_address = root.xpath('.//*[local-name() = "EmailAddress"]/text()')
           if email_address:
               etree.SubElement(sender, 'EmailAddress').text = email_address[0]

       etree.SubElement(new_header, 'SentDateTime').text = datetime.now().strftime("%Y%m%dT%H%M%S")
       message_note = root.xpath('.//*[local-name() = "MessageNote"]/text()')
       etree.SubElement(new_header, 'MessageNote').text = message_note[0] if message_note else "Converted to ONIX 3.0"

       if root.tag.endswith('Product') or root.tag == 'Product':
           logger.info("Processing single Product element")
           process_single_product(root, new_root, epub_features, epub_isbn, publisher_data)
       else:
           products = root.xpath('.//*[local-name() = "Product"]')
           if products:
               logger.info(f"Processing {len(products)} Product elements")
               for old_product in products:
                   process_single_product(old_product, new_root, epub_features, epub_isbn, publisher_data)
           else:
               logger.info("No Product elements found, creating new one")
               create_new_product(new_root, epub_features, epub_isbn, publisher_data)

       return etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8')

   except Exception as e:
       logger.error(f"Error processing ONIX: {str(e)}")
       logger.error(traceback.format_exc())
       raise
def process_single_product(old_product, new_root, epub_features, epub_isbn, publisher_data):
   if publisher_data is None:
       publisher_data = {}

   new_product = etree.SubElement(new_root, "Product")
   
   record_ref = old_product.xpath('.//*[local-name() = "RecordReference"]/text()')
   etree.SubElement(new_product, 'RecordReference').text = record_ref[0] if record_ref else f"EPUB_{epub_isbn}"
   etree.SubElement(new_product, 'NotificationType').text = '03'
   
   # Product Identifiers
   for identifier in old_product.xpath('.//*[local-name() = "ProductIdentifier"]'):
       new_identifier = etree.SubElement(new_product, 'ProductIdentifier')
       id_type = identifier.xpath('.//*[local-name() = "ProductIDType"]/text()')
       if id_type:
           etree.SubElement(new_identifier, 'ProductIDType').text = id_type[0]
           id_value = etree.SubElement(new_identifier, 'IDValue')
           if id_type[0] in ["03", "15"]:  # ISBN-13
               id_value.text = epub_isbn
           else:
               old_value = identifier.xpath('.//*[local-name() = "IDValue"]/text()')
               id_value.text = old_value[0] if old_value else ''

   # DescriptiveDetail
   descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')
   etree.SubElement(descriptive_detail, 'ProductComposition').text = publisher_data.get('product_composition', '00')
   etree.SubElement(descriptive_detail, 'ProductForm').text = publisher_data.get('product_form', 'EB')
   etree.SubElement(descriptive_detail, 'ProductFormDetail').text = 'E101'

   # Accessibility features
   for code, is_present in epub_features.items():
       if is_present and code in CODELIST_196:
           feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
           etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
           etree.SubElement(feature, 'ProductFormFeatureValue').text = code
           etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]

   # Process titles
   for old_title in old_product.xpath('.//*[local-name() = "Title"]'):
       title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
       etree.SubElement(title_detail, 'TitleType').text = '01'
       
       title_element = etree.SubElement(title_detail, 'TitleElement')
       etree.SubElement(title_element, 'TitleElementLevel').text = '01'
       
       title_text = old_title.xpath('.//*[local-name() = "TitleText"]/text()')
       if title_text:
           etree.SubElement(title_element, 'TitleText').text = title_text[0]
       
       subtitle = old_title.xpath('.//*[local-name() = "Subtitle"]/text()')
       if subtitle:
           etree.SubElement(title_element, 'Subtitle').text = subtitle[0]

   # Contributors
   for old_contributor in old_product.xpath('.//*[local-name() = "Contributor"]'):
       new_contrib = etree.SubElement(descriptive_detail, 'Contributor')
       role = old_contributor.xpath('.//*[local-name() = "ContributorRole"]/text()')
       if role:
           etree.SubElement(new_contrib, 'ContributorRole').text = role[0]
       
       for name_type in ['PersonName', 'PersonNameInverted', 'CorporateName']:
           name = old_contributor.xpath(f'.//*[local-name() = "{name_type}"]/text()')
           if name:
               etree.SubElement(new_contrib, name_type).text = name[0]

   # Language
   languages = old_product.xpath('.//*[local-name() = "Language"]')
   if languages:
       for old_lang in languages:
           new_lang = etree.SubElement(descriptive_detail, 'Language')
           role = old_lang.xpath('.//*[local-name() = "LanguageRole"]/text()')
           etree.SubElement(new_lang, 'LanguageRole').text = role[0] if role else '01'
           code = old_lang.xpath('.//*[local-name() = "LanguageCode"]/text()')
           etree.SubElement(new_lang, 'LanguageCode').text = code[0] if code else publisher_data.get('language_code', 'eng')
   else:
       new_lang = etree.SubElement(descriptive_detail, 'Language')
       etree.SubElement(new_lang, 'LanguageRole').text = '01'
       etree.SubElement(new_lang, 'LanguageCode').text = publisher_data.get('language_code', 'eng')

   # CollateralDetail
   collateral_detail = etree.SubElement(new_product, 'CollateralDetail')
   
   # TextContent
   for old_text in old_product.xpath('.//*[local-name() = "OtherText"]'):
       text_content = etree.SubElement(collateral_detail, 'TextContent')
       text_type = old_text.xpath('.//*[local-name() = "TextTypeCode"]/text()')
       text_type_value = text_type[0] if text_type else "03"
       if text_type_value == "99":
           text_type_value = "03"
       etree.SubElement(text_content, 'TextType').text = text_type_value
       etree.SubElement(text_content, 'ContentAudience').text = '00'
       
       text = old_text.xpath('.//*[local-name() = "Text"]/text()')
       if text:
           text_elem = etree.SubElement(text_content, 'Text')
           text_elem.text = text[0]
           
           text_format = old_text.xpath('.//*[local-name() = "TextFormat"]/text()')
           if text_format:
               text_elem.set('textformat', text_format[0].lower())

   # Supporting Resources
   for old_media in old_product.xpath('.//*[local-name() = "MediaFile"]'):
       new_media = etree.SubElement(collateral_detail, 'SupportingResource')
       etree.SubElement(new_media, 'ContentAudience').text = '00'
       
       media_type = old_media.xpath('.//*[local-name() = "MediaFileTypeCode"]/text()')
       etree.SubElement(new_media, 'ResourceContentType').text = media_type[0] if media_type else '01'
       
       etree.SubElement(new_media, 'ResourceMode').text = '03'
       
       resource_version = etree.SubElement(new_media, 'ResourceVersion')
       etree.SubElement(resource_version, 'ResourceForm').text = '02'
       
       link = old_media.xpath('.//*[local-name() = "MediaFileLink"]/text()')
       if link:
           etree.SubElement(resource_version, 'ResourceLink').text = link[0]

   # PublishingDetail
   publishing_detail = etree.SubElement(new_product, 'PublishingDetail')

   # Publisher
   publisher_name = old_product.xpath('.//*[local-name() = "PublisherName"]/text()')
   if publisher_name:
       publisher = etree.SubElement(publishing_detail, 'Publisher')
       etree.SubElement(publisher, 'PublishingRole').text = '01'
       etree.SubElement(publisher, 'PublisherName').text = publisher_name[0]

   # Publishing Status and Date
   status = old_product.xpath('.//*[local-name() = "PublishingStatus"]/text()')
   etree.SubElement(publishing_detail, 'PublishingStatus').text = status[0] if status else '04'
   
   pub_date = old_product.xpath('.//*[local-name() = "PublicationDate"]/text()')
   if pub_date:
       publishing_date = etree.SubElement(publishing_detail, 'PublishingDate')
       etree.SubElement(publishing_date, 'PublishingDateRole').text = '01'
       etree.SubElement(publishing_date, 'Date').text = pub_date[0]

   # ProductSupply
   product_supply = etree.SubElement(new_product, 'ProductSupply')
   supply_detail = etree.SubElement(product_supply, 'SupplyDetail')
   
   # Supplier
   supplier = etree.SubElement(supply_detail, 'Supplier')
   etree.SubElement(supplier, 'SupplierRole').text = '01'
   supplier_name = old_product.xpath('.//*[local-name() = "SupplierName"]/text()')
   etree.SubElement(supplier, 'SupplierName').text = supplier_name[0] if supplier_name else "Default Supplier"
   
   # Supply Date
   supply_date = etree.SubElement(supply_detail, 'SupplyDate')
   etree.SubElement(supply_date, 'SupplyDateRole').text = '08'
   etree.SubElement(supply_date, 'Date').text = datetime.now().strftime("%Y%m%d")
   
   # Availability
   etree.SubElement(supply_detail, 'ProductAvailability').text = '20'
   
   # Prices
   if publisher_data.get('prices'):
       for currency, amount in publisher_data['prices'].items():
           if amount:
               price = etree.SubElement(supply_detail, 'Price')
               etree.SubElement(price, 'PriceType').text = '02'
               etree.SubElement(price, 'CurrencyCode').text = currency.upper()
               etree.SubElement(price, 'PriceAmount').text = str(Decimal(amount))
def create_new_product(new_root, epub_features, epub_isbn, publisher_data):
   """Create a new product when none exists"""
   if publisher_data is None:
       publisher_data = {}

   new_product = etree.SubElement(new_root, "Product")
   
   # Basic product information
   etree.SubElement(new_product, 'RecordReference').text = f"EPUB_{epub_isbn}"
   etree.SubElement(new_product, 'NotificationType').text = '03'
   
   # Product Identifier
   identifier = etree.SubElement(new_product, 'ProductIdentifier')
   etree.SubElement(identifier, 'ProductIDType').text = '15'  # ISBN-13
   etree.SubElement(identifier, 'IDValue').text = epub_isbn
   
   # DescriptiveDetail
   descriptive_detail = etree.SubElement(new_product, 'DescriptiveDetail')
   etree.SubElement(descriptive_detail, 'ProductComposition').text = publisher_data.get('product_composition', '00')
   etree.SubElement(descriptive_detail, 'ProductForm').text = publisher_data.get('product_form', 'EB')
   etree.SubElement(descriptive_detail, 'ProductFormDetail').text = 'E101'
   
   # Add accessibility features
   for code, is_present in epub_features.items():
       if is_present and code in CODELIST_196:
           feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
           etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
           etree.SubElement(feature, 'ProductFormFeatureValue').text = code
           etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]

   # Add minimum required elements
   add_minimum_elements(new_product, publisher_data)

def add_minimum_elements(product, publisher_data):
   """Add minimum required elements to a product"""
   if publisher_data is None:
       publisher_data = {}

   desc_detail = product.find('DescriptiveDetail')
   if desc_detail is not None:
       # Title
       title_detail = etree.SubElement(desc_detail, 'TitleDetail')
       etree.SubElement(title_detail, 'TitleType').text = '01'
       title_element = etree.SubElement(title_detail, 'TitleElement')
       etree.SubElement(title_element, 'TitleElementLevel').text = '01'
       etree.SubElement(title_element, 'TitleText').text = "Title Not Available"
       
       # Language
       language = etree.SubElement(desc_detail, 'Language')
       etree.SubElement(language, 'LanguageRole').text = '01'
       etree.SubElement(language, 'LanguageCode').text = publisher_data.get('language_code', 'eng')

   # PublishingDetail with minimum requirements
   pub_detail = etree.SubElement(product, 'PublishingDetail')
   publisher = etree.SubElement(pub_detail, 'Publisher')
   etree.SubElement(publisher, 'PublishingRole').text = '01'
   etree.SubElement(publisher, 'PublisherName').text = publisher_data.get('sender_name', 'Default Publisher')
   etree.SubElement(pub_detail, 'PublishingStatus').text = '04'  # Active

   # ProductSupply with minimum requirements
   prod_supply = etree.SubElement(product, 'ProductSupply')
   supply_detail = etree.SubElement(prod_supply, 'SupplyDetail')
   
   supplier = etree.SubElement(supply_detail, 'Supplier')
   etree.SubElement(supplier, 'SupplierRole').text = '01'
   etree.SubElement(supplier, 'SupplierName').text = publisher_data.get('sender_name', 'Default Supplier')
   
   # Add required SupplyDate
   supply_date = etree.SubElement(supply_detail, 'SupplyDate')
   etree.SubElement(supply_date, 'SupplyDateRole').text = '08'
   etree.SubElement(supply_date, 'Date').text = datetime.now().strftime("%Y%m%d")
   
   etree.SubElement(supply_detail, 'ProductAvailability').text = '20'  # Available
   
   # Add a default price if none provided
   price = etree.SubElement(supply_detail, 'Price')
   etree.SubElement(price, 'PriceType').text = '02'  # RRP including tax
   etree.SubElement(price, 'CurrencyCode').text = 'USD'
   etree.SubElement(price, 'PriceAmount').text = '0.00'