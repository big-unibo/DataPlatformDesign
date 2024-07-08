# Data Platform Match & Select Algorithm
This repository stores the implementation of "Process-Driven Design of Cloud Data Platforms" [...].
The match and select algorithm has been implemented in Python 3.9 and thus requires it to be run. The application relies on GraphDB to store knowledge graphs and SPARQL queries to perform the matching part of the algorithm.

The application returns all optimal solution to the optimization problem.
Upon execution, the matched and selected graphs will be available in the `/dataplatform_design/src/test/scenarios/scenario_{scenario_name}/output` directory in the form of .json knowledge graphs.

## Getting Started - Deploying the environment
The list of mandatory dependencies to successfully run the script is explicited inside `requirements.txt` file in the project root directory.

### Deploy GraphDB
A `docker-compose.yml` file is placed in the project root directory and allows to build a standalone GraphDB istance on your machine by running 
   ```sh
   docker-compose up
   ```
GraphDB UI can then be reached via browser at `http://{GRAPH_DB_IP}:7200`.

### Scenario setup
A template for a test scenarios can be found in `/dataplatform_design/resources/scenario_template`. Each scenario is organized as follows:

- `scenario_0/`: main directory of a scenario.
- `scenario_0/configs/`: contains config files.
  - `config.yml`: Stores the algorithm parameters (e.g. GraphDB ip address, ontologies namespaces, etc.).
  - `repo-config.ttl`: Stores the GraphDB repository configs, such as the ruleset (default OWL-Max).
- `scenario_0/input/`: defines scenario inputs.
  - `adds_constraint/`: represents additional constraints such as preferences and mandatories constraints.
    - `preferences.ttl`: Describes services to be preferred in algorithm solution.
    - `mandatories.ttl`: Describes services to be mandatory in algorithm solution.
  - `ontologies/`: Contains all ontologies needed to run scenario.
    - `DPDO.ttl`: Data Platform Design ontology, <u><b> should never be changed </b></u>.
    - `ServiceEcosystem.ttl`: Describes the services among which to choose the optimal subset
    - `TagTaxonomy.ttl`: Describes the tag taxonomy through which categorize services and data pipelines.
    - `DFD.ttl`: Describes the data pipeline to be implemented.
  - `solution/`:
    - `solution.ttl`: Expected scenario solution.
- `scenario_0/output/`: where the algorithm stores computed scenario solutions.
  - `matched_graph.json`: describes the matched graph in a knowledge graph .json file
  - `selected_graph_solution_{number}.ext`: Describes a possible optimal solution computed for the scenario

A new scenario can be created by running
   ```sh
   python dataplatform_design/src/test/create_test_scenario.py --scenario_name {scenario_name}
   ```
The script takes additional optional parameters such as:
- --service_ecosystem {service_ontology.ttlpath}
- --dfd {path_to_service_ontology.ttl}
- --tag_taxonomy {path_to_service_ontology.ttl}
- --solution {path_to_service_ontology.ttl}
- --preferences {path_to_service_ontology.ttl}
- --mandatories {path_to_service_ontology.ttl}

which specify the path of the ontologies to be copied into the scenario. <u>Please note that in case of using user-defined ontologies with different namespaces than the default ones, such ontologies' namespaces <b>must</b> be updated in </u> `/dataplatform_design/src/test/scenarios/scenario_{scenario_name}/configs/config.yml`.


