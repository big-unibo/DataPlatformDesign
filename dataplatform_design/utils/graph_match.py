import os
import requests
import json
import utils
from rdflib import Namespace

logger = utils.setup_logger("DataPlat_Design_Match_Graph")
# Load config
config = utils.load_yaml(
    os.path.join("dataplatform_design", "resources", "configs", "config.yml")
)

PREFIX = config["prefix"]
DPDO = Namespace(config["ontologies"]["namespaces"]["DPDO"])
TAG_TAXONOMY = Namespace(config["ontologies"]["namespaces"]["TagTaxonomy"])
SERVICE_ECOSYSTEM = Namespace(config["ontologies"]["namespaces"]["ServiceEcosystem"])


def match_lakehouse_pattern(endpoint, repository_name, named_graph_uri, config):
    lakehouse_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        INSERT {{
                GRAPH <{named_graph_uri}> {{
                ?pathRepository <{DPDO.implementedBy}> <{SERVICE_ECOSYSTEM.Lakehouse}> .
                ?datalake <{DPDO.implementedBy}> <{SERVICE_ECOSYSTEM.Lakehouse}> .
            }}
        }}
        WHERE {{
            ?datalake rdf:type <{DPDO.Repository}> .
            ?datalake <{DPDO.hasTag}> <{TAG_TAXONOMY.Landing}> .
            ?datalake <{DPDO.flowsData}>+ ?repository .
            ?repository rdf:type <{DPDO.Repository}> .
            ?repository <{DPDO.flowsData}>+ ?dwh .
            ?dwh rdf:type <{DPDO.Repository}> .
            FILTER EXISTS {{
                ?datalake <{DPDO.flowsData}>+ ?dwh .
                ?dwh <{DPDO.hasTag}> <{TAG_TAXONOMY.Multidimensional}> .
            }}
            FILTER EXISTS {{
                ?repository <{DPDO.hasTag}> <{TAG_TAXONOMY.Relational}> .
            }}
            FILTER(?repository != ?dwh)
            {{
                ?datalake <{DPDO.flowsData}>+ ?pathRepository .
                ?pathRepository rdf:type <{DPDO.Repository}> .
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


def build_matched_graph(endpoint, repository_name, named_graph_uri, config):
    match_query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX drl: <http://example.org/drl/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT
        {{
            GRAPH <{named_graph_uri}>
            {{
                ?node <{DPDO.implementedBy}> ?service .
            }}
        }}
        WHERE {{
            ?node rdf:type <{DPDO.DFDNode}> .
            ?node <{DPDO.hasTag}> ?nodeTag .
            ?service rdf:type <{DPDO.Service}> .
            ?service <{DPDO.hasTag}> ?serviceTag .
            FILTER NOT EXISTS {{
                ?node <{DPDO.hasTag}> ?tag .
                FILTER NOT EXISTS {{
                    ?service <{DPDO.hasTag}> ?service_tag .
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

    return save_matched_graph(endpoint, repository_name, named_graph_uri)


def save_matched_graph(endpoint, repository_name, named_graph_uri):
    matched_graph_query = f"""
        SELECT ?node ?p ?o
        WHERE {{
            GRAPH <{named_graph_uri}>{{
            ?node <{DPDO.implementedBy}> ?service .
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
        with open(
            os.path.join(
                "dataplatform_design", "resources", "output", "matched_graph.json"
            ),
            "w",
        ) as write_file:
            json.dump(response.json(), write_file, indent=4)
        return True
    else:
        logger.error(response.status_code)
        logger.error(response.text)
        return False
