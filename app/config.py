"""Configuration module for the application"""
import os
import tempfile
from datetime import timedelta

class Config:
    """Base configuration class"""
    # Application
    APP_NAME = 'AccessONIX'
    COMPANY_NAME = 'desLibris Publishing Solutions'
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # Upload folder configuration
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'accessonix_uploads')
    ALLOWED_EXTENSIONS = {'epub', 'xml'}
    MAX_EPUB_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_XML_SIZE = 5 * 1024 * 1024   # 5MB
    
    # ONIX settings
    ONIX_VERSION = '3.0'
    ONIX_NAMESPACE = "http://ns.editeur.org/onix/3.0/reference"
    
    # Memory management
    MEMORY_OPTIMIZATION_THRESHOLD = 100  # MB
    CLEANUP_INTERVAL = 3600  # 1 hour in seconds
    
    # Logging configuration
    LOG_FILE = 'logs/accessonix.log'
    LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_MAX_BYTES = 10240
    LOG_BACKUP_COUNT = 10
    
    # Security
    CSRF_ENABLED = True
    SSL_REDIRECT = False
    
    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Rate limiting
    RATELIMIT_DEFAULT = "100/hour"
    RATELIMIT_STORAGE_URL = "memory://"

    @staticmethod
    def init_app(app):
        """Initialize application configuration"""
        # Create upload folder if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(app.config['LOG_FILE'])
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    TEMPLATES_AUTO_RELOAD = True
    EXPLAIN_TEMPLATE_LOADING = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Development-specific initialization
        import logging
        logging.basicConfig(level=logging.DEBUG)

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = False
    TESTING = True
    
    # Test-specific settings
    WTF_CSRF_ENABLED = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    
    # Use temporary directory for testing
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'accessonix_test')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production security settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # Use environment variables in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    
    # SSL redirect for Heroku
    SSL_REDIRECT = bool(os.environ.get('DYNO'))
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler(
            'logs/accessonix.log',
            maxBytes=cls.LOG_MAX_BYTES,
            backupCount=cls.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(cls.LOG_FORMAT))
        file_handler.setLevel(logging.INFO)
        
        # Add production-specific log handlers
        app.logger.addHandler(file_handler)
        
        # Handle proxy server headers
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

class HerokuConfig(ProductionConfig):
    """Heroku configuration"""
    
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        
        # Handle Heroku-specific requirements
        import logging
        import sys
        
        # Log to stderr
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        
        # Handle proxy server headers specific to Heroku
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1
        )

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'default': DevelopmentConfig
}