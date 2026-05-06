import logging
import sys

# Simplified for Cloud Run
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s',  # Cloud Run adds its own timestamp
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
