import sys
import logging
import yaml


def setup_logger(logger_name, log_level=10):
    log_format = "[%(asctime)s][%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # Create stream handler to print logs to standard output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


logger = setup_logger("DPD_utils")


# Given the weights of CPLEX objective function, sets preferences' weights to 0.5
def embed_preferences(variable_names, objective, preferenceFile):
    with open(preferenceFile, "r") as file:
        for line in file.readlines():
            if line in variable_names:
                objective[variable_names.index(line)] = 0.5
            else:
                logger.error(f"Can't embed preference {line}, aborting")
                sys.exit(1)
        return objective


def setup_logger(logger_name, log_level=10):
    log_format = "[%(asctime)s][%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # Create stream handler to print logs to standard output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def rdf(matched_graph, triple):
    return matched_graph.namespace_manager.normalizeUri(triple)


def load_yaml(path):
    with open(path) as yml_file:
        try:
            return yaml.load(yml_file, Loader=yaml.FullLoader)
        except yaml.YAMLError as exc:
            logger.exception(exc)
