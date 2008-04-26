#!/usr/local/bin/python
import cgi

form = cgi.FieldStorage()

print "Content-type: text/plain\n\n"

try:
	from pointrel20030812 import *
	
	if form.has_key('context'):
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
		if context == "" or context == "*": context = WILD
		if a == "" or a == "*": a = WILD
		if b == "" or b == "*": b = WILD
		if c == "" or c == "*": c = WILD
		print "search query: %s | %s | %s | %s" % (context, a, b, c)

		if form['results'].value == "All Matches":
			matches = Pointrel_allMatches(context, a, b, c)
			for match in matches:
				print match
		else:
			match = Pointrel_lastMatch(context, a, b, c)
			print match
		print "DONE"
	else:
		print "no context -- not searching. Put in '*' as wildcard"

except:
	print "exception occurred"
	import sys, traceback
	traceback.print_exc(file=sys.stdout)
	
	
