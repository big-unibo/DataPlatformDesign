import sys
import logging
import yaml
from rdflib.namespace import NamespaceManager
from rdflib import Graph, Namespace


def setup_logger(logger_name, log_level=logging.DEBUG):
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


def rdf(matched_graph, triple):
    return matched_graph.namespace_manager.normalizeUri(triple)


def setup_graph(namespaces):
    new_graph = Graph()
    namespace_manager = NamespaceManager(new_graph)
    new_graph.namespace_manager = namespace_manager

    # Add namespaces to matched graph
    [
        namespace_manager.bind(name, Namespace(namespace), override=False)
        for name, namespace in namespaces.items()
    ]
    return new_graph


def load_yaml(path):
    with open(path) as yml_file:
        try:
            return yaml.load(yml_file, Loader=yaml.FullLoader)
        except yaml.YAMLError as exc:
            logger.exception(exc)


def graphs_are_equal(expected_solution, proposed_solution, predicates):
    triples_to_remove = [(s, p, o) for s, p, o in proposed_solution if p in predicates]
    for triple in triples_to_remove:
        proposed_solution.remove(triple)

    if len(expected_solution) != len(proposed_solution):
        return False

    for triple in expected_solution:
        if triple not in proposed_solution:
            s, p, o = triple
            # logger.warning(f"{rdf(expected_solution,s)} {rdf(expected_solution,p)} {rdf(expected_solution,o)} from expected solution not in proposed solution")
            return False
    for triple in proposed_solution:
        if triple not in expected_solution:
            # logger.warning(f"{rdf(proposed_solution,s)} {rdf(proposed_solution,p)} {rdf(proposed_solution,o)} from proposed solution not in expected solution")
            return False
    return True
