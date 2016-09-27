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

.. _cluster:

**cluster**
    Global configuration of the Luna cluster. Configuration of external services.

.. _cluster-init:

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
            IP address of the interface of the master node. It is being used to access services provided by *lweb* using HTTP protocol: boot scripts, installation scripts, torrent tracker. Port to reach the services is specified as **--frontend_port**. Combination ``http://frontend_address:frontend_port`` can be used for quick check.

            Example::

                curl "http://10.30.255.254:7050/luna?step=boot"

            No default value for it! Should be set up right after **luna cluster init** command.

        **--frontend_port**
            TCP port of the HTTP reverse proxy server. Default is 7050. Please don't mix it with **--server_port**.

        **--server_port**
            Port *lweb* listens on localhost. Default is 7051. Service *lweb* opens socket only on 127.0.0.1 and port specified at **--server_port**. To reach *lweb* from remote HTTP reverse proxy server is using. Nginx is default. URL ``http://localhost:server_port`` allows to connect derectly to lweb avoiding HTTP-proxy.

            Example::

                curl "http://localhost:7051/luna?step=boot"

        **--tracker_interval**
            Default is *10* sec. "Interval in seconds that the client should wait between sending regular requests to the tracker." https://wiki.theory.org/BitTorrentSpecification.

        **--tracker_min_interval**
            Default is *5* sec. "Minimum announce interval. If present clients must not reannounce more frequently than this." https://wiki.theory.org/BitTorrentSpecification.

        **--tracker_maxpeers**
            Default is *200*. Torrent tracker max allowed peers. It is uppper bound for *numwant*: "Number of peers that the client would like to receive from the tracker." https://wiki.theory.org/BitTorrentSpecification.

        **--torrent_listen_port_min**
            *ltorrent* tunable. Start of the range of portrs opened to accept connections from other clients. Default is *7052*.

        **--torrent_listen_port_max**
            *ltorrent* tunable. End of the range of ports opened to accept connections from other clients. Default is *7200*.

        **--torrent_pidfile**
            Pid file for *ltorrent*. Default is */run/luna/ltorrent.pid*.

        **--lweb_num_proc**
            Number of worker processes for *lweb*. If 0 (default), is will be autodected and more likely will be equal to the number of cores.

        **--cluster_ips**
            IP of the master nodes. Valid for Luna's HA configuration. Should be empty for standalone config.

        **--named_include_file**
            Path to the file managed by luna to host network zones. Administrator needs to include this file to */etc/named.conf*. Default is */etc/named.luna.zones*.

        **--named_zone_dir**
            Path to folder where BIND NAMED is expecting to find zone files to load. Should be equal to *options { directory "" }* direcive from *named.conf*. Default is */var/named*.

    **sync**
        Command to rsync directories (**--path**) across master nodes in HA environment. Not vaid if option **--cluster_ips** is not configured.

    **makedns**
        Command to create zone files in **--named_zone_dir** and create/overwrite **--named_include_file**. It uses templates *templ_named_conf.cfg*, *templ_zone.cfg* and *templ_zone_arpa.cfg*.

    **makedhcp**
        Command to create dhcp config for BIND DHCPD server. To use this command **network** should be added to Luna configuration, and interface of the master node shoud have IP address in the range of this **network**. Please note, that cluster requires 2 times more IPs that the number of nodes. One half goes to IPs will be statically assigned to nodes, but second part is being required by nodes to boot. It will be used only in PXE environment. Even if node is know to Luna, Luna will not add dhcp reservation for it. This can be ajusted manually, though - create static *dhcpd.conf* based on the list of known nodes.

        NOTE. During its lifetime node uses 2 IP addresses. First it aquires in PXE environment, which is from DHCP range. Second is being assigned manually in initrd environment (if **--boot_if** is configured for node) and in OS. This is valid for all nodes, even for already known nodes. Luna does not change lease files on node discovery.

        **--no_ha**
            In HA environment (i.e if **--cluster_ips** is configured) do not use native DHCPD HA feature. Luna will just put the same copy of *dhcpd.conf* on both master nodes to support Active/Passive HA config. Has no effect for standalone setups and can be ommited.

        **--network**
            Name of the **network** object.

        **--start_ip**
            Start of the DHCP range.

        **--end_ip**
            End of the DHCP range.

    **delete**
        Delete cluster object from mongodb. Command requires all the other cluster objects to be deleted already. If you need to wipe cluster and know what you are doing, use MongoDB commands to nuke Luna config::

            # mongo
            > use luna
            > db.dropDatabase()

        Please note, it will not affect any files on disks. So all osimages, torrent files, configs, templates will be untouched.

**osimage**

    Object reflects OS files needs to be delivered on nodes.

    **list**
        Getting list of the configured objects for brief overview.

    **show**
        Detailed information about object.

        **--name**, **-n**
            Name of the object.

        **--raw**, **-R**
            Print raw JSON of the object.

    **add**
        Add **osimage** object to Luna configuration. Please make sure that kernel rpm is installed.

        **--name**, **-n**
            Name of the object.

        **--path**, **-p**
            Path where files (directory tree structure) of the image is being stored.

        **--kernver**, **-k**
            Kernel version of the image.

        **--kernopts**, **-o**
            Kernel options are used to pass additional parameters to kernel on boot.

    **change**
        Change parameters of the **osimage** object.

        **--name**, **-n**
            Name of the object.

        **--kernver**, **-k**
            Kernel version of the image.

        **--kernopts**, **-o**
            Kernel options are used to pass additional parameters to kernel on boot.

        **--dracutmodules**, **-d**
            Dracut modules for initrd. Comma separated list of the dracut modules. ``dracut(8)`` supports ``-a`` and ``-o`` options, so modules prepended with '-' sign (minus) will be ommited on initr build (``-o``).

        **--kernmodules**, **-m**
            Kernel modules for initrd. Comma separated list of the kernel modules. ``dracut(8)`` supports ``--add-drivers`` and ``--omit-drivers`` options, so modules prepended with '-' sign (minus) will be ommited on initr build (``--omit-drivers``).

    **pack**
        Command to 'pack' osimage, i.e. make it available for nodes to boot. Under the hood it creates tarball from directory tree, creates torrent file, put everything to *~luna/torrents/*, then build initrd and copy it with kernel to *~luna/boot/*. It also fills values for *initrdfile*, *kernfile*, *tarball* and *torrent* variables in ``luna osimage show`` output. In addition, if Luna is configured to working in HA environment (**--cluster_ips**) this subcommand syncronizes data for the osimage across all the master nodes.

        **--name**, **-n**
            Name of the object.

        **--image**, **-i**
            Create tarball and bittorrent file only.

        **--boot**, **-b**
            Prepare kernel and initrd only.

    **sync**
        Command to syncronize images between the master nodes (**--cluster_ips**).




