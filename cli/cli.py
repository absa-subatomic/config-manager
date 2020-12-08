import click

from cli.kube.pull_config import pull_config
from cli.kube.push_config import push_config
from cli.kube.clean_config import clean_config


@click.group()
def entry_point():
    pass


entry_point.add_command(pull_config)
entry_point.add_command(push_config)
entry_point.add_command(clean_config)

if __name__ == "__main__":
    entry_point()
