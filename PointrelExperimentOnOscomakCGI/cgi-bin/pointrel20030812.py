"""
Pointrel Data Repository System 20030812.2
Copyright 2000-2003 Paul D. Fernhout
See license.txt for license information
"""

import struct
import string
import cStringIO
import random
import zlib
import os
import time
import stat
import binascii
import socket
import sys
import cPickle

import xml.sax.saxutils

"""
def TopLevelExceptionHandler(type, value, traceback):
    print "Exception"
    sys.excepthook = sys.__excepthook__
    print type, value, traceback
    import pdb
    pdb.post_mortem(traceback)
 
sys.excepthook = TopLevelExceptionHandler
"""

# WILD is a marker token, typically never stored in database
class WILD:
	pass

NON_XML_ASCII_CHARACTERS = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0B\x0C\x0E\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1A\x1B\x1C\x1D\x1E\x1F"

debugFile = sys.stderr

longRepresentationLength = 8

class PointrelException(Exception):
	pass

########### SIMPLE INTERFACE FUNCTIONS ###############

"""
typical API useage:

Pointrel_initialize(archiveName)
Pointrel_startTransaction()
Pointrel_add(context, a, b, c)
Pointrel_finishTransaction()
string = Pointrel_lastMatch(context, WILD, b, c)
string = Pointrel_lastMatch(context, a, b, WILD)
list = Pointrel_allMatches(context, a, b, WILD)
string = Pointrel_generateUniqueID()

"""
_repository = None

# if true, allow adding without being in an explicit transaction
_allowImplicitTransactions = 1

# accessor to to allow use of less commonly used pointrel functions
# for example, to abandon a transaction, import from another archive, or do multi-archive searches
def Pointrel_getRepository():
	return _repository
	
#optional initialization step
def Pointrel_initialize(archive = ".hiddenG95ht/archive_default", logging = 1):
	global _repository
	_repository = PointrelDataRepositorySystem(archive, logging)
	if not _repository: raise PointrelException("problem opening repository" + archive)

# call before multiple adds
# optional if _allowImplicitTransactions is set
def Pointrel_startTransaction():
	if not _repository: Pointrel_initialize()
	_repository.startTransaction()

# call after start_transaction and adds to commit data
def Pointrel_finishTransaction():
	if not _repository: raise PointrelException("transaction not started")
	_repository.finishTransaction()

# add the triad with the defined context
# example: Pointrel_add("all email", id, "body", text)
def Pointrel_add(context, a, b, c):
	if not _repository: Pointrel_initialize()
	implicitTransaction = 0
	if not _repository.isInTransaction():
		if _allowImplicitTransactions:
			implicitTransaction = 1
			_repository.startTransaction()
		else:
			raise PointrelException("not in transaction")
	_repository.add(context, a, b, c)
	if implicitTransaction:
		_repository.finishTransaction()
	
# a search function
# if no wildcards, return all exact tuples or None
# a wildcard is WILD
# will return list of wildcard fields for single wildcard
# if multiple wildcards, returns list of entire tuples
# if return choice is None, returns list of entire tuples always
# if return choice is 0-3, returns list of specified field always (not very useful)
# result list will be ordered from earliest to latest
def Pointrel_allMatches(context, a, b, c, returnChoice=-1):
	if not _repository: Pointrel_initialize()
	return _repository.allMatches(context, a, b, c, returnChoice)
	
# a search function
# if no wildcards, return exact tuple if present or None
# a wildcard is WILD
# will return wildcard field for single wildcard
# if multiple wildcards, returns entire tuple
# if return choice is None, returns entire tuple always
# if return choice is 0-3, returns specified field always (not very useful)
def Pointrel_lastMatch(context, a, b, c, returnChoice=-1):
	if not _repository: Pointrel_initialize()
	return _repository.lastMatch(context, a, b, c, returnChoice)

# returns a unique id -- useful for making objects
def Pointrel_generateUniqueID():
	if not _repository: Pointrel_initialize()
	return _repository.generateUniqueID()
	
# alias for Pointrel_generateUniqueID()
def Pointrel_newObject():
	return Pointrel_generateUniqueID()
	
# add if last match for last value (of c) is different -- for convenience
def Pointrel_addIfNeededForLastValue(context, a, b, c):
	if not _repository: Pointrel_initialize()
	implicitTransaction = 0
	if not _repository.isInTransaction():
		if _allowImplicitTransactions:
			implicitTransaction = 1
			_repository.startTransaction()
		else:
			raise PointrelException("not in transaction")
	_repository.addIfNeededForLastValue(context, a, b, c)
	if implicitTransaction:
		_repository.finishTransaction()

def Pointrel_globalTimestamp():
	if not _repository: Pointrel_initialize()
	return GlobalTimestamp()

def simpleInterfaceTest():
	print " ================ testing pointrel simple ================="
	Pointrel_initialize("archive_simpleTest")
	Pointrel_startTransaction()
	Pointrel_add("test", "1", "2", "3")
	Pointrel_add("test", "1", "2", "4")
	Pointrel_add("test", "1", "4", "5")
	Pointrel_finishTransaction()
	#test of implicit transaction
	Pointrel_add("test", "3", "4", "5")
	#next should not change repository
	Pointrel_addIfNeededForLastValue("test", "3", "4", "5")
	print "should be 3", Pointrel_lastMatch("test", WILD, "4", "5")
	print "should be 4", Pointrel_lastMatch("test", "1", "2", WILD)
	print "should be list -- longer each time run",  Pointrel_allMatches("test", "1", WILD, WILD)
	print "should be unique id url -- different each time run", Pointrel_generateUniqueID()	


############ underlying supporting classes #################

"""
typical supporting API useage:

repository = PointrelDataRepositorySystem(archiveName)
repository.startTransaction()
repository.add(context, a, b, c)
repository.finishTransaction()
string = repository.lastMatch(context, WILD, b, c)
string = repository.lastMatch(context, a, b, WILD)
list = repository.allMatches(context, a, b, WILD)
string = repository.generateUniqueID()
"""

"""
Storage format:

All information is stored on 8 byte boundaries.

Archive format:
HEADER[1024] (with last tuple position in there at 512)
\r\n<+ end1
STRING RECORD
...
TUPLE RECORD
...
STRING RECORD
...
TUPLE RECORD
...
\r\n~> start1
\r\n<+ end2
STRING RECORD
...
TUPLE RECORD
...
\r\n~> start2

String Record Format:
0x7F010A0C
flags
dataStringLengthOnMedia 
dataStringHash(crc32)
lessThanLink 
greaterThanLink
lastUsers[4]
useCount[4]
dataString[length] padded at end with zeros to be 8 byte multiple

Tuple Record Format:
0x7F020A0C 
flags
strings[4]
previousUsers[4]
previousTupleLocation

Four byte headers for string and tuple record and embedded transaction start/end words
are used to attempt last ditch error recovery if no log file and problem with transaction file.
"""

class Constants:
	archiveFileExtension = ".pointrel_database.poi"
	logFileExtension = ".pointrel_database.xml"
	recoveryFileExtension = ".pointrel_recovery"
	lockFileExtension = ".pointrel_lock"
	#if no archive name is specified when creating a repository instance, this one is used
	defaultArchiveName = "archive_default"
	
	logFileHeader = """<?xml version="1.0" encoding="utf-8" ?>
<P:archive xmlns:P="http://www.pointrel.org/Pointrel20030812/NS/" version="20030812.1" archiveID="%s">
"""
	archiveHeaderSize = 1024
	#length must be archiveHeaderSize or under
	archiveVersion = "Pointrel Archive v20030812.1"
	# need to fill in header with unqiue ID
	archiveFileHeader = archiveVersion + "\n%s\nVisit: http://www.pointrel.org\n" +\
	"File contains strings, internal pointers, and relationships and is not intended to be editable.\n" +\
	"Any change to this file in an editor will likely corrupt it.\n"
	archiveLastTriadUsedPosition = 512
	
	recoveryFileHeader = archiveVersion + " Recovery File    \r\n"

	#these are constants because all users must agree so locking is coordinated
	lockMaxRetries = 99
	lockSleepAmount = 0.3
	halfTotalLockSleepAmount = 0.5 * lockSleepAmount * lockMaxRetries
	totalLockSleepAmount = lockSleepAmount * lockMaxRetries
	
	alignmentBytes = ["", "\0\0\0\0\0\0\0", "\0\0\0\0\0\0", "\0\0\0\0\0", "\0\0\0\0", "\0\0\0", "\0\0", "\0"]

	if len(recoveryFileHeader) % longRepresentationLength:
		raise PointrelException("recoveryFileHeader should be %s byte aligned" % longRepresentationLength)
	
class Options:
	#using logging is recommended for now as offering last ditch recovery option and data duplication
	defaultLogging = 1
	
	#this cache stores strings and locations for string index -- 
	# these should not change even if another process uses archive simultaneously
	caching = 1
	#may want to limit size of strings that are cached to under 32 or 256 bytes or so
	
	uniqueIdCounter = 0
	uniqueIdCounterReadFromFile = 1
	uniqueIdPrefix = "unique://"
	
	# the following can be set by importer to some unique domain or other string for maximum collision avoidance of unique IDs
	#may wish to set it to something else to obscure identity
	#uniqueLocalValue = socket.gethostname()
	#uniqueLocalValue = "localhost"
	uniqueLocalValue = "oscomak.net"
	
	#control whether any strings can be compressed -- had a problem with this and zlib decompress for Python 1.5.1
	dataStringCompressionAllowed = 0
	# the minimum size datastring at which compression will be attempted
	# will only store compressed if result less than uncompressed size
	dataStringCompressionThreshold = 64
	
	########### simple obfuscation support ##############
	# functions to support hiding data from casual snooping
	#support simple obfuscation using rotating all characters by a fixed amount
	#anyone using Pointrel can read your data if the know the approach
	#this is adequate for simple obfuscation like in a game data file or preventing casual snooping
	# but it is useless for any serious security -- don't rely on it for privacy protection
	# obfuscation also discourages hand editing of archive file which would break the string hash used in lookup
	dataStringObfuscationDesired = 0
	doNotObfuscateCompressedData = 1
	#note that compressed and obfuscated strings can still be read if these options above are turned off
	obfuscationRotationAmount = 37
	#note that the log file is not obfuscated
	# note that the structure of the file itself including tuple interrelationships is not obfuscated, only the text strings

	# allow a place to prevent time from being returned
	recordTransactionTime = 1
	
	# if ignoreOldLockFiles is true, old lock files will be ignored if older than maximumLockWait
	ignoreOldLockFiles = 0
	maximumLockWait = Constants.totalLockSleepAmount


