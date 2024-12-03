import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
import logging
import re
from datetime import datetime
import io

logger = logging.getLogger(__name__)

# Complete CODELIST_196 dictionary
CODELIST_196 = {
    '0': 'Accessibility summary',
    '1': 'LIA Compliance Scheme',
    '2': 'EPUB Accessibility Specification 1.0 A',
    '3': 'EPUB Accessibility Specification 1.0 AA',
    '4': 'EPUB Accessibility Specification 1.1',
    '5': 'PDF/UA',
    '8': 'Unknown accessibility',
    '9': 'Inaccessible, or known limited accessibility',
    '10': 'No reading system accessibility options actively disabled (except)',
    '11': 'Table of contents navigation',
    '12': 'Index navigation',
    '13': 'Single logical reading order',
    '14': 'Short alternative textual descriptions',
    '15': 'Full alternative textual descriptions',
    '16': 'Visualized data also available as non-graphical data',
    '17': 'Accessible math content as MathML',
    '18': 'Accessible chemistry content as ChemML',
    '19': 'Print-equivalent page numbering',
    '20': 'Synchronized pre-recorded audio',
    '21': 'Text-to-speech hinting provided',
    '22': 'Language tagging provided',
    '24': 'Dyslexia readability',
    '25': 'Use of color is not the sole means of conveying information',
    '26': 'Use of high contrast between text and background color',
    '27': 'Use of high contrast between foreground and background audio',
    '28': 'Full alternative audio descriptions',
    '29': 'Next/Previous structural navigation',
    '30': 'ARIA roles provided',
    '31': 'Accessible controls provided',
    '32': 'Landmark navigation',
    '34': 'Accessible chemistry content (as MathML)',
    '35': 'Accessible math content (as LaTeX)',
    '36': 'All textual content can be modified',
    '37': 'Use of ultra-high contrast between text foreground and background',
    '38': 'Unusual words or abbreviations explained',
    '39': 'Supplementary material to an audiobook is accessible',
    '40': 'Link purposes clear',
    '51': 'All non-decorative content supports reading via pre-recorded audio',
    '52': 'All non-decorative content supports reading without sight',
    '75': 'EEA Exception 1 – Micro-enterprises',
    '76': 'EAA exception 2 – Disproportionate burden',
    '77': 'EAA exception 3 – Fundamental modification',
    '80': 'WCAG v2.0',
    '81': 'WCAG v2.1',
    '82': 'WCAG v2.2',
    '84': 'WCAG level A',
    '85': 'WCAG level AA',
    '86': 'WCAG level AAA',
    '91': 'Latest accessibility assessment date',
    '92': 'Accessibility addendum',
    '93': 'Compliance certification by',
    '94': 'Compliance web page for detailed accessibility information',
    '95': 'Trusted intermediary\'s web page for detailed accessibility information',
    '96': 'Publisher\'s web page for detailed accessibility information',
    '97': 'Compatibility tested',
    '98': 'Trusted intermediary contact',
    '99': 'Publisher contact for further accessibility information'
}

def analyze_epub(epub_file):
    """
    Analyze EPUB file for accessibility features
    Returns: dict of accessibility features
    """
    accessibility_info = defaultdict(bool)
    language_tagging_detected = False
    page_numbering_detected = False
    landmark_navigation_detected = False
    dyslexia_support_detected = False
    
    try:
        with zipfile.ZipFile(io.BytesIO(epub_file.read())) as epub:
            logger.info("Checking content files for language tagging...")
            for item in epub.infolist():
                if item.filename.endswith(('.xhtml', '.html', '.xml')):
                    with epub.open(item.filename) as content:
                        content_str = content.read().decode('utf-8')
                        lang_pattern = r'<[^>]+(?:\s(?:lang|xml:lang)\s*=\s*["\']([^"\']+)["\'])[^>]*>'
                        matches = re.findall(lang_pattern, content_str, re.IGNORECASE)
                        if matches:
                            language_tagging_detected = True
                            for lang in matches:
                                logger.info(f"Language tagging detected in {item.filename}: lang='{lang}'")
                            break

                if language_tagging_detected:
                    break

            if language_tagging_detected:
                accessibility_info['22'] = True
                logger.info("Language tagging (code 22) detected in content files and set to True")
            else:
                logger.info("No language tagging detected in content files")

            # Check OPF file for metadata
            opf_path = next(path for path in epub.namelist() if path.endswith('.opf'))
            logger.info(f"OPF file found: {opf_path}")
            
            with epub.open(opf_path) as opf_file:
                tree = ET.parse(opf_file)
                root = tree.getroot()
                
                metadata = root.find('{http://www.idpf.org/2007/opf}metadata')
                if metadata is not None:
                    logger.info("Metadata found in OPF file")
                    for meta in metadata.findall('.//*'):
                        property = meta.get('property') or meta.get('name')
                        value = meta.text or meta.get('content')
                        
                        if property and value:
                            property = property.lower()
                            value = value.lower()
                            logger.debug(f"Found metadata: property={property}, value={value}")
                            
                            if 'conformsto' in property or 'conformsTo' in property:
                                analyze_conformance(value, accessibility_info)
                            
                            analyze_metadata_property(property, value, accessibility_info)

            # Check for page break markers in the EPUB content
            check_for_page_breaks(epub, accessibility_info)

            # Check for landmarks in the EPUB content
            check_for_landmarks(epub, accessibility_info)

            # Check for specific CSS properties that might indicate dyslexia support
            check_for_dyslexia_support(epub, accessibility_info)

            # Assume no accessibility options are disabled unless proven otherwise
            accessibility_info['10'] = True
            logger.info("Assuming no reading system accessibility options disabled")

            # Infer compliance based on certification
            infer_compliance(accessibility_info)

            logger.info("Accessibility info collected: " + ", ".join([f"{k}: {v}" for k, v in accessibility_info.items() if v]))
            return accessibility_info

    except Exception as e:
        logger.error(f"Error analyzing EPUB: {str(e)}")
        raise

