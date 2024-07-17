import os
import rdflib
from rdflib import Namespace
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

    predicates = ["implementedBy", "requires"]

    # if "matched_graph" in json_file:
    #     [
    #         print(str(p))
    #         for s, p, o in g
    #         # for predicate in predicates
    #         # if predicate in str(p)
    #     ]
    #     triples_to_remove = [
    #         (s, p, o)
    #         for s, p, o in g
    #         if all([predicate not in str(p) for predicate in predicates])
    #     ]

    #     for triple in triples_to_remove:
    #         g.remove(triple)

    #     for s, p, o in g:
    #         print(f"Subject: {s}, Predicate: {p}, Object: {o}")
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
            dot.edge(s_str, o_str, label=p_str)

    dot.render(save_path, format="png")
    dot.save(save_path + ".dot")


def process_directory_tree(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".ttl"):
                file_path = os.path.join(dirpath, filename)
                save_path = os.path.join(dirpath, filename.replace(".ttl", ""))
                if "config" not in file_path:
                    print(file_path)
                    g = parse_turtle_to_graph(file_path)
                    visualize_graph(g, save_path)
            elif filename.endswith(".json"):
                file_path = os.path.join(dirpath, filename)
                save_path = os.path.join(dirpath, filename.replace(".json", ""))
                if "config" not in file_path:
                    print(file_path)
                    g = parse_json_to_graph(file_path)
                    visualize_graph(g, save_path)


# Example usage
root_directory = "dataplatform_design/src/test/scenarios/"
process_directory_tree(root_directory)