class Performance:
	#counter = 1
	readbytes = 0

class ObfuscationTableConstructor:

	def makeObfuscationTableForward(self):
		inputString = ""
		for i in range(256):
			inputString = inputString + chr(i)
		outputString = ""
		for i in range(256):
			outputString = outputString + chr((i + Options.obfuscationRotationAmount) % 256)
		return string.maketrans(inputString, outputString)
		
	def makeObfuscationTableInverse(self):
		inputString = ""
		for i in range(256):
			inputString = inputString + chr(i)
		outputString = ""
		for i in range(256):
			outputString = outputString + chr(((i - Options.obfuscationRotationAmount) + 256) % 256)
		return string.maketrans(inputString, outputString)
		
class ObfuscationTable:
	obfuscationTableForward = ObfuscationTableConstructor().makeObfuscationTableForward()
	obfuscationTableInverse = ObfuscationTableConstructor().makeObfuscationTableInverse()

####### beginning of core code #############

class StringIndexRecord:
	representationLength = 14 * longRepresentationLength
	headerWord = 0x7F010A0C
	# flags field is intended to be used for things like whether entry is compressed, 
	# if it supports 64 bit pointers, and as a quick reference to if a tuple has been deleted
	# control whether uncompressed string is obfuscated (as in a game data file)
	# and also general info on the type of object stored
	Flag_ZlibCompression = 1
	Flag_Obfuscation = 2
	Flag_BinaryData = 4
	Flag_UnicodeData = 8
	Flag_PythonPickledData = 16
	Flag_TypeMask = Flag_BinaryData | Flag_UnicodeData | Flag_PythonPickledData
	
	def __init__(self, locationInArchiveFile, dataString, dataStringNeedsToBeRead=0):
		self.locationInArchiveFile = locationInArchiveFile
		self.lessThanLink = 0
		self.greaterThanLink = 0
		self.lastUsers = [0, 0, 0, 0]
		self.useCount = [0, 0, 0, 0]
		self.flags = 0
		self.dataStringNeedsToBeRead = dataStringNeedsToBeRead
		if not dataStringNeedsToBeRead:
			self.needToWriteString = 1
			#print>> debugFile, dataString
			if type(dataString) is str:
				self.dataStringLengthOnMedia = len(dataString)
				self.dataStringHash = zlib.crc32(dataString)
				self.dataString = dataString
				self.flags = self.flags | self.Flag_BinaryData
			elif type(dataString) is unicode:
				# treat as unicode string -- encode as UTF-8
				encodedString = dataString.encode("utf_8")
				self.dataStringLengthOnMedia = len(encodedString)
				self.dataStringHash = zlib.crc32(encodedString)
				self.dataString = encodedString
				self.flags = self.flags | self.Flag_UnicodeData
			else:
				# treat as arbitrary python object and pickle it
				encodedString = cPickle.dumps(dataString)
				self.dataStringLengthOnMedia = len(encodedString)
				self.dataStringHash = zlib.crc32(encodedString)
				self.dataString = encodedString
				self.flags = self.flags | self.Flag_PythonPickledData
		else:
			self.dataStringLengthOnMedia = None
			self.dataStringHash = None
			self.needToWriteString = 0
			self.dataString = None
		self.needToReadHeader = 1
		
	def readHeader(self, archiveFile):
		if self.needToReadHeader:
			#print>> debugFile, "read header", self.locationInArchiveFile
			archiveFile.seek(0,2)
			if archiveFile.tell() <  self.locationInArchiveFile:
				raise PointrelException("archive corrupt -- string record location beyond end of file", self.locationInArchiveFile)
			archiveFile.seek(self.locationInArchiveFile)
			#if archiveFile.tell() <>  self.locationInArchiveFile:
			#	raise PointrelException("string record failed to seek to location", self.locationInArchiveFile)
			binaryRepresentation = archiveFile.read(StringIndexRecord.representationLength)
			#Performance.readbytes = readbytes + StringIndexRecord.representationLength
			self.unpackRepresentation(binaryRepresentation)
			self.needToReadHeader = 0
			self.needToWriteString = 0
			
	def obfuscateString(self, aString):
		return string.translate(aString, ObfuscationTable.obfuscationTableForward)
	
	def deobfuscateString(self, aString):
		return string.translate(aString, ObfuscationTable.obfuscationTableInverse)
		
	def retrieveObject(self, archiveFile):
		if self.dataStringNeedsToBeRead:
			self.readString(archiveFile)
		# may want to cahce the results?
		if self.flags & self.Flag_BinaryData:
			return self.dataString
		elif self.flags & self.Flag_UnicodeData:
			return unicode(self.dataString, "utf_8")
		elif self.flags & self.Flag_PythonPickledData:
			return cPickle.loads(self.dataString)
		else:
			raise PointrelException("type not specified for string")
		
	def readString(self, archiveFile):
		if not self.dataStringNeedsToBeRead:
			return self.dataString
		if self.needToReadHeader:
			self.readHeader(archiveFile)	
		#print>> debugFile, "reading string", self.locationInArchiveFile
		#global counter
		#counter = counter + 1
		archiveFile.seek(self.locationInArchiveFile + StringIndexRecord.representationLength)
		self.dataString = archiveFile.read(self.dataStringLengthOnMedia)
		if self.flags & self.Flag_Obfuscation:
			self.dataString = self.deobfuscateString(self.dataString)
		if self.flags & self.Flag_ZlibCompression:
			self.dataString = zlib.decompress(self.dataString)
		#Performance.readbytes = Performance.readbytes + self.dataStringLengthOnMedia
		#print>> debugFile, "read string: ", self.dataString
		#if counter > 15:
		#	raise PointrelException("halt")
		self.dataStringNeedsToBeRead = 0
		return self.dataString
		
	def readStringAndAlignmentBytes(self, archiveFile):
		result = self.readString(archiveFile)
		align = self.dataStringLengthOnMedia % longRepresentationLength
		padding = archiveFile.read(len(Constants.alignmentBytes[align]))
		return result
		
	def write(self, archiveFile):
		if self.needToWriteString:
			# determine if makes sense to compress
			if Options.dataStringCompressionAllowed and self.dataStringLengthOnMedia >= Options.dataStringCompressionThreshold:
				compressedString = zlib.compress(self.dataString)
				compressedLength = len(compressedString)
				if compressedLength < self.dataStringLengthOnMedia:
					#print>> debugFile, "compressing", self.dataStringLengthOnMedia, "to", compressedLength
					self.flags = self.flags | self.Flag_ZlibCompression
					self.dataStringLengthOnMedia = compressedLength
			if Options.dataStringObfuscationDesired and not (Options.doNotObfuscateCompressedData and (self.flags & self.Flag_ZlibCompression)):
				#might not want to obfuscate compressed things since those are obfuscated already...
				#might also not want to obfuscate binary data (containing non-printables)...
				self.flags = self.flags | self.Flag_Obfuscation
		archiveFile.seek(self.locationInArchiveFile)
		binaryRepresentation = self.packRepresentationForWriting()
		archiveFile.write(binaryRepresentation)
		if self.needToWriteString:
			stringToWrite = self.dataString
			if self.flags & self.Flag_ZlibCompression:
				stringToWrite = compressedString
			if self.flags & self.Flag_Obfuscation:
				stringToWrite = self.obfuscateString(stringToWrite)
			archiveFile.write(stringToWrite)
			#make records align on four byte boundaries
			padding = Constants.alignmentBytes[self.dataStringLengthOnMedia % longRepresentationLength]
			if padding:
				archiveFile.write(padding)
			self.needToWriteString = 0
		
	def packRepresentationForWriting(self):
		return struct.pack("!QQQqQQQQQQQQQQ", \
			self.headerWord, self.flags, \
			self.dataStringLengthOnMedia, self.dataStringHash, self.lessThanLink, self.greaterThanLink, 
			self.lastUsers[0], self.lastUsers[1], self.lastUsers[2], self.lastUsers[3],
			self.useCount[0], self.useCount[1], self.useCount[2], self.useCount[3]
			)
		
	def unpackRepresentation(self, binaryRepresentation):
		#print>> debugFile, len(binaryRepresentation)
		tuple = struct.unpack("!QQQqQQQQQQQQQQ", binaryRepresentation)
		headerWordRead, self.flags,\
			self.dataStringLengthOnMedia, self.dataStringHash, self.lessThanLink, self.greaterThanLink, \
			self.lastUsers[0], self.lastUsers[1], self.lastUsers[2], self.lastUsers[3], \
			self.useCount[0], self.useCount[1], self.useCount[2], self.useCount[3] \
			= tuple
		## print "%x" % headerWordRead
		## print "%x" % self.headerWord
		if headerWordRead <> self.headerWord:
			raise PointrelException("string header incorrect -- archive corrupt")
		if self.flags & ~(self.Flag_ZlibCompression | self.Flag_Obfuscation | self.Flag_TypeMask):
			raise PointrelException("unknown string flags field used -- not yet supported")
			
		
	def setLink(self, direction, link):
		if direction < 0:
			self.lessThanLink = link
		elif direction > 0:
			self.greaterThanLink = link
		else:
			raise PointrelException("IndexRecord: Error -- direction value is zero")
			
	def updateLastUser(self, index, newLastUser):
		self.lastUsers[index] = newLastUser
		self.useCount[index] = self.useCount[index] + 1
		
	def compare(self, archiveFile, temporaryStringObject):
		#assume header already read
		#if self.needToReadHeader:
		#	self.readHeader(archiveFile)	
		
		#optimization to compare on hashes first
		#print>> debugFile, comparisonHash, self.dataStringHash
		if temporaryStringObject.dataStringHash < self.dataStringHash:
			#print>> debugFile, "lt hash"
			return -1
		elif temporaryStringObject.dataStringHash > self.dataStringHash:
			#print>> debugFile, "gt hash"
			return 1
		#print>> debugFile, "hash match"
		#hashes must match
		
		#now check if types match
		if (temporaryStringObject.flags & StringIndexRecord.Flag_TypeMask) < (self.flags & StringIndexRecord.Flag_TypeMask):
			#print>> debugFile, "lt type"
			return -1
		elif (temporaryStringObject.flags & StringIndexRecord.Flag_TypeMask) > (self.flags & StringIndexRecord.Flag_TypeMask):
			#print>> debugFile, "gt type"
			return 1

		# could optimize later so only reads partial data depending on comparison string lengths
		if self.dataString == None:
			self.readString(archiveFile)
		if temporaryStringObject.dataString < self.dataString:
			#print>> debugFile, "lt string"
			return -1
		elif temporaryStringObject.dataString > self.dataString:
			#print>> debugFile, "gt string"
			return 1
		else:
			return 0
			
	def xmlTypeCharacterAndEncodedString(self):
		typeCharacter = ""
		encodedString = None
		#print "dataString" , self.dataString
		if self.flags & self.Flag_BinaryData:	
			typeCharacter = "b"
			encodedString = self.dataString
			#check if string has problems...
			# check for ASCII characters not legal in XML
			# should be faster way?
			for c in encodedString:
				if (ord(c) > 127) or (c in NON_XML_ASCII_CHARACTERS):
					typeCharacter = "h"
					encodedString = binascii.b2a_hex(self.dataString)
					break
		elif self.flags & self.Flag_UnicodeData:
			typeCharacter = "u"
			encodedString = self.dataString
		elif self.flags & self.Flag_PythonPickledData:
			typeCharacter = "p"
			# expecting pickled data to be plain ASCII, but check it out
			encodedString = self.dataString			
		else:
			raise PointrelException("unexpected value type %s" % (self.flags & self.Flag_TypeMask))
		return (typeCharacter, encodedString)
			
	def __repr__(self):
		return "<StringIndexRecord " + `self.locationInArchiveFile` + " " + `self.lessThanLink` + " " + `self.greaterThanLink` + ">"

