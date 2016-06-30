from Luna import Luna
from bson import ObjectId
luna = Luna('luna')
print 1
print luna.create_obj('node', 'node012', {'kernopts': 'different kern opts', 'kernmodules': [{'module1': 'option1'}, {'module2': ['option21', 'option22']}]})
