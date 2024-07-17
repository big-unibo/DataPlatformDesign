from . import utils
from rdflib import Namespace
import itertools
from cplex import Cplex
import os
import contextlib
import sys


# Load default config
config = utils.load_yaml(
    os.path.join(
        "dataplatform_design", "resources", "scenario_template", "configs", "config.yml"
    )
)
# Setup log
logger = utils.setup_logger("DataPlat_Design_Select_Algorithm")

PREFIX = config["prefix"]
DPDO = Namespace(config["ontologies"]["namespaces"]["dpdo"])
TAG_TAXONOMY = Namespace(config["ontologies"]["namespaces"]["tag_taxonomy"])
SERVICE_ECOSYSTEM = Namespace(config["ontologies"]["namespaces"]["service_ecosystem"])


def setup_config(scenario_config):
    global config
    config = scenario_config


def normalize_name(name):
    return name.replace(PREFIX, "") if PREFIX in name else name


def denormalize_name(name):
    return PREFIX + name


def get_require_edges(graph):
    requires_query = f"""SELECT ?node ?service ?serviceRequirement WHERE {{
    {{
        ?node DPDO:implementedBy ?service .
        ?service DPDO:requires ?serviceRequirement .
    }}
    }}
                        """
    result = graph.query(requires_query)
    service_requirements_dict = {}

    # for service, require in result:
    #     if service not in service_requirements_dict:
    #         service_requirements_dict[service] = []
    #     if require not in service_requirements_dict[service]:
    #         service_requirements_dict[service].append(require)

    for node, service, serviceRequirement in result:
        node = normalize_name(node)
        service = normalize_name(service)
        serviceRequirement = normalize_name(serviceRequirement)
        if node not in service_requirements_dict:
            service_requirements_dict[node] = {}
        if service not in service_requirements_dict[node]:
            service_requirements_dict[node][service] = []
        service_requirements_dict[node][service].append(serviceRequirement)

    return service_requirements_dict
    # [
    #     [normalize_name(node)] + [f"{normalize_name(service)}" for service in services]
    #     for node, services in service_requirements_dict.items()
    # ]


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


def get_lakehouse_services(named_graph):
    lakehouse_services_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?datalake ?pathRepository
        WHERE {{
            ?datalake rdf:type <{DPDO.Repository}> .
            ?datalake <{DPDO.hasTag}> <{TAG_TAXONOMY.Landing}> .
            ?datalake <{DPDO.flowsData}>+ ?repository .
            ?repository rdf:type <{DPDO.Repository}> .
            ?repository <{DPDO.flowsData}>+ ?dwh .
            ?dwh rdf:type <{DPDO.Repository}> .
            FILTER EXISTS {{
                ?datalake <{DPDO.flowsData}>+ ?dwh .
                ?dwh <{DPDO.hasTag}> <{TAG_TAXONOMY.Multidimensional}> .
            }}
            FILTER EXISTS {{
                ?repository <{DPDO.hasTag}> <{TAG_TAXONOMY.Relational}> .
            }}
            FILTER(?repository != ?dwh)
            {{
                ?datalake <{DPDO.flowsData}>+ ?pathRepository .
                ?pathRepository rdf:type <{DPDO.Repository}> .
            }}
        }}
    """
    result = named_graph.query(lakehouse_services_query)
    lakehouse_services_dict = {}
    for node, followingNode in result:
        if node not in lakehouse_services_dict:
            lakehouse_services_dict[node] = []
        lakehouse_services_dict[node].append(str(followingNode))
    lakehouse_paths = [
        (
            [
                f"{normalize_name(node)}->{normalize_name(str(SERVICE_ECOSYSTEM.Lakehouse))}"
            ]
            + [
                f"{normalize_name(service)}->{normalize_name(str(SERVICE_ECOSYSTEM.Lakehouse))}"
                for service in services
            ]
        )
        for node, services in lakehouse_services_dict.items()
    ]
    return lakehouse_paths


def get_preferences(named_graph):
    lakehouse_services_query = f"""
        SELECT ?service
        WHERE {{
            ?service <{DPDO.isPreferred}> true.
        }}
    """
    result = named_graph.query(lakehouse_services_query)
    return [normalize_name(str(node[0])) for node in result]


def get_mandatories(named_graph):
    lakehouse_services_query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?node ?service
        WHERE {{
            ?node <{DPDO.isMandatory}> ?service .
            ?service a <{DPDO.Service}> .
        }}
    """
    result = named_graph.query(lakehouse_services_query)
    return [
        f"{normalize_name(str(node))}->{normalize_name(str(service))}"
        for node, service in result
    ]


