import logging
import os

log_file = os.getenv('ERROR_LOG')
logging.basicConfig(filename=log_file, filemode='a')
