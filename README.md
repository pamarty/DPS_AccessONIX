# AccessONIX

AccessONIX is a web application that generates ONIX 3.0 XML files for accessible EPUB formats. It analyzes EPUB files for accessibility features and combines them with existing ONIX data to create complete, standards-compliant ONIX files.

## Features

- Single-step EPUB accessibility analysis and ONIX generation
- Support for both Production and Publisher roles
- Complete ONIX 3.0 compatibility
- Automated accessibility feature detection
- Publisher information management
- Pricing information in multiple currencies
- Memory-optimized file processing
- Comprehensive error handling and validation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/accessonix.git
cd accessonix
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Local Development

1. Start the development server:
```bash
flask run
```

2. Visit `http://localhost:5000` in your browser

## Heroku Deployment

1. Install Heroku CLI and login:
```bash
heroku login
```

2. Create a new Heroku app:
```bash
heroku create your-app-name
```

3. Set environment variables:
```bash
heroku config:set FLASK_APP=app.main
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret-key
```

4. Deploy:
```bash
git push heroku main
```

## Usage

### Production Role
1. Upload EPUB file
2. Upload source ONIX XML
3. Enter EPUB ISBN
4. Generate ONIX file

### Publisher Role
1. Upload EPUB file
2. Upload source ONIX XML
3. Enter EPUB ISBN
4. Provide publisher information:
   - Sender details
   - Contact information
   - Product details
   - Pricing information
5. Generate ONIX file

## File Requirements

- EPUB files must be properly formatted and contain accessibility metadata
- ONIX XML files must be valid XML
- Maximum file size: 16MB
- ISBN must be 13 digits

## Directory Structure

```
accessonix/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── epub_analyzer.py
│   │   ├── onix_processor.py
│   │   ├── memory_utils.py
│   │   └── validators.py
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── help.html
│       └── error.html
├── logs/
├── tests/
├── .env
├── .gitignore
├── Procfile
├── README.md
├── requirements.txt
└── runtime.txt
```

## Testing

Run tests using:
```bash
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

## License

© desLibris Publishing Solutions. All rights reserved.

## Support

For support, please contact [support email].