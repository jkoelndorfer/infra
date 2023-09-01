"""
roles/miniserv/model
--------------------
"""


class Backup:
    def __init__(self, container_name: str, time: str, working_directory: str, src: str, dest: str) -> None:
        self.container_name = container_name
        self.time = time
        self.working_directory = working_directory
        self.src = src
        self.dest = dest
