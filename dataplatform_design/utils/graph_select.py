import utils
from rdflib import Namespace
import itertools
from cplex import Cplex

# Load config
config = utils.load_yaml("dataplatform_design/resources/config.yml")

PREFIX = config["prefix"]
DPDO = Namespace(config["ontologies"]["namespaces"]["DPDO"])


def normalize_name(name):
    normalized = name.replace(PREFIX, "")
    return normalized


def denormalize_name(name):
    return PREFIX + name


def get_require_edges(graph):
    requires_query = f"""SELECT ?node ?service ?serviceRequirement WHERE {{
    {{
        ?node <{DPDO.implementedBy}> ?service .
        ?service <{DPDO.requires}> ?serviceRequirement .
    }}
    }}
                        """
    result = graph.query(requires_query)

    service_requirements_dict = {}
    for node, service, serviceRequirement in result:
        if node not in service_requirements_dict:
            service_requirements_dict[node] = []
        if service not in service_requirements_dict[node]:
            service_requirements_dict[node].append(service)
        service_requirements_dict[node].append(serviceRequirement)

    return [
        [f"{normalize_name(node)}->{normalize_name(service)}" for service in services]
        for node, services in service_requirements_dict.items()
    ]


def get_minimal_coverage(graph):
    minimal_coverage = f"""SELECT ?node ?service WHERE {{
                        ?node <{DPDO.implementedBy}> ?service .
                    }}
                    """
    result = graph.query(minimal_coverage)
    minimal_coverage_dict = {}
    for node, service in result:
        if node not in minimal_coverage_dict:
            minimal_coverage_dict[node] = []
        minimal_coverage_dict[node].append(service)

    return {
        tuple(
            f"{normalize_name(node)}->{normalize_name(service)}" for service in services
        )
        for node, services in minimal_coverage_dict.items()
    }


def get_implementedby_edges(graph):
    implementedby_query = f"""SELECT ?node ?service WHERE {{
                    ?node <{DPDO.implementedBy}> ?service .
                }}
                """
    result = graph.query(implementedby_query)
    return [
        f"{normalize_name(node)}->{normalize_name(service)}" for node, service in result
    ]


def get_implementedby_services(graph):
    implementedby_query = f"""SELECT ?service WHERE {{
                    ?node <{DPDO.implementedBy}> ?service .
                }}
                """
    result = graph.query(implementedby_query)
    return list(set([f"{normalize_name(str(service[0]))}" for service in result]))


def get_dataflows(graph):
    dfd_edges = f"""SELECT ?node ?nextNode WHERE {{
                    ?node <{DPDO.flowsData}> ?nextNode .
                }}
                """
    result = graph.query(dfd_edges)
    dfd_edges_dict = {}
    for node, followingNode in result:
        if node not in dfd_edges_dict:
            dfd_edges_dict[node] = []
        dfd_edges_dict[node].append(str(followingNode))

    return [
        (str(normalize_name(node)), [normalize_name(service) for service in services])
        for node, services in dfd_edges_dict.items()
    ]


def get_compatible_services(graph):
    compatible_services = f"""SELECT ?service ?compatibleService WHERE {{
                    ?service <{DPDO.isCompatible}> ?compatibleService .
                }}
                """
    result = graph.query(compatible_services)
    minimal_coverage_dict = {}
    for node, followingNode in result:
        if node not in minimal_coverage_dict:
            minimal_coverage_dict[node] = []
        minimal_coverage_dict[node].append(str(followingNode))

    return [
        (str(normalize_name(node)), [normalize_name(service) for service in services])
        for node, services in minimal_coverage_dict.items()
    ]


def get_akin_services(graph, implementedby_edges, implemented_services, dfd_edges):
    akin_services = f"""
        SELECT ?service ?akinService WHERE {{
                            ?service <{DPDO.isAkin}> ?akinService .
                        }}
    """
    result = graph.query(akin_services)
    akin_services_dict = {}
    for node, followingNode in result:
        if node not in akin_services_dict:
            akin_services_dict[node] = []
        akin_services_dict[node].append(str(followingNode))

    akin_services = [
        (str(normalize_name(node)), [normalize_name(service) for service in services])
        for node, services in akin_services_dict.items()
    ]
    implementedby_edges = [
        (tuple.split("->")[0], tuple.split("->")[1]) for tuple in implementedby_edges
    ]
    implements_cartesian_product = list(
        itertools.product(*[implementedby_edges, implementedby_edges])
    )

    akins = []
    for source, dest in implements_cartesian_product:
        is_akin = False

        # DFD nodes
        dfd_source_node = source[0]
        dfd_dest_node = dest[0]

        # (DFD nodes) Implemented by
        dfd_source_node_implBy = source[1]
        dfd_dest_node_implBy = dest[1]

        # For every DFD edge (Flow)
        for source_edge, dest_edge in dfd_edges:
            # If source nodes of two "ImplementedBy" edges are connected by a DFD edge (Flow) then two services MUST be compatible
            if dfd_source_node == "DFD#ETL" and dfd_dest_node == "DFD#DWH":
                print(("HELLO"))
            if dfd_source_node == source_edge and dfd_dest_node in dest_edge:
                for service, list_akins in akin_services:
                    # Check for bi-directional compatibility
                    if (
                        dfd_source_node_implBy == service
                        and dfd_dest_node_implBy in list_akins
                    ) or (
                        dfd_dest_node_implBy == service
                        and dfd_source_node_implBy in list_akins
                    ):
                        is_akin = True
                if is_akin:
                    akins.append((source, dest))
    return list(set(akins))


