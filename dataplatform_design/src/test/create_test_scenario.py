import os
import test_utils
import sys

template_path = os.path.join("dataplatform_design", "resources", "scenario_template")
scenarios_directory = os.path.join("dataplatform_design", "src", "test", "scenarios")
parser = test_utils.get_scenario_parser(template_path)

args = parser.parse_args()
args_dict = vars(args)

scenario_name = args.scenario_name
logger = test_utils.setup_logger("DataPlatform_ScenarioCreation")
# Build scenario directory structure
new_scenario_path = os.path.join(scenarios_directory, scenario_name)

if os.path.exists(new_scenario_path):
    logger.exception(f"Scenario {new_scenario_path} alredy exists.")
    sys.exit(1)

template_structure = {
    "config": f"{template_path}/configs/",
    "ontologies": f"{template_path}/input/ontologies/",
    "adds_constraints": f"{template_path}/input/adds_constraints/",
    "solution": f"{template_path}/input/solution/",
    "output": f"{template_path}/output/",
}

scenario_resources_path_dict = {
    "dpdo": f"{new_scenario_path}/input/ontologies",
    "service_ecosystem": f"{new_scenario_path}/input/ontologies",
    "tag_taxonomy": f"{new_scenario_path}/input/ontologies",
    "dfd": f"{new_scenario_path}/input/ontologies",
    "mandatories": f"{new_scenario_path}/input/adds_constraints",
    "preferences": f"{new_scenario_path}/input/adds_constraints",
    "solution": f"{new_scenario_path}/input/solution",
    "repo_config": f"{new_scenario_path}/configs",
    "output": f"{new_scenario_path}/output",
}

# Build new scenario directory tree
for dir_name, dir_path in scenario_resources_path_dict.items():
    os.makedirs(dir_path, exist_ok=True)
    logger.info(f"Created scenario directory: {dir_path}")

new_config_path = os.path.join(
    scenario_resources_path_dict["repo_config"], "config.yml"
)

# # Push config files into new scenario
# test_utils.modify_yaml(
#     os.path.join(template_structure["config"], "config.yml"),
#     new_config_path,
#     ["graph_db", "repository"],
#     f"DataPlatformDesign_{scenario_name}",
# )
test_utils.normalize_repository_name(
    os.path.join(template_structure["config"], "repo-config.ttl"),
    os.path.join(scenario_resources_path_dict["repo_config"], "repo-config.ttl"),
    scenario_name,
)

# Move ontologies into new scenario folder

args_dict.update({"dpdo": os.path.join(template_structure["ontologies"], "DPDO.ttl")})

# Iterate over the dictionary

for arg_name, arg_value in args_dict.items():
    if arg_name not in [
        "scenario_name",
        "service_ecosystem",
        "tag_taxonomy",
        "dpdo",
        "preferences",
    ]:
        print(arg_name)
        # Copy args provided files

        test_utils.copy_file(
            arg_value,
            arg_value.replace(
                os.sep.join(arg_value.split(os.sep)[:-1]),
                scenario_resources_path_dict[arg_name],
            ),
        )

        # Update config file to refer to new ontologies.ttl paths
        test_utils.modify_yaml(
            new_config_path,
            new_config_path,
            (
                ["ontologies", "paths", arg_name]
                if arg_name not in ["mandatories", "preferences", "solution"]
                else (
                    ["ontologies", arg_name]
                    if arg_name == "solution"
                    else ["ontologies", "adds_constraints_paths", arg_name]
                )
            ),
            arg_value.replace(
                os.sep.join(arg_value.split(os.sep)[:-1]),
                scenario_resources_path_dict[arg_name],
            ),
        )
