# Disclaimer
It is an alpha-version.
This piece of code is another try to beat 'boot-storm'.
It uses torrent to deliver image to node.

|Number of nodes|Time for cold boot, min|Xcat cold boot, min|
|:-------------:|:---------------------:|:-----------------:|
|              1|                      3|                  9|
|             36|                      4|                 26|
|             72|                      4|                 53|

Image size is 1GB, provision node is equipped with 1Gb interface

# Start
Let's assume you have server with ip 10.30.255.254 as internal interface for cluster

# Server preparation

TODO. Will be raplaced by rpm scripts later on.
```
sed -i -e 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
setenforce 0
yum -y install git
cd /
git clone https://github.com/dchirikov/luna
useradd -d /opt/luna luna
chown luna: /opt/luna
chmod ag+rx /opt/luna
mkdir /run/luna
chown luna: /run/luna/
mkdir /var/log/luna
chown luna: /var/log/luna
mkdir /opt/luna/{boot,torrents}
chown luna: /opt/luna/{boot,torrents}
yum -y install yum-utils
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum -y install mongodb-server python-pymongo mongodb
yum -y install nginx
yum -y install python-tornado
yum -y install ipxe-bootimgs tftp-server tftp xinetd dhcp wget
yum -y install rb_libtorrent-python net-snmp-python
yum -y install /luna/hostlist/python-hostlist-1.14-1.noarch.rpm
mkdir /tftpboot
sed -e 's/^\(\W\+disable\W\+\=\W\)yes/\1no/g' -i /etc/xinetd.d/tftp
sed -e 's|^\(\W\+server_args\W\+\=\W-s\W\)/var/lib/tftpboot|\1/tftpboot|g' -i /etc/xinetd.d/tftp
[ -f /root/.ssh/id_rsa ] || ssh-keygen -t rsa -f /root/.ssh/id_rsa -N ''
systemctl enable xinetd
systemctl start xinetd
cp /usr/share/ipxe/undionly.kpxe /tftpboot/luna_undionly.kpxe
mv /etc/dhcp/dhcpd.conf{,.bkp_luna}
cp /luna/config/dhcpd/dhcpd.conf /etc/dhcp/
#vim /etc/dhcp/dhcpd.conf
cp /luna/config/nginx/luna.conf /etc/nginx/conf.d/
systemctl start nginx
systemctl enable nginx
systemctl start mongod
systemctl enable mongod
systemctl start dhcpd
systemctl enable dhcpd
```
# Creating links
```
cd /usr/lib64/python2.7
ln -s ../../../luna/src/module luna
cd /usr/sbin
ln -s ../../luna/src/exec/luna
ln -s ../../luna/src/exec/lpower
ln -s ../../luna/src/exec/lweb
ln -s ../../luna/src/exec/ltorrent
ln -s ../../luna/src/exec/lchroot
cd /opt/luna
ln -s /luna/src/templates
cd ~
```
# Creating osimage
```
mkdir -p /opt/luna/os/compute/var/lib/rpm
rpm --root /opt/luna/os/compute --initdb
yumdownloader  centos-release
rpm --root /opt/luna/os/compute -ivh centos-release\*.rpm
yum --installroot=/opt/luna/os/compute -y groupinstall Base
yum --installroot=/opt/luna/os/compute -y install kernel rootfiles openssh-server openssh openssh-clients tar nc wget curl rsync gawk sed gzip parted e2fsprogs ipmitool vim-enhanced vim-minimal grub2
```
## Set password for root and set up sshd
```
mkdir /opt/luna/os/compute/root/.ssh
chmod 700 /opt/luna/os/compute/root/.ssh
mount -t devtmpfs devtmpfs /opt/luna/os/compute/dev/
chroot  /opt/luna/os/compute
ssh-keygen -f /etc/ssh/ssh_host_ecdsa_key -N '' -t ecdsa
abrt-auto-reporting enabled
passwd
exit
cat /root/.ssh/id_rsa.pub >> /opt/luna/os/compute/root/.ssh/authorized_keys
chmod 600 /opt/luna/os/compute/root/.ssh/authorized_keys
cp -pr /luna/src/dracut/95luna /opt/luna/os/compute/usr/lib/dracut/modules.d/
```
# Create cluster config
Please note, in this case interface named 'enp7s0' is using. To figure out the proper name of the interface you probably need to specify any interface (eth0, for instance) and then boot in service mode first: `luna node change -n node001 --service y`. In service mode you can perform inventory of the interfaces, local disks, BMC features.
```
luna cluster init
luna cluster change --frontend_address 10.30.255.254
luna osimage add -n compute -p /opt/luna/os/compute
luna osimage pack -n compute
luna bmcsetup add -n base
luna network add -n cluster -N 10.30.0.0 -P 16
luna network add -n ipmi -N 10.31.0.0 -P 16
luna switch add -n switch01 --oid .1.3.6.1.2.1.17.7.1.2.2.1.2 --network ipmi --ip 10.31.253.21
luna group add -n compute -i enp7s0 -o compute
luna group change -n compute -b base
luna group change -n compute --boot_if enp7s0
luna group change -n compute --interface enp7s0 --setnet cluster
echo -e "DEVICE=enp0s3\nONBOOT=yes" | luna group change  --name compute --interface enp7s0 -e
luna group change -n compute --bmcnetwork --setnet ipmi
```
# (Optional) Edit partitioning

