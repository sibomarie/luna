def fun(a = 1, b= 'b'):
    import inspect
    print dir()
    frame = inspect.currentframe().f_locals
    print frame
#    print inspect.getargvalues(frame)
    return inspect.getargspec(fun)[0]

print fun()
