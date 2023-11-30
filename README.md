# Data Platform Match & Select Algorithm
This repository stores the implementation of "Towards a Process-Driven Design of Data Platforms" [...].
The match and select algorithm has been implemented in Python 3.9 and thus requires it to be run.
## Getting Started - Deploying the environment
The list of mandatory dependencies to successfully run the script is explicited inside `requirements.txt` file in the project root directory.
To ease the deploy and testing of the application, three ways have been provided to run the application:
### Docker-compose
Upon cloning the repository, simply open a bash shell inside the project directory and run
   ```sh
   docker-compose up
   ```

### Dev Container
The implementation has been carried out in Visual Studio Code and leverages a Dev Container which offers an isolated environment in which install dependencies and run applications. After cloning this repository to a folder, simply open it through Visual Studio Code and follow the guided procedure to build the container and work inside it.
### Manual installation
Dependencies might also be installed in a host machine without leveraging any isolated environment. 
To run the application, simply install the dependencies listed in **requirements.txt** file in the root project directory by opening a bash shell inside it and running
   ```sh
   pip install -r requirements.txt
   ```
However, this project leverages the [Graphviz](https://pypi.org/project/graphviz/) library to draw the output graphs; upon installing the needed dependencies, <u>Graphviz binaries **MUST** be added to the PATH variable on your host machine.</u>
## Launch the application
In order to launch the application, open a bash shell inside project root folder and run
   ```sh
   python src/match_and_select.py
   ```
The script takes up to four arguments:
1. `--dfd_graph` - Defines the path of the Data Flow Diagram stored in a .json format.
2. `--service_graph` - Defines the path of the Service Graph stored in a .json format.
3. `--preferences` - Defines the path of the list of services' preferences stored in a .txt format.
4. `--output_path` - Defines the folder in which store the output graphs.

Default values are given for each parameter so none of them is mandatory. Launching the application without parameters will result in the script looking for input graphs and preferences in the `input` folder and storing outputs in the `output` folder.

## Input semantics
The implementation leverages a nested **.json** representation of input graphs while preferences are stored in a **text** file.
   ### Service graph
   The service graph is represented through a list of JSON entries, where each entry is considere a service and described through the following semantics:
   ```json
"PostGIS": {
	"label": "Service",
	"properties": {
		"Variety (All)": {
			"Structured": ["Relational"]
		},
		"Data nature (All)": {
			"Spatial": ["Vectorial"]
		},
		"Volume (All)": ["Small", "Big"],
		"Goal (All)": {
			"Operational": []
		},
		"requires": ["EC2"],
		"isCompatible": [
			"Kinesis",
			"Sagemaker",
			"Lambda",
			"EMR"]
}
   ```
where 
1. `requires` defines the list of third service requirements for this service
2. `isCompatible`define the list of services this is compatible to

A more detailed and complete version can be found in `input/service_graph.json`.
### Data Flow Diagram
A Data Flow Diagram is represented through a list of JSON entries, where each entry defines a node in the graph and each node is described through the following semantics:
   ```json
"Sensor Data": {
	"label": "Repository",
		"properties": {
			"Variety (All)": {
				"Structured": ["Relational"]
			},
			"Data nature (All)": {
				"Spatial": ["Vectorial"]
			},
			"Volume (All)": ["Small"]
		},
		"edges": ["Enrich"]
}
   ```
  where 
  1. `edges` defines the nodes this one links to, following the edge **Sensor Data -> Enrich**.

A more detailed and complete version can be found in `input/dfd_graph.json`.
### Preferences
Services preferences are listed in a text file, where each row defines a preference:
   ```txt
   S3
   Sagemaker
   ```
   Such file will assign to each service a default weight of 0.5 in the objective function. <u>It is **mandatory** that preferences names match the names inside the service graph</u>, otherwise preferences will not be taken into account.