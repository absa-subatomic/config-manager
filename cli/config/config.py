import json
import logging
import sys
from typing import List

from kubernetes import config


def configure_logging():
    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logger_instance = logging.getLogger("config_loader")
    stderr = logging.StreamHandler(sys.stdout)
    stderr.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
    stderr.setLevel(logging.DEBUG)
    logger_instance.addHandler(stderr)
    return logger_instance


log = configure_logging()


class CmConfig(object):
    def __init__(self):
        self.profiles: List[Profile] = []
        self.kubeConfigs: List[KubeConfigDefinition] = []

    @staticmethod
    def from_json(json_obj):
        cm_config = CmConfig()
        if "profiles" in json_obj:
            for profile in json_obj["profiles"]:
                cm_config.profiles.append(Profile.from_json(profile))
        if "kubeConfigs" in json_obj:
            for kube_config in json_obj["kubeConfigs"]:
                cm_config.kubeConfigs.append(KubeConfigDefinition.from_json(kube_config))
        return cm_config


class Profile(object):
    def __init__(self, name, pull, push):
        self.name: str = name
        self.pull: PullConfig = pull
        self.push: PushConfig = push

    @staticmethod
    def from_json(json_obj):
        return Profile(json_obj["name"], PullConfig.from_json(json_obj["pull"]), PushConfig.from_json(json_obj["push"]))


class PullConfig(object):
    def __init__(self, namespace, kube_config_ref):
        self.namespace: str = namespace
        self.kubeConfigRef: KubeConfigReference = kube_config_ref

    @staticmethod
    def from_json(json_obj):
        kube_config_ref = KubeConfigReference.from_json(json_obj["kubeConfigRef"])
        return PullConfig(json_obj["namespace"], kube_config_ref)


class PushConfig(object):
    def __init__(self, namespace):
        self.namespace: str = namespace
        self.kubeConfigRefs: List[KubeConfigReference] = []

    @staticmethod
    def from_json(json_obj):
        push_config = PushConfig(json_obj["namespace"])
        for kube_config_ref in json_obj["kubeConfigRefs"]:
            push_config.kubeConfigRefs.append(KubeConfigReference.from_json(kube_config_ref))
        return push_config


class KubeConfigReference(object):
    def __init__(self, name, context):
        self.name: str = name
        self.context: str = context

    @staticmethod
    def from_json(json_obj):
        name = json_obj["name"]
        context = None
        if "context" in json_obj:
            context = json_obj["context"]
        return KubeConfigReference(name, context)


class KubeConfigDefinition(object):
    def __init__(self, name, path):
        self.name: str = name
        self.path: str = path

    @staticmethod
    def from_json(json_obj):
        name = json_obj["name"]
        path = None
        if "path" in json_obj:
            path = json_obj["path"]
        return KubeConfigDefinition(name, path)


def read_config() -> CmConfig:
    with open("config.json", "r") as fh:
        cm_config: CmConfig = CmConfig.from_json(json.loads(fh.read()))

    return cm_config


def load_kube_config_file(kube_config_ref: KubeConfigReference):
    for kube_config in read_config().kubeConfigs:
        if kube_config.name == kube_config_ref.name:
            context = "default"
            if kube_config_ref.context is not None:
                context = kube_config_ref.context
            if kube_config.path is None:
                log.info(f"Loading local kubeconfig with '{context}' context...")
                config.load_kube_config(context=kube_config_ref.context)
            else:
                log.info(f"Loading kubeconfig at '{kube_config.path}' with '{context}' context...")
                config.load_kube_config(kube_config.path, context=kube_config_ref.context)
