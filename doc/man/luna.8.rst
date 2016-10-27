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

BASIC CONCEPTS
==============

Luna operates sever type of objects in order to build installation script and environment for node.

Object **node** represents the actual physical (or virtual) host.

**group** object includes nodes which inherit all the properties from the group. Some unique properties like mac or IP-address are assigned to node directly.

**osimage** represents the content of / file system on nodes.

**network** is definition of IP network to which other Luna objects can connect and have assigned IP addresses.

**bmcsetup** hosts parameters for IPMI setting for baseboard management controller on nodes.

**switch** defines an ethernet switch nodes are connected to. It can be used for node discovery.

**otherdev** is using to reserve IP addresses and assign names to them. Can be used for PDUs, cooling systems and other devices which are not directly managed by Luna, but administrator wants to have them resolved via DNS.

**cluster** is central object to store configuration parameters.

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
        Print global cluster configuration.

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
            Port *lweb* listens on localhost. Default is 7051. Service *lweb* opens socket only on 127.0.0.1 and port specified at **--server_port**. To reach *lweb* from remote HTTP reverse proxy server is using. Nginx is default. URL ``http://localhost:server_port`` allows to connect directly to lweb avoiding HTTP-proxy.

            Example::

                curl "http://localhost:7051/luna?step=boot"

        **--tracker_interval**
            Default is *10* sec. "Interval in seconds that the client should wait between sending regular requests to the tracker." https://wiki.theory.org/BitTorrentSpecification.

        **--tracker_min_interval**
            Default is *5* sec. "Minimum announce interval. If present clients must not reannounce more frequently than this." https://wiki.theory.org/BitTorrentSpecification.

        **--tracker_maxpeers**
            Default is *200*. Torrent tracker max allowed peers. It is upper bound for *numwant*: "Number of peers that the client would like to receive from the tracker." https://wiki.theory.org/BitTorrentSpecification.

        **--torrent_listen_port_min**
            *ltorrent* tunable. Start of the range of ports opened to accept connections from other clients. Default is *7052*.

        **--torrent_listen_port_max**
            *ltorrent* tunable. End of the range of ports opened to accept connections from other clients. Default is *7200*.

        **--torrent_pidfile**
            PID file for *ltorrent*. Default is */run/luna/ltorrent.pid*.

        **--lweb_num_proc**
            Number of worker processes for *lweb*. If 0 (default), is will be auto-dected and more likely will be equal to the number of cores.

        **--cluster_ips**
            IP of the master nodes. Valid for Luna's HA configuration. Should be empty for standalone configuration.

        **--named_include_file**
            Path to the file managed by Luna to host network zones. Administrator needs to include this file to */etc/named.conf*. Default is */etc/named.luna.zones*.

        **--named_zone_dir**
            Path to folder where BIND NAMED is expecting to find zone files to load. Should be equal to *options { directory "" }* direcive from *named.conf*. Default is */var/named*.

    **sync**
        Command to rsync directories (**--path**) across master nodes in HA environment. Not valid if option **--cluster_ips** is not configured.

    **makedns**
        Command to create zone files in **--named_zone_dir** and create/overwrite **--named_include_file**. It uses templates *templ_named_conf.cfg*, *templ_zone.cfg* and *templ_zone_arpa.cfg*.

    **makedhcp**
        Command to create dhcp config-file for BIND DHCPD server. To use this command **network** should be added to Luna configuration, and interface of the master node should have IP address in the range of this **network**. Please note, that cluster requires 2 times more IPs that the number of nodes. One half goes to IPs will be statically assigned to nodes, but second part is being required by nodes to boot. It will be used only in PXE environment. Even if node is know to Luna, Luna will not add dhcp reservation for it. This can be adjusted manually, though - create static *dhcpd.conf* based on the list of known nodes.

        NOTE. During its lifetime node uses 2 IP addresses. First it acquires in PXE environment, which is from DHCP range. Second is being assigned manually in initrd environment (if **--boot_if** is configured for node) and in OS. This is valid for all nodes, even for already known nodes. Luna does not change lease files on node discovery.

        **--no_ha**
            In HA environment (i.e. if **--cluster_ips** is configured) do not use native DHCPD HA feature. Luna will just put the same copy of *dhcpd.conf* on both master nodes to support Active/Passive HA config. Has no effect for standalone setups and can be omitted.

        **--network**
            Name of the **network** object.

        **--start_ip**
            Start of the DHCP range.

        **--end_ip**
            End of the DHCP range.

    **delete**
        Delete cluster object from MongoDB. Command requires all the other cluster objects to be deleted already. If you need to wipe cluster and know what you are doing, use MongoDB commands to nuke Luna config::

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
            Dracut modules for initrd. Comma separated list of the dracut modules. ``dracut(8)`` supports ``-a`` and ``-o`` options, so modules which are prepended with '-' sign (minus) will be omitted on initrd build (``-o``).

        **--kernmodules**, **-m**
            Kernel modules for initrd. Comma separated list of the kernel modules. ``dracut(8)`` supports ``--add-drivers`` and ``--omit-drivers`` options, so modules which are prepended with '-' sign (minus) will be omitted on initrd build (``--omit-drivers``).

    **pack**
        Command to 'pack' **osimage**, i.e. make it available for nodes to boot. Under the hood it creates tarball from directory tree, creates torrent file, put everything to *~luna/torrents/*, then build initrd and copy it with kernel to *~luna/boot/*. It also fills values for *initrdfile*, *kernfile*, *tarball* and *torrent* variables in ``luna osimage show`` output. In addition, if Luna is configured to working in HA environment (**--cluster_ips**) this subcommand syncronizes data for the osimage across all the master nodes.

        **--name**, **-n**
            Name of the object.

        **--image**, **-i**
            Create tarball and bittorrent file only.

        **--boot**, **-b**
            Prepare kernel and initrd only.

    **sync**
        Command to synchronize images between the master nodes (**--cluster_ips**).

        **--name**, **-n**
            Name of the object.

    **clone**
        Command to clone **osimage** object including underlying files. As a result second identical object will be created with copy of all the files in another path. Convenient way not to recreate **osimage** from scratch or take a snapshot of what was already done.

        **--name**, **-n**
            Name of the object.

        **--to**, **-t**
            Name of the new (cloned) object.

        **--path**, **-p**
            Path to reach the files of the image.

    **rename**
        Rename object in Luna database.

        **--name**, **-n**
            Name of the object.

        **--newname**, **--nn**
            New name of the object.

    **delete**
        Delete object from Luna database.

        **--name**, **-n**
            Name of the object.

**bmcsetup**
    Object describes BMC configuration of the node. Parameters from this object will be used to render script from *templ_install.cfg*

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

        **--user**, **-u**
            Username to reach BMC from remote. Default is *ladmin*.

        **--password**, **-p**
            Password to reach BMC from remote. Default is *ladmin*.

        **--userid**, **-I**
            User ID for user. Default is *3*.

        **--netchannel**, **-N**
            Channel number for LAN settings of the BMC. Default is *1*.

        **--mgmtchannel**, **-M**
            Management channel of the BMC. Default is *1*.

    **change**
        Change **bmcsetup** object to Luna database.

        **--name**, **-n**
            Name of the object.

        **--user**, **-u**
            Username to reach BMC from remote. Default is *ladmin*.

        **--password**, **-p**
            Password to reach BMC from remote. Default is *ladmin*.

        **--userid**, **-I**
            User ID for user. Default is *3*.

        **--netchannel**, **-N**
            Channel number for LAN settings of the BMC. Default is *1*.

        **--mgmtchannel**, **-M**
            Management channel of the BMC. Default is *1*.

    **rename**
        Rename object in Luna database.

        **--name**, **-n**
            Name of the object.

        **--newname**, **--nn**
            New name of the object.

    **delete**
        Delete object from Luna database.

        **--name**, **-n**
            Name of the object.

**network**
    Object allows to manage network configuration and IP addresses of the cluster objects.

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

        **--network**, **-N**
            Network. Can be any IP address. Resulting network address will be calculated based on **--prefix**. For example 10.30.4.1/16 will be converted to 10.30.0.0.

        **--prefix**, **-P**
            Network prefix.

        **--ns_hostname**
            Nameserver for zone file (IN NS). See *templ_zone.cfg* and *templ_zone_arpa.cfg* for details.

        **--ns_ip**
            IP address of the nameserver. Most likely will be one of the IP addresses (in corresponding IP range) assigned to master node. See *templ_zone.cfg* and *templ_zone_arpa.cfg* for details.

    **change**
        Change **network** object to Luna database.

        **--name**, **-n**
            Name of the object.

        **--network**, **-N**
            Network. Can be any IP address. Resulting network address will be calculated based on **--prefix**. For example 10.30.4.1/16 will be converted to 10.30.0.0.

        **--prefix**, **-P**
            Network prefix.

        **--ns_hostname**
            Nameserver for zone file (IN NS). See *templ_zone.cfg* and *templ_zone_arpa.cfg* for details.

        **--ns_ip**
            IP address of the nameserver. Most likely will be one of the IP addresses (in corresponding IP range) assigned to master node. See *templ_zone.cfg* and *templ_zone_arpa.cfg* for details.

        **--reserve**
            *For advanced usage.* Locks IP from assigning to any cluster's device or host. This option will mark particular IP as 'occupied'. Please, consider to use *otherdev* first. This option will not assign any name for IP, so IP address will be ignored during zone creation.
        **--release**
            *For advanced usage.* Releases occupied IP. This option does not check if IP is assigned to any **node**, **switch** or **otherdev** object, so can cause IP conflicts or other instabilities in the cluster.

    **rename**
        Rename object in Luna database.

        **--name**, **-n**
            Name of the object.

        **--newname**, **--nn**
            New name of the object.

    **delete**
        Delete object from Luna database.

        **--name**, **-n**
            Name of the object.

**group**
    Common configuration for the group of nodes. Most of the changes in the configuration of the cluster will be performed in this object.

    **list**
        Getting list of the configured objects for brief overview.

    **show**
        Detailed information about object.

        **--name**, **-n**
            Name of the object.

        **--raw**, **-R**
            Print raw JSON of the object.

        **--osimage**, **-o**
            Show name of the **osimage** assigned to group.

        **--prescript**, **--pre**
            Show pre-install script.

        **--postscript**, **--post**
            Show post-install script.

        **--partscript**, **--part**
            Show partitioning script.

        **--bmcsetup**, **-b**
            Show **bmcsetup** config assigned to group.

        **--interface**, **-i**
            Show addition interface parameters assigned to interface.

        **--bmcnetwork**, **--bn**
            Show network assigned to group.

    **add**
        Add **group** object to Luna configuration.

        **--name**, **-n**
            Name of the object.

        **--osimage**, **-o**
            Name of the **osimage** to be assigned to group of nodes.

        **--bmcsetup**, **-b**
            Name of the **bmcsetup** object to configure BMC of nodes.

        **--bmcnetwork**, **--bn**
            Name of the **network** object. IP addresses from this network will be assigned to BMC. See *templ_install.cfg* for details.

        **--interface**, **-i**
            Name of the interface of the node in group. It is assumed that al nodes in group have the same (or similar) hardware configuration, which is typical for the HPC cluster: *em1*, *p2p1*, *eno1*, etc.

            **PLEASE NOTE** On the early stage of the cluster install process it is hard or not possible to figure out the proper name of the interfaces and other hardware config, so the best scenario here is to create group with name of the interface picked up by random, for instance *eth0*. Then add one **node** object to the group and configure to boot it in service mode (see below). In the following example **osimage** named *compute* as well as 2 networks *cluster* and *ipmi* need to be created upfront.

            Example::

                # luna group add --name service --osimage compute --interface eth0
                # luna group change --name service --interface eth0 --setnet cluster
                # luna group change --name service --bmcnetwork --setnet ipmi
                # luna node add --name servicenode --group service
                # luna node change --name servicenode --setupbmc n
                # luna node change --name servicenode --service n

            Then boot node and inspect hardware configuration in dracut environment: interface naming, physical disk location and proceed with **group** configuration.

    **change**
        Change configuration for the group of nodes.

        **--name**, **-n**
            Name of the object.

        **--osimage**, **-o**
            Name of the **osimage** to be assigned to group of nodes.

        **--prescript**, **--pre**
            Display/edit bash pre-install script. This script is being executed on the very early stage of the boot/install process. In conjunction with **-e** this parameter opens text editor (defined in **EDITOR** environment or **vi**). Parameters supports I/O redirection (pipes).

            Example::

                # echo "echo 'do something'" | luna group change --name service --prescript -e

        **--partscript**, **--part**
            Display/edit bash partitioning script. Luna does not support paritioning definitions (like anaconda, for example), so this is where **--partscript** comes into play. In conjunction with **-e** this parameter opens text editor (defined in **EDITOR** environment or **vi**). Parameters supports I/O redirection (pipes). By default following commands exist in installer environment: parted, partx, mkfs.ext2, mkfs.ext3, mkfs.ext4, mkfs.xfs (See *95luna/module-setup.sh*). It is expected that partscript will perform partitioning and creation of the filesystems and mount filesystems under */sysroot* where image of the operation system (**osimage**) will be unpacked. By default group has **--partscript** for diskless boot:

            Example::

                # mount -t tmpfs tmpfs /sysroot

            Diskful nodes a bit more complicated. This is far-for-ideal example, but allows to illustrate main idea::

                parted /dev/sda -s 'mklabel msdos'
                parted /dev/sda -s 'rm 1; rm 2'
                parted /dev/sda -s 'mkpart p ext2 1 256m'
                parted /dev/sda -s 'mkpart p ext3 256m 100%'
                parted /dev/sda -s 'set 1 boot on'
                mkfs.ext2 /dev/sda1
                mkfs.ext4 /dev/sda2
                mount /dev/sda2 /sysroot
                mkdir /sysroot/boot
                mount /dev/sda1 /sysroot/boot

            There are several issues in the primer above. First, it does not care about partitions already exists on disk. And second, it has a really critical issue here: it formats first available disk (sda) without checking if the disk we want to wipe can be wiped. Some systems have more that one disk. So example above should never be considered for production use. Well behaved scripts have to do some checks before::

                PATHTODEV=/dev/disk/by-path/pci-0000:02:00.0-scsi-0:2:0:0
                SCSI_DEVICE="0:2:0:0"   # from /sys/block/sda/device/scsi_device/
                SIZE=584843264          # from /sys/block/sda/size
                MODEL="PERC H730 Mini"  # from /sys/block/sda/device/model

                DISK=$(/usr/bin/basename $(/usr/bin/readlink -f ${PATHTODEV}))

                if [ ! ${SIZE} -eq $(cat /sys/block/${DISK}/size) ]; then
                    echo "ERROR! Size of the /dev/${DISK} is not ${SIZE}. Stoping"
                    exit 1
                fi
                if [ ! "${MODEL}" = "$(/bin/cat /sys/block/${DISK}/device/model | /usr/bin/sed 's/[\t ]*$//')" ]; then
                    echo "ERROR! Model of the /dev/${DISK} is not ${MODEL}. Stoping"
                    exit 2
                fi
                if [ ! "${SCSI_DEVICE}" = "$(/usr/bin/ls /sys/block/${DISK}/device/scsi_device/)" ]; then
                    echo "ERROR! SCSI device address of the /dev/${DISK} is not ${SCSI_DEVICE}. Stoping"
                    exit 3
                fi

                parted /dev/${DISK} -s 'mklabel msdos'
                partx -g -s /dev/${DISK} | awk '{print $1}' | while read PARTNUM; do
                    parted /dev/${DISK} -s "rm ${PARTNUM}"
                done
                parted /dev/${DISK} -s 'mkpart p ext2 1 512m'
                parted /dev/${DISK} -s 'mkpart p ext4 512m 100%'
                parted /dev/${DISK} -s 'set 1 boot on'
                mkfs.ext2 /dev/${DISK}1

        **--postscript**, **--post**
            Display/edit bash postinstall script. This script will be executed in initrd (dracut) environment after unpacking tarball. At this point image is downloaded, unpacked and should be located in /sysroot. This is the proper place to install bootloader or add some additional tunables to node. In conjunction with **-e** this parameter opens text editor (defined in **EDITOR** environment or **vi**). Parameters supports I/O redirection (pipes).

            Example::

                mount -t proc proc /sysroot/proc
                mount -t devtmpfs devtmpfs /sysroot/dev
                mount -t sysfs sysfs /sysroot/sys
                chroot /sysroot /bin/bash \
                    -c "/usr/sbin/grub2-mkconfig -o /boot/grub2/grub.cfg; \
                            /usr/sbin/grub2-install /dev/disk/by-path/pci-0000:02:00.0-scsi-0:2:0:0"
                cat <<EOF>>/sysroot/etc/fstab
                /dev/disk/by-path/pci-0000:02:00.0-scsi-0:2:0:0-part2   /       ext4    defaults        0 0
                /dev/disk/by-path/pci-0000:02:00.0-scsi-0:2:0:0-part1   /boot   ext2    defaults        0 0
                EOF

                umount /sysroot/dev
                umount /sysroot/proc
                umount /sysroot/sys

            It is a good practice to use location path to define particular disk, instead of /dev/sda, /dev/sdb, etc. One can be sure that bootloader will be installed on proper disk, as linux kernel can reassign disk order on boot.

        **--bmcsetup**, **-b**
            Name of the **bmcsetup** object to configure BMC of nodes.

        **--boot_if**, **--bi**
            Boot interface. This is used in initrd environment to find out which interface should be configured. Also it is used to add domain to hostname. This parameter implemented for convenience to allow administrator to login to node on install step for inventory and/or debug purposes. Parameter should match one of the configured interfaces. This parameter can be omitted. It that case node will try to configure all interfaces to acquire IP by DHCP, and administrator will need to find the proper IP looking to lease file. Know limitations: does not work with bond, vlan or bridge interfaces.

        **--torrent_if**, **-ti**
            Torrent interface. Optional parameter which interface torrent client on nodes should report as in use for seeding. If specifies should match **--boot_if**. Know limitations: does not work with bond, vlan or bridge interfaces.

        **--interface**, **-i**
            Interface to operate with. Following operations are supported: **--add**, **--delete**, **--setnet**, **--delnet**, **--edit**. 

        **--bmcnetwork**, **--bn**
            Supports **--setnet**, **--delnet** operations.

        **--add**, **-A**
            Add interface.

        **--delete**, **-D**
            Delete interface.

        **--setnet**, **--sn**
            Assign network to interface. IP addresses will be added to all nodes in corresponding group.

        **--delnet**, **--dn**
            Unassign network from interface. All IP addresses will be unassigned from nodes.

        **--edit**, **-e**
            Add/edit other parameters for interface: MTU, CONNECTED_MODE, TYPE, SLAVE, MASTER, etc. Parameter "DEVICE" will be added automatically.

    **rename**
        Rename object in Luna database.

        **--name**, **-n**
            Name of the object.

        **--newname**, **--nn**
            New name of the object.

    **delete**
        Delete object from Luna database.

        **--name**, **-n**
            Name of the object.

