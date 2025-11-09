#!/usr/bin/env python3

import sys

from backup.application import BackupApplication

if __name__ == "__main__":
    app = BackupApplication()
    sys.exit(app.main(sys.argv[1:]))
