Ansible Provisioning
====================

This directory contains Ansible roles and playbooks for provisioning
my infrastructure.

Getting Started
---------------

`requirements.txt` contains the set of Python requirements for running
Ansible. Python 3.10.5 is tested and working.

Configure a virtualenv in this directory:

```
> virtualenv -p python3 .venv
> source .venv/bin/activate
> pip install -r requirements.txt
```

Now Ansible playbooks can be executed.

Router Provisioning
-------------------

Run the router provisioning playbook like so:

```
> ansible-playbook router-provision.yml -e centurylink_pppoe_username=<FILL IN> -e centurylink_pppoe_password=<FILL IN> -e server_admin_password=<FILL IN>
```

The values for `centurylink_pppoe_username`, `centurylink_pppoe_password`,
and `server_admin_password` can be found in my password safe. Check the
and "CenturyLink PPPoE" for PPPoE credentials and "EdgeRouter 6P" for
the `server_admin_password`.