**node**
    Object to describe unique host properties.

    **list**
        Getting list of the configured objects for brief overview.

    **show**
        Detailed information about object.

        **--name**, **-n**
            Name of the object.

        **--raw**, **-R**
            Print raw JSON of the object.

    **add**
        Add **node** object to Luna configuration.

        **--name**, **-n**
            Name of the node. Can be omitted. In this case parameters *cluster nodeprefix* and *cluster nodedigits* will be used, and node name will be generated automatically.

        **--group**, **-g**
            **group** to which node will belong to.

    **change**
        Change properties of the node.

        **--name**, **-n**
            Name of the node.

        **--group**, **-g**
            Change group fro the node. Target group can have different interfaces or network configured, so all ip addresses will be unassigned.
        **--interface**, **-i**
            Change IP address for the interface.

        **--bmcip**
            Change IP address for BMC interface.

        **--mac**
            MAC address of the node.

        **--switch**, **-s**
            Switch node is connected to. Used for node discovery.

        **--port**, **-p**
            Port of the switch node is connected to.

        **--localboot**, **-l**
            Luna wont provide install/boot environment for node but force it to boot from local disk.

        **--setupbmc**, **--sb**
            Specify should node configure its BMC interface and IPMI parameters on each install. Good practice is to disable (set to *n*) this parameter after first successful install.

        **--service**, **--sv**
            Boot node to *service* mode. It is a standard install environment. Node will configure interface (if **--boot_if** is specified) and bring sshd up. No install or configure scripts will be running, data on disks will be kept intact. Can be used to initial inspection of the node: disk location, interface naming, etc. Or debug purposes: install scripts can be downloaded by curl and executed step-by-step manually.

    **rename**
        Rename object in Luna database. To update DNS **luna cluster makedns** should be executer afterwards

        **--name**, **-n**
            Name of the object.

        **--newname**, **--nn**
            New name of the object.

    **delete**
        Delete object from Luna database.

        **--name**, **-n**
            Name of the object.


