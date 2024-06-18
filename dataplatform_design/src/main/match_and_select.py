import json
import graphviz
from cplex import Cplex
import os.path as path
import utils
import argparse
import sys

default_service_graph_file = "service_graph.json"
default_dfd_graph_file = "dfd_graph.json"
default_preference_file = "preferences.txt"

default_input_folder = "input"
default_output_path = "output"

parser = argparse.ArgumentParser(description="Define input files location")
parser.add_argument(
    "-dfd",
    "--dfd_graph",
    help="Path of dfd_graph.json",
    default=path.join(default_input_folder, default_dfd_graph_file),
)
parser.add_argument(
    "-sg",
    "--service_graph",
    help="Path of service_graph.json",
    default=path.join(default_input_folder, default_service_graph_file),
)
parser.add_argument(
    "-p",
    "--preferences",
    help="Path of preferences.txt",
    default=path.join(default_input_folder, default_preference_file),
)
parser.add_argument(
    "-o", "--output_path", help="Output path", default=default_output_path
)

args = vars(parser.parse_args())

service_graph_path = args["service_graph"]
dfd_graph_path = args["dfd_graph"]
preferences_path = args["preferences"]
output_path = args["output_path"]

utils.create_directory(output_path)

# Load input graphs
try:
    service_graph = json.load(open(service_graph_path))
    dfd_graph = json.load(open(dfd_graph_path))
except FileNotFoundError as e:
    print("Couldnt' find input file")
    print(f"Error: {e}")
    sys.exit(1)
except json.JSONDecodeError as js:
    print("Something went wrong while decoding json file")
    print(f"Error: {js}")
    sys.exit(1)

# Matched graph
matched_graph = graphviz.Digraph(
    "G", filename=path.join(output_path, "matched_graph.gv"), strict=True
)

# Selected graph
selected_graph = graphviz.Digraph(
    "G", filename=path.join(output_path, "selected_graph.gv"), strict=True
)

##########################
# 1. BUILD MATCHED GRAPH #
##########################

# Matched graph "ImplementedBy" services
implementedBy_services = []
# Matched graph "ImplementedBy" edges
implementedBy_edges = []
# Matched graph "requires" edges
requires_edges = []

for dfd_entity_name, dfd_process_tags in dfd_graph.items():
    if dfd_entity_name not in matched_graph.body:
        shape = "box" if dfd_process_tags["label"] == "Repository" else "ellipse"
        matched_graph.node(dfd_entity_name, dfd_entity_name, color="black", shape=shape)
    for node in dfd_process_tags["edges"]:
        if node not in matched_graph.body:
            shape = "box" if dfd_graph[node]["label"] == "Repository" else "ellipse"
            matched_graph.node(node, node, color="black")
            matched_graph.edge(dfd_entity_name, node, color="black")
    for service_name, service_tags in service_graph.items():
        print(f"Trying to match DFD entity {dfd_entity_name} to service {service_name}")
        # If service tags and dfd node tags match
        if utils.match(
            "\t", dfd_process_tags["properties"], service_tags["properties"]
        ):
            implementedBy_services.append(service_name)
            if service_name not in matched_graph.body:
                matched_graph.node(service_name, service_name, color="blue")
            matched_graph.edge(
                dfd_entity_name, service_name, label="implementedBy", color="lightblue"
            )
            implementedBy_edges.append(f"{dfd_entity_name}->{service_name}")
            requirements = utils.find_requirements_for(service_graph, service_name)
            # Attach "requires" needs
            for service_requirement in requirements:
                if service_requirement not in matched_graph.body:
                    requires_edges.append(
                        [
                            f"{dfd_entity_name}->{service_requirement}",
                            f"{dfd_entity_name}->{service_name}",
                        ]
                    )
                    matched_graph.node(
                        service_requirement, service_requirement, color="blue"
                    )
                matched_graph.edge(
                    service_name,
                    service_requirement,
                    label="requires",
                    color="lightblue",
                    style="dashed",
                )
                implementedBy_services.append(service_requirement)

# Render matched graph in output folder
matched_graph.render(filename=path.join(output_path, "matched_graph"), format="svg")
implemented_services = list(set(implementedBy_services))


##############################
# 2. MATCHED GRAPH SELECTION #
##############################

# List of DFD edges (Flow)
dfd_edges = [(key, tag["edges"]) for key, tag in dfd_graph.items() if "edges" in tag]

# List of compatibilities for each service
compatibilities = [
    (key, tag["properties"]["isCompatible"])
    for key, tag in service_graph.items()
    if "isCompatible" in tag["properties"]
]

