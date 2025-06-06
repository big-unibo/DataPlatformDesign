from rdflib import Graph, URIRef, RDF
import os
import pytz
from rdflib.namespace import Namespace
import sys
import requests
import time

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../resources"))
)

from utils import utils, graphdb_utils, graph_match, graph_select, graph_augment

# Timezone
tz = pytz.timezone("Europe/Rome")
# Setup log
logger = utils.setup_logger("DataPlat_Design")

# Load config
config = utils.load_yaml(
    os.path.join(
        "dataplatform_design", "resources", "scenario_template", "configs", "config.yml"
    )
)


class DataPlatformDesigner:
    def __init__(self, endpoint, repository, named_graph, namespaces, scenario_path):
        self.endpoint = endpoint
        self.repository = repository
        self.named_graph = named_graph
        self.namespaces = namespaces
        self.scenario_path = scenario_path
        self.selection_constraints = []
        self.DPDO = Namespace(namespaces["dpdo"])
        self.TAG = Namespace(namespaces["tag_taxonomy"])
        self.DFD = Namespace(namespaces["dfd"])

    def setup_config(self, scenario_config):
        global config
        config = scenario_config
        graph_match.setup_config(scenario_config)
        graph_select.setup_config(scenario_config)
        graph_augment.setup_config(scenario_config)

    def add_selection_constraint(self, constraint):
        self.selection_constraints.append(constraint)

    def setup_graph_db(self, repo_config_path):
        print(f"ENDOPOINT: {self.endpoint}/rest/repositories/{self.repository}")
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
        try:
            # Embed lakehouse patterns & match graphw
            result, duration = graph_match.build_matched_graph(
                self.endpoint, self.repository, self.named_graph, matched_graph_path
            )
            if result:
                # # Load matched graph
                matched_graph.parse(
                    location=os.path.join(matched_graph_path),
                    format="json-ld",
                )

                # Focus only on named graph
                named_graph = Graph(
                    store=matched_graph.store, identifier=URIRef(self.named_graph)
                )

            return named_graph, duration

        except Exception as e:
            logger.exception("Something went wrong while building matched graph")
            logger.exception(e.__doc__)

    def augment_graph(self, matched_graph_path, dpdo_ontology_path):
        start_time = time.time()
        result, lakehouse_duration = graph_match.match_lakehouse_pattern(
            self.endpoint,
            self.repository,
            self.named_graph,
            matched_graph_path,
            self.namespaces,
        )

        matched_graph = utils.setup_graph(self.namespaces)

        # Load DPDO into matched graph
        matched_graph.parse(dpdo_ontology_path, format="turtle")
        matched_graph.parse(
            location=os.path.join(matched_graph_path),
            format="json-ld",
        )

        # Focus only on named graph
        named_graph = Graph(
            store=matched_graph.store, identifier=URIRef(self.named_graph)
        )
        start_time = time.time()
        result = graph_augment.augment_graph(named_graph)
        other_augment_duration = time.time() - start_time
        return result, lakehouse_duration + other_augment_duration

    def build_selected_graph(self, named_graph, selected_graph_output_path):
        # Solve the LP problem
        start_time = time.time()
        solutions, requires, costs = graph_select.select_services(named_graph)
        selection_duration = time.time() - start_time
        selected_graphs = []
        for solution in solutions:
            solution_number = solutions.index(solution)
            solution_output_path = os.path.join(
                selected_graph_output_path,
                f"selected_graph_solution_{solution_number}.json",
            )

            # Foreach new edge, add it to selected_graph
            solution_selected_graph = utils.setup_graph(self.namespaces)

            for c, s in named_graph.subject_objects(self.DPDO.flowsData):
                solution_selected_graph.add((c, self.DPDO.flowsData, s))
            for c, s in named_graph.subject_objects(RDF.type):
                solution_selected_graph.add((c, RDF.type, s))

            db_selected_graph = utils.setup_graph(self.namespaces)
            [
                db_selected_graph.add(
                    (
                        URIRef(graph_select.denormalize_name(edge.split("->")[0])),
                        getattr(self.DPDO, f"selected_{solution_number}"),
                        URIRef(graph_select.denormalize_name(edge.split("->")[1])),
                    )
                )
                for edge in solution["edges"]
            ]
            [
                db_selected_graph.add(
                    (
                        URIRef(graph_select.denormalize_name(edge.split("->")[0])),
                        getattr(self.DPDO, f"selected_{solution_number}"),
                        URIRef(graph_select.denormalize_name(edge.split("->")[1])),
                    )
                )
                for edge in requires[solution_number]
            ]
            [
                solution_selected_graph.add(
                    (
                        URIRef(graph_select.denormalize_name(edge.split("->")[0])),
                        getattr(self.DPDO, f"selected"),
                        URIRef(graph_select.denormalize_name(edge.split("->")[1])),
                    )
                )
                for edge in solution["edges"]
            ]
            [
                solution_selected_graph.add(
                    (
                        URIRef(graph_select.denormalize_name(edge.split("->")[0])),
                        getattr(self.DPDO, f"selected"),
                        URIRef(graph_select.denormalize_name(edge.split("->")[1])),
                    )
                )
                for edge in requires[solution_number]
            ]
            logger.debug(f"\n Pushing solution {solution_number} to GraphDb...:")

            data = db_selected_graph.serialize(format="turtle")
            headers = {"Content-Type": "application/x-turtle"}
            response = requests.post(
                f"{self.endpoint}/repositories/{self.repository}/statements",
                data=data,
                headers=headers,
            )
            if not response.status_code == 204:
                logger.error(
                    f"Something went wrong while pushing solution to {self.endpoint}",
                    response.status_code,
                )
                logger.error(response.text)
            logger.debug(f"\n Printing solution {solution_number}:")
            # for (
            #     node,
            #     p,
            #     service,
            # ) in solution_selected_graph.triples(
            #     ((None, getattr(self.DPDO, f"selected_{solution_number}"), None))
            # ):
            #     logger.debug(
            #         f"{utils.rdf(solution_selected_graph, node)}, {utils.rdf(solution_selected_graph, p)}, {utils.rdf(solution_selected_graph, service)}"
            #     )

            # Write selected_graph
            with open(
                solution_output_path,
                "w",
            ) as json_file:
                logger.debug("Saving selected graph...")
                json_file.write(
                    solution_selected_graph.serialize(format="json-ld", indent=4)
                )

            selected_graphs.append(solution_selected_graph)
        # logger.debug("Visualizing computed solutions")
        # visualize.process_directory_tree(self.scenario_path)

        return selected_graphs, costs, selection_duration

    def compare_solutions(self, selected_graphs, solution_path, costs):
        for solution, cost in zip(selected_graphs, costs):
            logger.debug(f"Comparing solution n° {selected_graphs.index(solution)}")
            expected_solution = utils.setup_graph(self.namespaces)
            expected_solution.parse(
                solution_path,
                format="turtle",
            )
            # Compare expected solution with computed solution
            if utils.graphs_are_equal(
                expected_solution, solution, [self.DPDO.flowsData, RDF.type]
            ):
                s = f"Expected solution matches solution {selected_graphs.index(solution)}!"
                # logger.info(s)
                return True, s, cost
        # logger.warning("No computed solution matches proposed one")
        return False, "No solution", -1
