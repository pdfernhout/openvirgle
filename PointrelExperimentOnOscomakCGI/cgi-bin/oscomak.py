#!/usr/local/bin/python
import cgi

form = cgi.FieldStorage()

# print "Content-type: text/plain\n\n"

try:
	from pointrel20030812 import *
	if form.has_key('name'):
        	name = form['name'].value
        	code = Pointrel_lastMatch("test", name, "code", WILD)
		#print code
		if code:
			code = code.replace('\r', '')
			exec code
		else:
			print "Content-type: text/plain\n\n"
			print "Unknown name '%s'" % name
	else:
                print "Content-type: text/plain\n\n"
                print "Unspecified name '%s'" % name


	"""	
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
	"""

except:
	print "Content-type: text/plain\n\n"
	print "exception occurred"
	import sys, traceback
	traceback.print_exc(file=sys.stdout)
	
	
