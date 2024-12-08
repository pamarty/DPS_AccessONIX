"""Utility functions for ONIX processing"""
import logging
from datetime import datetime
from decimal import Decimal
import re

logger = logging.getLogger(__name__)

def format_date(date_string):
    """Format date string to YYYYMMDD"""
    try:
        if not date_string:
            return datetime.now().strftime("%Y%m%d")
        
        date_string = str(date_string).strip()
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime("%Y%m%d")
            except ValueError:
                continue
        return datetime.now().strftime("%Y%m%d")
    except Exception as e:
        logger.warning(f"Error formatting date {date_string}: {str(e)}")
        return datetime.now().strftime("%Y%m%d")

def clean_text(text):
    """Clean and format text content"""
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', str(text))
    return text.strip()

def validate_price(price_str):
    """Validate and format price value"""
    try:
        if not price_str:
            return "0.00"
        price_str = re.sub(r'[^\d.]', '', str(price_str))
        price = Decimal(price_str)
        return str(price.quantize(Decimal('0.01')))
    except Exception as e:
        logger.warning(f"Price validation error for {price_str}: {str(e)}")
        return "0.00"

def get_element_text(parent, xpath, default=""):
    """Safely get element text using xpath"""
    try:
        elements = parent.xpath(xpath)
        return clean_text(elements[0]) if elements else default
    except Exception as e:
        logger.warning(f"Error getting element text for xpath {xpath}: {str(e)}")
        return default