class TupleIndexRecord:
	representationLength = 11 * longRepresentationLength
	headerWord = 0x7F020A0C
	
	def __init__(self, locationInArchiveFile, previousTupleLocation = 0):
		self.locationInArchiveFile = locationInArchiveFile
		self.strings = [0, 0, 0, 0]
		self.previousUsers = [0, 0, 0, 0]
		# store this value so can chain through all tuple sif needed
		self.previousTupleLocation = previousTupleLocation
		self.flags = 0
		
	def read(self, archiveFile):
		archiveFile.seek(0,2)
		if archiveFile.tell() <  self.locationInArchiveFile:
			raise PointrelException("archive corrupt -- tuple record location beyond end of file", self.locationInArchiveFile)
		archiveFile.seek(self.locationInArchiveFile)
		#if archiveFile.tell() <>  self.locationInArchiveFile:
		#	print>> debugFile, archiveFile.tell()
		#	raise PointrelException("tuple record failed to seek to location", self.locationInArchiveFile)
		binaryRepresentation = archiveFile.read(TupleIndexRecord.representationLength)
		#Performance.readbytes = Performance.readbytes + TupleIndexRecord.representationLength
		self.unpackRepresentation(binaryRepresentation)
		
	def write(self, archiveFile):
		archiveFile.seek(self.locationInArchiveFile)
		binaryRepresentation = self.packRepresentationForWriting()
		archiveFile.write(binaryRepresentation)
		
	def packRepresentationForWriting(self):
		#print>> debugFile, self.previousTupleLocation
		return struct.pack("!QQQQQQQQQQQ", 
			self.headerWord, self.flags,
			self.strings[0], self.strings[1], self.strings[2], self.strings[3],
			self.previousUsers[0], self.previousUsers[1], self.previousUsers[2], self.previousUsers[3],
			self.previousTupleLocation
			)
		
	def unpackRepresentation(self, binaryRepresentation):
		tuple = struct.unpack("!QQQQQQQQQQQ", binaryRepresentation)
		headerWordRead, self.flags, \
			self.strings[0], self.strings[1], self.strings[2], self.strings[3],\
			self.previousUsers[0], self.previousUsers[1], self.previousUsers[2], self.previousUsers[3],\
			self.previousTupleLocation \
			= tuple		
		if headerWordRead <> self.headerWord:
			raise PointrelException("tuple header incorrect -- archive corrupt")
		if self.flags <> 0:
			raise PointrelException("tuple flags field used -- not yet supported")

	def isIndexedMatch(self, indexedTemplate):
		if indexedTemplate[0] == 0 or self.strings[0] == indexedTemplate[0]:
			if indexedTemplate[1] == 0 or self.strings[1] == indexedTemplate[1]:
				if indexedTemplate[2] == 0 or self.strings[2] == indexedTemplate[2]:
					if indexedTemplate[3] == 0 or self.strings[3] == indexedTemplate[3]:
						return 1
		return 0


