import re
import os
import shutil
import yaml
import argparse
from os import path
import logging
import sys



def get_scenario_parser(template_path):

    parser = argparse.ArgumentParser(description="Define new scenario parameters")
    parser.add_argument(
        "--scenario_name", "--name", help="New scenario name", default="test_solution"
    )

    parser.add_argument(
        "-se",
        "--service_ecosystem",
        help="Path of ServiceEcosystem.ttl",
        default=path.join(template_path, "input", "ontologies", "ServiceEcosystem.ttl"),
    )

    parser.add_argument(
        "-tt",
        "--tag_taxonomy",
        help="Path of TagTaxonomy.ttl",
        default=path.join(template_path, "input", "ontologies", "TagTaxonomy.ttl"),
    )

    parser.add_argument(
        "-s",
        "--solution",
        help="Path of solution.ttl",
        default=path.join(template_path, "input", "solution", "solution.ttl"),
    )

    parser.add_argument(
        "-p",
        "--preferences",
        help="Path of preferences.ttl",
        default=path.join(
            template_path, "input", "adds_constraints", "preferences.ttl"
        ),
    )

    parser.add_argument(
        "-m",
        "--mandatories",
        help="Path of mandatories.ttl",
        default=path.join(
            template_path, "input", "adds_constraints", "mandatories.ttl"
        ),
    )
    parser.add_argument(
        "-dfd",
        "--dfd",
        help="Path of DFD.ttl",
        default=path.join(template_path, "input", "ontologies", "DFD.ttl"),
    )
    return parser


def normalize_repositories_names(repo_config_paths, test_scenario):
    try:
        for path in repo_config_paths:
            old_value_pattern = r"DataPlatformDesign_scenario[^\n]*\n"
            new_value_pattern = (
                f"DataPlatformDesign_{test_scenario}\n"
                if ".yml" in path
                else f'DataPlatformDesign_{test_scenario}";\n'
            )

            with open(path, "r") as f:
                content = f.read()

            # Cerca e modifica il valore nel contenuto del file
            modified_content = re.sub(old_value_pattern, new_value_pattern, content)

            with open(path, "w") as f:
                f.write(modified_content)
        return True
    except Exception as e:
        print(e.__doc__)
        print(str(e))
        return False


def normalize_repository_name(old_path, new_path, new_name):
    try:
        old_value_pattern = r"DataPlatformDesign_scenario[^\n]*\n"
        new_value_pattern = f'DataPlatformDesign_{new_name}";\n'

        with open(old_path, "r") as f:
            content = f.read()

        # Cerca e modifica il valore nel contenuto del file
        modified_content = re.sub(old_value_pattern, new_value_pattern, content)

        with open(new_path, "w") as f:
            f.write(modified_content)
        return True
    except Exception as e:
        print(e.__doc__)
        print(str(e))
        return False


def listdirs(path):
    return [
        os.path.join(path, d)
        for d in os.listdir(path)
        if os.path.isdir(os.path.join(path, d))
    ]


def modify_nested_key(data, key_list, new_value):
    if len(key_list) == 1:
        data[key_list[0]] = new_value
    else:
        current_level = data
        for key in key_list[:-1]:
            if key not in current_level:
                current_level[key] = {}
            current_level = current_level[key]
        current_level[key_list[-1]] = new_value


def copy_file(src, dst):
    """Copy a file from src to dst."""
    try:
        shutil.copy(src, dst)
        print(f"File copied from {src} to {dst}")
    except IOError as e:
        print(f"Unable to copy file. {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def modify_yaml(input_path, output_path, key_to_modify, new_value):
    """Reads a YAML file and returns the content as a dictionary."""
    with open(input_path, "r") as file:
        data = yaml.safe_load(file)

    # Modifica la chiave nidificata
    modify_nested_key(data, key_to_modify, new_value)

    """Writes a dictionary to a YAML file."""
    with open(output_path, "w") as file:
        yaml.safe_dump(data, file)


def setup_logger(logger_name, log_level=10):
    log_format = "[%(asctime)s][%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # Create stream handler to print logs to standard output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
