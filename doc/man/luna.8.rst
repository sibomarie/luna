====
luna
====

-------------------------------------------
command to edit Luna cluster configuration.
-------------------------------------------

:Author: Dmitry Chirikov
:Date:   October 2016
:Manual section: 8

SYNOPSIS
========

``luna`` [ *--help* | *-h* ]

``luna`` *object* [ *--help* | *-h* ]

``luna`` *object* *action* [ *--help* | *-h* ] [ *OPTIONS* ...]

DESCRIPTION
===========

``luna`` is used to view and edit objects in Luna database.

GETTING QUICK HELP
==================

``--help``, ``-h``
    Getting list of supported objects.
*object* [ ``--help``, ``-h`` ]
    Getting list of supported actions for object.
*object* *action* [ ``--help``, ``-h`` ]
    Getting list of supported options for particular object and action.

OBJECTS, ACTIONS AND OPTIONS
============================

``cluster``
    Global configuration of the Luna cluster. Configuration of external services.

    ``init``
        Initialize cluster configuration.

        ``--nodeprefix``, ``--prefix``, ``-p``
            Prefix for newly created nodes: nodeXXX, hostXXX, nXXX, etc. Default is "*node*".

        ``--nodedigits``, ``--digits``, ``-d``
            Leading zeros to node number: node01, node001, node0001, etc. Default is *3*.

        ``--path``
            Path to store kernels, initrd, tarballs (with packed OSes), bittorrent files, scripts' templates. It is assumed that it is a HOMEDIR for user, used to run services (see bellow). Default is "*/opt/luna*"

        ``--user``
            Name of the system user to start luna services (lweb, ltorrent). All files are needed to be accessed by daemons should be owned by this user. Default is *luna*

    ``show``
        Print global cluster config.
