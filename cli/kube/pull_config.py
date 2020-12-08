import base64
import json
import logging
import os
import shutil
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
    logger_instance = logging.getLogger("get_config")
    stderr = logging.StreamHandler(sys.stdout)
    stderr.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
    stderr.setLevel(logging.DEBUG)
    logger_instance.addHandler(stderr)
    return logger_instance


log = configure_logging()


def get_config_maps(kube_config, namespace):
    api_instance = kubernetes.client.CoreV1Api(kubernetes.client.ApiClient(kube_config))

    try:
        config_maps = api_instance.list_namespaced_config_map(namespace)

        cwd = os.getcwd()

        local_config_directory = path.join(cwd, "local-config")

        ns_output_directory = path.join(local_config_directory, namespace, "config-maps")
        if os.path.exists(ns_output_directory) and os.path.isdir(ns_output_directory):
            shutil.rmtree(ns_output_directory)
        os.makedirs(ns_output_directory)

        for config_map in config_maps.items:
            cm_output_dir = path.join(ns_output_directory, config_map.metadata.name)
            os.mkdir(cm_output_dir)
            for config_key in config_map.data:
                cm_file_path = path.join(cm_output_dir, config_key)
                with open(cm_file_path, "w") as fh:
                    fh.write(config_map.data[config_key])

    except ApiException as e:
        if e.status == 404:
            log.error(json.loads(e.body)["message"])
            exit(1)
        raise e


def get_secrets(kube_config, namespace):
    api_instance = kubernetes.client.CoreV1Api(kubernetes.client.ApiClient(kube_config))

    try:
        secrets = api_instance.list_namespaced_secret(namespace)

        cwd = os.getcwd()

        local_config_directory = path.join(cwd, "local-config")

        ns_output_directory = path.join(local_config_directory, namespace, "secrets")
        if os.path.exists(ns_output_directory) and os.path.isdir(ns_output_directory):
            shutil.rmtree(ns_output_directory)
        os.makedirs(ns_output_directory)

        for secret in secrets.items:
            if secret.type != "Opaque":
                continue

            secret_output_dir = path.join(ns_output_directory, secret.metadata.name)
            os.mkdir(secret_output_dir)
            for secret_key in secret.data:
                cm_file_path = path.join(secret_output_dir, secret_key)
                with open(cm_file_path, "w") as fh:
                    fh.write(base64.b64decode(secret.data[secret_key]).decode("utf-8"))

    except ApiException as e:
        if e.status == 404:
            log.error(json.loads(e.body)["message"])
            exit(1)
        raise e


def _pull_config(namespace, kube_config_file, profile):
    log.info("Trying to load kubeconfig...")

    if profile is not None:
        cm_config = read_config()
        for profile_definition in cm_config.profiles:
            if profile_definition.name == profile:
                namespace = profile_definition.pull.namespace
                load_kube_config_file(profile_definition.pull.kubeConfigRef)
    else:
        if kube_config_file == "local":
            config.load_kube_config()
        else:
            config.load_kube_config(kube_config_file)

    c = kubernetes.client.Configuration()
    c.assert_hostname = False
    kubernetes.client.Configuration.set_default(c)

    get_config_maps(c, namespace)
    get_secrets(c, namespace)
    log.info("Done pulling config")


@click.command(name="pull", help="Get config files for a namespace")
@click.option("--namespace", required=False, help="Namespace to find the deployment to watch")
@click.option("--kube_config_file", default="local", help="Path to kube config file to use")
@click.option("--profile", required=False, help="Profile to use. If specified, overrides all other options")
def pull_config(namespace, kube_config_file, profile):
    _pull_config(namespace, kube_config_file, profile)


if __name__ == '__main__':
    _pull_config(None, None, "dev")
