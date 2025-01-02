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

def process_form_features(descriptive_detail, old_product, epub_features):
    """Process product form features including accessibility features"""
    # Process existing product form features
    old_features = old_product.xpath('.//*[local-name() = "ProductFormFeature"]')
    for old_feature in old_features:
        feature_type = old_feature.xpath('.//*[local-name() = "ProductFormFeatureType"]/text()')
        if feature_type and feature_type[0] != "09":  # Skip accessibility features
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = feature_type[0]
            
            feature_value = old_feature.xpath('.//*[local-name() = "ProductFormFeatureValue"]/text()')
            if feature_value:
                etree.SubElement(feature, 'ProductFormFeatureValue').text = feature_value[0]

    # Add accessibility features
    for code, is_present in epub_features.items():
        if is_present and code in CODELIST_196:
            feature = etree.SubElement(descriptive_detail, 'ProductFormFeature')
            etree.SubElement(feature, 'ProductFormFeatureType').text = "09"
            etree.SubElement(feature, 'ProductFormFeatureValue').text = code
            etree.SubElement(feature, 'ProductFormFeatureDescription').text = CODELIST_196[code]

def process_titles(descriptive_detail, old_product):
    """Process title information"""
    for old_title in old_product.xpath('.//*[local-name() = "Title"]'):
        title_type = old_title.xpath('.//*[local-name() = "TitleType"]/text()')
        if not title_type or title_type[0] == "01":  # Main title
            title_detail = etree.SubElement(descriptive_detail, 'TitleDetail')
            etree.SubElement(title_detail, 'TitleType').text = '01'
            
            title_element = etree.SubElement(title_detail, 'TitleElement')
            etree.SubElement(title_element, 'TitleElementLevel').text = '01'
            
            title_text = old_title.xpath('.//*[local-name() = "TitleText"]/text()')
            etree.SubElement(title_element, 'TitleText').text = title_text[0] if title_text else 'Unknown Title'

            subtitle = old_title.xpath('.//*[local-name() = "Subtitle"]/text()')
            if subtitle:
                etree.SubElement(title_element, 'Subtitle').text = subtitle[0]

def process_contributors(descriptive_detail, old_product):
    """Process contributor information"""
    for old_contributor in old_product.xpath('.//*[local-name() = "Contributor"]'):
        new_contributor = etree.SubElement(descriptive_detail, 'Contributor')
        
        # ContributorRole must come first
        role = old_contributor.xpath('.//*[local-name() = "ContributorRole"]/text()')
        if role:
            etree.SubElement(new_contributor, 'ContributorRole').text = role[0]

        # Personal name elements in correct order
        person_name = old_contributor.xpath('.//*[local-name() = "PersonName"]/text()')
        if person_name:
            etree.SubElement(new_contributor, 'PersonName').text = person_name[0]

        inverted_name = old_contributor.xpath('.//*[local-name() = "PersonNameInverted"]/text()')
        if inverted_name:
            etree.SubElement(new_contributor, 'PersonNameInverted').text = inverted_name[0]

        names_before = old_contributor.xpath('.//*[local-name() = "NamesBeforeKey"]/text()')
        if names_before:
            etree.SubElement(new_contributor, 'NamesBeforeKey').text = names_before[0]

        key_names = old_contributor.xpath('.//*[local-name() = "KeyNames"]/text()')
        if key_names:
            etree.SubElement(new_contributor, 'KeyNames').text = key_names[0]

        # Biographical note comes after name components
        bio = old_contributor.xpath('.//*[local-name() = "BiographicalNote"]/text()')
        if bio:
            etree.SubElement(new_contributor, 'BiographicalNote').text = bio[0]

        # ContributorPlace with proper structure
        country = old_contributor.xpath('.//*[local-name() = "CountryCode"]/text()')
        if country:
            place = etree.SubElement(new_contributor, 'ContributorPlace')
            etree.SubElement(place, 'ContributorPlaceRelator').text = '00'
            etree.SubElement(place, 'CountryCode').text = country[0]

def process_language(descriptive_detail, old_product, publisher_data=None):
    """Process language information"""
    language = etree.SubElement(descriptive_detail, 'Language')
    
    # LanguageRole must come first
    lang_role = old_product.xpath('.//*[local-name() = "LanguageRole"]/text()')
    etree.SubElement(language, 'LanguageRole').text = lang_role[0] if lang_role else DEFAULT_LANGUAGE_ROLE
    
    # Then LanguageCode
    if publisher_data and publisher_data.get('language_code'):
        etree.SubElement(language, 'LanguageCode').text = publisher_data['language_code']
    else:
        lang_code = old_product.xpath('.//*[local-name() = "LanguageCode"]/text()')
        etree.SubElement(language, 'LanguageCode').text = lang_code[0] if lang_code else DEFAULT_LANGUAGE_CODE

def process_subjects(descriptive_detail, old_product):
    """Process subject information"""
    for old_subject in old_product.xpath('.//*[local-name() = "Subject"]'):
        scheme = old_subject.xpath('.//*[local-name() = "SubjectSchemeIdentifier"]/text()')
        code = old_subject.xpath('.//*[local-name() = "SubjectCode"]/text()')
        heading = old_subject.xpath('.//*[local-name() = "SubjectHeadingText"]/text()')
        
        if scheme and (code or heading):
            new_subject = etree.SubElement(descriptive_detail, 'Subject')
            etree.SubElement(new_subject, 'SubjectSchemeIdentifier').text = scheme[0]
            
            scheme_name = old_subject.xpath('.//*[local-name() = "SubjectSchemeName"]/text()')
            if scheme_name:
                etree.SubElement(new_subject, 'SubjectSchemeName').text = scheme_name[0]
            
            if code:
                etree.SubElement(new_subject, 'SubjectCode').text = code[0]
            
            if heading:
                etree.SubElement(new_subject, 'SubjectHeadingText').text = heading[0]

def process_audience(descriptive_detail, old_product):
    """Process audience information"""
    audience_code = old_product.xpath('.//*[local-name() = "AudienceCode"]/text()')
    if audience_code:
        audience = etree.SubElement(descriptive_detail, 'Audience')
        etree.SubElement(audience, 'AudienceCodeType').text = '01'
        etree.SubElement(audience, 'AudienceCodeValue').text = audience_code[0]

def process_extent(descriptive_detail, old_product):
    """Process extent information"""
    for old_extent in old_product.xpath('.//*[local-name() = "Extent"]'):
        extent_type = old_extent.xpath('.//*[local-name() = "ExtentType"]/text()')
        extent_value = old_extent.xpath('.//*[local-name() = "ExtentValue"]/text()')
        extent_unit = old_extent.xpath('.//*[local-name() = "ExtentUnit"]/text()')
        
        if extent_type and extent_value and extent_unit:
            try:
                value = int(extent_value[0])
                if value > 0:
                    new_extent = etree.SubElement(descriptive_detail, 'Extent')
                    etree.SubElement(new_extent, 'ExtentType').text = extent_type[0]
                    etree.SubElement(new_extent, 'ExtentValue').text = str(value)
                    etree.SubElement(new_extent, 'ExtentUnit').text = extent_unit[0]
            except (ValueError, TypeError):
                logger.warning(f"Invalid extent value: {extent_value[0]}")
                continue