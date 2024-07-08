import requests
import utils
import os
from . import utils

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


def load_ontology(file_path, endpoint, repository, named_graph, namespace):

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
        if response.status_code == 204:
            logger.info(f"{namespace} uploaded to {endpoint}")
        else:
            logger.error(
                f"Failed to load {namespace} to {endpoint}: status code {response.status_code}"
            )
        return response.status_code


def build_output_graph(path, graph_repository, named_graph):
    with open(path, "rb") as f:
        file_content = f.read()
        headers = {"Content-Type": "application/x-turtle", "Accept": "application/json"}

    upload_url = f"http://localhost:7200/repositories/{graph_repository}/rdf-graphs/service?graph={named_graph}"
    response = requests.post(upload_url, headers=headers, data=file_content)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.status_code


def check_or_create_repository(repository_name, repo_config_path, endpoint):
    # Verifica se il repository esiste
    response = requests.get(endpoint + "/repositories")
    response.raise_for_status()
    repositories = response.content.decode("utf-8")
    repository_exists = repository_name in repositories

    # Se il repository non esiste, crealo
    if not repository_exists:
        return create_repository(repository_name, repo_config_path, endpoint)
    else:
        logger.info("Repository already existing")
        return True


def delete_repository(repository_name, endpoint):

    response = requests.delete(f"{endpoint}/rest/repositories/{repository_name}")

    if response.status_code == 200:
        logger.info(f"Successfully deleted  repository '{repository_name}'.")
    else:
        logger.error(f"Couldn't delete repository '{repository_name}'.")
        logger.error(f"Status Code: {response.status_code}")
        logger.error(f"Text: {response.content}")


def create_repository(repository_name, repo_config_path, endpoint):
    with open(
        repo_config_path,
        "rb",
    ) as file:
        files = {"config": file}
        response = requests.post(f"{endpoint}/rest/repositories", files=files)

    if response.status_code != 201:
        logger.error(f"Failed to create repository: {response.text}")
        print(f"Response status code: {response.status_code}")
        print(f"Response text: {response.text}")
        return False
    response.raise_for_status()
    logger.info(f"Successfully created repository {repository_name}")
    return True


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
            return response.status_code >= 500
    except Exception as e:
        logger.exception(
            f"Something went wrong while checking for named graph {named_graph_uri}"
        )
        logger.exception(e.__doc__)
        logger.exception(str(e))
        return False


def post_ontology_on_db(namespace, local_path, endpoint, repository, named_graph):
    if not ontology_exists(endpoint, repository, named_graph, namespace):
        return load_ontology(local_path, endpoint, repository, named_graph, namespace)
    else:
        logger.info(f"{namespace} already in {endpoint}")
        return True


def setup_graphdb(
    graphdb_endpoint, graphdb_repository, repo_config_path, graphdb_named_graph
):
    return all(
        [
            check_or_create_repository(
                graphdb_repository, repo_config_path, graphdb_endpoint
            ),
            check_or_create_named_graph(
                graphdb_repository, graphdb_named_graph, graphdb_endpoint
            ),
        ]
    )
