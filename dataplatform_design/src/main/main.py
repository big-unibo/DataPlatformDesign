from rdflib import Graph, Namespace, URIRef
import os
import pytz
from rdflib.namespace import Namespace
import sys
import argparse

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../resources"))
)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../utils")))

import utils
import graphdb_utils
import graph_match
import graph_select

# Timezone
tz = pytz.timezone("Europe/Rome")
# Setup logger
logger = utils.setup_logger("DataPlat_Design")
# Load config
config = utils.load_yaml("dataplatform_design/resources/config.yml")

# GraphDB endpoint
GRAPHDB_ENDPOINT = config["graph_db"]["endpoint"]
GRAPHDB_REPOSITORY = config["graph_db"]["repository"]
GRAPHDB_NAMED_GRAPH = config["graph_db"]["named_graph"]
SOLUTION_PATH = config["input"]["expected_solution_path"]
# .ttl paths representing ontologies
PATHS = config["ontologies"]["paths"]
NAMESPACES = config["ontologies"]["namespaces"]

DPDO = Namespace(NAMESPACES["DPDO"])
TAG = Namespace(NAMESPACES["TagTaxonomy"])
DFD = Namespace(NAMESPACES["DFD"])

# Setup GraphDB environment by creating repository & named graph
graphdb_utils.setup_graphdb(GRAPHDB_ENDPOINT, GRAPHDB_REPOSITORY, GRAPHDB_NAMED_GRAPH)

# Push ontologies into GraphDB
if not all(
    ontology
    for ontology in [
        # Returns True if ontology is already present or successfully pushed to DB
        graphdb_utils.post_ontology_on_db(
            namespace, path, GRAPHDB_ENDPOINT, GRAPHDB_REPOSITORY, GRAPHDB_NAMED_GRAPH
        )
        # Post ontology on db foreach (file_path, namespace) in config
        for path, namespace in zip(
            config["ontologies"]["paths"].values(),
            config["ontologies"]["namespaces"].values(),
        )
    ]
):
    logger.exception(
        f"Something went wrong while pushing ontologies to {GRAPHDB_ENDPOINT}"
    )
    sys.exit(1)


# Setup matched graph
matched_graph = utils.setup_graph(NAMESPACES)
# Load DPDO into matched graph
matched_graph.parse(config["ontologies"]["paths"]["DPDO"], format="turtle")


# Embed lakehouse patterns & match graph
if graph_match.match_lakehouse_pattern(
    GRAPHDB_ENDPOINT, GRAPHDB_REPOSITORY, GRAPHDB_NAMED_GRAPH, config["ontologies"]
) & graph_match.build_matched_graph(
    GRAPHDB_ENDPOINT,
    GRAPHDB_REPOSITORY,
    GRAPHDB_NAMED_GRAPH,
    config["ontologies"],
):

    # # Load matched graph
    matched_graph.parse(
        location=os.path.join("output", "matched_graph.json"),
        format="json-ld",
    )

    # Focus only on named graph
    named_graph = Graph(
        store=matched_graph.store, identifier=URIRef(GRAPHDB_NAMED_GRAPH)
    )

    preferences = []
    mandatories = []

    # Solve the LP problem
    solution = graph_select.select_services(named_graph, preferences, mandatories)

    # Foreach new edge, add it to selected_graph
    selected_graph = utils.setup_graph(NAMESPACES)
    [
        selected_graph.add(
            (
                URIRef(graph_select.denormalize_name(edge.split("->")[0])),
                DPDO.selected,
                URIRef(graph_select.denormalize_name(edge.split("->")[1])),
            )
        )
        for edge in solution
    ]

    logger.info("Printing solution:")
    for (
        node,
        p,
        service,
    ) in selected_graph.triples(((None, DPDO.selected, None))):
        logger.info(
            f"{utils.rdf(selected_graph, node)}, {utils.rdf(selected_graph, p)}, {utils.rdf(selected_graph, service)}"
        )

    # Write selected_graph
    with open(os.path.join("output", "selected_graph.json"), "w") as json_file:
        json_file.write(selected_graph.serialize(format="json-ld", indent=4))

    # Retrieve expected solution
    expected_solution = utils.setup_graph(NAMESPACES)
    expected_solution.parse(
        os.path.join("input", "solution", "solution.ttl"), format="turtle"
    )

    # Compare expected solution with computed solution
    if not utils.graphs_are_equal(expected_solution, selected_graph):
        logger.error("Expected and proposed solution don't match!")
    else:
        logger.info("Expected solution matches proposed solution!")