**switch**
    Object to define ethernet switch hosts are connected to. In order to support node discovery Luna needs an access to switch to fetch data about learned mac-addresses.

    **list**
        Getting list of the configured objects for brief overview.

    **show**
        Detailed information about object.

        **--name**, **-n**
            Name of the object.

        **--raw**, **-R**
            Print raw JSON of the object.

    **add**
        Add **switch** object to Luna configuration.

        **--name**, **-n**
            Name of the object.
    
        **--network**, **-N**
            Network in which switch has configured IP address.

        **--ip**, **-i**
            IP address to get access to the switch by SNMP.

        **--read**, **-r**
            SNMP community for read access.

        **--rw**, **-w**
            SNMP community for read/write access.

        **--oid**, **-o**
            OID where learned MAC addresses are stored. Examples are::
                
                .1.3.6.1.2.1.17.7.1.2.2.1.2
                .1.3.6.1.2.1.17.4.3.1.2
                .1.3.6.1.2.1.17.7.1.2.2
                .1.3.6.1.2.1.17.4.3.1.2
            
            Please pay attention to a first dot before OID.

            For debug purposes administrator can use ``snmpwalk`` to get the list of known MAC addresses::
                
                $ snmpwalk -On -c public -v 1 switch01 .1.3.6.1.2.1.17.7.1.2.2.1
                .1.3.6.1.2.1.17.7.1.2.2.1.2.1.24.102.218.96.27.201 = INTEGER: 210
                .1.3.6.1.2.1.17.7.1.2.2.1.2.1.24.102.218.96.32.165 = INTEGER: 210
                .1.3.6.1.2.1.17.7.1.2.2.1.2.1.24.102.218.96.40.218 = INTEGER: 210
                .1.3.6.1.2.1.17.7.1.2.2.1.2.1.24.102.218.96.40.254 = INTEGER: 210

            Last 6 numbers here is MAC address octets::

                >>> dec_mac = "24.102.218.94.31.155"
                >>> ":".join([hex(int(e)).split('x')[1] for e in dec_mac.split('.')])
                '18:66:da:5e:1f:9b'

    **change**
        Change **switch** object property.

        **--name**, **-n**
            Name of the object.
    
        **--network**, **-N**
            Network in which switch has configured IP address.

        **--ip**, **-i**
            IP address to get access to the switch by SNMP.

        **--read**, **-r**
            SNMP community for read access.

        **--rw**, **-w**
            SNMP community for read/write access.

        **--oid**, **-o**
            OID where learned MAC addresses are stored. See examples for **switch add --oid**

    **rename**
        Rename object in Luna database. To update DNS **luna cluster makedns** should be executer afterwards

        **--name**, **-n**
            Name of the object.

        **--newname**, **--nn**
            New name of the object.

    **delete**
        Delete object from Luna database.

        **--name**, **-n**
            Name of the object.