class PointrelArchive:
	transactionStartWord = "\0\0\0\0\r\n<+\0\0\0\0\0\0\0\0"
	transactionFinishWord = "\r\n~>\0\0\0\0"

	def __init__(self, archiveName = Constants.defaultArchiveName, logging = 1):
		self.archiveName = archiveName
		self.archiveFile = None
		self.recoveryStringsStored = {}
		self.recoveryCheckPointFileSize = 0
		self.recoveryCheckPointLastTuple = 0
		if Options.caching:
			self.stringCache = {}
			self.positionCache = {}
		self.inTransaction = 0
		self.writtenTransactionHeaderToLog = 0
		# also used to store location where header is
		self.writtenTransactionHeaderToArchive = 0
		self.logging = logging
		self.usingAsReadOnly = 0
		self.lockFileLastRefresh = 0
		# archive ID is set when archive created or read/updated
		self.uniqueArchiveID = None

	def transactionTime(self):
		if Options.recordTransactionTime:
			return int(time.time())
		else:
			return 0

	def startTransaction(self):
		if self.inTransaction:
			raise PointrelException("already in transaction")
		self.writtenTransactionHeaderToLog = 0
		self.writtenTransactionHeaderToArchive = 0
		#print>> debugFile, "begin transaction"
		self.lockArchive()
		self.recoverFromFailedTransactionIfNeeded()
		self.archiveFile = self.openFileForWriting()
		self.simpleCheckArchiveIntegrityForLastTransaction()
		self.startRecoveryFile()
		self.inTransaction = 1
	
	def finishTransaction(self):
		if self.writtenTransactionHeaderToArchive:
			#print>> debugFile, "writing trans end"
			locationOfEndMarker = self.seekLastPosition()
			self.archiveFile.write(self.transactionFinishWord)
			binaryRepresentation = struct.pack("!Q", self.writtenTransactionHeaderToArchive)
			self.archiveFile.write(binaryRepresentation)
			theTime = self.transactionTime()
			binaryRepresentation = struct.pack("!QQ", 0, theTime)
			self.archiveFile.write(binaryRepresentation)
			self.archiveFile.seek(self.writtenTransactionHeaderToArchive + longRepresentationLength)
			binaryRepresentation = struct.pack("!Q", locationOfEndMarker)
			self.archiveFile.write(binaryRepresentation)
			self.writtenTransactionHeaderToArchive = 0
			self.archiveFile.flush()
		self.archiveFile.close()
		self.archiveFile = None
		if self.writtenTransactionHeaderToLog:
			self.writeTransactionEndToLogFile()
		#now assume archive correct on media, so can remove recovery information
		self.removeRecoveryFile()
		self.inTransaction = 0
		self.unlockArchive()
		#print>> debugFile, "end transaction"

	def abandonTransaction(self):
		self.archiveFile.close()
		self.archiveFile = None
		self.recoverFromFailedTransactionIfNeeded(1)
		self.inTransaction = 0
		self.unlockArchive()
		
	#defining this myself to allow support for Python 1.5.1
	def getmtime(self, filename):
		mtime = os.stat(filename)[stat.ST_MTIME]
		return mtime
		
	# hoping this is reasonably robust and portable
	# probably could also use recovery file as a lock file (except for read only searches)
	def lockArchive(self):
		tryCount = 0
		if os.path.exists(self.archiveName + Constants.lockFileExtension):
			inUseTime = int(time.time()) - self.getmtime(self.archiveName + Constants.lockFileExtension)
		else:
			inUseTime = 0
		if Options.ignoreOldLockFiles and inUseTime > Options.maximumLockWait:
			pass
		else:
			while os.path.exists(self.archiveName + Constants.lockFileExtension):
				if tryCount == 0:
					print>> debugFile, "waiting on lock for " + self.archiveName
					print>> debugFile, "lock has been in use for %d seconds" % inUseTime
					if inUseTime > Options.maximumLockWait:
						print>> debugFile, "since lock has been in use for so long, it might be left over from a program failure"
				# might want to randomize delay to avoid syncronizing lockouts with other users
				# random.random() * 2.0 * Constants.lockSleepAmount
				time.sleep(Constants.lockSleepAmount)
				tryCount = tryCount + 1
				if tryCount > Constants.lockMaxRetries:
					inUseTime = int(time.time()) - self.getmtime(self.archiveName + Constants.lockFileExtension)
					if Options.ignoreOldLockFiles and inUseTime > Options.maximumLockWait:
						break
					else:
						raise PointrelException("timeout - could not get lock")
		# make the lock file
		open(self.archiveName + Constants.lockFileExtension, "w").close()
		self.lockFileLastRefresh = time.time()
		
	def unlockArchive(self):
		if os.path.exists(self.archiveName + Constants.lockFileExtension):
			os.remove(self.archiveName + Constants.lockFileExtension)
		else:
			raise PointrelException("lock file unexpectedly disappeared")
			
	def refreshLockFileIfNeeded(self):
		"make sure lock file is kept up to date on long transactions"
		if self.inTransaction:
			theTime = time.time()
			if theTime > self.lockFileLastRefresh + Constants.halfTotalLockSleepAmount:
				# try a few times if needed in case lock file is being inspected by other process -- like win2000 properties
				for i in range(10):
					try:
						open(self.archiveName + Constants.lockFileExtension, "w").close()
						self.lockFileLastRefresh = theTime
						return
					except:
						print>> debugFile, "lock file being inspected by other process -- retrying refresh"
						time.sleep(0.17)
				raise PointrelException("could not refresh lock file")
			
	# returns false if no archive exists
	def startUsingReadOnly(self):
		#print>> debugFile, "startUsingReadOnly"
		if self.archiveFile:
			raise PointrelException("Archive file should not be set")
		self.lockArchive()
		self.recoverFromFailedTransactionIfNeeded()
		self.archiveFile = self.openFileForReading()
		if self.archiveFile:
			self.usingAsReadOnly = 1
		else:
			self.unlockArchive()
		return self.archiveFile <> None
		
	def finishUsingReadOnly(self):
		#print>> debugFile, "finishUsingReadOnly"
		if not self.usingAsReadOnly:
			raise PointrelException("archive not read only")
		if self.archiveFile:
			self.archiveFile.close()
			self.archiveFile = None
		self.usingAsReadOnly = 0
		self.unlockArchive()
		
	def checkOpen(self):
		if not self.archiveFile or self.archiveFile.closed:
			raise PointrelException("archive file not open")
		
	def createFile(self):
		#create the file
		print>> debugFile, "creating archive file", self.archiveName + Constants.archiveFileExtension
		self.uniqueArchiveID = GenerateUniqueID()
		#print>> debugFile, "uniqueArchiveID =" , self.uniqueArchiveID
		archiveFile = open(self.archiveName + Constants.archiveFileExtension, "w+b")
		#make an empty zeroth record
		archiveFile.write(Constants.archiveFileHeader % self.uniqueArchiveID)
		archiveFile.write("\0" * (Constants.archiveHeaderSize - len(Constants.archiveFileHeader % self.uniqueArchiveID)))
		#there will be a zero position for last triad
		#archiveFile.seek(Constants.archiveLastTriadUsedPosition)
		#archiveFile.write("\0\0\0\0")
		return archiveFile
		
	def openFileForWriting(self):
		try:
			archiveFile = open(self.archiveName + Constants.archiveFileExtension, "r+b")
			version = archiveFile.readline()[:-1]
			if version <> Constants.archiveVersion:
				raise PointrelException("archive version not supported for writing: " + version)
			self.uniqueArchiveID = archiveFile.readline()[:-1]
			#print>> debugFile, "uniqueArchiveID =" , self.uniqueArchiveID
		except IOError, error:
			archiveFile = self.createFile()
		return archiveFile
		
	def openFileForReading(self):
		try:
			archiveFile = open(self.archiveName + Constants.archiveFileExtension, "rb")
			version = archiveFile.readline()[:-1]
			if version <> Constants.archiveVersion:
				raise PointrelException("archive version not supported for reading: " + version)
			self.uniqueArchiveID = archiveFile.readline()[:-1]
			#print>> debugFile, "uniqueArchiveID =" , self.uniqueArchiveID
		except IOError, error:
			#print>> debugFile, "could not open archive: " + self.archiveName + Constants.archiveFileExtension
			archiveFile = None
		return archiveFile
	
	# last transaction might be incomplete if recover file was deleted
	# if this raises an exception -- need to rebuild archive from log or from archive itself
	# could ignore problem but this is not advised as other internal pointers may be incorrect...
	def simpleCheckArchiveIntegrityForLastTransaction(self):
		size = self.seekLastPosition()
		if size == Constants.archiveHeaderSize:
			print>> debugFile, "archive with only header"
			return 1
		self.archiveFile.seek(-4 * longRepresentationLength, 2)
		binaryRepresentation = self.archiveFile.read(4 * longRepresentationLength)
		# these two unpack strings need to be updated if longRepresentationLength changes
		tuple = struct.unpack("!8sQQQ", binaryRepresentation)
		if tuple[0] <> self.transactionFinishWord:
			raise PointrelException("transaction incomplete at end -- rebuild archive!")
		if tuple[1] > size or tuple[1] < Constants.archiveHeaderSize:
			raise PointrelException("transaction start location is corrupt -- rebuild archive!")
		self.archiveFile.seek(tuple[1])
		binaryRepresentation = self.archiveFile.read(4 * longRepresentationLength)
		tuple = struct.unpack("!8sQQQ", binaryRepresentation)
		if tuple[0] <> self.transactionStartWord[:longRepresentationLength]:
			raise PointrelException("transaction start incorrect -- rebuild archive!")
		if tuple[1] <> size - 4 * longRepresentationLength:
			raise PointrelException("transaction start reference to end location is corrupt -- rebuild archive!")
		#otherwise, everything OK with tail end of file and last transaction
		#print>> debugFile, "last transaction OK"
		return 1
	
	# ensures data four byte boundary aligned
	def currentPosition(self):
		position = self.archiveFile.tell()
		if position % longRepresentationLength:
			raise PointrelException("archive corrupt -- not aligned on %s byte boundary" % longRepresentationLength)
		return position

	# ensures data four byte boundary aligned
	def seekLastPosition(self):
		self.archiveFile.seek(0, 2)
		position = self.archiveFile.tell()
		if position % longRepresentationLength:
			raise PointrelException("archive corrupt -- not aligned on %s byte boundary" % longRepresentationLength)
		return position

	################### recovery file ####################
	
	# question -- is it always OK to assume in recovery file if length of record is OK that data was written correctly?
	def recoverFromFailedTransactionIfNeeded(self, abandoning=0):
		if self.archiveFile:
			raise PointrelException("should not have open archive file when call recoverFromFailedTransactionIfNeeded")
		if not os.path.exists(self.archiveName + Constants.recoveryFileExtension):
			return
		try:
			recoveryFile = open(self.archiveName + Constants.recoveryFileExtension, "r+b")
			#print>> debugFile, "recovery file exists..."
			#print>> debugFile, "should recover here"
			header = recoveryFile.read(len(Constants.recoveryFileHeader))
			if header <> Constants.recoveryFileHeader:
				raise PointrelException("recovery file header was not as expected:" + header)
			binaryRepresentation = recoveryFile.read(2 * longRepresentationLength)
			if len(binaryRepresentation) <> 2 * longRepresentationLength:
				#print>> debugFile, "recovery file header incomplete"
				#print>> debugFile, "transaction probably made no archive changes"
				pass
			else:
				print>> debugFile, "recovery in progress"
				self.archiveFile = self.openFileForWriting()
				
				tuple = struct.unpack("!QQ", binaryRepresentation)
				recoveryCheckPointFileSize, recoveryCheckPointLastTuple = tuple
				
				#loop while have complete records
				# assume a partial record indicates a failure before archive itself was modified
				i = 0
				while 1:
					binaryRepresentation = recoveryFile.read(longRepresentationLength)
					if len(binaryRepresentation) <> longRepresentationLength:
						break
					tuple = struct.unpack("!Q", binaryRepresentation)
					locationInArchiveFile = tuple[0]
					record = StringIndexRecord(locationInArchiveFile, None, 1)
					binaryRepresentation = recoveryFile.read(StringIndexRecord.representationLength)
					if len(binaryRepresentation) <> StringIndexRecord.representationLength:
						break
					record.unpackRepresentation(binaryRepresentation)
					#print>> debugFile, "about to reset string record for archive"
					record.write(self.archiveFile)
					i = i + 1
				print>> debugFile, "updated %s string records" % (i)
				print>> debugFile, "about to update archive length"
				self.writeLastTupleUsedPosition(recoveryCheckPointLastTuple)
				# probably should replace this truncate with a scheme for using extra allocated file space
				# by storing a file length used indicator in header
				# since not all platforms may support truncate
				self.archiveFile.truncate(recoveryCheckPointFileSize)
				self.archiveFile.flush()
				self.archiveFile.close()
				self.archiveFile = None
				self.writeRecoveryToLogFile(abandoning)
				print>> debugFile, "recovery done"
			#assume as of now archive file is in consistent state on media
			# now can delete or truncate recovery file
			recoveryFile.close()
			self.removeRecoveryFile()
		except IOError, error:
			#print>> debugFile, "recovery file does not exist -- proceed normally"
			pass
		#if somehow called when have been saving strings and this function called for abandon -- 
		#reset the string which were previously stored
		self.recoveryStringsStored = {}

	def startRecoveryFile(self):
		recoveryFile = open(self.archiveName + Constants.recoveryFileExtension, "w+b")
		self.recoveryStringsStored = {}
		# read this first so move from begin of file to end
		self.recoveryCheckPointLastTuple = self.readLastTupleUsedPosition()
		#seek to end to find size
		self.recoveryCheckPointFileSize = self.seekLastPosition()
		# write initial archive file length and the last tuple position
		recoveryFile.write(Constants.recoveryFileHeader)
		binaryRepresentation = struct.pack("!QQ", self.recoveryCheckPointFileSize, self.recoveryCheckPointLastTuple)
		recoveryFile.write(binaryRepresentation)
		recoveryFile.flush()
		recoveryFile.close()
		#print>> debugFile, "started recovery file -- old length %d -- old last tuple %d" % (self.recoveryCheckPointFileSize, self.recoveryCheckPointLastTuple)
		
	def appendStringRecordToRecoveryFileIfFirstTimeUpdated(self, stringRecord):
		#don't do strings that are new
		if stringRecord.locationInArchiveFile >= self.recoveryCheckPointFileSize:
			return
		if self.recoveryStringsStored.has_key(stringRecord.locationInArchiveFile):
			return
		recoveryFile = open(self.archiveName + Constants.recoveryFileExtension, "r+b")
		recoveryFile.seek(0, 2)
		binaryRepresentation = struct.pack("!Q", stringRecord.locationInArchiveFile)
		recoveryFile.write(binaryRepresentation)
		binaryRepresentation = stringRecord.packRepresentationForWriting()
		recoveryFile.write(binaryRepresentation)
		recoveryFile.flush()
		recoveryFile.close()
		self.recoveryStringsStored[stringRecord.locationInArchiveFile] = 1
		#print>> debugFile, "stored string header in recovery file", stringRecord.locationInArchiveFile

	def removeRecoveryFile(self):
		if os.path.exists(self.archiveName + Constants.recoveryFileExtension):
			os.remove(self.archiveName + Constants.recoveryFileExtension)
		# or could just set size to the  header instead of removing
		#recoveryFile = open(self.archiveName + Constants.recoveryFileExtension, "w+b")
		#recoveryFile.write(Constants.recoveryFileHeader)
		#recoveryFile.flush()
		#recoveryFile.close()
		
	#returns end location
	def seekToEndAndWriteTransactionHeaderIfNeeded(self):
		location = self.seekLastPosition()
		if not self.writtenTransactionHeaderToArchive:
			#print>> debugFile, "writing trans start"
			# transactionStartWord includes padding for four bytes of end location
			self.archiveFile.write(self.transactionStartWord)
			binaryRepresentation = struct.pack("!QQ", 0, self.transactionTime())
			self.archiveFile.write(binaryRepresentation)
			self.archiveFile.flush()
			self.writtenTransactionHeaderToArchive = location
			location = self.currentPosition()
		return location
		
	################### string handling ##################
	
	def readStringIndexRecord(self, location):
		record = StringIndexRecord(location, None, 1)
		record.readHeader(self.archiveFile)
		return record
		
	def addStringIndexRecord(self, string):
		location = self.seekToEndAndWriteTransactionHeaderIfNeeded()
		record = StringIndexRecord(location, string)
		record.write(self.archiveFile)
		return record
		
	def addOrFindStringRecord(self, string, readOnlyFlag = 0):
		#print>> debugFile, "search string for:", string
		if not readOnlyFlag:
			self.refreshLockFileIfNeeded()
		self.checkOpen()
		
		if Options.caching:
			try:
				if self.stringCache.has_key(string):
					location = self.stringCache[string]
					return self.readStringIndexRecord(location)
			except TypeError, e:
				# may generate type error if object not hashable
				pass
		#skip first section so can reserve zero to mean final link and also skip transaction header
		location = Constants.archiveHeaderSize + len(self.transactionStartWord) + 2 * longRepresentationLength
		currentIndexRecord = None
		comparison = 0
		
		temporaryStringObject = StringIndexRecord(0, string)
		#stringHash = zlib.crc32(string)
		#pathLength = 0
		fileSize = self.seekLastPosition()
		if fileSize > location:
			while location:
				#print>> debugFile, "searching string at location", location
				#pathLength = pathLength + 1
				currentIndexRecord = self.readStringIndexRecord(location)
				comparison = currentIndexRecord.compare(self.archiveFile, temporaryStringObject)
				#print>> debugFile, comparison
				#doesn't seem to help much to cache intermediate results -- forces string load from disk
				if comparison == 0:
					if Options.caching:
						try:
							self.stringCache[string] = location
						except TypeError, e:
							# may generate type error if object not hashable
							pass
						self.positionCache[location] = string
					#print>> debugFile, "foundrecord", currentIndexRecord
					return currentIndexRecord
				elif comparison < 0:
					location = currentIndexRecord.lessThanLink
				else:
					location = currentIndexRecord.greaterThanLink
			
		#must not be there
		if readOnlyFlag:
			return None
			
		# add at end and update record
		#print>> debugFile, "adding path length: ", pathLength
		newRecord = self.addStringIndexRecord(string)
		if Options.caching:
			try:
				self.stringCache[string] = newRecord.locationInArchiveFile
			except TypeError, e:
				# may generate type error if object not hashable
				pass
			self.positionCache[newRecord.locationInArchiveFile] = string
			#print>> debugFile, "added: ", string
			#print>> debugFile, "at:", newRecordLocation
		if currentIndexRecord:
			self.appendStringRecordToRecoveryFileIfFirstTimeUpdated(currentIndexRecord)
			currentIndexRecord.setLink(comparison, newRecord.locationInArchiveFile)
			currentIndexRecord.write(self.archiveFile)

		#print>> debugFile, "newrecord", newRecord

		return newRecord

	def addOrFindStringIndex(self, string, readOnlyFlag = 0):
		if Options.caching:
			if self.stringCache.has_key(string):
				return self.stringCache[string]

		record = self.addOrFindStringRecord(string, readOnlyFlag)
		if readOnlyFlag and (not record):
			return 0
		location = record.locationInArchiveFile
		if Options.caching:
			self.positionCache[location] = string
		return location
		
	def findStringIndex(self, string):
		return self.addOrFindStringIndex(string, 1)

	def stringForIndex(self, location):
		if Options.caching:
			if self.positionCache.has_key(location):
				return self.positionCache[location]
		record = self.readStringIndexRecord(location)
		#string = record.readString(self.archiveFile)
		string = record.retrieveObject(self.archiveFile)
		if Options.caching:
			self.positionCache[location] = string
		return string

	def stringRecordForIndex(self, location):
		record = self.readStringIndexRecord(location)
		return record

	############### tuple handling #####################
	
	def writeLastTupleUsedPosition(self, position):
		#print>> debugFile, "write last", position
		self.archiveFile.seek(Constants.archiveLastTriadUsedPosition)
		binaryRepresentation = struct.pack("!Q", position)
		self.archiveFile.write(binaryRepresentation)
		
	def readLastTupleUsedPosition(self):
		self.archiveFile.seek(Constants.archiveLastTriadUsedPosition)
		binaryRepresentation = self.archiveFile.read(longRepresentationLength)
		result = struct.unpack("!Q", binaryRepresentation)
		#print>> debugFile, "read last", result[0]
		return result[0]
				
	def readTupleIndexRecord(self, location):
		record = TupleIndexRecord(location)
		record.read(self.archiveFile)
		return record
		
	def addTupleIndexRecord(self, stringLocations, previousUsers, previousTupleLocation):
		location = self.seekToEndAndWriteTransactionHeaderIfNeeded()
		record = TupleIndexRecord(location, previousTupleLocation)
		record.strings = stringLocations
		record.previousUsers = previousUsers
		record.write(self.archiveFile)
		return record
		
	def addTupleWithoutLogging(self, tuple):
		if len(tuple) <> 4:
			raise PointrelException("Tuple length must be four")
		self.refreshLockFileIfNeeded()
			
		stringLocations = []
		previousUsers = []
		
		self.checkOpen()
		
		previousTupleLocation = self.readLastTupleUsedPosition()
		
		#find strings so written before tuple
		index = 0
		for string in tuple:
			stringIndexRecord = self.addOrFindStringRecord(string)
			stringLocations.append(stringIndexRecord.locationInArchiveFile)
			previousUsers.append(stringIndexRecord.lastUsers[index])
			index = index + 1
		
		#add new tuple records
		newTupleRecord = self.addTupleIndexRecord(stringLocations, previousUsers, previousTupleLocation)
		self.writeLastTupleUsedPosition(newTupleRecord.locationInArchiveFile)

		#update strings for new tuple
		index = 0
		for string in tuple:
			stringIndexRecord = self.stringRecordForIndex(stringLocations[index])
			self.appendStringRecordToRecoveryFileIfFirstTimeUpdated(stringIndexRecord)
			stringIndexRecord.updateLastUser(index, newTupleRecord.locationInArchiveFile)
			stringIndexRecord.write(self.archiveFile)
			index = index + 1

		return newTupleRecord.locationInArchiveFile
			
	def stringsForLocation(self, location):
		record = self.readTupleIndexRecord(location)
		return (self.stringForIndex(record.strings[0]), 
				self.stringForIndex(record.strings[1]),
				self.stringForIndex(record.strings[2]),
				self.stringForIndex(record.strings[3]))

	#returns a locvation in index file caller can load a record from
	def nextToSearch(self, previousRecord, indexedTemplate):
		#really should store searching strategy after initial evaluation...
		# especially if want to allow multiple fields to matchdef nextToSearch(self, previous, indexedTemplate)
		# if zero, assume starting out
		self.refreshLockFileIfNeeded()
		if (previousRecord == None):
			# heuristic -- since don't save counts -- obsolete -- as do -- but not fixed yet
			if (0 <> indexedTemplate[1]):
				stringRecord = self.stringRecordForIndex(indexedTemplate[1])
				return stringRecord.lastUsers[1]
			elif (0 <>  indexedTemplate[3]):
				stringRecord = self.stringRecordForIndex(indexedTemplate[3])
				return stringRecord.lastUsers[3]
			elif (0 <>  indexedTemplate[2]):
				stringRecord = self.stringRecordForIndex(indexedTemplate[2])
				return stringRecord.lastUsers[2]
			# check if only one context to search on
			elif (0 <>  indexedTemplate[0]):
				stringRecord = self.stringRecordForIndex(indexedTemplate[0])
				return stringRecord.lastUsers[0]
			# check for pathalogical case -- nothing to search on -- when using filters -- skip for now
			#elif ??????????????????????:
			#	return 0
			# otherwise hard case of multiple search contexts and no specifics
			# just search everything
			else:
				return self.readLastTupleUsedPosition()
		else:
			# proceed through indexes
			# somethat similar to section of above except going through prior rather than last_user
			# heuristic -- since don't save counts 
			if (0 <> indexedTemplate[1]):
				return previousRecord.previousUsers[1]
			elif (0 <> indexedTemplate[3]):
				return previousRecord.previousUsers[3]
			elif (0 <> indexedTemplate[2]):
				return previousRecord.previousUsers[2]
			# check if only one context to search on
			elif (0 <> indexedTemplate[0]):
				return previousRecord.previousUsers[0]
			# check for pathalogical case -- nothing to search on -- not done now
			#elif (??????):
			#	return 0
			# otherwise hard case of multiple search contexts and no specifics
			# just search everything
			else:
				return previousRecord.previousTupleLocation

	def findSeparatorForTuple(self, tupleOfStrings):
		separarator = ""
		while 1:
			separarator = separarator + "|"
			ok = 1
			for i in range(4):
				if string.count(tupleOfStrings[i], separarator) > 0:
					ok = 0
			if ok:
				return separarator

	########### logging ####################
	def writeStartOfLogFile(self):
		f = open(self.archiveName + Constants.logFileExtension, "w+b")
		f.write(Constants.logFileHeader % self.uniqueArchiveID)
		return f
		
	# transactions may not be nested -- so if the are, indicates a failed transaction
	def writeRecoveryToLogFile(self, abandoning=0):
		if not self.logging:
			return
		try:
			f = open(self.archiveName + Constants.logFileExtension, "r+b")
			f.seek(0, 2)
		except IOError, error:
			f = self.writeStartOfLogFile()
			
		if abandoning:
			f.write("\t<P:abandon/></P:transaction>\n")
		else:
			f.write("\t<P:recovery/></P:transaction>\n")
		f.flush()
		f.close()
		
	def writeTransactionStartToLogFile(self):
		if not self.logging:
			return
		try:
			f = open(self.archiveName + Constants.logFileExtension, "r+b")
			# f.seek(0, 2)
			trailer = "</P:archive>\n"
			f.seek(-len(trailer), 2)
			if f.read(len(trailer)) <> trailer:
				print>> debugFile, "ERROR IN TRAILER AT END OF LOG FILE"
				print>> debugFile, "PROBABLY DUE TO FAILED TRANSACTION"
			else:
				f.seek(-len(trailer), 2)
				# write over it...
			
		except IOError, error:
			f = self.writeStartOfLogFile()
			
		f.write("\t<P:transaction>\n")
		f.flush()
		f.close()

	def writeTransactionEndToLogFile(self):
		if not self.logging:
			return
		try:
			f = open(self.archiveName + Constants.logFileExtension, "r+b")
			f.seek(0, 2)
		except IOError, error:
			f = self.writeStartOfLogFile()
	
		f.write("\t</P:transaction>\n</P:archive>\n")
		# does it need to write out a count value?
		f.flush()
		f.close()

	def writeTupleToLogFile(self, tupleOfStrings, position):
		if not self.logging:
			return
			
		#optimization to only modify log file only if at least one tuple being written
		if not self.writtenTransactionHeaderToLog:
			self.writeTransactionStartToLogFile()
			self.writtenTransactionHeaderToLog = 1

		#separator = self.findSeparatorForTuple(tupleOfStrings)

		try:
			f = open(self.archiveName + Constants.logFileExtension, "r+b")
			f.seek(0, 2)
		except IOError, error:
			f = self.writeStartOfLogFile()

		#f = open(self.archiveName + Constants.logFileExtension, "ab")

		start = f.tell()
		
		output = cStringIO.StringIO()
		
		#write byte of space to use for flags
		# I don't understnad why this is needed
		# output.write(" ")
		
		
		hexEncoded = ""
		sRecord = StringIndexRecord(0, tupleOfStrings[0])		
		aRecord = StringIndexRecord(0, tupleOfStrings[1])
		bRecord = StringIndexRecord(0, tupleOfStrings[2])
		cRecord = StringIndexRecord(0, tupleOfStrings[3])
		
		sType, sString = sRecord.xmlTypeCharacterAndEncodedString()
		aType, aString = aRecord.xmlTypeCharacterAndEncodedString()
		bType, bString = bRecord.xmlTypeCharacterAndEncodedString()
		cType, cString = cRecord.xmlTypeCharacterAndEncodedString()
		
		encodingTypes = sType + aType + bType + cType
		
		output.write("\t\t<P:triad\n")
		output.write("\t\t\tr=")
		output.write(xml.sax.saxutils.quoteattr(`position`))
		if encodingTypes <> "bbbb":
			output.write("\n\t\t\ttypes=")
			output.write(xml.sax.saxutils.quoteattr(encodingTypes))
		output.write("\n\t\t\ts=")
		output.write(xml.sax.saxutils.quoteattr(sString))
		output.write("\n\t\t\ta=")
		output.write(xml.sax.saxutils.quoteattr(aString))
		output.write("\n\t\t\tb=")
		output.write(xml.sax.saxutils.quoteattr(bString))
		output.write("\n\t\t\tc=")
		output.write(xml.sax.saxutils.quoteattr(cString))
		output.write("\n\t\t/>\n")
		
		#write out as one call and hope to minimize failing in the middle --  not essential but nice
		f.write(output.getvalue())
		f.flush()
		f.close()
		
		return start
		
	##### useful for importing ############
	
	def seekToFirstRecord(self):
		self.archiveFile.seek(Constants.archiveHeaderSize)
				
	def readNextTupleRecord(self):
		tupleRecord = None
		#print>> debugFile, "readNextTupleRecord"
		while 1:
			#print>> debugFile, "loop"
			position = self.archiveFile.tell()
			#print>> debugFile, "pos", position
			headerType = self.archiveFile.read(longRepresentationLength)
			if len(headerType) <> longRepresentationLength:
				#print>> debugFile, "EOF"
				break
			self.archiveFile.seek(-longRepresentationLength, 1)
			type,  = struct.unpack("!Q", headerType)
			#print>> debugFile, "type", type
			if type == StringIndexRecord.headerWord:
				#print>> debugFile, "string"
				stringRecord = StringIndexRecord(position, None, 1)
				stringRecord.readStringAndAlignmentBytes(self.archiveFile)
			elif type == TupleIndexRecord.headerWord:
				#print>> debugFile, "tuple"
				tupleRecord = TupleIndexRecord(position)
				tupleRecord.read(self.archiveFile)
				break
			elif headerType == PointrelArchive.transactionFinishWord:
				#print>> debugFile, "finish transaction"
				self.archiveFile.read(2 * longRepresentationLength)
			elif headerType == PointrelArchive.transactionStartWord[:longRepresentationLength]:
				#print>> debugFile, "start transaction"
				self.archiveFile.read(2 * longRepresentationLength)
			else:
				print>> debugFile, "    %x" %(type), `headerType`
				raise PointrelException("Potentially corrupt archive -- unexpected record")
		#print>> debugFile, "out"
		return tupleRecord
	
	############### typical internal api ##################
	
	# return a matching triad in this archive
	# starts at a previous triad record so can call multiple times to get all matches
	# call with previous of None to search from the end of all triads 
	# returns None if no match at end
	# template is assumed to contain index references and not strings
	def searchForIndexedTemplate(self, previousRecord, indexedTemplate):
		#print>> debugFile, "search start"
		current = self.nextToSearch(previousRecord, indexedTemplate)
		
		while (current != 0) :
			#print>> debugFile, "search", current
			currentRecord = self.readTupleIndexRecord(current)
			# check for match, which includes looking at filter
			if (currentRecord.isIndexedMatch(indexedTemplate)):
				return currentRecord
				
			# otherwise move to next node
			current = self.nextToSearch(currentRecord, indexedTemplate)
		
		return None

	def add(self, tupleOfStrings):
		#changed the order of these so could record tuple position in log
		#this means binary file may be slighly different than (ahead of) log in a crash
		
		#update indexes
		tupleIndex = self.addTupleWithoutLogging(tupleOfStrings)
		
		#write to log file
		logLocation = self.writeTupleToLogFile(tupleOfStrings, tupleIndex)
		
		return tupleIndex

	# return None if a component string can't be found
	def makeIndexedTemplate(self, template):
		result = []
		for element in template:
			if element == WILD:
				result.append(0)
			else:
				match = self.findStringIndex(element)
				if not match:
					return None
				result.append(match)
		return tuple(result)
		
	def stringsForTupleRecord(self, record):
		return (self.stringForIndex(record.strings[0]), 
				self.stringForIndex(record.strings[1]),
				self.stringForIndex(record.strings[2]),
				self.stringForIndex(record.strings[3]))

	def stringForTupleRecordField(self, record, field):
		return self.stringForIndex(record.strings[field])

