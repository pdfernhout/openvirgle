# intended to allow dynamic dispatch

# determines the model from the frame if it is not specified (the usual case)
# eventually maybe could pass in nested args for each path element
def DispatchEventForPath(event, modelSpecification, pathSpecification):
    # path may be either string or tuple with string at start and then arguments
    if type(pathSpecification) == tuple:
        path = pathSpecification[0]
        args = pathSpecification[1:]
    else:
        path = pathSpecification
        args = None
    # just assume single path item for now
    # eventually: pathElements = path.split() and loop on these
    # clean up leading and trailing spaces, just in case
    pathElement = path.strip()
    
    if not pathElement:
        return
    
    if not modelSpecification:
        # determine model from event
        component = event.source
        frame = component.topLevelAncestor
        model = frame.rootPane.getClientProperty("model")
    else:
        # eventually could pass in a model path
        model = modelSpecification
        # frame might be used in error reporting
        frame = None

    try:
        function = getattr(model, pathElement)
    except AttributeError:
        print "undefined path/function: '%s' in model: %s frame: %s" % (pathElement, model, frame)
        return
    if args:
        function(event, *args)
    else:
        function(event)       
 