You can use ramdisk, or write your own partition script.
```
luna group change -n compute --partscript -e
```
For /dev/sda it could be, for example
```
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
```
# (Optional) Edit postscript to install bootloader (/dev/sda)
```
cat << EOF | luna group change -n compute  --post -e
mount -o bind /proc /sysroot/proc
mount -o bind /dev /sysroot/dev
chroot /sysroot /bin/bash -c "/usr/sbin/grub2-mkconfig -o /boot/grub2/grub.cfg; /usr/sbin/grub2-install /dev/sda"
umount /sysroot/dev
umount /sysroot/proc
EOF
```
# Add node.
```
luna node add -g compute
```
Name will be generated.
```
luna node change -n node001 -s switch01
luna node change -n node001 -p 1
```
# Start services
```
ltorrent start
lweb start
```
# Check if it is working
```
curl "http://10.30.255.254:7050/luna?step=boot"
wget "http://10.30.255.254:7050/boot/compute-vmlinuz-3.10.0-327.10.1.el7.x86_64"
curl "http://10.30.255.254:7050/luna?step=install&node=node001"
```
# Boot node

# Enable boot from localdisk
```
luna node change -n node001 --localboot y
```
# Optional
Enable service boot
```
luna node change -n node001 --service y
```
Disable bmcsetup
```
luna node change -n node001 --setupbmc n
```
# MongoDB config (optional)
NOTE: By default MongoDB listens only loopback interface and provides no credentials ckecking.

To set up replica set edit ```/etc/mongod.conf```

(example)
```
bind_ip = 127.0.0.1,10.30.255.254
replSet = luna
```
after that mongod needs to be restarted:
```
systemctl restart mongod
```
using mongo cli, setup replica set:
```
rs.initiate()
```
Then restart mongod and back to cli.
Add root user:
```
use admin
db.createUser({user: "root", pwd: "<password>", roles: [ { role: "root", db: "admin" } ]})
```
edit config mongod to enable auth:
```
auth = true
```
restart mongod:
```
systemctl restart mongod
```
Enter to mongo shell:
```
mongo -u root -p <password> --authenticationDatabase admin
```
Create user for Luna:
```
use luna
db.createUser({user: "luna", pwd: "<password>", roles: [{role: "dbOwner", db: "luna"}]})
```
Now we are ready to create config file for connection:
```
cat << EOF > /etc/luna.conf
[MongoDB]
replicaset=luna
server=localhost
authdb=luna
user=luna
password=<password>
EOF
```
(Optional. Set up HA)
Consider you have:
|           10.30.255.251 |   master1 |
|           10.30.255.252 |   master2 |
|(floating) 10.30.255.254 |   master  |
```
openssl rand -base64 741 > /etc/mongo.key
chown mongodb: /etc/mongo.key
chmod 400 /etc/mongo.key
```
Add parameter to  /etc/mongod.conf
```
keyFile = /etc/mongo.key
```
Copy files to other master
```
scp -pr /etc/mongo.key 10.30.255.252:/etc/
scp /etc/mongod.conf 10.30.255.252:/etc/
```