def testPointrelArchive():
	pa = PointrelArchive()
	tupleIndex = pa.add(("test", "hello", "there", "world"))
	print tupleIndex
	print pa.stringsForLocation(tupleIndex)
#testPointrelArchive()

def testBinaryTreeIndex():
	a = PointrelArchive()
	a.open()
	print a.addOrFindStringIndex("foo")
	print a.addOrFindStringIndex("bar\0")
	print a.addOrFindStringIndex("baz\0")
	print a.addOrFindStringIndex("foo")
	print a.addOrFindStringIndex("baz")
	print a.addOrFindStringIndex("bazzoo")
	print a.addOrFindStringIndex("baz\0")
	print a.addOrFindStringIndex("bar")
	print a.addOrFindStringIndex("bar\0")
	print a.addOrFindStringIndex("bazzoo")
	a.close()
#testBinaryTreeIndex()

class PointrelDataRepositorySystem:
	def __init__(self, archiveName = Constants.defaultArchiveName, logging = Options.defaultLogging):
		self.archiveForAdding = archiveName
		self.activeArchives = [archiveName]
		self.archiveCache = {}
		self.transactionLevel = 0
		self.logging = logging
		self.allowNestedTransactions = 0
		
	def isInTransaction(self):
		return self.transactionLevel > 0
		
	def failIfNotInTransaction(self):
		if self.transactionLevel < 1:
			raise PointrelException("Error: not in transaction")
			
	### archive control user API ############
	
	# starts a new transaction -- may be nested
	def startTransaction(self, allowNestedTransactions = 0):
		if not allowNestedTransactions and self.transactionLevel > 0:
			raise PointrelException("nested transacitons not allowed without flag set")
		if not self.allowNestedTransactions:
			self.allowNestedTransactions = allowNestedTransactions
		if self.transactionLevel == 0:
			for archiveName in self.activeArchives:
				self.archiveForName(archiveName).startTransaction()
		self.transactionLevel = self.transactionLevel + 1
	
	# ends a transaction, but does not commit if nested until top one finishes
	def finishTransaction(self):
		self.transactionLevel = self.transactionLevel - 1
		if self.transactionLevel == 0:
			for archiveName in self.activeArchives:
				self.archiveForName(archiveName).finishTransaction()
			self.allowNestedTransactions = 0
		if self.transactionLevel < 0:
			self.transactionLevel = 0
			raise PointrelException("Error: too many end transactions")
		
	def abandonTransaction(self):
		if self.transactionLevel > 0:
			for archiveName in self.activeArchives:
				self.archiveForName(archiveName).abandonTransaction()
			self.transactionLevel = 0
			self.allowNestedTransactions = 0
		else:
			raise PointrelException("not in transaction")

	# call this in a "finally" after a transaction if want to ensure things are cleaned up if user coding error
	def cleanUpIfUnfinishedTransaction(self):
		if self.transactionLevel > 0:
			self.abandonTransaction()

	### functions for allowing more than one archive to be active so all are searched ###
	def setArchiveForAdding(self, archiveName):
		self.archiveForAdding = archiveName
		
	def removeFromActive(self, archiveName):
		self.activeArchives.remove(archiveName)
		
	def addToActive(self, archiveName):
		self.activeArchives.append(archiveName)
	
	def insertToActive(self, location, archiveName):
		self.activeArchives.insert(location, archiveName)
		
	### support functions #######

	def archiveForName(self, archiveName):
		if self.archiveCache.has_key(archiveName):
			return self.archiveCache[archiveName]
		
		result = PointrelArchive(archiveName, self.logging)		
		self.archiveCache[archiveName] = result
		return result
		
	def lastMatchTuple(self, template, selection=None):
		if len(template) <> 4:
			raise PointrelException("Tuple length must be four")
		result = None
		for archiveName in self.activeArchives:
			archive = self.archiveForName(archiveName)
			if not self.isInTransaction():
				if not archive.startUsingReadOnly():
					continue
			#need to index template for each file as string ids are file specific
			indexedTemplate = archive.makeIndexedTemplate(template)

			#if indexedTemplate is None, one or more strings were not matched, so can not have any matching tuples
			if indexedTemplate:
				tupleIndexRecord = archive.searchForIndexedTemplate(None, indexedTemplate)
				if tupleIndexRecord:
					if selection == None:
						result = archive.stringsForTupleRecord(tupleIndexRecord)
					else:
						result = archive.stringForTupleRecordField(tupleIndexRecord, selection)
			if not self.isInTransaction():
				archive.finishUsingReadOnly()
			if result:
				break
		return result	

	#return a list of all matches, from oldest to newest 
	def allMatchesTuple(self, template, selection=None):
		if len(template) <> 4:
			raise PointrelException("Tuple length must be four")
		matches = []
		for archiveName in self.activeArchives:
			archive = self.archiveForName(archiveName)
			if not self.isInTransaction():
				if not archive.startUsingReadOnly():
					continue
			#need to index template for each file as string ids are file specific
			indexedTemplate = archive.makeIndexedTemplate(template)

			#if indexedTemplate is None, one or more strings were not matched, so can not have any matching tuples
			if indexedTemplate:
				tupleIndexRecord = archive.searchForIndexedTemplate(None, indexedTemplate)
	
				while tupleIndexRecord:
					if selection == None:
						matches.append(archive.stringsForTupleRecord(tupleIndexRecord))
					else:
						matches.append(archive.stringForTupleRecordField(tupleIndexRecord, selection))
					tupleIndexRecord = archive.searchForIndexedTemplate(tupleIndexRecord, indexedTemplate)
			if not self.isInTransaction():
				archive.finishUsingReadOnly()
		# reverse the list so goes oldest to most recent
		# in practive most callers desire this behavior
		if matches:
			matches.reverse()
		return matches
 
	def addTuple(self, tuple):
		if len(tuple) <> 4:
			raise PointrelException("Tuple length must be four")
		self.failIfNotInTransaction()
		archive = self.archiveForName(self.archiveForAdding)
		tupleIndex = archive.add(tuple)
		#value is meaningless outside of knowing what archive it is in
		return tupleIndex
		
	# add if last match for last value is different
	def addIfNeededForLastValueTuple(self, tuple):
		if len(tuple) <> 4:
			raise PointrelException("Tuple length must be four")
		searchTuple = (tuple[0], tuple[1], tuple[2], WILD)
		lastMatch = self.lastMatchTuple(searchTuple)
		if lastMatch <> tuple:
			self.addTuple(tuple)

	# return last match or a tuple with empty strings
	def lastMatchOrEmptyTuple(self, tuple):
		result = self.lastMatchTuple(tuple)
		if not result:
			result = ("", "", "", "")
		return result
		
	def wildcardAnalysis(self, tuple):
		lastWildCard = -1
		wildCardCount = 0
		for i in range(len(tuple)):
			if tuple[i] == WILD:
				lastWildCard = i
				wildCardCount = wildCardCount + 1
		return (lastWildCard, wildCardCount)
		
	#defining this myself to allow support for Python 1.5.1
	def abspath(self, filename):
		#good enough for optional test
		if "abspath" in dir(os.path):
			return os.path.normcase(os.path.abspath(filename))
		else:
			return os.path.normcase(os.path.normpath(os.path.join(os.getcwd(), filename)))
	#print>> debugFile, abspath("foo")
		
	### common user API ############
	
	# must be in a tranascation to add
	# here is the recommended example:
	#
	# repository.startTransaction()
	# try:
	#    repository.add("context", "a", "b", "c")
	#    repository.finishTransaction()
	# finally:
	#    repository.cleanUpIfFailedTransaction()
	#
	# the try--finally and cleanup call is not strictly needed as archive will clean up itself the next time used for a transaction
	# however, it also handles some issues related to abandoning nested transactions
	# and will immediately do an abandon / recover to keep the archive in a consistent state
	
	# add a tuple
	def add(self, context, a, b, c):
		return self.addTuple((context, a, b, c))

	# if no wildcards, return exact tuple if present or None
	# a wildcard is WILD
	# will return wildcard field for single wildcard
	# if multiple wildcards, returns entire tuple
	# if return choice is None, returns entire tuple always
	# if return choice is 0-3, returns specified field always (not very useful)
	# does not need to be in a transaction to search
	def lastMatch(self, context, a, b, c, returnChoice=-1):
		tuple = (context, a, b, c)
		lastWildCard, wildCardCount = self.wildcardAnalysis(tuple)
		if wildCardCount == 0:
			selection = None
		elif wildCardCount == 1:
			selection = lastWildCard
		else:
			selection = None
		if returnChoice <> -1:
			selection = returnChoice
		return self.lastMatchTuple(tuple, selection)

	# if no wildcards, return all exact tuples or None
	# a wildcard is WILD
	# will return list of wildcard fields for single wildcard
	# if multiple wildcards, returns list of entire tuples
	# if return choice is None, returns list of entire tuples always
	# if return choice is 0-3, returns list of specified field always (not very useful)
	# does not need to be in a transaction to search
	# result list will be ordered from earliest to latest
	def allMatches(self, context, a, b, c, returnChoice=-1):
		tuple = (context, a, b, c)
		lastWildCard, wildCardCount = self.wildcardAnalysis(tuple)
		if wildCardCount == 0:
			selection = None
		elif wildCardCount == 1:
			selection = lastWildCard
		else:
			selection = None
		if returnChoice <> -1:
			selection = returnChoice
		return self.allMatchesTuple(tuple, selection)

	##########  convenience functions ###################
	
	# add if last match for last value is different
	def addIfNeededForLastValue(self, context, a, b, c):
		self.addIfNeededForLastValueTuple((context, a, b, c))

	# return entire last match tuple or a tuple with empty strings
	def lastMatchOrEmpty(self, context, a, b, c):
		return self.lastMatchOrEmptyTuple((context, a, b, c))
		
	# import one tuple at a time sequentially from import archive
	# reduces memory useage by not reading entire archive into memory as tuples
	def importArchive(self, archiveName, addTupleOnlyIfNeededForLastValue = 0):
		# might not catch situation if change current directory after open archive for writing
		if self.abspath(archiveName) == self.abspath(self.archiveForAdding):
			raise PointrelException("importArchive: can not import an archive into itself: " + self.abspath(archiveName))
		importArchive = PointrelArchive(archiveName)
		if importArchive.startUsingReadOnly():
			try:
				importArchive.seekToFirstRecord()
				while 1:
					tupleRecord = importArchive.readNextTupleRecord()
					if not tupleRecord:
						break
					# save and trestore position since altered by looking up strings
					oldPosition = importArchive.archiveFile.tell()
					tuple = importArchive.stringsForTupleRecord(tupleRecord)
					importArchive.archiveFile.seek(oldPosition)
					#print>> debugFile, tuple
					if addTupleOnlyIfNeededForLastValue:
						self.addIfNeededForLastValueTuple(tuple)
					else:
						self.addTuple(tuple)			
			finally:
				importArchive.finishUsingReadOnly()

	def globalTimestamp(self):
		return GlobalTimestamp()
	
	def generateUniqueID(self):
		return GenerateUniqueID()

