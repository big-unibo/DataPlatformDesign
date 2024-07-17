import os
import requests
import json
from . import utils
from rdflib import Namespace

logger = utils.setup_logger("DataPlat_Design_Match_Graph")
# Load config
config = utils.load_yaml(
    os.path.join(
        "dataplatform_design", "resources", "scenario_template", "configs", "config.yml"
    )
)


def setup_config(scenario_config):
    global config
    config = scenario_config


PREFIX = config["prefix"]
DPDO = Namespace(config["ontologies"]["namespaces"]["dpdo"])
TAG_TAXONOMY = Namespace(config["ontologies"]["namespaces"]["tag_taxonomy"])
SERVICE_ECOSYSTEM = Namespace(config["ontologies"]["namespaces"]["service_ecosystem"])


def match_lakehouse_pattern(endpoint, repository_name, named_graph_uri):
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
            OPTIONAL{{
                ?datalake <{DPDO.flowsData}>+ ?repository .
                ?repository rdf:type <{DPDO.Repository}> .
                ?repository <{DPDO.flowsData}>+ ?dwh .

                FILTER EXISTS {{
                ?repository <{DPDO.hasTag}> <{TAG_TAXONOMY.Relational}> .
            }}
            }}
            ?dwh rdf:type <{DPDO.Repository}> .
            FILTER EXISTS {{
                ?datalake <{DPDO.flowsData}>+ ?dwh .
                ?dwh <{DPDO.hasTag}> <{TAG_TAXONOMY.Multidimensional}> .
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
        logger.debug("Successfully checked for Lakehouse pattern.")
        return True
    else:
        logger.error(
            "Something went wrong while checking for Lakehouse", response.status_code
        )
        logger.error(response.content)
        return False


def build_matched_graph(endpoint, repository_name, named_graph_uri, match_graph_path):
    match_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        INSERT {{
                GRAPH <{named_graph_uri}> {{
                ?node <{DPDO.implementedBy}> ?service .
                }}
            }}
        WHERE {{
            ?node rdf:type <{DPDO.DFDNode}> .
            ?node <{DPDO.hasTag}> ?nodeTag .

            ?service rdf:type <{DPDO.Service}> .
            ?service <{DPDO.hasTag}> ?serviceTag .

            ?nodeTag a ?dfd_tag_class .
            ?serviceTag a ?service_tag_class .

    		?service_tag_clas rdfs:subClassOf <{DPDO.Tag}> .
    		?dfd_tag_class rdfs:subClassOf <{DPDO.Tag}> .

            FILTER NOT EXISTS {{
                ?more_specific_service_class rdfs:subClassOf ?service_tag_class .
                ?serviceTag rdf:type ?more_specific_service_class .
            }}

            ?dfd_tag_class rdfs:subClassOf* ?service_tag_class .

            FILTER NOT EXISTS {{
                ?node <{DPDO.hasTag}> ?tag .
                FILTER NOT EXISTS {{
            		?service <{DPDO.hasTag}> ?service_tag .
                    ?tag a ?not_service_tag_class .
                    ?service_tag a ?not_dfd_tag_class .

            		?not_service_tag_class rdfs:subClassOf <{DPDO.Tag}> .
            		?not_dfd_tag_class rdfs:subClassOf <{DPDO.Tag}> .

                    ?not_dfd_tag_class rdfs:subClassOf* ?not_service_tag_class .

                    FILTER NOT EXISTS {{
                            ?more_specific_service_class rdfs:subClassOf ?not_service_tag_class .
                            ?service_tag rdf:type ?more_specific_service_class .
                        }}
               }}
            }}
            FILTER (?service != <{SERVICE_ECOSYSTEM.Lakehouse}>) .
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
        logger.debug("Successfully matched DFD and Service Graph.")
    else:
        logger.error("Couldn't match DFD: HTTP error code:", response.status_code)
        logger.error(response.content)

    return save_matched_graph(
        endpoint, repository_name, named_graph_uri, match_graph_path
    )


def save_matched_graph(endpoint, repository_name, named_graph_uri, match_graph_path):

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
        logger.debug("Retrieved matched graph")
        output_path = os.path.join(match_graph_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            with open(
                output_path,
                "w",
            ) as write_file:
                json.dump(response.json(), write_file, indent=4)
            logger.debug(f"Saved matched graph to {output_path}")
            return True
        except Exception as e:
            logger.exception(str(e))
            logger.exception(e.__doc__)
    else:
        logger.error(response.status_code)
        logger.error(response.text)
        return False
