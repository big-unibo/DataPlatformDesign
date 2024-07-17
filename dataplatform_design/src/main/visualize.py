import os
import rdflib
from graphviz import Digraph


def parse_turtle_to_graph(turtle_file):
    g = rdflib.Graph()
    g.parse(turtle_file, format="turtle")
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
                    else ("ellipse" if (s_str in process) else "hexagon")
                ),
                style="filled",
                color="lightblue" if "DFD" in s else "yellow",
            )
            dot.node(
                o_str,
                o_str,
                shape=(
                    "box"
                    if (o_str in repository)
                    else ("ellipse" if (o_str in process) else "hexagon")
                ),
                style="filled",
                color="lightblue" if "DFD" in o else "yellow",
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


# Example usage
root_directory = "dataplatform_design/src/test/scenarios/"
process_directory_tree(root_directory)
