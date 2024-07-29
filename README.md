# Optimizing blueprints of cloud data platforms

[![build](https://github.com/big-unibo/DataPlatformDesign/actions/workflows/build.yml/badge.svg)](https://github.com/big-unibo/DataPlatformDesign/actions/workflows/build.yml)

## Research papers

This repository contains the implementation of the following research paper:

- Francia, Matteo, Golfarelli Matteo, and Pasini Manuele. "Process-Driven Design of Cloud Data Platforms". Submitted to **Information Systems** (2024) 

## Getting Started

Main features

- The application works with scenarios, each of them defining a data pipeline to be implemented with respect to a certain service ecosystem and a taxonomy of tags.
- The match and select algorithm has been implemented in Python 3.9 and thus requires it to be run. The application relies on GraphDB (reachable via browser at `http://127.0.0.1:7200`) to store knowledge graphs and SPARQL queries to perform the matching part of the algorithm.
- The application returns all optimal solution to the optimization problem.
- Upon execution, the matched and selected graphs will be available in the `/dataplatform_design/src/test/scenarios/scenario_{scenario_name}/output` directory in the form of `.json` knowledge graphs and a visual `.png` representation.

Running the approach

- The steps necessary to run the approach can be found in the Github action [build](https://github.com/big-unibo/DataPlatformDesign/blob/master/.github/workflows/build.yml)
- The list of mandatory (Python) dependencies to successfully run the script is explicited inside `requirements.txt` file in the project root directory.

### Scenario setup

A template for a design scenario can be found in `/dataplatform_design/resources/scenario_template`. Each scenario is organized as follows:

- `scenario_0/`: main directory of a scenario.
- `scenario_0/configs/`: contains config files.
  - `config.yml`: Stores the algorithm parameters (e.g. GraphDB ip address, ontologies namespaces, etc.);
  - `repo-config.ttl`: Stores the GraphDB repository configs, such as the ruleset (default OWL-Max).
- `scenario_0/input/`: defines scenario inputs.
  - `adds_constraint/`: represents additional constraints such as preferences and mandatories constraints.
    - `preferences.ttl`: Describes services to be preferred in algorithm solution.
  - `ontologies/`: Contains all ontologies needed to run scenario.
    - `DPDO.ttl`: Data Platform Design ontology, <u><b> should never be changed </b></u>;
    - `ServiceEcosystem.ttl`: Describes the services among which to choose the optimal subset. (default: AWS service ecosystem).
    - `TagTaxonomy.ttl`: Describes the tag taxonomy through which categorize services and data pipelines;
    - `DFD.ttl`: Describes the data pipeline to be implemented.
  - `solution/`:
    - `solution.ttl`: Expected scenario solution.
- `scenario_0/output/`: where the algorithm stores computed scenario solutions.
  - `matched_graph.json`: describes the matched graph in a knowledge graph .json file;
  - `matched_graph.png`: visual representation of matched graph;
  - `selected_graph_solution_{number}.json`: json representation for solution {number};
  - `selected_graph_solution_{number}.png`: visual representation of solution {number}.

A new scenario can be created by running

   ```sh
   python dataplatform_design/src/test/create_test_scenario.py --scenario_name {scenario_name}
   ```

<u>Please note that in case of using user-defined ontologies with different namespaces than the default ones, such ontologies' namespaces and prefixes <b>must</b> be updated in </u> `/dataplatform_design/src/test/scenarios/scenario_{scenario_name}/configs/config.yml`.

### Testing scenarios

Once scenarios have been defined, all of them can be tested via

   ```sh
   python dataplatform_design/src/test/test_solutions.py
   ```

Such script will compute the optimal set of services implementing the DFD for each scenario, and will compare each computed solution to the proposed one, returning true if <u>for each scenario</u>, one of the computed solution matches the proposed one.
