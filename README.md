AMPR Portal API Python bindings
===============================

Install Dependencies
--------------------

    sudo pip install paramiko requests

Usage
-----

    ampr = AMPRAPI()
    result = ampr.endpoint

Example (with "encap" endpoint)
-------------------------------

    >>> import amprapi
    >>> ampr = amprapi.AMPRAPI()
    >>> for entry in ampr.encap:
    ...     print "%(network)s/%(netmask)s via %(gatewayIP)s" % entry
    ...
    44.151.22.22/32 via 2.10.28.74
    44.182.69.0/24 via 5.15.186.251
    44.133.30.64/32 via 5.57.28.49
    ...


Settings
========

To use the AMPR Portal API, you need to set an API key via your AMPR Portal
Profile. Once you have set your API key, save your username and API key in
`settings.py`.


updateros.py
=============

Requests the list of encap routes from the AMPR Portal API, then updates the
target Mikrotik router with new, removed, or changed routes.

Usage
-----

	./updateros.py [-v] [-n] [-f] TARGET_IP

`-f` force. Continue even when sanity check fails.

`-n` dry-run. No changes will be made to target router.

`-v` verbose mode. Commands to target router will be printed.
