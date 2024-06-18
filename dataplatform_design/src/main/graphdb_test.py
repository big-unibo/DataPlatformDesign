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


def lakehouse_pattern(endpoint, repository_name, named_graph_uri, config):
    lakehouse_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX {config["prefix"]["DFD"]}: <{config["namespaces"]["DFD"]}>
        PREFIX {config["prefix"]["ServiceEcosystem"]}: <{config["namespaces"]["ServiceEcosystem"]}>
        PREFIX {config["prefix"]["TagTaxonomy"]}: <{config["namespaces"]["TagTaxonomy"]}>
        PREFIX {config["prefix"]["DPDO"]}: <{config["namespaces"]["DPDO"]}>

        INSERT {{
                GRAPH <{named_graph_uri}>
            {{
                ?datalake DPDO:implementedBy ServiceEcosystem:Lakehouse .
                ?dwh DPDO:implementedBy ServiceEcosystem:Lakehouse .
                ?repository DPDO:implementedBy ServiceEcosystem:Lakehouse .
            }}
        }}
        WHERE {{
            ?datalake rdf:type DPDO:Repository .
            ?datalake DPDO:hasTag TagTaxonomy:File .
            ?datalake DPDO:flowsData+ ?repository .
            ?repository rdf:type DPDO:Repository.
            ?repository DPDO:flowsData+ ?dwh .
            ?dwh rdf:type DPDO:Repository.
            FILTER EXISTS {{
                ?datalake DPDO:flowsData+ ?dwh .
                ?dwh DPDO:hasTag TagTaxonomy:Multidimensional
            }}
            FILTER(?repository != ?dwh)
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

    matched_graph_query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX {config["prefix"]["DPDO"]}: <{config["namespaces"]["DPDO"]}>

    SELECT ?node ?service
    WHERE {{
        ?node DPDO:implementedBy ?service .
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
        return response.text
    else:
        logger.error(response.status_code)
        logger.error(response.text)
        return None


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
if lakehouse_pattern(
    GRAPHDB_ENDPOINT, GRAPHDB_REPOSITORY, GRAPHDB_NAMED_GRAPH, config["ontologies"]
):
    test = match_dfd(
        GRAPHDB_ENDPOINT,
        GRAPHDB_REPOSITORY,
        GRAPHDB_NAMED_GRAPH,
        config["ontologies"],
    )
    # # Load matched graph
    matched_graph.parse(
        data=match_dfd(
            GRAPHDB_ENDPOINT,
            GRAPHDB_REPOSITORY,
            GRAPHDB_NAMED_GRAPH,
            config["ontologies"],
        ),
        format="json-ld",
    )


for (
    s,
    p,
    o,
) in matched_graph.triples(((None, DPDO.implementedBy, None))):
    print(f"Subject: {rdf(s)}, Predicate: {rdf(p)}, Object: {rdf(o)}")
