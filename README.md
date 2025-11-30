Infrastructure Management
=========================

This repository is a central place for management of my personal infrastructure.
Like many nerds, I have an overly engineered home infrastructure setup -- but I
have fun doing it and it provides me some useful services.

This repository is broken into a few different top-level directories:

* `aws`: *legacy*; contains AWS-specific bits, such as Lambda function code
* `container-images`: contains custom container image builds, most notably the
   backupjob container which runs backups
* `srvtools`: contains tools that are deployed to servers, including pyinfra
* `terraform`: *legacy*; contains terraform stacks and reusable modules for provisioning
  infrastructure
* `terragrunt`: contains terragrunt global configuration, stacks, units, and reusable
  modules for provisioning infrastructure

Overview
--------

This repository provides a full infrastructure deployment for a few useful
services:

* Personal dynamic DNS that is _almost_ compatible with the
  [dyndns2 protocol][1]. The only reason it isn't is because
  of some limitations with API Gateway at the time of this
  writing.
* A personal [Syncthing][2] file sync server.
* A nightly backup service that saves all of the Syncthing
  directories to S3 using [restic][3] and [rclone][4].
* A statically generated [blog][6].
* A [Vaultwarden][6] ([Bitwarden][7] clone) installation.

[1]: https://sourceforge.net/p/ddclient/wiki/protocols/#dyndns2
[2]: https://syncthing.net/
[3]: https://github.com/restic/restic
[4]: https://rclone.org/
[5]: https://www.johnk.io
[6]: https://github.com/dani-garcia/vaultwarden
[7]: https://bitwarden.com/
