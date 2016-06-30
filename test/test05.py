from Luna import Luna
from bson import ObjectId
luna = Luna('luna', ['nodes','cluster','osimage'])
print 1
print luna.secure_fields('nodes', {})
print 2
print luna.secure_fields('nodes', {'n': 100, 'aaa': 'bbb', '_reverse_links': 'link', 'bbb': 4})
print 3
print luna.secure_fields('node', {'n': 100, 'aaa': 'bbb', '_reverse_links': 'link', 'bbb': 4})
