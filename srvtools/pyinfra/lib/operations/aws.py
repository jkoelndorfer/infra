"""
lib/operations
--------------

This module contains custom pyinfra AWS operations.
"""

from pyinfra import host, state
from pyinfra.api import operation, OperationError, StringCommand, QuoteString
from pyinfra.api.command import make_formatted_string_command as scmd
from pyinfra.facts.files import Sha256File
from pyinfra.operations.util import files


# See the source of the files.download operation [1][2]
# as a reference for implementing this.
#
# [1]: https://github.com/Fizzadar/pyinfra/blob/a47cf23e81e2cd40cc9ffdd29717c91966b5a751/pyinfra/operations/files.py#L59
# [2]: https://docs.pyinfra.com/en/2.x/operations/files.html#files-download
@operation(
    pipeline_facts={"file": "dest"},
)
def s3_download(
    src: str,
    dest: str,
    user: str,
    group: str,
    mode: str,
    sha256sum: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
):
    """
    Downloads a file from S3 to the path given by `dest`.
    """

    if not src.startswith("s3://"):
        raise OperationError("src must start with 's3://'")

    do_download = True
    if sha256sum == host.get_fact(Sha256File, path=dest):
        do_download = False

    temp_file = None
    if do_download:
        temp_file = state.get_temp_filename(dest)
        yield StringCommand(
            "aws",
            "s3",
            "cp",
            QuoteString(src),
            QuoteString(temp_file),
            env={
                "AWS_ACCESS_KEY_ID": aws_access_key_id,
                "AWS_SECRET_ACCESS_KEY": aws_secret_access_key,
            }
        )
        yield scmd(
            r"""
            test "$(sha256sum {0} | awk {1})" = {2} || (printf {3} >&2 && exit 1)
            """,
            QuoteString(temp_file),
            QuoteString("{ print $1 }"),
            QuoteString(sha256sum),
            QuoteString(r"sha256sum did not match\n"),
        )
        yield StringCommand("mv", QuoteString(temp_file), QuoteString(dest))

    yield files.chown(dest, user, group)
    yield files.chmod(dest, mode)

    for f in filter(lambda i: i is not None, [dest, temp_file]):
        host.delete_fact(Sha256File, kwargs={"path": f})
