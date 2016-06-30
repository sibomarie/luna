from Luna import Luna
from bson import ObjectId
luna = Luna()
print 1
print luna.find_obj('cluster',{'_id': ObjectId('568a25448809993112671998')})
print 2
print luna.find_obj('cluster',{'name': 'luna'})
print 3
print luna.find_obj('cluster',{'name': 'test'})
print 4
print luna.find_obj('cluster',{'n': 1})
print 5
print luna.find_obj('cluster',{'aaa': 'ccc'})

