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

**luna** [ *--help* | *-h* ]

**luna** *object* [ *--help* | *-h* ]

**luna** *object* *action* [ *--help* | *-h* ] [ *OPTIONS* ...]

DESCRIPTION
===========

**luna** is used to view and edit objects in Luna database.

GETTING QUICK HELP
==================

**--help**, **-h**
    Getting list of supported objects.
*object* [ **--help**, **-h** ]
    Getting list of supported actions for object.
*object* *action* [ **--help**, **-h** ]
    Getting list of supported options for particular object and action.

OBJECTS, ACTIONS AND OPTIONS
============================

**cluster**
    Global configuration of the Luna cluster. Configuration of external services.

    **init**
        Initialize cluster configuration.

        **--nodeprefix**, **--prefix**, **-p**
            Prefix for newly created nodes: nodeXXX, hostXXX, nXXX, etc. Default is "*node*".

        **--nodedigits**, **--digits**, **-d**
            Leading zeros to node number: node01, node001, node0001, etc. Default is *3*.

        **--path**
            Path to store kernels, initrd, tarballs (with packed OSes), bittorrent files, scripts' templates. It is assumed that it is a HOMEDIR for user, used to run services (see bellow). Default is "*/opt/luna*"

        **--user**
            Name of the system user to start luna services (lweb, ltorrent). All files are needed to be accessed by daemons should be owned by this user. Default is *luna*

    **show**
        Print global cluster config.

        **--raw**, **-R**
            Print raw JSON of the object.

    **change**
        Change global cluster configuration options.

        **--nodeprefix**, **--prefix**, **-p**
            Prefix for newly created nodes: nodeXXX, hostXXX, nXXX, etc.

        **--nodedigits**, **--digits**, **-d**
            Leading zeros to node number: node01, node001, node0001, etc.

        **--path**
            Path to store kernels, initrd, tarballs (with packed OSes), bittorrent files, scripts' templates. User defined in **--user** should have *rw* access to this folder.

        **--user**
            Name of the system user is used to start luna services (lweb, ltorrent). All files are needed to be accessed by daemons should be owned by this user.

        **--frontend_address**
            IP address of the interface of the master node. It is being used to access services provided by *lweb* using HTTP protocol: boot scripts, installation scripts, torrent tracker. Port to reach the services is specified as **--frontend_port**. Combination http://frontend_address:frontend_port can be used for quick check.
            
            Example:
                
                ```
                curl "http://10.30.255.254:7050/luna?step=boot"
                ```

            No default value for it! Should be set up right after **luna cluster init** command.