# Returns all couple of services that were matched and might be selected for two contiguos DFD entities but have no compatibility between each other.
def find_not_compatible_edges(implemented_by_edges, dfd_edges, compatibilities):
    implemented_by_edges = [
        (tuple.split("->")[0], tuple.split("->")[1]) for tuple in implemented_by_edges
    ]
    implements_cartesian_product = list(
        itertools.product(*[implemented_by_edges, implemented_by_edges])
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


def select_services(named_graph, preferences, mandatories):
    minimal_coverage = get_minimal_coverage(named_graph)
    requires_edges = get_require_edges(named_graph)
    implementedby_edges = get_implementedby_edges(named_graph)
    dfd_edges = get_dataflows(named_graph)
    compatibilities = get_compatible_services(named_graph)
    not_compatible_services = find_not_compatible_edges(
        implementedby_edges, dfd_edges, compatibilities
    )
    implemented_services = get_implementedby_services(named_graph)
    akin_services = get_akin_services(
        named_graph, implementedby_edges, implemented_services, dfd_edges
    )

    ##############################
    #   CONSTRAINTS DEFINITION   #
    ##############################

    ### 4th Constraint - Services' minimal coverage
    fourth_constraint = [[list(t), [1 for _ in enumerate(t)]] for t in minimal_coverage]
    fourth_constraint_names = ["c" + str(i) for i, _ in enumerate(fourth_constraint)]
    fourth_rhs = [1 for _ in enumerate(fourth_constraint)]
    fourth_constraint_senses = ["E" for _ in enumerate(fourth_constraint)]

    ### 5th Constraint - Services' requirements
    fifth_constraint = [
        [
            constraint,
            [-1 * (len(constraint) - 1)] + [1 for _ in range(len(constraint) - 1)],
        ]
        for constraint in requires_edges
    ]
    fifth_constraint_names = ["r" + str(i) for i, _ in enumerate(fifth_constraint)]
    fifth_rhs = [0 for _ in fifth_constraint]
    fifth_constraint_senses = ["E" for _ in fifth_constraint]

    ### 6th Constraint - Services' compatibilities
    sixth_constraint = [
        [[f"{source[0]}->{source[1]}", f"{dest[0]}->{dest[1]}"], [1, 1]]
        for source, dest in not_compatible_services
    ]
    sixth_rhs = [1 for _ in sixth_constraint]
    sixth_constraint_senses = ["L" for _ in sixth_constraint]
    sixth_constraint_names = ["comp" + str(i) for i, _ in enumerate(sixth_constraint)]

    ### 7th Constraint - Services' edges
    edges_constraint = [
        [[edge, edge.split("->")[1]], [1, -1]] for edge in implementedby_edges
    ] + [[[edge[0], edge[0].split("->")[1]], [1, -1]] for edge in requires_edges]
    edges_constraint_names = ["edge" + str(i) for i, _ in enumerate(edges_constraint)]
    edges_rhs = [0 for _ in edges_constraint]
    edges_constraint_senses = ["L" for _ in edges_constraint]

    ### 8th Constraint - Services' affinities
    affinity_constraint = [
        [[f"{source[0]}->{source[1]}", f"{dest[0]}->{dest[1]}"], [1, -1]]
        for source, dest in akin_services
    ]
    affinity_constraint_names = [
        "edge" + str(i) for i, _ in enumerate(affinity_constraint)
    ]
    affinity_rhs = [0 for _ in affinity_constraint]
    affinity_constraint_senses = ["G" for _ in affinity_constraint]

    #############################
    # 2.2 PROBLEM FORMALIZATION #
    #############################

    problem = Cplex()
    problem.set_problem_type(Cplex.problem_type.LP)
    problem.objective.set_sense(problem.objective.sense.minimize)

    # Setting problem's variable names: [implemented services + "ImplementBy" edges + "requires" edges]
    variable_names = list(
        set(
            implementedby_edges
            + implemented_services
            + [constraint for sub_list in requires_edges for constraint in sub_list]
        )
    )

    # Setting variable's value bounds
    lower_bounds = [0 for _ in variable_names]
    upper_bounds = [1 for _ in variable_names]

    # Setting variables' weights to minimize, weight(arch) = 0 since we don't want to minimize them
    objective = [0 if "->" in variable else 1 for variable in variable_names]
    # objective = utils.embed_preferences(variable_names, objective, preferences_path)

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

    problem.linear_constraints.add(
        lin_expr=affinity_constraint,
        senses=affinity_constraint_senses,
        rhs=affinity_rhs,
        names=affinity_constraint_names,
    )
    # Solve the problem
    problem.solve()

    selected_services = []
    selected_edges = []

    for i, name in enumerate(problem.variables.get_names()):
        selected = problem.solution.get_values(i)
        # print(f"{name}: {selected}")
        if "->" in name and selected:
            selected_edges.append(name)
        elif selected:
            selected_services.append(name)

    return selected_edges
