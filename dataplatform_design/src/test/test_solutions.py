import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../resources"))
)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../main/")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../test/")))

import test_utils
from utils import utils
from dataplatform_designer import DataPlatformDesigner
import unittest

logger = utils.setup_logger("DataPlat_Design_Test")


def get_path(folder):
    return os.path.join("dataplatform_design", "src", "test", "scenarios", folder)


def test_scenarioI(self, scenario_directory, n_solutions=1):
    test_utils.normalize_repositories_names(
        [
            os.path.join(scenario_directory, "configs", "config.yml"),
            os.path.join(scenario_directory, "configs", "repo-config.ttl"),
        ],
        scenario_directory.split(os.sep)[-1],
    )

    scenario_config_path = os.path.join(scenario_directory, "configs", "config.yml")
    # Load config
    config = utils.load_yaml(scenario_config_path)

    # GraphDB endpoint
    GRAPHDB_ENDPOINT = config["graph_db"]["endpoint"]
    GRAPHDB_REPOSITORY = config["graph_db"]["repository"]
    GRAPHDB_NAMED_GRAPH = config["graph_db"]["named_graph"]

    # logger.info(f"Running scenario {scenario_directory}")

    # .ttl paths representing ontologies
    NAMESPACES = config["ontologies"]["namespaces"]

    # Remove all files from the folder
    if os.path.exists(os.path.join(scenario_directory, "output")):
        for file_name in os.listdir(os.path.join(scenario_directory, "output")):
            file_path = os.path.join(
                os.path.join(scenario_directory, "output"), file_name
            )
            if os.path.isfile(file_path):
                os.remove(file_path)

    matched_graph_path = os.path.join(
        scenario_directory, "output", "matched_graph.json"
    )
    selected_graph_path = os.path.join(scenario_directory, "output")
    solution_path = config["ontologies"]["solution"]

    dataplat_designer = DataPlatformDesigner(
        GRAPHDB_ENDPOINT,
        GRAPHDB_REPOSITORY,
        GRAPHDB_NAMED_GRAPH,
        NAMESPACES,
        scenario_directory,
    )

    dataplat_designer.setup_config(config)

    dataplat_designer.setup_graph_db(
        os.path.join(scenario_directory, "configs", "repo-config.ttl")
    )

    dataplat_designer.load_ontologies(
        [
            (path, namespace)
            for path, namespace in reversed(
                list(
                    zip(
                        config["ontologies"]["paths"].values(),
                        config["ontologies"]["namespaces"].values(),
                    )
                )
            )
        ]
    )

    dataplat_designer.add_constraints(
        config["ontologies"]["adds_constraints_paths"].values()
    )

    # Building matched graph
    matched_graph = dataplat_designer.build_matched_graph(
        config["ontologies"]["paths"]["dpdo"],
        matched_graph_path,
    )

    # Augmenting matched graph
    matched_graph = dataplat_designer.augment_graph(matched_graph)

    # Building selected graph
    selected_graphs, costs = dataplat_designer.build_selected_graph(
        matched_graph,
        selected_graph_path,
    )

    # Compare solution to given one
    res, s, solution_cost = dataplat_designer.compare_solutions(
        selected_graphs, solution_path, costs
    )
    self.assertTrue(res)
    self.assertEqual(len(selected_graphs), n_solutions)
    # assert result, f"Testing {scenario_directory}, result: {result}"


class TestSolutions(unittest.TestCase):

    def test_requires01(self):
        test_scenarioI(self, get_path("requires01"))

    def test_requires02(self):
        test_scenarioI(self, get_path("requires02"))

    def test_mandatory01(self):
        test_scenarioI(self, get_path("mandatory01"))

    def test_isAkin01(self):
        test_scenarioI(self, get_path("isAkin01"))

    def test_isAkin02(self):
        test_scenarioI(self, get_path("isAkin02"))

    def test_isAkin03(self):
        try:
            test_scenarioI(self, get_path("isAkin03"))
        except Exception as e:
            logger.exception(e.__doc__)
            return True

    def test_isCompatible01(self):
        test_scenarioI(self, get_path("isCompatible01"))

    def test_lakehouse01(self):
        test_scenarioI(self, get_path("lakehouse01"))

    def test_lakehouse02(self):
        test_scenarioI(self, get_path("lakehouse02"))

    def test_lakehouse03(self):
        test_scenarioI(self, get_path("lakehouse03"))

    def test_lakehouse04(self):
        test_scenarioI(self, get_path("lakehouse04"))

    def test_isCompatible02(self):
        test_scenarioI(self, get_path("isCompatible02"))

    def test_ico01(self):
        test_scenarioI(self, get_path("ico01"), n_solutions=2)

    def test_ico02(self):
        test_scenarioI(self, get_path("ico02"), n_solutions=1)

    def test_watering(self):
        test_scenarioI(self, get_path("watering"), n_solutions=2)
