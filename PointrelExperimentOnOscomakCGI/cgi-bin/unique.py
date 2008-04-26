#!/usr/local/bin/python

#import cgi
#form = cgi.FieldStorage()

print "Content-type: text/plain\n\n"

try:
	from pointrel20030812 import *	
	print "new unique key:"
	print Pointrel_generateUniqueID()
except:
	print "exception occurred"
	import sys, traceback
	traceback.print_exc(file=sys.stdout)
	
	
