# Config Manager
Config Manager is a cli python tool written to help manage configMaps and secrets
a multi-cluster kubernetes setup. The problem this aims to solve is that maintaining
secrets and configMaps in multiple clusters means for example it is easy to modify a 
config map in one cluster and forget to do so in another. This creates configuration
disparities which are frustrating to deal with. Whilst putting this config into a
Git repository that gets synced to the cluster would be ideal, there are additional
challenges if your config contains sensitive information. There are number of projects
that aim to solve that challenge which allow such a GitOps setup. For example:
- https://github.com/bitnami-labs/sealed-secrets
- https://github.com/mozilla/sops
- https://github.com/zendesk/helm-secrets (uses sops)

This cli tool is just another tool to help solve this problem, but not in a GitOps
way.

The core functionality of the cli is that it allows you to pull down all secrets 
and configMaps to a local folder for a single cluster, make modifications locally,
then push the changes to a number of upstream clusters.

## Setup
The tool is written in Python 3 and uses `pipenv` to manage its dependencies. Make
sure you have `Python 3` installed on your machine and follow the steps below in this
repositories root directory:

- `pip install pipenv`
- `pipenv install`
- `pipenv shell` - this activates the local venv and needs to be run in every new shell session where the cli will be used
- `./cm.py`

The last command should present the following output if the setup is correct:
```
Usage: cm.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  clean  Remove local config
  pull   Get config files for a namespace
  push   Update config files for a namespace
```

## Usage
There are 2 ways to use Config Manager (CM). The first and recommended way, is to create
a config file with defined 'profiles' that can be used. The second is to use command line
arguments and repeat commands to action the pull and push tasks. We will discuss both 
usages in this README.

### Pre-config
This cli uses either your local KubeConfig or specified sets of KubeConfig files. It is 
important to have local KubeConfig file(s) that allow you to access the clusters you will
be operating on.

### Profiles
To use profiles, we will use a set of local KubeConfig files. Create a directory called 
`kube-configs` and store each KubeConfig file in this directory. For example assume we have 
the following files created:
- `kube-configs/nonprod-cluster-a.yaml`
- `kube-configs/nonprod-cluster-b.yaml`
- `kube-configs/prod-cluster-a.yaml`
- `kube-configs/prod-cluster-b.yaml`

Where each `nonprod` cluster is has dev namespace and each prod cluster has a `prod` namespace.
Create a file called `config.json` in the root directory with the following contents:
```json
{
  "profiles": [
    {
      "name": "dev",
      "pull": {
        "namespace": "dev",
        "kubeConfigRef": {
          "name": "nonprod-cluster-a"
        }
      },
      "push": {
        "namespace": "dev",
        "kubeConfigRefs": [
          {
            "name": "nonprod-cluster-a"
          },
          {
            "name": "nonprod-cluster-b"
          }
        ]
      }
    },
    {
      "name": "prod",
      "pull": {
        "namespace": "prod",
        "kubeConfigRef": {
          "name": "prod-cluster-a"
        }
      },
      "push": {
        "namespace": "prod",
        "kubeConfigRefs": [
          {
            "name": "prod-cluster-a"
          },
          {
            "name": "prod-cluster-b"
          }
        ]
      }
    }
  ],
  "kubeConfigs": [
    {
      "name": "nonprod-cluster-a",
      "path": "path/to/kube-configs/nonprod-cluster-a.yaml"
    },
    {
      "name": "nonprod-cluster-b",
      "path": "path/to/kube-configs/nonprod-cluster-b.yaml"
    },
    {
      "name": "prod-cluster-a",
      "path": "path/to/kube-configs/prod-cluster-a.yaml"
    },
    {
      "name": "prod-cluster-b",
      "path": "path/to/kube-configs/prod-cluster-b.yaml"
    }
  ]
}
```

This creates 2 profiles: `dev` and `prod`. These can now be used to manage your config in
the `prod` and `nonprod` clusters following the below steps:

Run 

`./cm.py pull --profile=dev`

This we create a folder  `local-config/dev`. Inside this folder there will be `secrets` and 
`config-maps` directories. Each configMaps and each `Opaque` secret will be represented by a
folder in the relevant directory which each file representing a key value pair. The file 
contents can now be modified locally and saved. The changes can then be pushed usng the command

`./cm.py push --profile=dev`

This will push the local config to both the nonprod clusters into the dev `namespace`. The same
process can be used with the `prod` profile.

Once you are done, you should not keep copies of sensitive config locally so it can be cleaned up
by running:

`./cm.py clean`

## Command Line Config
The tool can be used without profiles too. Get all the KubeConfigs as before:

- `kube-configs/nonprod-cluster-a.yaml`
- `kube-configs/nonprod-cluster-b.yaml`
- `kube-configs/prod-cluster-a.yaml`
- `kube-configs/prod-cluster-b.yaml`

You can then pull the config locally using the command:

`./cm.py pull --namespace=dev --kube_config_file=path/to/kube-configs/nonprod-cluster-a.yaml`

The config will be pulled and can be modified as described in the profile section. It can then
be pushed using the following 2 commands:

```shell
./cm.py push --namespace=dev --kube_config_file=path/to/kube-configs/nonprod-cluster-a.yaml
./cm.py push --namespace=dev --kube_config_file=path/to/kube-configs/nonprod-cluster-b.yaml
```

This process can be repeated for `prod` too.

## Using your local KubeConfig
You can also use your local KubeConfig (located at `~/.kube/config`) for both methods. When 
specifying profiles take note following:

`kubeConfigRefs` - you can additionally specify a kube context to set here. If the context is,
not specified then the default context from the KubeConfig file will be used. Example of using context:

```json
        ...
        "kubeConfigRef": {
          "name": "local",
          "context": "nonprod-cluster-a"
        }
        ...
```

`kubeConfigs` - specifying the path to the KubeConfig file is optional. If not specified, it will automatically
try use the one at `~/.kube/config`. Example of no path:
```json
   ...
    "kubeConfigs": [
        {
          "name": "local"
        },
    ]
   ...
```

The local KubeConfig can also be used with the command line arguments. To do this, do not specify the 
`--kube_config_file` cli option and manage the active context using kubectl. E.g:

```shell
kubectl config set-context nonprod-cluster-a
./cm.py push --namespace=dev
kubectl config set-context nonprod-cluster-b
./cm.py push --namespace=dev
```