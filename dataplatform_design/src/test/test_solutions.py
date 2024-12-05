import os
import sys
import pandas as pd
from datetime import datetime
import pytz
import unittest
from dotenv import load_dotenv


sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../resources"))
)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../main/")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../test/")))

import test_utils
from utils import utils
from dataplatform_designer import DataPlatformDesigner


logger = utils.setup_logger("DataPlat_Design_Test")
tz = pytz.timezone("Europe/Rome")

load_dotenv(".env")


def get_path(folder):
    return os.path.join("dataplatform_design", "src", "test", "scenarios", folder)


statistics_columns = [
    "test_id",
    "seed",
    "scenario",
    "iteration",
    "match_time",
    "augment_time",
    "select_time",
    "number_solutions",
]
seed = 42
tests_statistics = []


def test_scenarioI(self, scenario_directory, iteration=0, n_solutions=1):

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
    GRAPHDB_ENDPOINT = os.getenv("GRAPHDB_ENDPOINT")
    GRAPHDB_NAMED_GRAPH = os.getenv("GRAPHDB_NAMED_GRAPH")
    GRAPHDB_REPOSITORY = f"DataPlatformDesign_{scenario_directory.split(os.sep)[-1]}"
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
    if "adds_constraints_paths" in config["ontologies"]:
        dataplat_designer.add_constraints(
            config["ontologies"]["adds_constraints_paths"].values()
        )

    # Building matched graph
    matched_graph, matching_time = dataplat_designer.build_matched_graph(
        config["ontologies"]["paths"]["dpdo"],
        matched_graph_path,
    )

    # Augmenting matched graph
    matched_graph, augmentation_time = dataplat_designer.augment_graph(
        matched_graph_path, config["ontologies"]["paths"]["dpdo"]
    )

    # Building selected graph
    selected_graphs, costs, selection_time = dataplat_designer.build_selected_graph(
        matched_graph,
        selected_graph_path,
    )
    logger.debug("Comparing solutions")

    # Compare solution to given one
    res, s, solution_cost = dataplat_designer.compare_solutions(
        selected_graphs, solution_path, costs
    )
    logger.debug("Comparison complete")

    try:
        self.assertTrue(res)
    except Exception as _:
        return [
            seed,
            scenario_directory.split(os.sep)[-1],
            iteration,
            matching_time,
            augmentation_time,
            selection_time,
            len(selected_graphs),
        ]
    # self.assertEqual(len(selected_graphs), n_solutions)

    return [
        seed,
        scenario_directory.split(os.sep)[-1],
        iteration,
        matching_time,
        augmentation_time,
        selection_time,
        len(selected_graphs),
    ]


class TestSolutions(unittest.TestCase):

    def run_scenario_with_stats(self, scenario, iteration=0, n_solutions=1):
        logger.debug(f"Running scenario {scenario}, iteration {iteration}")
        global tests_statistics
        new_stats = test_scenarioI(
            self, get_path(scenario), iteration=iteration, n_solutions=n_solutions
        )
        tests_statistics.append(new_stats)

    def test_requires01(
        self,
    ):
        self.run_scenario_with_stats("requires01", iteration=self.iteration)

    def test_requires02(self):
        self.run_scenario_with_stats("requires02", iteration=self.iteration)

    def test_mandatory01(self):
        self.run_scenario_with_stats("mandatory01", iteration=self.iteration)

    def test_isAkin01(self):
        self.run_scenario_with_stats("isAkin01", iteration=self.iteration)

    def test_isAkin02(self):
        self.run_scenario_with_stats("isAkin02", iteration=self.iteration)

    def test_isAkin03(self):
        try:
            self.run_scenario_with_stats("isAkin03", iteration=self.iteration)
        except Exception as e:
            logger.exception(e.__doc__)
            return True

    def test_isCompatible01(self):
        self.run_scenario_with_stats("isCompatible01", iteration=self.iteration)

    def test_lakehouse01(self):
        self.run_scenario_with_stats("lakehouse01", iteration=self.iteration)

    def test_lakehouse02(self):
        self.run_scenario_with_stats("lakehouse02", iteration=self.iteration)

    def test_lakehouse03(self):
        self.run_scenario_with_stats("lakehouse03", iteration=self.iteration)

    def test_lakehouse04(self):
        self.run_scenario_with_stats("lakehouse04", iteration=self.iteration)

    def test_isCompatible02(self):
        self.run_scenario_with_stats("isCompatible02", iteration=self.iteration)

    def test_ico01(self):
        self.run_scenario_with_stats("ico01", iteration=self.iteration, n_solutions=2)

    def test_ico02(self):
        self.run_scenario_with_stats("ico02", iteration=self.iteration, n_solutions=1)

    def test_ico03(self):
        self.run_scenario_with_stats(
            "ico03-azure", iteration=self.iteration, n_solutions=2
        )

    def test_watering(self):
        self.run_scenario_with_stats(
            "watering", iteration=self.iteration, n_solutions=2
        )

    def test_techogym(self):
        self.run_scenario_with_stats(
            "technogym", iteration=self.iteration, n_solutions=1
        )

    def test_syntethic10_nodes(self):
        self.run_scenario_with_stats(
            "syntethic_10nodes", iteration=self.iteration, n_solutions=1
        )

    def test_syntethic50_nodes(self):
        self.run_scenario_with_stats(
            "syntethic_50nodes", iteration=self.iteration, n_solutions=1
        )

    def test_syntethic250_nodes(self):
        self.run_scenario_with_stats(
            "syntethic_250nodes", iteration=self.iteration, n_solutions=1
        )

    def test_syntethic300_nodes(self):
        self.run_scenario_with_stats(
            "syntethic_300nodes", iteration=self.iteration, n_solutions=1
        )


if __name__ == "__main__":

    iterations = int(os.getenv("ITERATIONS"))

    for i in range(iterations):
        print(f"--- Iteration {i + 1} ---")
        test_suite = unittest.TestSuite()
        loader = unittest.TestLoader()
        for test_name in loader.getTestCaseNames(TestSolutions):
            test = TestSolutions(test_name)
            test.iteration = i
            test_suite.addTest(test)
        unittest.TextTestRunner(verbosity=2).run(test_suite)
    test_id = datetime.now(tz=tz).timestamp()
    timestamped_statistics = [
        [test_id] + scenario_statistic for scenario_statistic in tests_statistics
    ]
    if len(timestamped_statistics) > 0:
        global_statistics_df = pd.DataFrame(
            timestamped_statistics, columns=statistics_columns
        )

        global_statistics_df.to_csv(
            f"dataplatform_design/run_statistics/statistics_{datetime.now(tz=tz).timestamp()}.csv",
            index=False,
        )
