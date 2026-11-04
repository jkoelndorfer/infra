Infrastructure Management
=========================

This repository is a central place for management of my personal infrastructure.
Like many nerds, I have an overly engineered home infrastructure setup -- but I
have fun doing it and it provides me some useful services.

This repository is broken into a few different top-level directories:

* `container-images`: contains custom container image builds, most notably the
   backupjob container which runs backups
* `deploy`: contains a small, opionated, custom [Pulumi Automation API][1] framework
  for provisioning infrastructure consistently and eliminating boilerplate. This is
  what infrastructure as code _should be_.

Overview
--------

This repository provides a full infrastructure deployment for a few useful
services:

* Personal dynamic DNS for the homelab, using a subset of the
  [dyndns2 protocol][2].
* A personal [Syncthing][3] file sync server.
* A nightly backup service that saves all of the Syncthing
  directories to S3 using [restic][4] and [rclone][5].
* A statically generated [blog][6].
* A [Vaultwarden][7] ([Bitwarden][8] clone) installation.

[1]: https://www.pulumi.com/automation/
[2]: https://help.dyn.com/remote-access-api/perform-update/
[3]: https://syncthing.net/
[4]: https://github.com/restic/restic
[5]: https://rclone.org/
[6]: https://www.johnk.io
[7]: https://github.com/dani-garcia/vaultwarden
[8]: https://bitwarden.com/
