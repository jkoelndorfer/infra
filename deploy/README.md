# Infrastructure Deployment

This directory contains code to deploy infrastructure.

[Pulumi](https://www.pulumi.com/docs/) is used to provision infrastructure resources.
[pyinfra](https://docs.pyinfra.com) is used to configure individual nodes.

## Getting Started

### Pulumi

`pcli` is the command-line interface that is used to operate on infrastructure
stacks, state, etc. It includes built-in help. The [Pulumi CLI](https://www.pulumi.com/docs/iac/cli/)
is not usable directly without jumping through some hoops.

For general use, ensure the following environment variables are set:

`PULUMI_CONFIG_PASSPHRASE` or `PULUMI_CONFIG_PASSPHRASE_FILE`. Pulumi picks these
up directly. See [Pulumi environment variable documentation](https://www.pulumi.com/docs/iac/cli/environment-variables/).

`INFRALIB_CONFIG_PATH`: The path to the infralib configuration file, which is
expected to be in YAML format. Presently this resides in the `infra-deploy`
Syncthing folder in `config/config.yaml`.

`INFRALIB_LOCAL_BACKEND_PATH`: The local path that Pulumi is pointed to as a
state backend. Presently this resides in the `infra-deploy` Syncthing folder
in `pulumi/backend`.

## Architecture

This deployment code uses Pulumi to provision infrastructure. Pulumi's
[automation API](https://www.pulumi.com/automation/) (via the
[Python SDK](https://www.pulumi.com/docs/iac/languages-sdks/python/)) is
used so that individual [Pulumi project](https://www.pulumi.com/docs/iac/concepts/projects/)
configurations need not be maintained.

### Core Concepts: Deployment

Deployment code is located in `infralib/deployment`. Classes are named for and
have a similar purpose to their Pulumi counterparts, but they are a bit more
opinionated.

#### `InfrastructureProject`

An `InfrastructureProject` corresponds to a [Pulumi project](https://www.pulumi.com/docs/iac/concepts/projects/).
Unlike a Pulumi project, a `Pulumi.yaml` is not required. All projects are
required to use the same runtime and provider versions.

`InfrastructureProject`s must be given a `name`. The name is used to
identify the project via the commandline and is used as Pulumi's internal
project name.

The project defines infrastructure resources and deploys those resources
to a `DeploymentTarget`. Each `InfrastructureProject` defines its valid
`DeploymentTarget`s.

#### `DeploymentTarget`

A `DeploymentTarget` defines where an `InfrastructureProject` is deployed. It
consists of an environment (`dev` or `prod`) and an optional region. The region
should correspond to a cloud provider region, such as `us-east-1` in AWS,
if specified.

When an `InfrastructureProject` is deployed, one of the arguments it receives is
the `DeploymentTarget` that infrastructure is to be deployed to.

#### `InfrastructureStack`

An `InfrastructureStack` corresponds to a [Pulumi stack](https://www.pulumi.com/docs/iac/concepts/stacks/).
A stack marries an `InfrastructureProject` and a `DeploymentTarget`. It has
outputs that can be referenced from other project code.

When `InfrastructureProject`s declare their dependencies, they declare them on
an `InfrastructureStack`.

This deployment code will ultimately store one [state](https://www.pulumi.com/docs/iac/concepts/state-and-backends/)
file per `InfrastructureStack`, the same as Pulumi would typically.

### Core Concepts: Pulumi Integration

Pulumi integration code is located in `infralib/pulumi`. It provides the interface
between `infralib/deployment` code and Pulumi.

#### `PulumiOperator`

`PulumiOperator` is the class responsible for performing Pulumi operators in the same
way that the Pulumi CLI would. It exposes methods like `up` and `preview`.

It accepts `infralib/deployment` types, like `InfrastructureStack`, directly. It
converts those types to Pulumi-native types under the hood, then performs the
requested operation.

### Core Concepts: CLI

The `cli` module uses the [click](https://click.palletsprojects.com/en/stable/)
library to expose a commandline interface to infrastructure deployment
operations.

Run the `pcli` script to use it. It includes built-in help.

### Core Concepts: Projects

The `projects` module is where concrete `InfrastructureProject`s are defined.
On import, the `projects` module walks itself and imports every source file it
can find so that each `InfrastructureProject` is registered.

Ensure that subdirectories contain an `__init__.py` so that they are properly
recognized as submodules.
