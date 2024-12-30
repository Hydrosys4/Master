import secrets

# configuration
#SECRET_KEY = 'thisisnotsafe'
SECRET_KEY = secrets.token_hex(16)
UPLOAD_FOLDER = "static/upload"
MAX_CONTENT_LENGTH = 1048576