# support functions

def GlobalTimestamp():
	return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(time.time()))

def GenerateUniqueID():
	#this is seeded by the time when loaded...
	#so other machine starting at same time will be synchronized
	number = random.random()
	numberString = `number`
	#print>> debugFile, numberString
	discard, randomString = string.split(numberString, ".")
	if Options.uniqueIdCounterReadFromFile:
		try:
			try:
				f = open(".hiddenG95ht/a_pointrel_uniqueIDCounter.txt", "r+")
				f.seek(0, 0)
				contents = f.read()
				if contents:
					Options.uniqueIdCounter = string.atoi(contents)
					#print>> debugFile,  "read uniqueID ", Options.uniqueIdCounter
				Options.uniqueIdCounter = Options.uniqueIdCounter + 1
			except:
				f = open(".hiddenG95ht/a_pointrel_uniqueIDCounter.txt", "w")
			f.seek(0, 0)
			f.write(`Options.uniqueIdCounter`)
			f.close()
		except Exception, e:
			Options.uniqueIdCounter = Options.uniqueIdCounter + 1
	else:
		Options.uniqueIdCounter = Options.uniqueIdCounter + 1
	return Options.uniqueIdPrefix + Options.uniqueLocalValue + ":" + `Options.uniqueIdCounter` + ":" + randomString

