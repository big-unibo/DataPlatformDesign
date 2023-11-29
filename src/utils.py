import itertools
import sys

def match(tag, dfd_tags, service_tags):
    for property, values in dfd_tags.items():
        print(f"{tag}Checking dfd property {property}")
        # If first level property not supported in service, can't match
        if property not in service_tags:
            print(
                f"Property {property} values {values} not in {service_tags.keys()}, trying next service..."
            )
            return False
        # IF there are subproperties
        if isinstance(values, dict):
            print(f"{tag}Checking {property} subproperties...")
            print(
                f"{tag}Checking for dfd subproperty {values} with {service_tags[property]}"
            )
            # Match them
            if not match(tag + "\t", values, service_tags[property]):
                return False
            else:
                print(f"{tag}Property {values} matches {service_tags[property]}")
        else:
            # No subproperties, check equivalence of this property
            if not set(values) <= set(service_tags[property]):
                print(
                    f"{tag}{values} for {property} can't match {service_tags[property]}"
                )
                return False
            else:
                print(f"{tag}Property {values} matches {service_tags[property]}")
    print(f"{tag}{values} matches {service_tags[property]}")
    return True

# Returns all service requirement for a given service in a service graph
def find_requirements_for(service_graph, service_name):
    requires = "requires"
    if service_name in service_graph.keys():
        if requires in service_graph[service_name]["properties"]:
            return service_graph[service_name]["properties"][requires]
        else:
            return []

## Returns all couple of services that were matched and might be selected for two contiguos DFD entities but have no compatibility between each other.
def find_not_compatible_edges(edges, dfd_edges, compatibilities):
    test = [(tuple.split("->")[0], tuple.split("->")[1]) for tuple in edges]
    implements_cartesian_product = list(
        itertools.product(*[test, test])
    )

    not_compatible_services = []
    for source, dest in implements_cartesian_product:
        compatible = False

        # DFD nodes
        dfd_source_node = source[0]
        dfd_dest_node = dest[0]

        # (DFD nodes) Implemented by
        dfd_source_node_implBy = source[1]
        dfd_dest_node_implBy = dest[1]

        # Exclude self-joined nodes through cartesian product
        if dfd_source_node == dfd_dest_node:
            compatible = True

        # For every DFD edge (Flow)
        for source_edge, dest_edge in dfd_edges:
            # If source nodes of two "ImplementedBy" edges are connected by a DFD edge (Flow) then two services MUST be compatible
            if dfd_source_node == source_edge and dfd_dest_node in dest_edge:
                for service, compatibilitiy in compatibilities:
                    # Check for bi-directional compatibility
                    if (
                        dfd_source_node_implBy == service
                        and dfd_dest_node_implBy in compatibilitiy
                    ) or (
                        dfd_dest_node_implBy == service
                        and dfd_source_node_implBy in compatibilitiy
                    ):
                        compatible = True
                if not compatible:
                    not_compatible_services.append((source, dest))
    return list(set(not_compatible_services))

def embed_dfd_graph(json_graph, new_graph):
    for node_name, node_tags in json_graph.items():
        if not node_name in new_graph.body:
            shape = "ellipse"
            color = "black"
            style = "solid"
            if node_tags["label"] == "Repository":
                shape = "box"
            new_graph.node(node_name, node_name, shape=shape, color=color, style=style)
            for node in node_tags["edges"]:
                if not node_name in new_graph.body:
                    if node_tags["label"] == "Repository":
                        shape = "box"
                    new_graph.node(
                        node_name, node_name, shape=shape, color=color, style=style
                    )
                new_graph.edge(node_name, node, color=color)
    return new_graph

def embed_selected_graph(selected_graph, dfd_graph, selected_services, selected_arcs, requires_arcs):
    selected_graph = embed_dfd_graph(dfd_graph, selected_graph)

    for service in selected_services:
        selected_graph.node(service, service, color="blue")

    for arc in selected_arcs:
        source = arc.split("->")[0]
        dest = arc.split("->")[1]
        # If it's a require edge
        sub_require = False
        require = False
        for require_source, require_dest in requires_arcs:
            if require_source == arc or require_dest == arc:
                require = require_dest == arc
                selected_graph.edge(
                    require_dest.split("->")[1],
                    require_source.split("->")[1],
                    color="lightblue",
                    label="require",
                    style="dashed",
                )
                sub_require = True
        if not sub_require or require:
            selected_graph.edge(
                source, dest, color="lightblue", label="ImplementedBy", style="bold"
            )
    return selected_graph

def embed_preferences(variable_names, objective, preferenceFile):
    with open(preferenceFile, 'r') as file:
        for line in  file.readlines():
            if line in variable_names:
               objective[variable_names.index(line)] = 0.5
            else:
               print(f"Can't embed preference {line}, aborting")
               sys.exit(1)
        return objective