# AGENTS.md

Personal infrastructure, deployed with Pulumi's Automation API in Python. All
Pulumi-related work belongs in `deploy/`.

## Repository layout

| Path | Status |
| --- | --- |
| `deploy/` | **Modern. Work here.** Pulumi projects, the `pcli` CLI, and tests. |
| `terraform/`, `terragrunt/` | **Legacy.** Do not extend. Read them only as a reference when porting something to `deploy/`. |
| `container-images/` | Custom images, such as `backupjob`, which `homelab.backup` deploys. |
| `srvtools/` | Tools deployed to servers, including pyinfra. |

Paths below are relative to `deploy/`. `deploy/README.md` explains the
architecture in more depth.

## Commands

Run these from `deploy/`. The scripts set up the environment themselves through
`with-venv` (mise for tools, uv for packages), so do not activate a virtualenv
or call `pip`.

```bash
./run-checks                # linters and every test, including slow ones
./run-linters               # mypy --strict . and ruff check .
./run-tests                 # pytest under coverage; extra args go to pytest
./run-tests -m "not slow"   # skip the slow tests (see "Slow tests" below)
./run-tests -k test_name
./with-venv ruff format .   # not enforced by the scripts, but the tree is formatted
./pcli --help               # infrastructure CLI
./pcli test check           # render every stack offline and check the results
./pcli test render -p homelab.unifi -e prod   # print what a stack would create
```

The test suite needs:

- **The Pulumi CLI on `PATH`.** It is pinned in `mise.toml`; run `mise install`
  if `mise ls` shows it as missing.
- **`PULUMI_CONFIG_PASSPHRASE` set.** Any value works, because tests use a
  temporary backend: `PULUMI_CONFIG_PASSPHRASE=test ./run-tests`.

Without these, tests fail with `No such file or directory: 'pulumi'` or
`passphrase must be set`. Those are environment problems, not code bugs. Tests
need no cloud credentials, but the first run downloads the `command` provider
plugin.

### Slow tests

Tests marked `@pytest.mark.slow` run real Pulumi operations against a temporary
backend and take most of the suite's time. They are the operator tests in
`tests/infralib/pulumi/test_operator.py` and the `pcli stack` tests in
`tests/cli/test_stack_cmd.py`.

Run them only when a change touches infralib's Pulumi code: `infralib/pulumi/`,
`cli/stack.py`, or the Pulumi CLI or SDK versions. For any other change, run
`./run-linters` and `./run-tests -m "not slow"` before calling work finished,
instead of `./run-checks`. Coverage of `infralib/pulumi/` and `cli/stack.py` drops
when the slow tests are skipped; that is expected.

## Safety: this manages live infrastructure

- **`pcli test` is always safe to run.** It uses Pulumi's mock runtime and dummy
  configuration. `main()` skips global initialization for it, so it never loads
  real configuration or touches a backend, and it needs no credentials.
- **Do not run `pcli stack up`, `destroy`, or `rename` unless the user asks.**
  They act on real AWS, GCP, and homelab resources. Never add `--no-confirm` on
  your own initiative.
- **`pcli stack preview` is not read-only.** It refreshes by default, which
  writes to state, and it creates the stack in state if the stack does not exist
  yet. Treat it as needing the same request from the user, and use `--no-refresh`
  to reduce its effect.
- **Do not use the `pulumi` CLI directly against the backend**, and do not edit
  state files. To get a synthesized project directory, use `pcli stack shell`.
- **Do not read or print the files behind `INFRALIB_CONFIG_PATH` or
  `INFRALIB_LOCAL_BACKEND_PATH`** unless asked. They hold real configuration and
  state, and the folder is synced by Syncthing, so changes propagate.
- Generating secrets that land in Pulumi state is acceptable. Pulumi's state
  encrypts secrets. The state is protected and not pushed to any remote source,
	except via encrypted backups.

`pcli` requires `INFRALIB_CONFIG_PATH`, `INFRALIB_LOCAL_BACKEND_PATH`, and
`PULUMI_CONFIG_PASSPHRASE` (or `PULUMI_CONFIG_PASSPHRASE_FILE`). If they are
missing, ask the user rather than creating substitutes.