# This function checks that a binary archive is properly structured
# This code needs to be in agreement with the rest of the code
# in terms of the assumptions it makes abotu a binary archives structure
def PerformIntegrityCheckOnArchive(archiveName=Constants.defaultArchiveName):
	
	### check recovery file
	
	try:
		recovery = open(archiveName + Constants.recoveryFileExtension, "rb").read()
		print "recovery length", len(recovery)
		if len(recovery) <> len(Constants.recoveryFileHeader):
			raise PointrelException("recovery file has contents -- run recovery first")
		else:
			print "recovery file OK"
	except:
		print "no recovery file"
	
	### check some data
	
	archive = PointrelArchive(archiveName, 0)
	archive.archiveFile = archive.openFileForReading()
	
	archive.archiveFile.seek(0,2)
	archiveSize = archive.archiveFile.tell()
	
	print "archiveLastTriadUsed", archive.readLastTupleUsedPosition()
		
	print "about to read all records"
	
	archive.archiveFile.seek(Constants.archiveHeaderSize)
	transactionCount = 0
	while 1:
		transactionCount = transactionCount + 1
		transactionStartPosition = archive.archiveFile.tell()
		transactionData = archive.archiveFile.read(2 * longRepresentationLength)
		if len(transactionData) == 0: 
			print "reached end of file"
			break
		print "transactionCount", transactionCount
		print "transactionStartPosition", transactionStartPosition
		if len(transactionData) <> 2 * longRepresentationLength:
			print "len(transactionData)", len(transactionData)
			raise PointrelException("corrupt start transaction header")
		signature, transactionEndPosition = struct.unpack("!QQ", transactionData)
		if transactionData[:longRepresentationLength] <> PointrelArchive.transactionStartWord[:longRepresentationLength]:
			raise PointrelException("transaction start signature incorrect")
		print "transactionEndPosition from start header", transactionEndPosition
		archive.archiveFile.seek(transactionEndPosition)
		transactionData = archive.archiveFile.read(2 * longRepresentationLength)
		if len(transactionData) == 0: 
			raise PointrelException("no end transaction")
		if len(transactionData) <> 2 * longRepresentationLength:
			raise PointrelException("corrupt end transaction header")
		signature, transactionStartPositionRead = struct.unpack("!QQ", transactionData)
		if transactionData[:longRepresentationLength] <> PointrelArchive.transactionFinishWord:
			raise PointrelException("transaction end signature incorrect")
		if transactionStartPositionRead <> transactionStartPosition:
			raise PointrelException("transaction start position read not same as real start position")
		print "transaction start and end match OK"
		print "reading records in transaction"
		######
		archive.archiveFile.seek(transactionStartPosition + 2 * longRepresentationLength + 2 * longRepresentationLength)
		while 1:
			position = archive.archiveFile.tell()
			print "  reading from:", position
			if position % longRepresentationLength:
				print "archive corrupt -- record not %d byte aligned" % longRepresentationLength
			headerType = archive.archiveFile.read(longRepresentationLength)
			if len(headerType) == 0:
				print "  EOF"
				break
			archive.archiveFile.seek(-longRepresentationLength, 1)
			type,  = struct.unpack("!Q", headerType)
			if type == StringIndexRecord.headerWord:
				print "    string record",
				stringRecord = StringIndexRecord(position, None, 1)
				stringRecord.readString(archive.archiveFile)
				align = stringRecord.dataStringLengthOnMedia % longRepresentationLength
				padding = archive.archiveFile.read(len(Constants.alignmentBytes[align]))
				value = "  contents: '" + stringRecord.dataString + "'"
				#print value.encode('ascii', 'replace')
				print repr(value)
				print "  ", stringRecord.lessThanLink, stringRecord.greaterThanLink, stringRecord.lastUsers, stringRecord.useCount, stringRecord.flags
				if padding <> Constants.alignmentBytes[align]:
					print "padding: '%s'" % (padding)
					print ord(padding[-1])
					print "alignmentBytes[align]: '%s'" % (Constants.alignmentBytes[align])
					print "align: '%d'" % (align)
					raise PointrelException("alignment bytes not as expected")
				if stringRecord.lessThanLink > archiveSize:
					raise PointrelException("archive corrupt -- lessThanLink link beyond EOF")
				if stringRecord.greaterThanLink > archiveSize:
					raise PointrelException("archive corrupt -- greaterThanLink link beyond EOF")
				for link in stringRecord.lastUsers:
					if link > archiveSize:
						raise PointrelException("archive corrupt -- lastUsers link %d beyond EOF" % (link))
			elif type == TupleIndexRecord.headerWord:
				print "    tuple record", 
				tupleRecord = TupleIndexRecord(position)
				tupleRecord.read(archive.archiveFile)
				print tupleRecord.strings, tupleRecord.previousUsers, tupleRecord.previousTupleLocation
			elif headerType == PointrelArchive.transactionFinishWord:
				print "  read end transaction"
				archive.archiveFile.read(2 * longRepresentationLength + 2 * longRepresentationLength )
				break
			else:
				print "    %x" %(type), `headerType`
				raise PointrelException("unexpected record")

