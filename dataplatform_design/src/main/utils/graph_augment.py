import os
import requests
import json
from . import utils
from rdflib import Namespace

logger = utils.setup_logger("DataPlat_Design_Augmentation_Graph")
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


def augment_graph(graph):
    return embed_mandatories(graph)


def embed_mandatories(graph):

    mandatories_query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        DELETE {{
            ?s {DPDO.implementedBy} ?c .
        }}
        INSERT {{
            ?s {DPDO.implementedBy} ?o .
        }}
        WHERE {{
            ?s rdf:type {DPDO.DFDNode} .
            ?s {DPDO.isMandatory} ?o .
            OPTIONAL {{
                ?s {DPDO.implementedBy} ?c .
            }}
        }}
    """

    try:
        # graph.query(mandatories_query)
        return graph
    except Exception as e:
        logger.exception("Something went wrong during graph augmentation..")
        logger.exception(e.__doc__)
        logger.exception(str(e))