**otherdev**
    Service object to name other devices in cluster. Used on DNS zone creation.

    **list**
        Getting list of the configured objects for brief overview.

    **show**
        Detailed information about object.

        **--name**, **-n**
            Name of the object.

        **--raw**, **-R**
            Print raw JSON of the object.

   **add**
        Change **otherdev** properties.

        **--name**, **-n**
            Name of the object.

        **--network**, **-N**
            Network device connected to.

        **--ip**, **-i**
            IP address of the device.

   **change**
        Change **otherdev** properties.

        **--name**, **-n**
            Name of the object.

        **--network**, **-N**
            Network device connected to.

        **--ip**, **-i**
            IP address of the device. If this parameter omitted assigned network will be deleted from object.

    **rename**
        Rename object in Luna database. To update DNS **luna cluster makedns** should be executer afterwards

        **--name**, **-n**
            Name of the object.

        **--newname**, **--nn**
            New name of the object.

    **delete**
        Delete object from Luna database.

        **--name**, **-n**
            Name of the object.

FILES
=====

/etc/luna.conf
    Credentials to access to MongoDB.
templ_dhcpd.cfg
    Template for /etc/dhcpd.conf
templ_install.cfg
    Template for installation script.
templ_ipxe.cfg
    Template for iPXE boot menu.
templ_named_conf.cfg
    Template for ISC BIND (named) include config file.
templ_nodeboot.cfg
    Template for iPXE boot script.
templ_zone_arpa.cfg
    Template for ISC BIND (named) reverse-zone file.
templ_zone.cfg
    Template for ISC BIND (named) zone-file.