def test1():
	Options.ignoreOldLockFiles = 1
	print "testing"
	pdrs = PointrelDataRepositorySystem()
	#pdrs = PointrelDataRepositorySystem(logging=0)
	pdrs.startTransaction()
	#first, unicode handling test
	pdrs.add("test", 'x' + unichr(500) + 'x', 'y' + unichr(2000) + 'y', 'z' + unichr(10000) + 'z')
	#second, non-ASCII
	pdrs.add("test", 'x' + chr(128) + 'x', 'y' + chr(0) + 'y', 'z' + chr(255) + 'z')
	#second, python objects
	pdrs.add("test", 10, ["hello", "goodbye"], PointrelDataRepositorySystem)
	pdrs.add({}, None, test1, dir(PointrelDataRepositorySystem))
	# now test loop
	for i in range(10):
		#print "---------------------- loop", i
		print i
		#print 1
		pdrs.add("test", "hello", "there", "world")
		#print 2
		pdrs.add("test", "goodbye", "there", "world")
		#print 3
		pdrs.add("test", "goodbye", "there", `i`)
		#print 4
		pdrs.allMatches(WILD, "hello", WILD, WILD)
		#print 5
		pdrs.allMatches(WILD, WILD, WILD, "world")
		#print 6
		pdrs.lastMatch(WILD, WILD, WILD, "world")
		#print 7
	pdrs.finishTransaction()
	#pdrs.abandonTransaction()

def test2():
	print "testing"
	for i in range(10):
		print PointrelDataRepositorySystem().generateUniqueID()

if __name__ == '__main__':
	#import profile
	#profile.run("test1()")
	#print "readbytes", Performance.readbytes
	test1()
	test2()
	simpleInterfaceTest()
	print "\n =========== testing binary archive integrity ===================="
	PerformIntegrityCheckOnArchive()
	

#END OF CODE

"""
def rebuildArchiveFromCorruptArchive():
	pass
	# go through archive
	# match start transaction
	# skip through each record, 
	#  find valid end transaction or an invalid record and EOF or a start transaction
	# if no valid end transaction, skip entire section
	# otherwise, for each string or tuple, add to new archive
	# repeat for subsequent transactions
"""

"""
	CODE THAT CAN BE MODIFIED TO REBUILD ARCHIVE FROM LOG
	# does not handle transactions 
	def readAllTuplesFromFile(self, fileName):
		tuples = []
		try:
			f = open(fileName)
		except:
			return tuples
		lines = f.readlines()
		f.close()
		lineIndex = 0
		while lineIndex < len(lines):
			segments = string.split(line, ";", 1)
			separarator = segments[0]
			status = separarator[0]
			separarator = separarator[1:]
			content = segments[1]
			#in case embedded new line, keep appending
			while string.count(content, separarator) < 4:
				lineIndex = lineIndex + 1
				content = content + line
			tupleElements = string.split(content, separarator)
			#discard the last newline
			newTuple = tuple(tupleElements[0:-1])
			tuples.append(newTuple)
			#print>> debugFile, "adding", tuple
			lineIndex = lineIndex + 1
		return tuples
		
	def readNextTuple(self, f):
		line = f.readline()
		if not line:
			return None
		segments = string.split(line, ";", 1)
		separarator = segments[0]
		status = separarator[0]
		separarator = separarator[1:]
		content = segments[1]
		#in case embedded new line, keep appending
		while string.count(content, separarator) < 4:
			content = content + f.readline()
		tupleElements = string.split(content, separarator)
		#discard the last newline
		newTuple = tuple(tupleElements[0:-1])
		return newTuple
		
"""

# ########### NOTES #################################
#another attempt at pointrel -- something simplest -- grew a little in complexity...
# almost intentionally least efficient design
# but does support multiple active contents for reading 
# and specify where things are added
# and added a context field at start -- for dividing up into modules within the file module

# #########################################

# what if just refer to tuples as contents?
# how to store a big thing? 0 0 big
#but then other tuples that refer to it contain it.
#unless refer through a query?
#if put same tuple in twice -- meaningless? [or meaning something in sense of time -- change over time]
#using tuple when mean triad...

#realizing data only meaningful in the context of the running program
#even if that program is essentially just the user and "common sense"
#when accept person and users as part of the information loop, can use more linguistical concepts
# can accept that some user somewhere will know where to start with data
# or will know how to search data to find a place to start or things of use

# to add
# support for regular expressions in search
# progress indicator through long search

#issues -- violating principle of locality
# related data in object not nearby
# really needs an associative memory
# obviously, could build cache? or some other process? some other optimization....

# issue -- no way to reference relationship or even a string
# need to use it as a direct thing -- as a literal 
# need to assume relationships are literals...
# or need to deal with relationships at a higher level as objects not tuples

#questions -- is a file.flush() before a file.close() really needed?

# ##################
# need to think of database as sequence of tuples -- where there is meaning in the sequence?
# but then association is hard in hardware? unless associate with time index as well?
# reason order matters is when defining a current value
# or looking at history of values

# ########################
# probably should store position in log file in tuples...
# especially so can update them if deletion etc.

#perhaps to do
# recovery from log file only
# deleting transactions -- store deletion information as of some file length, to support next item
# support for viewing transactions up to at a point in time
