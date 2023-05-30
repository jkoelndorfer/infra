Infrastructure Management
=========================

This repository is a central place for management of my personal infrastructure.
Like many nerds, I have an overly engineered home infrastructure setup -- but I
have fun doing it and it provides me some useful services.

This repository is broken into a few different top-level directories:

* `aws`: contains AWS-specific bits, such as Lambda function code
* `packer`: contains scripts and configuration to support building images
* `srvtools`: contains tools that are deployed to servers, including ansible
* `terraform`: contains terraform stacks and reusable modules for provisiong
  infrastructure

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
  directories to S3 using [rclone][3].
* A statically generated [blog][4].
* A [Vaultwarden][5] ([Bitwarden][6] clone) installation.


[1]: https://sourceforge.net/p/ddclient/wiki/protocols/#dyndns2
[2]: https://syncthing.net/
[3]: https://rclone.org/
[4]: https://www.johnk.io
[5]: https://github.com/dani-garcia/vaultwarden
[6]: https://bitwarden.com/
