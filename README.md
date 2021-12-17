# molgenis-py-bbmri-eric

MOLGENIS Python tooling for BBMRI-ERIC.

## Description
This library contains tools for the MOLGENIS BBMRI-ERIC Directory that help with
staging and publishing the data of the national nodes. **Staging** is the process of copying
data from a national node's external server (for example [BBMRI-NL](https://catalogue.bbmri.nl/menu/main/home)) to
the staging area on the ERIC directory. Not all national nodes have external servers; these
do not need to be staged. **Publishing** is the process of copying and combining the data from the staging areas
to the public combined tables of the directory.

## Usage

These tools can be used as a library in a script. Start by installing the library with
`pip install molgenis-py-bbmri-eric`.

```python
from molgenis.bbmri_eric.bbmri_client import EricSession
from molgenis.bbmri_eric.eric import Eric

# First, initialise an EricSession (an extension of the molgenis-py-client Session)
session = EricSession(url="<DIRECTORY_URL>")
session.login("<USERNAME>", "<PASSWORD>")

# Get the nodes you want to work with
nodes_to_stage = session.get_external_nodes(["NL", "BE"])
nodes_to_publish = session.get_nodes() # all nodes

# Create an Eric instance and use that to perform the desired actions
eric = Eric(session)
staging_report = eric.stage_external_nodes(nodes_to_stage)
publishing_report = eric.publish_nodes(nodes_to_publish)

if publishing_report.has_errors():
    raise ValueError("Some nodes did not publish correctly")
```

If you want to use the data of a node for another purpose, you can use the `EricSession`
and `ExternalServerSession` to retrieve these.

```python
from molgenis.bbmri_eric.bbmri_client import EricSession, ExternalServerSession
from molgenis.bbmri_eric.model import NodeData

# Get the staging and published data of NL from the directory
session = EricSession(url="<DIRECTORY_URL")
nl = session.get_nodes(["NL"])
nl_staging_data: NodeData = session.get_staging_node_data(nl)
nl_published_data: NodeData = session.get_published_node_data(nl)

# Get the data from the external server of NL
external_session = ExternalServerSession(node=nl)
nl_external_data: NodeData = external_session.get_node_data()

# Now you can use the NodeData objects as you wish
for person in nl_external_data.persons.rows:
    print(person)
```


## For developers
This project uses [pre-commit](https://pre-commit.com/) and [pipenv](https://pypi.org/project/pipenv/) for the development workflow.

Install pre-commit and pipenv if you haven't already:
```
pip install pre-commit
pip install pipenv
```

Install the git commit hooks:
```
pre-commit install
```

Create an environment and install the package including all (dev) dependencies:
```
pipenv install --dev
```

Enter the environment:
```
pipenv shell
```

Build and run the tests:
```
tox
```

The package's command-line entry point is already installed
```
eric -h
```


## Note

This project has been set up using PyScaffold 4.0.2. For details and usage
information on PyScaffold see https://pyscaffold.org/.
