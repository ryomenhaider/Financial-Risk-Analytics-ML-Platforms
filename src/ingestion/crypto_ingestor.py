from config.logging_config import get_logger

logger = get_logger(__name__)

logger.info("Application started")
logger.error("something failed")