def analyze_conformance(value, accessibility_info):
    """Analyze conformance metadata"""
    if 'epub-a11y-11' in value or 'epub accessibility 1.1' in value:
        accessibility_info['4'] = True  # EPUB Accessibility 1.1
        accessibility_info['3'] = True  # EPUB Accessibility 1.0 AA
        accessibility_info['2'] = True  # EPUB Accessibility 1.0 A
        logger.info("EPUB Accessibility 1.1 detected (includes 1.0 AA and 1.0 A)")
    elif 'epub-a11y-10' in value or 'epub accessibility 1.0' in value:
        if 'aa' in value:
            accessibility_info['3'] = True  # EPUB Accessibility 1.0 AA
            accessibility_info['2'] = True  # EPUB Accessibility 1.0 A
            logger.info("EPUB Accessibility 1.0 AA detected (includes 1.0 A)")
        else:
            accessibility_info['2'] = True  # EPUB Accessibility 1.0 A
            logger.info("EPUB Accessibility 1.0 A detected")
    
    analyze_wcag_conformance(value, accessibility_info)

def analyze_wcag_conformance(value, accessibility_info):
    """Analyze WCAG conformance levels"""
    if 'wcag' in value:
        if '2.2' in value:
            accessibility_info['82'] = True  # WCAG 2.2
            accessibility_info['81'] = True  # WCAG 2.1
            accessibility_info['80'] = True  # WCAG 2.0
            logger.info("WCAG 2.2 detected (includes 2.1 and 2.0)")
        elif '2.1' in value:
            accessibility_info['81'] = True  # WCAG 2.1
            accessibility_info['80'] = True  # WCAG 2.0
            logger.info("WCAG 2.1 detected (includes 2.0)")
        elif '2.0' in value:
            accessibility_info['80'] = True  # WCAG 2.0
            logger.info("WCAG 2.0 detected")
        
        if '-aaa-' in value:
            accessibility_info['86'] = True  # WCAG AAA
            accessibility_info['85'] = True  # WCAG AA
            accessibility_info['84'] = True  # WCAG A
            logger.info("WCAG AAA level detected (includes AA and A)")
        elif '-aa-' in value:
            accessibility_info['85'] = True  # WCAG AA
            accessibility_info['84'] = True  # WCAG A
            logger.info("WCAG AA level detected (includes A)")
        elif '-a-' in value:
            accessibility_info['84'] = True  # WCAG A
            logger.info("WCAG A level detected")

def analyze_metadata_property(property, value, accessibility_info):
    """Analyze metadata properties for accessibility features"""
    if 'pdf/ua' in value:
        accessibility_info['5'] = True
        logger.info("PDF/UA detected")
    
    if 'accessibility-summary' in property or 'accessibilitysummary' in property:
        accessibility_info['0'] = True
        logger.info("Accessibility summary detected")
    
    if 'accessibilityfeature' in property:
        analyze_accessibility_features(value, accessibility_info)

    if any(key in value for key in ['dyslexia', 'readability', 'customizable']):
        accessibility_info['24'] = True
        logger.info("Dyslexia readability features detected")
    
    if 'page-list' in value or 'page-map' in value:
        accessibility_info['19'] = True
        logger.info("Print-equivalent page numbering detected")
    
    if 'contrast' in value and ('high' in value or 'enhanced' in value):
        accessibility_info['26'] = True
        logger.info("High contrast detected")
    
    if 'controls' in value and 'accessible' in value:
        accessibility_info['31'] = True
        logger.info("Accessible controls detected")
    
    analyze_additional_metadata(property, value, accessibility_info)