Edit mongod.conf to to change the ip address there:
```
sed -i -e 's/10.30.255.251/10.30.255.252/' /etc/mongod.conf
```
Restart mongo instances on both servers:
```
systemctl restart mongod
```
In mongo shell add another member:
```
rs.add("10.30.255.252")
```
Then restart mongod instance on other master.

Check status:
```
luna:PRIMARY> rs.status()
{
        "set" : "luna",
        "date" : ISODate("2016-06-28T11:03:04Z"),
        "myState" : 1,
        "members" : [
                {
                        "_id" : 0,
                        "name" : "10.30.255.251:27017",
                        "health" : 1,
                        "state" : 1,
                        "stateStr" : "PRIMARY",
                        "uptime" : 209,
                        "optime" : Timestamp(1467111677, 1),
                        "optimeDate" : ISODate("2016-06-28T11:01:17Z"),
                        "electionTime" : Timestamp(1467111711, 1),
                        "electionDate" : ISODate("2016-06-28T11:01:51Z"),
                        "self" : true
                },
                {
                        "_id" : 1,
                        "name" : "10.30.255.252:27017",
                        "health" : 1,
                        "state" : 2,
                        "stateStr" : "SECONDARY",
                        "uptime" : 79,
                        "optime" : Timestamp(1467111677, 1),
                        "optimeDate" : ISODate("2016-06-28T11:01:17Z"),
                        "lastHeartbeat" : ISODate("2016-06-28T11:03:04Z"),
                        "lastHeartbeatRecv" : ISODate("2016-06-28T11:03:03Z"),
                        "pingMs" : 1,
                        "lastHeartbeatMessage" : "syncing to: 10.30.255.251:27017",
                        "syncingTo" : "10.30.255.251:27017"
                }
        ],
        "ok" : 1
}
```
# (Optional) Adding arbiter

For HA config with two nodes following config is suggested. On each node, ypu will have MongoDB with full data sets ready to handle data requests. As we have only 2 instances, in the case of one-node-fail, alive instance will consider a split-brain situation and demote itself to secondary (will refuse to handle requests).

To avoid such situation, we need to have tie-breaker - arbiter. It a tiny service (in terms of memory footprint and service logic) which add one vote to elections. We will have the copy of arbiter on two nodes. And pacemaker will be in charge to bring one and only one copy of arbiter online. Pacemaker should have STONITH configured.

Another point of this config, that you will have your database up and running even if you have a mess with pacemaker. In this case you will have arbiter down, but regular MongoDB instances will have 2 votes out of 3 (more than half).

Copy mongod config:
```
cp /etc/mongod.conf /etc/mongod-arbiter.conf
```
Change following:
```
bind_ip = 127.0.0.1,10.30.255.254   # 255.254 will be cluster (floating) ip here
port = 27018                        # non standart port not to conflict with other MongoDB instancess
pidfilepath = /var/run/mongodb-arbiter/mongod.pid
logpath = /var/log/mongodb/mongod-arbiter.log
unixSocketPrefix = /var/run/mongodb-arbiter
dbpath = /var/lib/mongodb-arbiter
nojournal = true                    # disable journal in order to reduce amount of data in dbpath
noprealloc = true                   # disable noprealloc for the same reason
smallfiles = true                   # same considerations
```
Create environmental file:
```
cat << EOF > /etc/sysconfig/mongod-arbiter
> OPTIONS="--quiet -f /etc/mongod-arbiter.conf"
> EOF
```
For initialization you need to bring floating IP up on one node:
```
ip a add 10.30.255.254/16 dev eth1
```
Create systemd service:
```
cat << EOF > /etc/systemd/system/mongod-arbiter.service
[Unit]
Description=Arbiter for MongoDB
After=syslog.target network.target

[Service]
Type=forking
User=mongodb
PermissionsStartOnly=true
EnvironmentFile=/etc/sysconfig/mongod-arbiter
ExecStartPre=-/usr/bin/mkdir /var/run/mongodb-arbiter
ExecStartPre=/usr/bin/chown -R mongodb:root /var/run/mongodb-arbiter
ExecStart=/usr/bin/mongod $OPTIONS run
ExecStopPost=-/usr/bin/rm -rf /var/run/mongodb-arbiter
PrivateTmp=true
LimitNOFILE=64000
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
```
Create paths for arbiter:
```
mkdir /var/lib/mongodb-arbiter
chown mongodb:root /var/lib/mongodb-arbiter
chmod 750 /var/lib/mongodb-arbiter
```
Start service:
```
systemctl start mongodb-arbiter
```
As you have mongod-arbiter startted, you need to add it to MongoDB's replicaset.

