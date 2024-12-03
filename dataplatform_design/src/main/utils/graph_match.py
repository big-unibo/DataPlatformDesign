import os
import requests
import json
from . import utils
from rdflib import Namespace, Graph, URIRef
import rdflib
import time

logger = utils.setup_logger("DataPlat_Design_Match_Graph")
# Load config
config = utils.load_yaml(
    os.path.join(
        "/",
        "dataplatform_design",
        "dataplatform_design",
        "resources",
        "scenario_template",
        "configs",
        "config.yml",
    )
)


def setup_config(scenario_config):
    global config
    config = scenario_config


PREFIX = config["prefix"]
DPDO = Namespace(config["ontologies"]["namespaces"]["dpdo"])
TAG_TAXONOMY = Namespace(config["ontologies"]["namespaces"]["tag_taxonomy"])
SERVICE_ECOSYSTEM = Namespace(config["ontologies"]["namespaces"]["service_ecosystem"])


def match_lakehouse_pattern(
    endpoint, repository_name, named_graph_uri, matched_graph_path, namespaces
):

    lakehouse_query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?datalake ?pathRepository ?dwh
        WHERE {{
            ?datalake rdf:type <{DPDO.Repository}> .
            ?datalake <{DPDO.hasTag}> <{TAG_TAXONOMY.Landing}> .
            OPTIONAL {{
                ?datalake <{DPDO.flowsData}>+ ?repository_pattern .
                ?repository_pattern rdf:type <{DPDO.Repository}> .
                ?repository_pattern <{DPDO.flowsData}>+ ?dwh .
                FILTER EXISTS {{
                    ?repository_pattern <{DPDO.hasTag}> <{TAG_TAXONOMY.Structured}> .
                }}
            }}
            ?dwh rdf:type <{DPDO.Repository}> .
            FILTER EXISTS {{
                ?datalake <{DPDO.flowsData}>+ ?dwh .
                ?dwh <{DPDO.hasTag}> <{TAG_TAXONOMY.Multidimensional}> .
            }}
            FILTER (?repository_pattern != ?dwh)
            {{
                ?datalake <{DPDO.flowsData}>+ ?pathRepository .
                ?pathRepository rdf:type <{DPDO.Repository}> .
            }}
            FILTER EXISTS{{
                ?datalake <{DPDO.implementedBy}> <{SERVICE_ECOSYSTEM.Lakehouse}> .
                ?pathRepository <{DPDO.implementedBy}> <{SERVICE_ECOSYSTEM.Lakehouse}> .
            }}

        }}
    """
    start_time = time.time()
    response = requests.post(
        f"{endpoint}/repositories/{repository_name}",
        data=lakehouse_query,
        headers={
            "Content-Type": "application/sparql-query",
            "Accept": "application/sparql-results+json",
        },
    )

    if response.status_code == 200:
        lakehouse_implements = response.json()

        lakehouse = []
        duration = 0
        if len(lakehouse_implements["results"]["bindings"]) > 0:
            for result in lakehouse_implements["results"]["bindings"]:
                datalake = result["datalake"]["value"]
                pathRepository = result["pathRepository"]["value"]
                dwh = result["dwh"]["value"]

                lakehouse.append(f"<{datalake}>")
                lakehouse.append(f"<{pathRepository}>")
                lakehouse.append(f"<{dwh}>")
            lakehouse = list(set(lakehouse))
            if len(lakehouse) > 0:
                delete_query = [f"\n?s != {dfd_node} " for dfd_node in lakehouse]

                delete_useless_lakehouse = f"""
                    DELETE {{
                        GRAPH <{named_graph_uri}> {{
                            ?s <{DPDO.implementedBy}> <{SERVICE_ECOSYSTEM.Lakehouse}> .
                        }}
                    }}
                    WHERE {{
                        GRAPH <{named_graph_uri}> {{
                            ?s <{DPDO.implementedBy}> <{SERVICE_ECOSYSTEM.Lakehouse}> .
                            FILTER({"&& ".join(delete_query)})
                        }}
                    }}
                """

                response = requests.post(
                    f"{endpoint}/repositories/{repository_name}/statements",
                    data=delete_useless_lakehouse,
                    headers={
                        "Content-Type": "application/sparql-update",
                    },
                )
                logger.debug("Successfully checked for Lakehouse pattern.")
            duration = time.time() - start_time
        return (
            save_matched_graph(
                endpoint, repository_name, named_graph_uri, matched_graph_path
            ),
            duration,
        )
    else:
        logger.error(
            "Something went wrong while checking for Lakehouse", response.status_code
        )
        logger.error(response.content)
        return False, 0


def build_matched_graph(endpoint, repository_name, named_graph_uri, match_graph_path):
    start_time = time.time()
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
    duration = time.time() - start_time
    dfd_implements_query = f"""SELECT ?node
    WHERE {{
        ?node a <{DPDO.DFDNode}> .
        FILTER NOT EXISTS{{
            ?node <{DPDO.implementedBy}> ?service .
            }}
    }}"""
    dfd_implements_response = requests.post(
        f"{endpoint}/repositories/{repository_name}",
        data=dfd_implements_query,
        headers={
            "Content-Type": "application/sparql-query",
            "Accept": "application/sparql-results+json",
        },
    )
    at_least_implement_query = f"""
        SELECT ?previous_node ?following_node
            WHERE {{
                ?previous_node <{DPDO.implementedBy}> ?service .

                ?following_node  <{DPDO.implementedBy}> ?another_service .

                ?previous_node <{DPDO.flowsData}> ?following_node .

                FILTER NOT EXISTS{{
                    ?service <{DPDO.isCompatible}> ?another_service .
                }}
                FILTER NOT EXISTS{{
                    ?previous_node <{DPDO.implementedBy}> ?yet_another_service .
                    ?following_node  <{DPDO.implementedBy}> ?yet_another_another_service .
                    ?yet_another_service <{DPDO.isCompatible}> ?yet_another_another_service .
                }}
            }}
    """
    dfd_compatible_response = requests.post(
        f"{endpoint}/repositories/{repository_name}",
        data=at_least_implement_query,
        headers={
            "Content-Type": "application/sparql-query",
            "Accept": "application/sparql-results+json",
        },
    )
    compatible_node_count = dfd_compatible_response.json()["results"]["bindings"]

    not_implements = dfd_implements_response.json()["results"]["bindings"]

    if (
        response.status_code == 204
        and len(not_implements) <= 0
        and len(compatible_node_count) <= 0
    ):
        logger.debug("Successfully matched DFD and Service Graph.")
    else:
        if len(not_implements) > 0:
            for not_implement in not_implements:
                logger.exception(
                    f"""Couldn't find implementedBy arc for {not_implement["node"]["value"]}"""
                )
            raise Exception(
                f"Couldn't find implementedBy arcs for DFD Nodes "
                + str(
                    [not_implement["node"]["value"] for not_implement in not_implements]
                )
            )
        elif len(compatible_node_count) > 0:
            for linked_nodes in compatible_node_count:
                previous_node = linked_nodes["previous_node"]["value"]
                following_node = linked_nodes["following_node"]["value"]
                logger.exception(
                    f"Couldn't find compatible services for ({previous_node}, {following_node})"
                )
            raise Exception(
                "Couldn't find compatible services for consecutive DFD nodes "
                + str(
                    [
                        (
                            linked_nodes["previous_node"]["value"],
                            linked_nodes["following_node"]["value"],
                        )
                        for linked_nodes in compatible_node_count
                    ]
                )
            )
        else:
            logger.error("Couldn't match DFD: HTTP error code:", response.status_code)
            logger.error(response.content)

    return (
        save_matched_graph(
            endpoint, repository_name, named_graph_uri, match_graph_path
        ),
        duration,
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
