import os
import rdflib
from rdflib import Namespace, URIRef
from graphviz import Digraph


def parse_turtle_to_graph(turtle_file):
    g = rdflib.Graph()
    g.parse(turtle_file, format="turtle")
    return g


def parse_json_to_graph(json_file):

    g = rdflib.Graph()

    g.parse(
        location=os.path.join(json_file),
        format="json-ld",
    )

    predicates = ["implementedBy", "requires", "flowsData", "type"]

    if "matched_graph" in json_file:
        # Focus only on named graph
        named_graph = rdflib.Graph(
            store=g.store, identifier=URIRef("http://dpdo_example.com/DPD_Graph")
        )
        triples_to_remove = [
            (s, p, o)
            for s, p, o in named_graph
            if all([predicate not in str(p) for predicate in predicates])
        ]

        for triple in triples_to_remove:
            named_graph.remove(triple)

        return named_graph
    return g


def visualize_graph(g, save_path):
    dot = Digraph(comment="RDF Graph")

    repository = {}
    process = {}
    for s, p, o in g:
        s_str = str(s).split("#")[-1]
        p_str = str(p).split("#")[-1]
        o_str = str(o).split("#")[-1]

        if "DFD" in s and "type" in p_str:
            if o_str == "Repository":
                repository[s_str] = True
            if o_str == "Process":
                process[s_str] = True

    for s, p, o in g:
        s_str = str(s).split("#")[-1]
        p_str = str(p).split("#")[-1]
        o_str = str(o).split("#")[-1]
        if p_str not in ["type", "hasTag", "name", "imports", "label"]:
            dot.node(
                s_str,
                s_str,
                shape=(
                    "box"
                    if (s_str in repository)
                    else ("oval" if (s_str in process) else "oval")
                ),
                style="filled",
                color="steelblue" if "DFD" in s else "gold",
            )
            dot.node(
                o_str,
                o_str,
                shape=(
                    "box"
                    if (o_str in repository)
                    else ("oval" if (o_str in process) else "oval")
                ),
                style="filled",
                color="steelblue" if "DFD" in o else "gold",
            )

            def e_color(s):
                if s == "flowsData":
                    return "black"
                if s == "selected":
                    return "red"
                return "grey"

            def e_style(s):
                if s == "requires":
                    return "dashed"
                if s == "isCompatible":
                    return "dotted"
                return "solid"

            dot.edge(
                s_str,
                o_str,
                label=(
                    p_str
                    if p_str
                    not in ["implementedBy", "flowsData", "isCompatible", "requires"]
                    else ""
                ),
                style=e_style(p_str),
                color=e_color(p_str),
            )

    dot.render(save_path, format="png")
    # dot.save(save_path + ".dot")


def process_directory_tree(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".ttl"):
                file_path = os.path.join(dirpath, filename)
                save_path = os.path.join(dirpath, filename.replace(".ttl", ""))
                if "config" not in file_path:
                    g = parse_turtle_to_graph(file_path)
                    visualize_graph(g, save_path)
            elif filename.endswith(".json"):
                file_path = os.path.join(dirpath, filename)
                save_path = os.path.join(dirpath, filename.replace(".json", ""))
                if "config" not in file_path:
                    g = parse_json_to_graph(file_path)
                    visualize_graph(g, save_path)


# Example usage
for root_directory in [
    "dataplatform_design/src/test/scenarios/",
    "dataplatform_design/resources",
]:
    process_directory_tree(root_directory)