def embed_additional_constraints(variable_names, preferences):
    objective = []
    for variable in variable_names:
        if "->" in variable:
            objective.append(0)
        else:
            if variable in preferences and variable:
                objective.append(0.5)
            else:
                objective.append(1)
    return objective
    # return [
    #     (
    #         0
    #         if "->" in variable
    #         else (
    #             0
    #             if variable in mandatories
    #             else (
    #                 0.5
    #                 if variable in preferences and variable not in mandatories
    #                 else 1
    #             )
    #         )
    #     )
    #     for variable in variable_names
    # ]


def select_services(named_graph):
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
    lakehouse_implements = get_lakehouse_services(named_graph)
    preferences = get_preferences(named_graph)
    mandatories = get_mandatories(named_graph)

    ##############################
    #   CONSTRAINTS DEFINITION   #
    ##############################

    ### 4th Constraint - Services' minimal coverage
    fourth_constraint = [[list(t), [1 for _ in enumerate(t)]] for t in minimal_coverage]
    fourth_constraint_names = ["c" + str(i) for i, _ in enumerate(fourth_constraint)]
    fourth_rhs = [1 for _ in enumerate(fourth_constraint)]
    fourth_constraint_senses = ["E" for _ in enumerate(fourth_constraint)]

    ### 5th Constraint - Services' requirements
    seen = set()
    fifth_constraint = [
        [
            [service] + requires,
            (
                ([-1 * (len(requires))] + [1 for _ in range(len(requires))])
                if len(requires) > 1
                else ([-1 * len(requires)] + [1 for _ in range(len(requires))])
            ),
        ]
        for services in requires_edges.values()
        for service, requires in services.items()
        if (
            tuple([service] + requires),
            tuple(
                ([-1 * (len(requires))] + [1 for _ in range(len(requires))])
                if len(requires) > 1
                else ([-1 * len(requires)] + [1 for _ in range(len(requires))])
            ),
        )
        not in seen
        and not seen.add(
            (
                tuple([service] + requires),
                tuple(
                    ([-1 * (len(requires))] + [1 for _ in range(len(requires))])
                    if len(requires) > 1
                    else ([-1 * len(requires)] + [1 for _ in range(len(requires))])
                ),
            )
        )
    ]

    # fifth_constraint = [
    #     [list(set(constraint)), truth] for constraint, truth in fifth_constraint
    # ]
    fifth_constraint_names = ["r" + str(i) for i, _ in enumerate(fifth_constraint)]
    fifth_rhs = [0 for _ in fifth_constraint]
    fifth_constraint_senses = ["G" for _ in fifth_constraint]

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
        [[edge, edge.split("->")[1]], [-1, 1]] for edge in implementedby_edges
    ]  # + [[[edge[0], edge[0].split("->")[1]], [1, -1]] for edge in requires_edges]
    edges_constraint_names = ["edge" + str(i) for i, _ in enumerate(edges_constraint)]
    edges_rhs = [0 for _ in edges_constraint]
    edges_constraint_senses = ["G" for _ in edges_constraint]

    ### 8th Constraint - Services' affinities
    affinity_constraint = [
        [[f"{source[0]}->{source[1]}", f"{dest[0]}->{dest[1]}"], [1, -1]]
        for source, dest in akin_services
    ]
    affinity_constraint_names = [
        "affinity" + str(i) for i, _ in enumerate(affinity_constraint)
    ]
    affinity_rhs = [0 for _ in affinity_constraint]
    affinity_constraint_senses = ["E" for _ in affinity_constraint]

    ### 8th Constraint - Services' affinities
    lakehouse_constraint = [
        [
            lakehouse_path,
            [1 for _ in range(len(lakehouse_path) - 1)]
            + [-1 * (len(lakehouse_path) - 1)],
        ]
        for lakehouse_path in lakehouse_implements
    ]

    lakehouse_constraint_names = [
        "lakehouse" + str(i) for i, _ in enumerate(lakehouse_constraint)
    ]
    lakehouse_rhs = [0 for _ in lakehouse_constraint]
    lakehouse_constraint_senses = ["E" for _ in lakehouse_constraint]

    ### 9th Constraint - Services' mandatories
    mandatory_constraint = [[[mandatory], [1]] for mandatory in mandatories]

    mandatory_constraint_names = [
        "mandatory" + str(i) for i, _ in enumerate(mandatory_constraint)
    ]
    mandatory_constraint_rhs = [1 for _ in mandatory_constraint]
    mandatory_constraint_senses = ["E" for _ in mandatory_constraint]

    #############################
    # 2.2 PROBLEM FORMALIZATION #
    #############################

    problem = Cplex()

    problem.set_log_stream(None)
    problem.set_error_stream(None)
    problem.set_warning_stream(None)
    problem.set_results_stream(None)

    problem.set_problem_type(Cplex.problem_type.LP)
    problem.objective.set_sense(problem.objective.sense.minimize)

    # Setting problem's variable names: [implemented services + "ImplementBy" edges + "requires" edges]
    variable_names = list(
        set(
            implementedby_edges
            + implemented_services
            + list(
                set(
                    [
                        service
                        for sub_list in requires_edges.values()
                        for service_require in sub_list.values()
                        for service in service_require
                    ]
                )
            )
        )
    )

    # Setting variable's value bounds
    lower_bounds = [0 for _ in variable_names]
    upper_bounds = [1 for _ in variable_names]

    # Setting variables' weights to minimize, weight(arch) = 0 since we don't want to minimize them
    objective = [0 if "->" in variable else 1 for variable in variable_names]
    objective = embed_additional_constraints(variable_names, preferences)

    variable_types = [problem.variables.type.binary for _ in variable_names]

    problem.variables.add(
        obj=objective,
        lb=lower_bounds,
        ub=upper_bounds,
        types=variable_types,
        names=variable_names,
    )

    problem.linear_constraints.add(
        lin_expr=fourth_constraint,
        senses=fourth_constraint_senses,
        rhs=fourth_rhs,
        names=fourth_constraint_names,
    )

    # Adding constraints
    problem.linear_constraints.add(
        lin_expr=fifth_constraint,
        senses=fifth_constraint_senses,
        rhs=fifth_rhs,
        names=fifth_constraint_names,
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

    problem.linear_constraints.add(
        lin_expr=lakehouse_constraint,
        senses=lakehouse_constraint_senses,
        rhs=lakehouse_rhs,
        names=lakehouse_constraint_names,
    )

    problem.linear_constraints.add(
        lin_expr=mandatory_constraint,
        senses=mandatory_constraint_senses,
        rhs=mandatory_constraint_rhs,
        names=mandatory_constraint_names,
    )

    # Generate and populate the solution pool
    problem.parameters.mip.pool.intensity.set(4)  # Set the pool intensity to high
    problem.parameters.mip.limits.populate.set(10**2)  # Set a high limit for the pool
    problem.parameters.mip.pool.relgap.set(0.0)
    problem.populate_solution_pool()

    num_solutions = problem.solution.pool.get_num()
    logger.debug(f"Number of solutions found: {num_solutions}")

    all_solutions = []
    all_requires = []

    for i in range(num_solutions):
        # if problem.solution.pool.get_objective_value(i) <= min_obj:
        selected_services = []
        selected_edges = []
        solution_values = problem.solution.pool.get_values(i)

        for j, name in enumerate(problem.variables.get_names()):
            selected = solution_values[j]
            if "->" in name and selected > 0:
                selected_edges.append(name)
            elif selected > 0:
                selected_services.append(name)
        all_solutions.append({"services": selected_services, "edges": selected_edges})
        all_requires.append(
            [
                f"{service}->{require}"
                for dfd in requires_edges.values()
                for service, requires in dfd.items()
                for require in requires
                if service in selected_services
            ]
        )
    return all_solutions, all_requires
