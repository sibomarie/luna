import luna
#node1 = luna.Node(group='compute-group', create = True)
#node1.add_ip()
node2 = luna.Node('node015')
#node2.del_ip()
#node2.del_bmc_ip()
#node2.del_bmc_ip()
group = luna.Group('compute-group')
group.add_interface('ib0', 'internal3')
