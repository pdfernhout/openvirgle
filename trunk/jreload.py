# jreload.py.
# Taken and extended from xreload as posted by Guido van Rossum:
# Source: http://mail.python.org/pipermail/edu-sig/2007-February/007787.html
# Including some Zope changes from:
# http://svn.zope.de/plone.org/plone/plone.reload/trunk/plone/reload/xreload.py
# PDF modified further for Jython not to use sets and to use regular import with temporary deletion

import imp
import sys
import types
import marshal

# PDF modified for Jython
# Less general than xreload; can only reload modules in current directory
def jreload(oldModule, moduleName):
        
    # temporarily remove old module and later restore it
    del sys.modules[moduleName]
    try:
        newModule = __import__(moduleName)
    finally:
        sys.modules[moduleName] = oldModule
    topLevelNames = newModule.__dict__.keys()
    # delete unused names
    for name in oldModule.__dict__.keys():
        if name not in topLevelNames:
            delattr(oldModule, name)

    # Update all top level variables in module in old module (e.g. classes, functions, imports) 
    # to point to possibly new implementations.

    for topLevelName in topLevelNames:
        newObject = newModule.__dict__[topLevelName]
        try:
            oldObject = oldModule.__dict__[topLevelName]
        except KeyError:
            oldModule.__dict__[topLevelName] = newObject
            continue
        changed = _update(oldObject, newObject, oldModule)
        oldModule.__dict__[topLevelName] = changed

def _update(oldobj, newobj, mod):
    """Update oldobj, if possible in place, with newobj.

    If oldobj is immutable, this simply returns newobj.

    Args:
      oldobj: the object to be updated
      newobj: the object used as the source for the update

    Returns:
      either oldobj, updated in place, or newobj.
    """
    
    if type(oldobj) is not type(newobj):
        # Cop-out: if the type changed, give up
        return newobj
    if hasattr(newobj, "__reload_update__"):
        # Provide a hook for updating
        return newobj.__reload_update__(oldobj)
    
    # Module check taken from: http://svn.zope.de/plone.org/plone/plone.reload/trunk/plone/reload/xreload.py
    new_module = getattr(newobj, '__module__', None)
    if new_module != mod.__name__:
        # Do not update objects in-place that have been imported.
        # Bug: Jython does not set module of top level functions
        # Just update their references.
        return newobj
        
    if isinstance(newobj, types.ClassType):
        return _update_class(oldobj, newobj)
    if isinstance(newobj, types.FunctionType):
        return _update_function(oldobj, newobj)
    if isinstance(newobj, types.MethodType):
        return _update_method(oldobj, newobj)
    # XXX Support class methods, static methods, other decorators
    # Not something we recognize, just give up
    return newobj

def _update_function(oldfunc, newfunc):
    """Update a function object."""
    oldfunc.__doc__ = newfunc.__doc__
    oldfunc.__dict__.update(newfunc.__dict__)
    oldfunc.func_code = newfunc.func_code
    # PDF check for Jython -- where readonly in 2.2 -- latest svn as of March 2008 has fixed
    # http://article.gmane.org/gmane.comp.lang.jython.cvs/2561
    try:
        oldfunc.func_defaults = newfunc.func_defaults
    except TypeError:
        if oldfunc.func_defaults != newfunc.func_defaults:
            # just assign over it
            print "function defaults changed for ", oldfunc
            print "this verion of Jython does not support updating them, so changing the entire function instead"
            print "DynamicXYZListeners should still be able to call the changed function"
            # may have problems if called directly bia stored reference -- not updating bound class of new function? Not sure of this?
            return newfunc
            
    # XXX What else?
    return oldfunc

def _update_method(oldmeth, newmeth):
    """Update a method object."""
    # XXX What if im_func is not a function?
    changed = _update_function(oldmeth.im_func, newmeth.im_func)
    return changed

def _update_class(oldclass, newclass):
    """Update a class object."""
    # XXX What about __slots__?
    olddict = oldclass.__dict__
    newdict = newclass.__dict__
    # PDF changed to remove use of set as not in Jython 2.2
    for name in olddict.keys():
        if name not in newdict:
            delattr(oldclass, name)
    for name in newdict.keys():
        if name not in ["__dict__", "__doc__"]:
            if name not in olddict:
                setattr(oldclass, name,  newdict[name])
                continue
            new = getattr(newclass, name)
            old = getattr(oldclass, name, None)
            if new == old:
                continue
            if old is None:
                setattr(oldclass, name, new)
                continue
            if isinstance(new, types.MethodType):
                changed = _update_method(old, new)
                setattr(oldclass, name, changed)
            elif isinstance(new, types.FunctionType):
                # __init__ is a function
                changed = _update_function(old, new)
                setattr(oldclass, name, changed)
            else:
                # Fallback to just replace the item
                setattr(oldclass, name, new)
    return oldclass
