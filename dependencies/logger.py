import logging


def setup_logger(name, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s:%(module)s:%(levelname)s:%(message)s')

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)

    log = logging.getLogger(name)
    log.setLevel(level)
    log.addHandler(ch)

    return log
