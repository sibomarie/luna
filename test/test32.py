import luna
node1 = luna.Node(group='compute-group', create = True)
print str(node1.show())
node = luna.Node('node015')
print str(node.show())

group = luna.Group('compute-group')
print str(group.show())
