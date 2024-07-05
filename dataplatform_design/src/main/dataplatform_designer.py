from rdflib import Graph, URIRef
import os
import pytz
from rdflib.namespace import Namespace
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../resources"))
)

from utils import utils, graphdb_utils, graph_match, graph_select

# Timezone
tz = pytz.timezone("Europe/Rome")
# Setup log
logger = utils.setup_logger("DataPlat_Design")
# Load config
config = utils.load_yaml(
    os.path.join("dataplatform_design", "resources", "configs", "config.yml")
)


class DataPlatformDesigner:
    def __init__(self, endpoint, repository, named_graph, namespaces):
        self.endpoint = endpoint
        self.repository = repository
        self.named_graph = named_graph
        self.namespaces = namespaces
        self.DPDO = Namespace(namespaces["dpdo"])
        self.TAG = Namespace(namespaces["tag_taxonomy"])
        self.DFD = Namespace(namespaces["dfd"])

    def setup_graph_db(self, repo_config_path):
        graphdb_utils.delete_repository(self.repository, self.endpoint)
        return graphdb_utils.setup_graphdb(
            self.endpoint, self.repository, repo_config_path, self.named_graph
        )

    def load_ontologies(self, ontologies):
        if not all(
            ontology
            for ontology in [
                # Returns True if ontology is already present or successfully pushed to DB
                graphdb_utils.post_ontology_on_db(
                    namespace,
                    path,
                    self.endpoint,
                    self.repository,
                    self.named_graph,
                )
                # Post ontology on db foreach (file_path, namespace) in config
                for path, namespace in ontologies
            ]
        ):
            logger.exception(
                f"Something went wrong while pushing ontologies to {self.endpoint}"
            )
            sys.exit(1)

    def add_constraints(self, constraints):
        return all(
            [
                graphdb_utils.load_ontology(
                    path,
                    self.endpoint,
                    self.repository,
                    self.named_graph,
                    f"Costraint {path}",
                )
                for path in constraints
            ]
        )

    def build_matched_graph(self, dpdo_ontology_path, matched_graph_path):
        # Setup matched graph
        matched_graph = utils.setup_graph(self.namespaces)

        # Load DPDO into matched graph
        matched_graph.parse(dpdo_ontology_path, format="turtle")
        # Embed lakehouse patterns & match graph
        if graph_match.match_lakehouse_pattern(
            self.endpoint, self.repository, self.named_graph
        ) & graph_match.build_matched_graph(
            self.endpoint, self.repository, self.named_graph, matched_graph_path
        ):

            # # Load matched graph
            matched_graph.parse(
                location=os.path.join(matched_graph_path),
                format="json-ld",
            )

            # Focus only on named graph
            named_graph = Graph(
                store=matched_graph.store, identifier=URIRef(self.named_graph)
            )
            return named_graph

    def build_selected_graph(self, named_graph, selected_graph_output_path):
        # Solve the LP problem
        solution = graph_select.select_services(named_graph)

        # Foreach new edge, add it to selected_graph
        selected_graph = utils.setup_graph(self.namespaces)
        [
            selected_graph.add(
                (
                    URIRef(graph_select.denormalize_name(edge.split("->")[0])),
                    self.DPDO.selected,
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
        ) in selected_graph.triples(((None, self.DPDO.selected, None))):
            logger.info(
                f"{utils.rdf(selected_graph, node)}, {utils.rdf(selected_graph, p)}, {utils.rdf(selected_graph, service)}"
            )
            # Write selected_graph
        with open(
            selected_graph_output_path,
            "w",
        ) as json_file:
            json_file.write(selected_graph.serialize(format="json-ld", indent=4))

        return selected_graph

    def compare_solution(self, selected_graph, solution_path):
        expected_solution = utils.setup_graph(self.namespaces)
        expected_solution.parse(
            solution_path,
            format="turtle",
        )
        # Compare expected solution with computed solution
        if not utils.graphs_are_equal(expected_solution, selected_graph):
            logger.error("Expected and proposed solution don't match!")
            return False
        else:
            logger.info("Expected solution matches proposed solution!")
            return True
