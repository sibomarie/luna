from Luna import Luna
from bson import ObjectId
luna = Luna('luna')
# { "_id" : ObjectId("5690699d88099905da449924"), "mdate" : ISODate("2016-01-09T01:59:57.128Z"), "name" : "node011", "n" : 1, "cdate" : ISODate("2016-01-09T01:59:57.128Z"), "parm111" : "val111", "parm411" : [ { "name" : "parm421", "options" : "val421" }, { "name" : "parm422", "options" : "val422" } ], "parm311" : { "name" : "parm321", "options" : "val321" }, "parm211" : "val211" }
print 1
print luna.get_value('node', 'node011', ['parm111'])
print 2
print luna.get_value('node', 'node011', ['parm411', 'parm421', 'options'])
print 3
print luna.get_value('node', 'node011', ['parm311', 'parm321', 'options'])
print 4
print luna.get_value('node', 'node011', ['parm411', 'parm422', 'options'])
print 5
print luna.get_value('node', 'node011', ['parm411', 'parm422', 'opt'])
print 6
print luna.get_value('node', 'node011', ['parm411', 'parm422'])
print 7
print luna.get_value('node', 'node012', ['parm1', 'parm2', 'parm3', 'parm4', 'options'])
print 8
print luna.get_value('node', 'node012', ['parm1'])