Connect to mongo shell with root priviledges:
```
mongo -u root -p <password> --authenticationDatabase admin
```
Add arbiter to replica's config:
```
rs.addArb("10.30.255.254:27018")
```
Check config:
```
luna:PRIMARY> rs.config()
{
        "_id" : "luna",
        "version" : 6,
        "members" : [
                {
                        "_id" : 0,
                        "host" : "10.30.255.251:27017"
                },
                {
                        "_id" : 1,
                        "host" : "10.30.255.252:27017"
                },
                {
                        "_id" : 2,
                        "host" : "10.30.255.254:27018",
                        "arbiterOnly" : true
                }
        ]
}
```
Check status:
```
luna:PRIMARY> rs.status()
{
        "set" : "luna",
        "date" : ISODate("2016-07-01T09:51:50Z"),
        "myState" : 1,
        "members" : [
                {
                        "_id" : 0,
                        "name" : "10.30.255.251:27017",
                        "health" : 1,
                        "state" : 1,
                        "stateStr" : "PRIMARY",
                        "uptime" : 255135,
                        "optime" : Timestamp(1467366651, 1),
                        "optimeDate" : ISODate("2016-07-01T09:50:51Z"),
                        "electionTime" : Timestamp(1467149146, 1),
                        "electionDate" : ISODate("2016-06-28T21:25:46Z"),
                        "self" : true
                },
                {
                        "_id" : 1,
                        "name" : "10.30.255.252:27017",
                        "health" : 1,
                        "state" : 2,
                        "stateStr" : "SECONDARY",
                        "uptime" : 217570,
                        "optime" : Timestamp(1467366651, 1),
                        "optimeDate" : ISODate("2016-07-01T09:50:51Z"),
                        "lastHeartbeat" : ISODate("2016-07-01T09:51:49Z"),
                        "lastHeartbeatRecv" : ISODate("2016-07-01T09:51:49Z"),
                        "pingMs" : 1,
                        "syncingTo" : "10.30.255.251:27017"
                },
                {
                        "_id" : 2,
                        "name" : "10.30.255.254:27018",
                        "health" : 1,
                        "state" : 7,
                        "stateStr" : "ARBITER",
                        "uptime" : 9,
                        "lastHeartbeat" : ISODate("2016-07-01T09:51:49Z"),
                        "lastHeartbeatRecv" : ISODate("2016-07-01T09:51:49Z"),
                        "pingMs" : 0
                }
        ],
        "ok" : 1
}
```
At this point you are ready to copy data and config to other node.

Shutdown arbiter on first node:
```
systemctl stop mongod-arbiter
```
Copy files:
```
for f in /etc/mongod-arbiter.conf /etc/sysconfig/mongod-arbiter /etc/systemd/system/mongod-arbiter.service /var/lib/mongodb-arbiter; do scp -pr $f master2:$f ; done

```
On the second node fix ownership and permissions:
```
chown -R mongodb:root /var/lib/mongodb-arbiter
chmod 750 /var/lib/mongodb-arbiter
```
Bring floating ip down on first node:
```
ip a del 10.30.255.254/16 dev eth1
```
And bring it up on second
```
ip a add 10.30.255.254/16 dev eth1
```
Run arbiter on the second node
```
systemctl start mongod-arbiter
```
Connect to mongo shell and make sure that you have all instances up:
```
luna:PRIMARY> rs.status()
```
