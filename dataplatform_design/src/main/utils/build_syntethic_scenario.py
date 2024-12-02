import os
import utils
from rdflib import Graph, URIRef
import random
import yaml

logger = utils.setup_logger("DataPlat_Design_Syntethic_Scenario_Builder")


class TreeNode:
    def __init__(self, value, depth=0):
        self.value = value
        self.depth = depth  # Livello del nodo nell'albero
        self.left = None
        self.right = None


def build_binary_dfd_tree(n, seed=None):
    """
    Costruisce un albero binario con esattamente `n` nodi. Ogni nodo ha due figli,
    ma solo uno dei due figli verrà esploso per continuare la costruzione dell'albero.

    Args:
        n (int): Numero totale di nodi da creare nell'albero.
        seed (int, optional): Seed per il generatore casuale per garantire risultati riproducibili.

    Returns:
        TreeNode: Radice dell'albero binario costruito.
    """
    if seed is not None:
        random.seed(seed)  # Imposta il seed per risultati riproducibili

    if n <= 0:
        return None

    root = TreeNode(1, depth=0)  # Nodo radice
    current_nodes = [root]  # Lista dei nodi pronti per essere espansi
    value = 2  # Valore iniziale per i nodi successivi
    created_nodes = 1  # Contatore dei nodi creati

    while created_nodes < n:
        current = current_nodes.pop(0)

        if created_nodes < n:
            left_child = TreeNode(value, depth=current.depth + 1)
            current.left = left_child
            value += 1
            created_nodes += 1

        if created_nodes < n:
            right_child = TreeNode(value, depth=current.depth + 1)
            current.right = right_child
            value += 1
            created_nodes += 1

        if current.left and current.right:
            chosen_child = random.choice([current.left, current.right])
            current_nodes.append(chosen_child)
        elif current.left:
            current_nodes.append(current.left)
        elif current.right:
            current_nodes.append(current.right)

    return root


def tag_and_save_dfd_tree(root, seed, ttl_file, services_ttl_file):
    """
    Esporta l'albero in formato Turtle (.ttl) e aggiunge i tag dai servizi.

    Args:
        root (TreeNode): Radice dell'albero binario.
        ttl_file (str): Percorso del file .ttl di output.
        services_ttl_file (str): Percorso del file dei servizi (.ttl) da cui estrarre i tag.
    """
    random.seed(seed)

    def get_node_type(depth):
        """
        Determina il tipo del nodo (Process o Repository) in base al livello.
        """
        return "DPDO:Process" if depth % 2 == 0 else "DPDO:Repository"

    def write_node_to_ttl(node, node_id, ttl_lines, service_tags_dict):
        """
        Scrive un nodo e le sue relazioni nel formato Turtle.
        """
        left_id = f"N{node.left.value}" if node.left else None
        right_id = f"N{node.right.value}" if node.right else None
        node_type = get_node_type(node.depth)

        ttl_lines.append(f"DFD:{node_id} rdf:type owl:NamedIndividual, {node_type};")
        if left_id:
            ttl_lines.append(f"    DPDO:flowsData DFD:{left_id};")
        if right_id:
            ttl_lines.append(f"    DPDO:flowsData DFD:{right_id};")

        # Seleziona un servizio casuale e usa i suoi tag
        service_name, tags = random.choice(list(service_tags_dict.items()))
        tag_1, tag_2 = tags

        # Usa il prefisso TagTaxonomy per i tag
        ttl_lines.append(f"    DPDO:hasTag TagTaxonomy:{tag_1}, TagTaxonomy:{tag_2};")

        ttl_lines.append(f'    DPDO:name "{node_id}".\n')

    def load_service_tags(services_ttl_file):
        """
        Carica le coppie di tag dai servizi nel file .ttl.
        """
        g = Graph()
        g.parse(services_ttl_file, format="turtle")

        # Predicato per i tag dei servizi
        predicate = URIRef(
            "http://www.foo.bar/dataplatform_design/ontologies/DPDO#hasTag"
        )

        service_tags_dict = {}

        for subject, pred, obj in g:
            if pred == predicate:
                service_name = str(subject).split("#")[
                    -1
                ]  # Estrae il nome del servizio dalla URI
                tag = str(obj).split("#")[-1]  # Estrae il tag dalla URI
                if service_name not in service_tags_dict:
                    service_tags_dict[service_name] = []
                service_tags_dict[service_name].append(tag)

        # Filtra solo i servizi con esattamente 2 tag
        valid_services = {
            service: tags
            for service, tags in service_tags_dict.items()
            if len(tags) == 2
        }

        return valid_services

    # Carica i tag dal file dei servizi
    service_tags_dict = load_service_tags(services_ttl_file)

    ttl_lines = [
        "@prefix DFD: <http://www.foo.bar/dataplatform_design/ontologies/DFD#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix DPDO: <http://www.foo.bar/dataplatform_design/ontologies/DPDO#> .",
        "@prefix TagTaxonomy: <http://www.foo.bar/dataplatform_design/ontologies/TagTaxonomy#> .",  # Aggiungi il prefisso TagTaxonomy
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "\n",
    ]

    # Uso di una visita in ampiezza per scrivere i nodi
    queue = [(root, f"N{root.value}")]  # Coda con (nodo, id nodo)
    while queue:
        node, node_id = queue.pop(0)
        write_node_to_ttl(node, node_id, ttl_lines, service_tags_dict)

        if node.left:
            queue.append((node.left, f"N{node.left.value}"))
        if node.right:
            queue.append((node.right, f"N{node.right.value}"))

    # Salva il file .ttl
    with open(ttl_file, "w") as f:
        f.write("\n".join(ttl_lines))
    print(f"File TTL salvato in: {ttl_file}")


