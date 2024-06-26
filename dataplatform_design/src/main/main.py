from rdflib import Graph, Namespace, URIRef
import os
import pytz
from rdflib.namespace import NamespaceManager, Namespace
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../resources"))
)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../utils")))

import utils
import graphdb_utils
import graph_match
import graph_select
import networkx as nx
import matplotlib.pyplot as plt


variable_names = []
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
matched_graph = Graph()
namespace_manager = NamespaceManager(matched_graph)
matched_graph.namespace_manager = namespace_manager

# Add namespaces to matched graph
[
    namespace_manager.bind(name, Namespace(namespace), override=False)
    for name, namespace in NAMESPACES.items()
]

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

    named_graph = Graph(
        store=matched_graph.store, identifier=URIRef(GRAPHDB_NAMED_GRAPH)
    )

    preferences = []
    mandatories = []

    solution = graph_select.select_services(named_graph, preferences, mandatories)

    selected_services = []
    selected_edges = []

    # Explore solution
    print("---------")
    print("Problem Solution:")
    print("---------")
    for i, name in enumerate(solution.variables.get_names()):
        selected = solution.solution.get_values(i)
        print(f"{name}: {selected}")
        if "->" in name and selected:
            selected_edges.append(name)
        elif selected:
            selected_services.append(name)
    print("---------")
    print(f"Solution cost: {solution.solution.get_objective_value()}")

    [
        named_graph.add(
            (
                URIRef(graph_select.denormalize_name(edge.split("->")[0])),
                DPDO.selected,
                URIRef(graph_select.denormalize_name(edge.split("->")[1])),
            )
        )
        for edge in selected_edges
    ]

for (
    node,
    p,
    service,
) in named_graph.triples(((None, DPDO.selected, None))):
    print(
        f"{utils.rdf(named_graph, node)}, {utils.rdf(named_graph, p)}, {utils.rdf(named_graph, service)}"
    )
