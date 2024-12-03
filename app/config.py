import os
import tempfile
from datetime import timedelta

class BaseConfig:
    """Base configuration"""
    # Application
    APP_NAME = 'AccessONIX'
    COMPANY_NAME = 'desLibris Publishing Solutions'
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or tempfile.gettempdir()
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # File handling
    ALLOWED_EXTENSIONS = {'epub', 'xml'}
    MAX_EPUB_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_XML_SIZE = 5 * 1024 * 1024   # 5MB
    
    # ONIX settings
    ONIX_VERSION = '3.0'
    ONIX_NAMESPACE = "http://ns.editeur.org/onix/3.0/reference"
    
    # Memory management
    MEMORY_OPTIMIZATION_THRESHOLD = 500  # MB
    CLEANUP_INTERVAL = 3600  # 1 hour in seconds
    
    # Logging
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = 'accessonix.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
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
        pass

class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    TEMPLATES_AUTO_RELOAD = True
    EXPLAIN_TEMPLATE_LOADING = True
    
    # SQLAlchemy settings if needed for development
    SQLALCHEMY_ECHO = True
    
    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)
        
        # Development-specific initialization
        import logging
        logging.basicConfig(level=logging.DEBUG)

class TestingConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Test-specific settings
    WTF_CSRF_ENABLED = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    
    # Use temporary directory for test uploads
    UPLOAD_FOLDER = tempfile.gettempdir()
    
    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)

class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production security settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # SSL redirect
    SSL_REDIRECT = True if os.environ.get('DYNO') else False
    
    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app)
        
        # Production-specific logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        file_handler = RotatingFileHandler(
            'logs/accessonix.log',
            maxBytes=cls.LOG_MAX_SIZE,
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
        from flask import request
        
        # Log to stderr
        import sys
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        
        # Handle proxy server headers specific to Heroku
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

# Additional configuration functions
def get_env_config():
    """Get configuration based on environment"""
    return config[os.getenv('FLASK_ENV', 'default')]