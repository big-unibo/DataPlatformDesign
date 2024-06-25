from SPARQLWrapper import SPARQLWrapper, JSON, POST
from dotenv import load_dotenv
from rdflib import Graph, Namespace, URIRef
import os
import pytz
import utils
from rdflib.namespace import NamespaceManager, RDFS, Namespace, RDF
from owlready2 import get_ontology
import yaml
import requests
import sys
import json
from cplex import Cplex
import string
import random

variable_names = []


def rdf(triple):
    return matched_graph.namespace_manager.normalizeUri(triple)


def load_yaml(path):
    with open(path) as yml_file:
        try:
            return yaml.load(yml_file, Loader=yaml.FullLoader)
        except yaml.YAMLError as exc:
            logger.exception(exc)


def ontology_exists(endpoint, repository, named_graph, namespace):
    endpoint_url = f"{endpoint}/repositories/{repository}"
    query = f"""
    ASK WHERE {{
      GRAPH <{named_graph}> {{
        <{namespace}> ?p ?o .
      }}
    }}
    """
    response = requests.post(
        endpoint_url,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
    )

    if response.status_code != 200:
        raise Exception(f"Query failed with status code {response.status_code}")

    results = response.json()
    return results["boolean"]


def load_ontology(file_path, endpoint, repository, named_graph):
    endpoint_url = f"{endpoint}/repositories/{repository}"
    with open(file_path, "rb") as f:
        data = f.read()
        headers = {"Content-Type": "text/turtle"}
        response = requests.post(
            f"{endpoint_url}/rdf-graphs/service?graph={named_graph}",
            data=data,
            headers=headers,
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.status_code


def build_output_graph(path, graph_repository, named_graph):
    with open(path, "rb") as f:
        file_content = f.read()
        headers = {"Content-Type": "application/x-turtle", "Accept": "application/json"}

    upload_url = f"http://localhost:7200/repositories/{graph_repository}/rdf-graphs/service?graph={named_graph}"
    response = requests.post(upload_url, headers=headers, data=file_content)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.status_code


def check_or_create_repository(repository_name, endpoint):
    # Verifica se il repository esiste
    response = requests.get(endpoint + "/repositories")
    response.raise_for_status()
    repositories = response.content.decode("utf-8")
    repository_exists = repository_name in repositories

    # Se il repository non esiste, crealo
    if not repository_exists:
        create_repository(repository_name, endpoint)
    else:
        logger.info("Repository already existing")


def create_repository(repository_name, endpoint):
    # Crea il repository
    payload = {"config": "default"}
    response = requests.post(
        endpoint + "/repositories/" + repository_name, json=payload
    )
    response.raise_for_status()
    logger.info(f"Succesfully created repository {repository_name}")


def normalize_name(name):
    normalized = name.replace(PREFIX, "")
    if not normalized in variable_names:
        variable_names.append(normalized)
    return normalized


def check_or_create_named_graph(repository_name, named_graph_uri, endpoint):
    query = f"""
        CREATE GRAPH <{named_graph_uri}> ;
        INSERT DATA {{ GRAPH <{named_graph_uri}> {{ <ex:s1> <ex:p1> <ex:o1> }} }}
        """
    # Esecuzione della richiesta POST
    headers = {
        "Content-Type": "application/sparql-update",
    }
    try:
        response = requests.post(
            f"{endpoint}/repositories/{repository_name}/statements",
            data=query,
            headers=headers,
        )
        if response.status_code == 204:
            logger.info("Graph created and data inserted successfully")
            return True
        else:
            logger.exception(f"Error: {response.status_code}")
            logger.exception(response.text)
            return response.status_code == 500
    except Exception as e:
        logger.exception(
            f"Something went wrong while checking for named graph {named_graph_uri}"
        )
        logger.exception(e.__doc__)
        logger.exception(str(e))
        return False


def match_lakehouse_pattern(endpoint, repository_name, named_graph_uri, config):
    lakehouse_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX {config["prefix"]["DFD"]}: <{config["namespaces"]["DFD"]}>
        PREFIX {config["prefix"]["ServiceEcosystem"]}: <{config["namespaces"]["ServiceEcosystem"]}>
        PREFIX {config["prefix"]["TagTaxonomy"]}: <{config["namespaces"]["TagTaxonomy"]}>
        PREFIX {config["prefix"]["DPDO"]}: <{config["namespaces"]["DPDO"]}>

        INSERT {{
                GRAPH <{named_graph_uri}> {{
                ?c DPDO:implementedBy ServiceEcosystem:Lakehouse .
                ?datalake DPDO:implementedBy ServiceEcosystem:Lakehouse .
            }}
        }}
        WHERE {{
            ?datalake rdf:type DPDO:Repository .
            ?datalake DPDO:hasTag TagTaxonomy:Landing .
            ?datalake DPDO:flowsData+ ?repository .
            ?repository rdf:type DPDO:Repository .
            ?repository DPDO:flowsData+ ?dwh .
            ?dwh rdf:type DPDO:Repository .
            FILTER EXISTS {{
                ?datalake DPDO:flowsData+ ?dwh .
                ?dwh DPDO:hasTag TagTaxonomy:Multidimensional .
            }}
            FILTER EXISTS {{
                ?repository DPDO:hasTag TagTaxonomy:Relational .
            }}
            FILTER(?repository != ?dwh)
            {{
                ?datalake DPDO:flowsData+ ?pathRepository .
                ?pathRepository rdf:type DPDO:Repository .
            }}
        }}

    """

    lakehouse_headers = {
        "Content-Type": "application/sparql-update",
        # "Accept": "text/turtle",  # o "application/ld+json" se preferisci JSON-LD
    }
    response = requests.post(
        f"{endpoint}/repositories/{repository_name}/statements",
        data=lakehouse_query,
        headers=lakehouse_headers,
    )

    if response.status_code == 204:
        logger.info("Successfully checked for Lakehouse pattern.")
        return True
    else:
        logger.error(
            "Something went wrong while checking for Lakehouse", response.status_code
        )
        logger.error(response.content)
        return False


def match_dfd(endpoint, repository_name, named_graph_uri, config):
    match_query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX drl: <http://example.org/drl/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX {config["prefix"]["DPDO"]}: <{config["namespaces"]["DPDO"]}>
        INSERT
        {{
            GRAPH <{named_graph_uri}>
            {{
                ?node DPDO:implementedBy ?service .
            }}
        }}
        WHERE {{
            ?node rdf:type DPDO:DFDNode .
            ?node DPDO:hasTag ?nodeTag .
            ?service rdf:type DPDO:Service .
            ?service DPDO:hasTag ?serviceTag .
            FILTER NOT EXISTS {{
                ?node DPDO:hasTag ?tag .
                FILTER NOT EXISTS {{
                    ?service DPDO:hasTag ?service_tag .
                    ?tag rdfs:subClassOf* ?service_tag .
                }}
            }}
        }}
    """

    match_headers = {
        "Content-Type": "application/sparql-update",
        # "Accept": "text/turtle",  # o "application/ld+json" se preferisci JSON-LD
    }

    response = requests.post(
        f"{endpoint}/repositories/{repository_name}/statements",
        data=match_query,
        headers=match_headers,
    )

    if response.status_code == 204:
        logger.info("Successfully matched DFD and Service Graph.")
    else:
        logger.error("Couldn't match DFD: HTTP error code:", response.status_code)
        logger.error(response.content)

    return save_matched_graph(endpoint, repository_name, named_graph_uri, config)


def save_matched_graph(endpoint, repository_name, named_graph_uri, config):
    matched_graph_query = f"""
        PREFIX {config["prefix"]["DPDO"]}: <{config["namespaces"]["DPDO"]}>

        SELECT ?node ?p ?o
        WHERE {{
            GRAPH <{named_graph_uri}>{{
            ?node DPDO:implementedBy ?service .
            ?node ?p ?o 
            }}
        }}
    """
    matched_graph_headers = {
        "Content-Type": "application/sparql-query",
        "Accept": "application/ld+json",  # o "application/ld+json" se preferisci JSON-LD
    }
    response = requests.get(
        f"{endpoint}/repositories/{repository_name}/statements",
        params={"query": matched_graph_query},
        headers=matched_graph_headers,
    )
    response.raise_for_status()

    if response.status_code == 200:
        logger.info("Retrieved matched graph")
        with open(os.path.join("output", "matched_graph.json"), "w") as write_file:
            json.dump(response.json(), write_file, indent=4)
        return True
    else:
        logger.error(response.status_code)
        logger.error(response.text)
        return False


def post_ontology_on_db(namespace, local_path, endpoint, repository, named_graph):
    if not ontology_exists(endpoint, repository, named_graph, namespace):
        status_code = load_ontology(local_path, endpoint, repository, named_graph)
        if status_code == 204:
            logger.info(f"{namespace} uploaded to {endpoint}")
            return True
        else:
            logger.error(
                f"Failed to load {namespace} to {endpoint}: status code {status_code}"
            )
            return False
    else:
        logger.info(f"{namespace} already in {endpoint}")
        return True


def setup_graph(graphdb_endpoint, graphdb_repository, graphdb_named_graph):
    check_or_create_repository(graphdb_repository, graphdb_endpoint)
    check_or_create_named_graph(
        graphdb_repository, graphdb_named_graph, graphdb_endpoint
    )


def get_require_edges(graph):
    requires_query = f"""SELECT ?node ?service ?serviceRequirement WHERE {{
    {{
        ?node DPDO:implementedBy ?service .
        ?service DPDO:requires ?serviceRequirement .
    }}
    }}
                        """
    result = graph.query(requires_query)

    service_requirements_dict = {}
    for node, service, serviceRequirement in result:
        if node not in service_requirements_dict:
            service_requirements_dict[node] = []
        if service not in service_requirements_dict[node]:
            service_requirements_dict[node].append(service)
        service_requirements_dict[node].append(serviceRequirement)

    return [
        [f"{normalize_name(node)}->{normalize_name(service)}" for service in services]
        for node, services in service_requirements_dict.items()
    ]


def get_minimal_coverage(graph):
    minimal_coverage = f"""SELECT ?node ?service WHERE {{
                        ?node <{DPDO.implementedBy}> ?service .
                    }}
                    """
    result = graph.query(minimal_coverage)
    minimal_coverage_dict = {}
    for node, service in result:
        if node not in minimal_coverage_dict:
            minimal_coverage_dict[node] = []
        minimal_coverage_dict[node].append(service)

    return {
        tuple(
            f"{normalize_name(node)}->{normalize_name(service)}" for service in services
        )
        for node, services in minimal_coverage_dict.items()
    }


def get_implementedby_edges(graph):
    implementedby_query = f"""SELECT ?node ?service WHERE {{
                    ?node <{DPDO.implementedBy}> ?service .
                }}
                """
    result = graph.query(implementedby_query)
    return [
        f"{normalize_name(node)}->{normalize_name(service)}" for node, service in result
    ]


def get_implementedby_services(graph):
    implementedby_query = f"""SELECT ?service WHERE {{
                    ?node <{DPDO.implementedBy}> ?service .
                }}
                """
    result = graph.query(implementedby_query)
    return list(set([f"{normalize_name(str(service[0]))}" for service in result]))


def get_dataflows(graph):
    dfd_edges = f"""SELECT ?node ?nextNode WHERE {{
                    ?node <{DPDO.flowsData}> ?nextNode .
                }}
                """
    result = graph.query(dfd_edges)
    dfd_edges_dict = {}
    for node, followingNode in result:
        if node not in dfd_edges_dict:
            dfd_edges_dict[node] = []
        dfd_edges_dict[node].append(str(followingNode))

    return [
        (str(normalize_name(node)), [normalize_name(service) for service in services])
        for node, services in dfd_edges_dict.items()
    ]


def get_compatible_services(graph):
    compatible_services = f"""SELECT ?service ?compatibleService WHERE {{
                    ?service <{DPDO.isCompatible}> ?compatibleService .
                }}
                """
    result = graph.query(compatible_services)
    minimal_coverage_dict = {}
    for node, followingNode in result:
        if node not in minimal_coverage_dict:
            minimal_coverage_dict[node] = []
        minimal_coverage_dict[node].append(str(followingNode))

    return [
        (str(normalize_name(node)), [normalize_name(service) for service in services])
        for node, services in minimal_coverage_dict.items()
    ]


# Timezone
tz = pytz.timezone("Europe/Rome")
# Setup logger
logger = utils.setup_logger("DataPlat_Design")
# Load config
config = load_yaml("dataplatform_design/src/resources/config.yml")

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
PREFIX = "http://www.semanticweb.org/manuele.pasini2/ontologies/2024/4/"

# Setup GraphDB environment by creating repository & named graph
setup_graph(GRAPHDB_ENDPOINT, GRAPHDB_REPOSITORY, GRAPHDB_NAMED_GRAPH)

# Push input ontologies into GraphDB
if not all(
    ontology
    for ontology in [
        # Return True if ontology is already present or successfully pushed to DB
        post_ontology_on_db(
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


matched_graph = Graph()
namespace_manager = NamespaceManager(matched_graph)
matched_graph.namespace_manager = namespace_manager

# Add namespaces to graph
[
    namespace_manager.bind(name, Namespace(namespace), override=False)
    for name, namespace in NAMESPACES.items()
]

# Load DPDO into graph
matched_graph.parse(config["ontologies"]["paths"]["DPDO"], format="turtle")


# Embed lakehouse patterns
if match_lakehouse_pattern(
    GRAPHDB_ENDPOINT, GRAPHDB_REPOSITORY, GRAPHDB_NAMED_GRAPH, config["ontologies"]
) & match_dfd(
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

    minimal_coverage = get_minimal_coverage(named_graph)
    requires_edges = get_require_edges(named_graph)
    implementedby_edges = get_implementedby_edges(named_graph)
    dfd_edges = get_dataflows(named_graph)
    compatibilities = get_compatible_services(named_graph)
    not_compatible_services = utils.find_not_compatible_edges(
        implementedby_edges, dfd_edges, compatibilities
    )
    implemented_services = get_implementedby_services(named_graph)

# minimal_coverage = [
#     (f"{node}->{service}") for service in minimal_coverage_dict[node]]
#     for node in minimal_coverage_dict.keys()
# ]

##############################
# 2.1 CONSTRAINTS DEFINITION #
##############################

### 4th Constraint - Services' minimal coverage
fourth_constraint = [[list(t), [1 for _ in enumerate(t)]] for t in minimal_coverage]
fourth_constraint_names = ["c" + str(i) for i, _ in enumerate(fourth_constraint)]
fourth_rhs = [1 for _ in enumerate(fourth_constraint)]
fourth_constraint_senses = ["E" for _ in enumerate(fourth_constraint)]

### 5th Constraint - Services' requirements
fifth_constraint = [
    [constraint, [-1] + [1 for _ in range(len(constraint) - 1)]]
    for constraint in requires_edges
]
fifth_constraint_names = ["r" + str(i) for i, _ in enumerate(fifth_constraint)]
fifth_rhs = [0 for _ in fifth_constraint]
fifth_constraint_senses = ["E" for _ in fifth_constraint]

### 6th Constraint - Services' compatibilities
not_compatible_services = utils.find_not_compatible_edges(
    implementedby_edges, dfd_edges, compatibilities
)
sixth_constraint = [
    [[f"{source[0]}->{source[1]}", f"{dest[0]}->{dest[1]}"], [1, 1]]
    for source, dest in not_compatible_services
]
sixth_rhs = [1 for _ in sixth_constraint]
sixth_constraint_senses = ["L" for _ in sixth_constraint]
sixth_constraint_names = ["comp" + str(i) for i, _ in enumerate(sixth_constraint)]

### 7th Constraint - Services' edges
edges_constraint = [
    [[edge, edge.split("->")[1]], [1, -1]] for edge in implementedby_edges
] + [[[edge[0], edge[0].split("->")[1]], [1, -1]] for edge in requires_edges]
edges_constraint_names = ["edge" + str(i) for i, _ in enumerate(edges_constraint)]
edges_rhs = [0 for _ in edges_constraint]
edges_constraint_senses = ["L" for _ in edges_constraint]

#############################
# 2.2 PROBLEM FORMALIZATION #
#############################

problem = Cplex()
problem.set_problem_type(Cplex.problem_type.LP)
problem.objective.set_sense(problem.objective.sense.minimize)

# Setting problem's variable names: [implemented services + "ImplementBy" edges + "requires" edges]
variable_names = list(
    set(
        implementedby_edges
        + implemented_services
        + [constraint for sub_list in requires_edges for constraint in sub_list]
    )
)

# Setting variable's value bounds
lower_bounds = [0 for _ in variable_names]
upper_bounds = [1 for _ in variable_names]

# Setting variables' weights to minimize, weight(arch) = 0 since we don't want to minimize them
objective = [0 if "->" in variable else 1 for variable in variable_names]
# objective = utils.embed_preferences(variable_names, objective, preferences_path)

problem.variables.add(
    obj=objective, lb=lower_bounds, ub=upper_bounds, names=variable_names
)

# Adding constraints
problem.linear_constraints.add(
    lin_expr=fifth_constraint,
    senses=fifth_constraint_senses,
    rhs=fifth_rhs,
    names=fifth_constraint_names,
)

problem.linear_constraints.add(
    lin_expr=fourth_constraint,
    senses=fourth_constraint_senses,
    rhs=fourth_rhs,
    names=fourth_constraint_names,
)

problem.linear_constraints.add(
    lin_expr=sixth_constraint,
    senses=sixth_constraint_senses,
    rhs=sixth_rhs,
    names=sixth_constraint_names,
)

problem.linear_constraints.add(
    lin_expr=edges_constraint,
    senses=edges_constraint_senses,
    rhs=edges_rhs,
    names=edges_constraint_names,
)

# Solve the problem
problem.solve()

###########################
# 3. BUILD SELECTED GRAPH #
###########################

selected_services = []
selected_edges = []

# Explore solution
print("---------")
print("Problem Solution:")
print("---------")
for i, name in enumerate(problem.variables.get_names()):
    selected = problem.solution.get_values(i)
    print(f"{name}: {selected}")
    if "->" in name and selected:
        selected_edges.append(name)
    elif selected:
        selected_services.append(name)
print("---------")
print(f"Solution cost: {problem.solution.get_objective_value()}")

# selected_graph = utils.embed_selected_graph(
#     selected_graph, dfd_graph, selected_services, selected_edges, requires_edges
# )
# selected_graph.render(filename=path.join(output_path, "selected_graph"), format="svg")

for (
    node,
    p,
    service,
) in named_graph.triples(((None, DPDO.requires, None))):
    print(f"Node: {rdf(node)}, Predicate: {rdf(p)}, Object: {rdf(service)}")