def generate_services(tag_taxonomy, seed, num_services, output_file):
    prefix_lines = """
    @prefix ServiceEcosystem: <http://www.foo.bar/dataplatform_design/ontologies/ServiceEcosystem#>.
    @prefix TagTaxonomy: <http://www.foo.bar/dataplatform_design/ontologies/TagTaxonomy#>.
    @prefix DPDO: <http://www.foo.bar/dataplatform_design/ontologies/DPDO#>.
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.
    @prefix owl: <http://www.w3.org/2002/07/owl#>.
    """
    random.seed(seed)

    with open(output_file, "w") as ttl_file:
        ttl_file.write(prefix_lines)

        for i in range(1, num_services + 1):
            service_id = f"S{i}"
            service_uri = f"ServiceEcosystem:{service_id}"
            header_uri = f"http://www.foo.bar/dataplatform_design/ontologies/ServiceEcosystem#{service_id}"


            tag1, tag2 = random.sample(tag_taxonomy, 2)


            ttl_file.write(f"###  {header_uri}\n")
            ttl_file.write(f"{service_uri}\n")
            ttl_file.write(f"\trdf:type owl:NamedIndividual, DPDO:Service;\n")
            ttl_file.write(f"\tDPDO:hasTag TagTaxonomy:{tag1}, TagTaxonomy:{tag2};\n")


            ttl_file.write(f"\tDPDO:isCompatible\n")
            all_services = [
                f"ServiceEcosystem:S{j}" for j in range(1, num_services + 1) if j != i
            ]
            #compatible_services = all_services
            compatible_services = random.sample(
                all_services, len(all_services) * 3 // 4
            )
            ttl_file.write("        " + ",\n        ".join(compatible_services) + ";\n")

            # Nome del servizio
            ttl_file.write(f'    DPDO:name "{service_id}".\n\n')

def modify_yaml(file_path, modifications):
    """
    Load a YAML file, modify its entries, and save it back to the same file.

    Args:
        file_path (str): The path to the YAML file.
        modifications (dict): A dictionary where keys are the YAML paths (dot-separated) to be updated 
                              and values are the new values to set.

    Example:
        modifications = {
            "key1.subkey": "new_value",
            "key2": "another_value"
        }
    """
    def set_nested_value(data, path, value):
        """Set a value in a nested dictionary using a dot-separated path."""
        keys = path.split(".")
        for key in keys[:-1]:
            data = data.setdefault(key, {})
        data[keys[-1]] = value

    try:
        # Load the YAML file
        with open(file_path, "r") as file:
            yaml_data = yaml.safe_load(file) or {}

        # Apply modifications
        for path, value in modifications.items():
            set_nested_value(yaml_data, path, value)

        # Save the updated YAML back to the file
        with open(file_path, "w") as file:
            yaml.dump(yaml_data, file, default_flow_style=False)

        print(f"File '{file_path}' successfully updated.")

    except Exception as e:
        print(f"An error occurred: {e}")

tag_taxonomy = [
    "Language_all",
    "Python",
    "SQL",
    "LowCode",
    "Delta",
    "Cumulative",
    "Functionality_all",
    "Computing_all",
    "Collection_all",
    "Data_Volume_all",
    "Data_Nature_all",
    "Data_Model_all",
    "Data_Zones_all",
    "ETL",
    "Archive",
    "Batch",
    "Big",
    "Classification",
    "Document",
    "File",
    "Graph",
    "Key_Value",
    "Landing",
    "Machine_Learning",
    "Mini_Batch",
    "Multidimensional",
    "Reporting",
    "Operational",
    "Processed",
    "Pull",
    "Push",
    "Raster",
    "Regression",
    "Relational",
    "Semi_Structured",
    "Small",
    "Spatial",
    "Streaming",
    "Structured",
    "Temporal",
    "Vectorial",
    "Wide_Column",
]

seed = 42 
services_card = 200
scenarios_dfd_cardinality = [10, 100, 1000]

scenarios_directory = os.path.join("dataplatform_design", "src", "test", "scenarios")


for scenario in scenarios_dfd_cardinality:
    scenario_name = f"syntethic_{scenario}nodes"
    new_scenario_ontologies_path = os.path.join(
        scenarios_directory, scenario_name, "input", "ontologies"
    )

    os.system(
        f"python dataplatform_design/src/test/create_test_scenario.py --scenario_name {scenario_name}"
    )

    updates = {
        "ontologies.path.ServiceEcosystem": f"{os.path.join(new_scenario_ontologies_path, 'ServiceEcosystem.ttl')}",
    }

    modify_yaml(os.path.join(scenarios_directory, scenario_name, "configs", "config.yml"), updates)

    generate_services(
        tag_taxonomy,
        seed,
        num_services=services_card,
        output_file=os.path.join(new_scenario_ontologies_path, "ServiceEcosystem.ttl"),
    )
    binary_tree = build_binary_dfd_tree(scenario, seed=seed)

    tag_and_save_dfd_tree(
        binary_tree,
        seed,
        os.path.join(new_scenario_ontologies_path, "DFD.ttl"),
        os.path.join(new_scenario_ontologies_path, "ServiceEcosystem.ttl"),
    )