## Architecture

| Path | Contents |
| --- | --- |
| `infralib/deployment/` | `InfrastructureProject`, `InfrastructureStack`, `DeploymentTarget`, `DeploymentContext` |
| `infralib/pulumi/` | `PulumiOperator`, `InfrastructureComponent`, `ProviderFactory`, backend and naming helpers |
| `infralib/config/` | Typed configuration, parsed from YAML |
| `infralib/testing/` | Offline rendering and checks behind `pcli test` |
| `infralib/error.py` | All infralib errors, derived from `InfralibError` |
| `cli/` | Click CLI behind `pcli` |
| `projects/` | Concrete projects, such as `dns.zones` and `homelab.traefik` |
| `provision/` | pyinfra inventory, deployment and server roles. Do not run it against real hosts unless the user asks. `render_switch_config` only prints switch commands |
| `tests/` | Mirrors `cli/` and `infralib/`; `tests/projects/` renders every project |

There are no `Pulumi.yaml` files. A project is a Python class, and a stack is a
project plus a target. Stacks are named `<project>/<env>` or
`<project>/<env>.<region>`, for example `homelab.vaultwarden/prod`.

## Adding or changing a project

Copy a similar project. `projects/noop.py` is the minimal example, and
`projects/homelab/vaultwarden/` is a typical Kubernetes service.

```python
class HomelabExampleProject(InfrastructureProject):
    name = "homelab.example"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [HomelabTraefikProject.stack(DeploymentTarget(Environment.PROD, None))]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(e, None) for e in [Environment.DEV, Environment.PROD]]

    def pulumi_program(self) -> None: ...
```

- **Registration is automatic.** Subclassing registers the project, and importing
  `projects` imports every module under it. Every package directory needs an
  `__init__.py`, or the project is silently not discovered.
- **Keep import time free of side effects.** Every module is imported on each
  `pcli` run. Do the work inside `pulumi_program()`.
- **Layout:** `projects/<area>/<name>/project.py`, with `__init__.py` re-exporting
  the class and listing it in `__all__`. Names are dotted: `<area>.<name>`.
- **Declare every stack you read from.** `dependencies()` lists direct
  dependencies only, and `dctx.outputs(stack)` raises `UndeclaredDependencyError`
  for anything else. Dependency cycles raise `CircularDependencyError`.
- **Choose the dependency's target deliberately.** Shared services use prod for
  every environment (`DeploymentTarget(Environment.PROD, None)`). Per-environment
  dependencies pass `target` through. See `homelab/backup/project.py` for both.
- **Expose outputs through classmethods on the owning project**, such as
  `AWSAccountsProject.lookup_account` and `DNSZonesProject.lookup_zone`, so that
  consumers do not parse another project's raw outputs.
- **Reuse the homelab helpers** in `projects/homelab/kubernetes/`
  (`HomelabKubernetesDeployment`, `namespace`, `helm_release`, `service_fqdn`,
  volumes) and `projects/homelab/traefik/` before using raw Kubernetes resources.
- **Pin container image tags and chart versions.**
- **Split large programs** into `provision_*` functions in sibling modules, as in
  `homelab/backup/`.

### Pulumi behavior that differs from the defaults

Every stack is configured in `infralib/pulumi/operator/tools.py` with:

- **Default providers disabled.** Every resource needs an explicit provider. Get
  one from `self.dctx.provider_factory` and pass it through
  `ResourceOptions(provider=...)`. Accounts other than management use
  `AWSAccountsProject.lookup_account`, which returns a provider.
- **Autonaming set to `verbatim`.** No random suffix is added, so physical names
  must be unique and replacements can collide with the resource they replace.

### Components

Subclass `InfrastructureComponent[ArgsDataclass]`:

- Implement `provision()`, which the constructor calls.
- Pass `self.default_ropts` to child resources so they are parented correctly.
- Declare outputs with `self.output()`. Calling `register_outputs()` raises an
  error.

### Renames can replace resources

These all change a resource's URN, so Pulumi may delete and recreate it. Call out
any such change to the user, especially for stateful resources:

