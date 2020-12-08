import base64
import json
import logging
import os
import sys
from os import path

import click
import kubernetes
from kubernetes import config
from kubernetes.client.rest import ApiException

from cli.config.config import read_config, load_kube_config_file


def configure_logging():
    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logger_instance = logging.getLogger("push_config")
    stderr = logging.StreamHandler(sys.stdout)
    stderr.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
    stderr.setLevel(logging.DEBUG)
    logger_instance.addHandler(stderr)
    return logger_instance


log = configure_logging()


def push_config_maps(kube_config, namespace):
    api_instance = kubernetes.client.CoreV1Api(kubernetes.client.ApiClient(kube_config))

    try:
        config_maps = api_instance.list_namespaced_config_map(namespace)

        cwd = os.getcwd()

        local_config_directory = path.join(cwd, "local-config")

        ns_output_directory = path.join(local_config_directory, namespace, "config-maps")
        if not os.path.exists(ns_output_directory) or not os.path.isdir(ns_output_directory):
            log.error(f"{ns_output_directory} does not exist. Exiting...")
            sys.exit(1)

        config_map_dict = {}

        for config_map in config_maps.items:
            config_map_dict[config_map.metadata.name] = config_map

        dir_name_index = 1
        file_name_index = 2
        for local_config_name in next(os.walk(ns_output_directory))[dir_name_index]:
            config_map_directory = path.join(ns_output_directory, local_config_name)
            config_map_data_entries = next(os.walk(config_map_directory))[file_name_index]
            config_map_data = {}
            for data_key in config_map_data_entries:
                with open(path.join(config_map_directory, data_key), "r") as fh:
                    config_map_data[data_key] = fh.read()

            if local_config_name in config_map_dict:
                config_map_dict[local_config_name].data = config_map_data
                log.info(f"Updating config map {local_config_name}")

                api_instance.replace_namespaced_config_map(local_config_name, namespace,
                                                           config_map_dict[local_config_name])
            else:
                log.info(f"Config map {local_config_name} does not exist! Skipping")

    except ApiException as e:
        if e.status == 404:
            log.error(json.loads(e.body)["message"])
            exit(1)
        raise e


def push_secrets(kube_config, namespace):
    api_instance = kubernetes.client.CoreV1Api(kubernetes.client.ApiClient(kube_config))

    try:
        secrets = api_instance.list_namespaced_secret(namespace)

        cwd = os.getcwd()

        local_config_directory = path.join(cwd, "local-config")

        ns_output_directory = path.join(local_config_directory, namespace, "secrets")
        if not os.path.exists(ns_output_directory) or not os.path.isdir(ns_output_directory):
            log.error(f"{ns_output_directory} does not exist. Exiting...")
            sys.exit(1)

        secret_dict = {}

        for secret in secrets.items:
            secret_dict[secret.metadata.name] = secret

        dir_name_index = 1
        file_name_index = 2
        for local_secret_name in next(os.walk(ns_output_directory))[dir_name_index]:
            secret_directory = path.join(ns_output_directory, local_secret_name)
            secret_data_entries = next(os.walk(secret_directory))[file_name_index]
            secret_data = {}
            for data_key in secret_data_entries:
                with open(path.join(secret_directory, data_key), "r") as fh:
                    secret_data[data_key] = base64.b64encode(str.encode(fh.read())).decode("utf-8")

            if local_secret_name in secret_dict:
                secret_dict[local_secret_name].data = secret_data
                log.info(f"Updating secret {local_secret_name}")

                api_instance.replace_namespaced_secret(local_secret_name, namespace,
                                                       secret_dict[local_secret_name])
            else:
                log.info(f"Secret {local_secret_name} does not exist! Skipping")

    except ApiException as e:
        if e.status == 404:
            log.error(json.loads(e.body)["message"])
            exit(1)
        raise e


# Used to create a closure with kube_config_ref available to deferred function
def create_set_config_closure(kube_config_ref):
    def set_config():
        load_kube_config_file(kube_config_ref)

    return set_config


def _push_config(namespace, kube_config_file, profile):
    log.info("Trying to load kubeconfig...")

    contexts = []

    if profile is not None:
        cm_config = read_config()
        for profile_definition in cm_config.profiles:
            if profile_definition.name == profile:
                namespace = profile_definition.push.namespace
                for push_kube_config in profile_definition.push.kubeConfigRefs:
                    contexts.append(create_set_config_closure(push_kube_config))

    else:
        if kube_config_file == "local":
            def set_config():
                log.info("Using local kube config...")
                config.load_kube_config()

            contexts.append(set_config)
        else:
            def set_config():
                log.info(f"Using kube config located at {kube_config_file}...")
                config.load_kube_config(kube_config_file)

            contexts.append(set_config)

    for load_context_function in contexts:
        load_context_function()
        c = kubernetes.client.Configuration()
        c.assert_hostname = False
        kubernetes.client.Configuration.set_default(c)
        push_config_maps(c, namespace)
        push_secrets(c, namespace)
        log.info("Done pushing config for current context")


@click.command(name="push", help="Update config files for a namespace")
@click.option("--namespace", required=False, help="Namespace to find the deployment to watch")
@click.option("--kube_config_file", default="local", help="Path to kube config file to use")
@click.option("--profile", required=False, help="Profile to use. If specified, overrides all other options")
def push_config(namespace, kube_config_file, profile):
    _push_config(namespace, kube_config_file, profile)


if __name__ == '__main__':
    _push_config(None, None, "dev")
