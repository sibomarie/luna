from Luna import Luna
from bson import ObjectId
luna = Luna('luna')
# { "_id" : ObjectId("5690699d88099905da449924"), "mdate" : ISODate("2016-01-09T01:59:57.128Z"), "name" : "node011", "n" : 1, "cdate" : ISODate("2016-01-09T01:59:57.128Z"), "parm111" : "val111", "parm411" : [ { "name" : "parm421", "options" : "val421" }, { "name" : "parm422", "options" : "val422" } ], "parm311" : { "name" : "parm321", "options" : "val321" }, "parm211" : "val211" }
print 1
print luna.set_value('node', 'node012', ['parm111'], 'testval')
print 2
print luna.set_value('node', 'node011', ['parm411', 'parm421', 'options'], 'testval')
print 3
print luna.set_value('node', 'node011', ['parm311', 'parm321', 'options'], 'testval')
print 4
print luna.set_value('node', 'node012', ['parm411', 'parm422', 'options'], 'testval')
print 5
print luna.set_value('node', 'node012', ['parm411', 'parm422', 'opt'], 'testval')
print 6
print luna.set_value('node', 'node012', ['parm411', 'parm422'], 'testval')
print 6
print luna.set_value('node', 'node012', ['parm1', 'parm2', 'parm3', 'parm4', 'options'], 'testval')
print 7
print luna.set_value('node', 'node012', ['interfaces','eno2', 'mtu'], 9000)
print 7
print luna.set_value('node', 'node012', ['kernels','2.6.18','bonding','options','mode'], 3)
