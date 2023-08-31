"""
roles/miniserv/model
--------------------
"""


class Backup:
    def __init__(self, name: str, time: str, working_directory: str, src: str, dest: str) -> None:
        self.name = name
        self.time = time
        self.working_directory = working_directory
        self.src = src
        self.dest = dest