- logical resource names
- `InfrastructureComponent` subclass names, which are part of the type token
- project names, or anything else in the stack's identity (`pcli stack rename`
  moves a stack's state)

Bringing an existing resource under management uses `ResourceOptions(import_=...)`;
the `namespace()` helper takes `import_=True`. Imports are temporary: remove them once
the import has been deployed, because a leftover import prevents a stack from being
rebuilt. `pcli test check` and `./run-tests` fail while one is in place.

## Code style

Python 3.14 with `mypy --strict`, including tests. Match the surrounding code:

- Every module opens with a docstring: a title, an underline of `=` of matching
  length, and a description. Tests and `infralib` use `path/to/module -- Title`;
  `projects` uses the dotted module name.
- Docstrings start on the line after the opening quotes.
- Use modern syntax: `X | None`, `class Foo[T]`, and unquoted forward references.
- Use dataclasses for component arguments, named `<Component>Args`.
- Common names: `dctx` for `DeploymentContext`, `ropts`/`opts` for
  `ResourceOptions`.
- Import the public API from `infralib`, and add new public names to its
  `__init__.py` and `__all__`.
- New errors go in `infralib/error.py`. The CLI turns expected errors into
  `click.ClickException`.
- Comments explain why, not what. Link external documentation with `[1]`-style
  footnotes in docstrings. Use `NOTE:` for manual steps and non-obvious constraints.
- Avoid `# type: ignore`. `pcast` (in `infralib/pulumi/types.py`) covers cases
  where Pulumi's types reject an `Output` that works at runtime.
- Shell scripts: a banner comment naming the script, tab indentation, and paths
  resolved from `script_dir`.

## Testing

- Add tests under `tests/`, mirroring the source path, for any change to `cli/` or
  `infralib/`.
- **Do not write throwaway mock scripts to test a project.** `tests/projects/`
  renders every stack of every project and runs the checks in
  `infralib/testing/checks.py`, so new projects are covered automatically.
- **To test a change to a project, render the previous revision and compare.** Run
  this from `deploy/`, with `<rev>` set to the revision the change is based on, and
  use a temporary directory that is outside the repository:

  ```bash
  git archive <rev> . | tar -x -C "$old_tree"
  diff -u <("$old_tree/pcli" test render -p homelab.unifi -e prod) \
          <(./pcli test render -p homelab.unifi -e prod)
  ```

  For a change to shared code, leave out `-p` and `-e` to compare every stack. Read
  the diff and confirm that it contains only what you intended. Call out URN changes,
  because they can replace resources.
- **If a render crashes on a value that a provider would compute,** add it to
  `_computed_state` or `_CALL_RESULTS` in `infralib/testing/render.py`.
- **Rendering does not validate a deployment.** No provider code runs, so it cannot
  find provider validation errors, missing permissions, collisions with existing
  resources, or chart behavior. Say so when reporting: real validation needs a
  preview, which the user must request.
- Operator tests run real Pulumi against a temporary local backend. Use the
  fixtures in `tests/conftest.py` and `tests/infralib/pulumi/conftest.py`, along
  with `Environment.TEST`, `CommandOnlyProviderFactory`, and the Pulumi mock
  fixture.
- **DO NOT** write tests to make assertions about specific projects. Infrastructure
  functionality needs to be manually validated after deployment and after every
	change. Previews help detect unwanted changes.
- Never point tests at real cloud providers or real configuration.
- Mark code that only runs against real providers with `# pragma: no cover`, as in
  `StandardProviderFactory`.

## Dependencies

- Change Python dependencies with `uv add` or by editing `pyproject.toml`, and keep
  `uv.lock` in sync.
- The Pulumi CLI (`mise.toml`) and the Python SDK (`pyproject.toml`) are pinned
  separately. Check both when bumping either.
- `pcli` disables automatic plugin downloads, so provider plugins must already be
  installed.

## Version control

The repository is colocated jj and git, so `HEAD` is normally detached.
Ensure you know which commit the user would like to base work on.

Commit subjects are `<scope>: <Imperative summary>`, for example
`deploy/homelab: Implement homelab.backup project` or
`pulumi provider: Add support for instantiating Kubernetes client`.
