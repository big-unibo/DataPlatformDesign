from SPARQLWrapper import SPARQLWrapper, JSON, POST
from dotenv import load_dotenv
from rdflib import Graph, Namespace, URIRef
import os
import pytz
import dataplatform_design.src.main.utils.utils as utils
from rdflib.namespace import NamespaceManager, RDFS, Namespace, RDF
from owlready2 import get_ontology
import yaml
import requests
import sys
import json
from cplex import Cplex
import string
import random

# Setup logger
logger = utils.setup_logger("DataPlat_Design_GraphDB_Utils")


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