minimal_coverage = []
for edge in implementedBy_edges:
    sub_constraint = []
    for edge2 in implementedBy_edges:
        if edge2.split("->")[0] == edge.split("->")[0]:
            sub_constraint.append(edge2)
    minimal_coverage.append(sub_constraint)
minimal_coverage = set(tuple(elem) for elem in minimal_coverage)

##############################
# 2.1 CONSTRAINTS DEFINITION #
##############################

### 4th Constraint - Services' minimal coverage
fourth_constraint = [[list(t), [1 for _ in enumerate(t)]] for t in minimal_coverage]
fourth_constraint_names = ["c" + str(i) for i, _ in enumerate(fourth_constraint)]
fourth_rhs = [1 for _ in enumerate(fourth_constraint)]
fourth_constraint_senses = ["E" for _ in enumerate(fourth_constraint)]

### 5th Constraint - Services' requirements
fifth_constraint = [[constraint, [-1, 1]] for constraint in requires_edges]
fifth_constraint_names = ["r" + str(i) for i, _ in enumerate(fifth_constraint)]
fifth_rhs = [0 for _ in fifth_constraint]
fifth_constraint_senses = ["E" for _ in fifth_constraint]

### 6th Constraint - Services' compatibilities
not_compatible_services = utils.find_not_compatible_edges(
    implementedBy_edges, dfd_edges, compatibilities
)
sixth_constraint = [
    [[f"{source[0]}->{source[1]}", f"{dest[0]}->{dest[1]}"], [1, 1]]
    for source, dest in not_compatible_services
]
sixth_rhs = [1 for _ in sixth_constraint]
sixth_constraint_senses = ["L" for _ in sixth_constraint]
sixth_constraint_names = ["comp" + str(i) for i, _ in enumerate(sixth_constraint)]

### 7th Constraint - Services' edges
edges_constraint = [
    [[edge, edge.split("->")[1]], [1, -1]] for edge in implementedBy_edges
] + [[[edge[0], edge[0].split("->")[1]], [1, -1]] for edge in requires_edges]
edges_constraint_names = ["edge" + str(i) for i, _ in enumerate(edges_constraint)]
edges_rhs = [0 for _ in edges_constraint]
edges_constraint_senses = ["L" for _ in edges_constraint]

#############################
# 2.2 PROBLEM FORMALIZATION #
#############################

problem = Cplex()
problem.set_problem_type(Cplex.problem_type.LP)
problem.objective.set_sense(problem.objective.sense.minimize)

# Setting problem's variable names: [implemented services + "ImplementBy" edges + "requires" edges]
variable_names = list(
    set(
        implementedBy_edges
        + implemented_services
        + [constraint for sub_list in requires_edges for constraint in sub_list]
    )
)

# Setting variable's value bounds
lower_bounds = [0 for _ in variable_names]
upper_bounds = [1 for _ in variable_names]

# Setting variables' weights to minimize, weight(arch) = 0 since we don't want to minimize them
objective = [0 if "->" in variable else 1 for variable in variable_names]
objective = utils.embed_preferences(variable_names, objective, preferences_path)

problem.variables.add(
    obj=objective, lb=lower_bounds, ub=upper_bounds, names=variable_names
)

# Adding constraints
problem.linear_constraints.add(
    lin_expr=fifth_constraint,
    senses=fifth_constraint_senses,
    rhs=fifth_rhs,
    names=fifth_constraint_names,
)

problem.linear_constraints.add(
    lin_expr=fourth_constraint,
    senses=fourth_constraint_senses,
    rhs=fourth_rhs,
    names=fourth_constraint_names,
)

problem.linear_constraints.add(
    lin_expr=sixth_constraint,
    senses=sixth_constraint_senses,
    rhs=sixth_rhs,
    names=sixth_constraint_names,
)

problem.linear_constraints.add(
    lin_expr=edges_constraint,
    senses=edges_constraint_senses,
    rhs=edges_rhs,
    names=edges_constraint_names,
)

# Solve the problem
problem.solve()

###########################
# 3. BUILD SELECTED GRAPH #
###########################

selected_services = []
selected_edges = []

# Explore solution
print("---------")
print("Problem Solution:")
print("---------")
for i, name in enumerate(problem.variables.get_names()):
    selected = problem.solution.get_values(i)
    print(f"{name}: {selected}")
    if "->" in name and selected:
        selected_edges.append(name)
    elif selected:
        selected_services.append(name)
print("---------")
print(f"Solution cost: {problem.solution.get_objective_value()}")

selected_graph = utils.embed_selected_graph(
    selected_graph, dfd_graph, selected_services, selected_edges, requires_edges
)
selected_graph.render(filename=path.join(output_path, "selected_graph"), format="svg")
