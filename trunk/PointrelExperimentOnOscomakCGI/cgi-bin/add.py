#!/usr/local/bin/python
import cgi

form = cgi.FieldStorage()

print "Content-type: text/plain\n\n"

try:
	from pointrel20030812 import *
	
	if form.has_key('context'):
		print "adding relationship"
		context = form['context'].value
		if form.has_key('object'):
			a = form['object'].value
		else:
			a = ""
		if form.has_key('relation'):
			b = form['relation'].value
		else:
			b = ""
		if form.has_key('value'):
			c = form['value'].value
		else:
			c = ""
		print "adding: %s | %s | %s | %s" % (context, a, b, c)
		Pointrel_add(context, a, b, c)
		print "added"
	else:
		print "no context -- not adding"

except:
	print "exception occurred"
	import sys, traceback
	traceback.print_exc(file=sys.stdout)
	
	
