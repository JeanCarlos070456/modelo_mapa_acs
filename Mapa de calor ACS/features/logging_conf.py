import logging

def setup_logging(level=logging.INFO):
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(level=level, format=fmt)
    return logging.getLogger("acs-dashboard")