def analyze_accessibility_features(value, accessibility_info):
    """Analyze accessibility features from metadata"""
    feature_mapping = {
        'tableofcontents': '11',
        'index': '12',
        'readingorder': '13',
        'alternativetext': '14',
        'longdescription': '15',
        'alternativerepresentation': '16',
        'mathml': '17',
        'chemml': '18',
        'printpagenumbers': '19',
        'pagenumbers': '19',
        'pagebreaks': '19',
        'synchronizedaudiotext': '20',
        'ttsmarkup': '21',
        'displaytransformability': '24',
        'fontcustomization': '24',
        'textspacing': '24',
        'colorcustomization': '24',
        'texttospeech': '24',
        'readingtools': '24',
        'highcontrast': '26',
        'colorcontrast': '26',
        'audiocontrast': '27',
        'fullaudiodescription': '28',
        'structuralnavigation': '29',
        'aria': '30',
        'accessibleinterface': '31',
        'accessiblecontrols': '31',
        'accessiblenavigation': '31',
        'landmarks': '32',
        'landmarknavigation': '32',
        'chemistryml': '34',
        'latex': '35',
        'modifiabletextsize': '36',
        'ultracolorcontrast': '37',
        'glossary': '38',
        'accessiblesupplementarycontent': '39',
        'linkpurpose': '40'
    }
    
    for key, code in feature_mapping.items():
        if key in value:
            accessibility_info[code] = True
            logger.info(f"Accessibility feature detected: {CODELIST_196[code]}")

def analyze_additional_metadata(property, value, accessibility_info):
    """Analyze additional metadata properties"""
    if 'accessibilityhazard' in property and 'none' in value:
        accessibility_info['36'] = True
        logger.info("All textual content can be modified")
    
    if 'certifiedby' in property:
        accessibility_info['93'] = True
        logger.info("Compliance certification detected")
    
    if ('accessibilityapi' in property or 
        'a11y:certifierReport' in property or 
        ('accessibility' in property and value.startswith('http'))):
        accessibility_info['94'] = True
        logger.info(f"Compliance web page detected: {value}")
    
    if 'accessmode' in property or 'accessmodesufficient' in property:
        if 'textual' in value:
            accessibility_info['52'] = True
            logger.info("All non-decorative content supports reading without sight")
        if 'auditory' in value:
            accessibility_info['51'] = True
            logger.info("All non-decorative content supports reading via pre-recorded audio")
    
    if property == 'dcterms:modified':
        try:
            date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            accessibility_info['91'] = True
            logger.info("Latest accessibility assessment date detected")
        except ValueError:
            logger.warning(f"Unable to parse date: {value}")

def check_for_page_breaks(epub, accessibility_info):
    """Check for page break markers in EPUB content"""
    for item in epub.infolist():
        if item.filename.endswith(('.xhtml', '.html')):
            with epub.open(item.filename) as content:
                content_str = content.read().decode('utf-8')
                if 'epub:type="pagebreak"' in content_str:
                    accessibility_info['19'] = True
                    logger.info("Print-equivalent page numbering detected (pagebreak markers)")
                    break

def check_for_landmarks(epub, accessibility_info):
    """Check for landmarks in EPUB content"""
    for item in epub.infolist():
        if item.filename.endswith('.opf'):
            with epub.open(item.filename) as content:
                opf_content = content.read().decode('utf-8')
                if '<guide>' in opf_content or 'epub:type="landmarks"' in opf_content:
                    accessibility_info['32'] = True
                    logger.info("Landmark navigation detected")
                    break

def check_for_dyslexia_support(epub, accessibility_info):
    """Check for CSS properties indicating dyslexia support"""
    for item in epub.infolist():
        if item.filename.endswith('.css'):
            with epub.open(item.filename) as css_file:
                css_content = css_file.read().decode('utf-8')
                if any(prop in css_content for prop in ['font-family', 'letter-spacing', 'word-spacing', 'line-height', 'background-color', 'color']):
                    accessibility_info['24'] = True
                    logger.info("CSS properties supporting dyslexia readability detected")
                    break

def infer_compliance(accessibility_info):
    """Infer compliance based on certification and features"""
    # Infer compliance based on certification
    if accessibility_info['93']:  # If certified
        accessibility_info['4'] = True  # EPUB Accessibility 1.1
        accessibility_info['3'] = True  # EPUB Accessibility 1.0 AA
        accessibility_info['2'] = True  # EPUB Accessibility 1.0 A
        accessibility_info['81'] = True  # WCAG 2.1
        accessibility_info['80'] = True  # WCAG 2.0
        accessibility_info['85'] = True  # WCAG Level AA
        accessibility_info['84'] = True  # WCAG Level A
        logger.info("Inferred EPUB Accessibility 1.1, 1.0 AA, 1.0 A and WCAG 2.1 AA, 2.0 AA compliance based on certification")

    # Infer compliance based on presence of key accessibility features
    if accessibility_info['11'] and accessibility_info['13'] and accessibility_info['30'] and accessibility_info['52']:
        if not accessibility_info['4']:
            accessibility_info['4'] = True
            accessibility_info['3'] = True
            accessibility_info['2'] = True
            logger.info("Inferred EPUB Accessibility 1.1, 1.0 AA, 1.0 A compliance based on presence of key accessibility features")

    # Infer color contrast if the EPUB is accessible
    if accessibility_info['4'] or accessibility_info['3'] or accessibility_info['2']:
        accessibility_info['26'] = True
        logger.info("Inferred high contrast between text and background color based on accessibility compliance")