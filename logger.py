import logging
import datetime

# Create a logger
logger = logging.getLogger(__name__)

# Set the log level (optional)
logger.setLevel(logging.DEBUG)

# Create a formatter with a datetime format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Create a handler and set the formatter
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)