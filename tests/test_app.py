import pytest
import os
import io
from lxml import etree
from app.utils.epub_analyzer import analyze_epub
from app.utils.onix_processor import process_onix

class TestAccessONIX:
    """Test suite for AccessONIX application"""
    
    @pytest.fixture
    def sample_epub(self):
        """Create a minimal valid EPUB file for testing"""
        epub_content = io.BytesIO()
        with zipfile.ZipFile(epub_content, 'w') as epub:
            # Add content.opf
            opf_content = '''<?xml version="1.0" encoding="UTF-8"?>
            <package xmlns="http://www.idpf.org/2007/opf" version="3.0">
                <metadata>
                    <meta property="schema:accessibilityFeature">tableOfContents</meta>
                    <meta property="schema:accessibilityFeature">readingOrder</meta>
                    <meta property="schema:accessibilityHazard">none</meta>
                </metadata>
            </package>'''
            epub.writestr('content.opf', opf_content)
            
            # Add basic HTML content
            html_content = '''<!DOCTYPE html>
            <html lang="en">
                <head><title>Test</title></head>
                <body><p>Test content</p></body>
            </html>'''
            epub.writestr('content.html', html_content)
        
        epub_content.seek(0)
        return epub_content

    @pytest.fixture
    def sample_onix(self):
        """Create a minimal valid ONIX file for testing"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
        <ONIXMessage release="3.0">
            <Header>
                <Sender>
                    <SenderName>Test Publisher</SenderName>
                </Sender>
            </Header>
            <Product>
                <RecordReference>test123</RecordReference>
                <NotificationType>03</NotificationType>
                <ProductIdentifier>
                    <ProductIDType>15</ProductIDType>
                    <IDValue>9781234567890</IDValue>
                </ProductIdentifier>
            </Product>
        </ONIXMessage>'''

    def test_index_page(self, client):
        """Test if index page loads correctly"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'AccessONIX' in response.data

    def test_help_page(self, client):
        """Test if help page loads correctly"""
        response = client.get('/help')
        assert response.status_code == 200
        assert b'Help Information' in response.data

    def test_file_upload_without_files(self, client):
        """Test file upload endpoint without files"""
        response = client.post('/process')
        assert response.status_code == 400
        assert b'Both files are required' in response.data

    def test_file_upload_with_invalid_files(self, client):
        """Test file upload with invalid file types"""
        data = {
            'epub_file': (io.BytesIO(b'test'), 'test.txt'),
            'onix_file': (io.BytesIO(b'test'), 'test.txt'),
            'epub_isbn': '1234567890123'
        }
        response = client.post('/process', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert b'Invalid EPUB file format' in response.data

    def test_epub_analysis(self, sample_epub):
        """Test EPUB analysis functionality"""
        features = analyze_epub(sample_epub)
        assert features['11']  # Table of contents
        assert features['13']  # Reading order
        assert features['36']  # Modifiable content

    def test_onix_processing(self, sample_epub, sample_onix):
        """Test ONIX processing functionality"""
        features = analyze_epub(sample_epub)
        processed_xml = process_onix(features, sample_onix.encode(), '9781234567890')
        
        # Parse and validate the processed XML
        root = etree.fromstring(processed_xml)
        assert root.tag.endswith('ONIXMessage')
        assert root.get('release') == '3.0'
        
        # Check for accessibility features
        features = root.findall('.//{*}ProductFormFeature')
        assert len(features) > 0
        
        # Check ISBN update
        isbn = root.find('.//{*}ProductIdentifier/{*}IDValue')
        assert isbn.text == '9781234567890'

    def test_publisher_role_processing(self, client, sample_epub, sample_onix):
        """Test processing with publisher role"""
        data = {
            'epub_file': (sample_epub, 'test.epub'),
            'onix_file': (io.BytesIO(sample_onix.encode()), 'test.xml'),
            'epub_isbn': '9781234567890',
            'role': 'publisher',
            'sender_name': 'Test Publisher',
            'contact_name': 'John Doe',
            'email': 'john@example.com',
            'product_composition': '00',
            'product_form': 'EB',
            'language_code': 'eng',
            'price_cad': '9.99',
            'price_gbp': '5.99',
            'price_usd': '7.99'
        }
        
        response = client.post('/process', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        
        # Parse the response XML
        root = etree.fromstring(response.data)
        
        # Check publisher information
        sender = root.find('.//{*}SenderName')
        assert sender.text == 'Test Publisher'
        
        # Check pricing information
        prices = root.findall('.//{*}Price')
        assert len(prices) == 3

    def test_memory_optimization(self, client, sample_epub, sample_onix):
        """Test memory optimization during processing"""
        from app.utils.memory_utils import check_memory_usage
        
        initial_memory = check_memory_usage()
        
        # Process large files multiple times
        for _ in range(5):
            data = {
                'epub_file': (sample_epub, 'test.epub'),
                'onix_file': (io.BytesIO(sample_onix.encode()), 'test.xml'),
                'epub_isbn': '9781234567890'
            }
            client.post('/process', data=data, content_type='multipart/form-data')
        
        final_memory = check_memory_usage()
        
        # Check that memory usage hasn't grown significantly
        assert final_memory - initial_memory < 100  # Less than 100MB growth

    def test_error_handling(self, client):
        """Test error handling scenarios"""
        # Test file size limit
        large_file = io.BytesIO(b'0' * (16 * 1024 * 1024 + 1))
        data = {
            'epub_file': (large_file, 'large.epub'),
            'onix_file': (io.BytesIO(b'test'), 'test.xml'),
            'epub_isbn': '9781234567890'
        }
        response = client.post('/process', data=data, content_type='multipart/form-data')
        assert response.status_code == 413

        # Test invalid ISBN
        data = {
            'epub_file': (io.BytesIO(b'test'), 'test.epub'),
            'onix_file': (io.BytesIO(b'test'), 'test.xml'),
            'epub_isbn': '123'  # Invalid ISBN
        }
        response = client.post('/process', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert b'Invalid ISBN format' in response.data