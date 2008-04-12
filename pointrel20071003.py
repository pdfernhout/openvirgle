# Copyright Paul D. Fernhout 2007-2008
# LGPL license for this file
# simple implementation using one storage file and memory caching (and perhaps in the future optional index).

# later, maybe should not load big strings for valueBytes -- leave them on disk and load as needed
# perhaps add in license field for text, and for relationship (maybe separated by slashes) -- use metadata?

# print "pointrel20071002 starting"

"""
Record format [optional] {comment}
Signature: Pointrel20071003.0.2 pointrel-repository://z53a83f9-5b82-44qa-9543-3da836373b67
+timestamp|sequence|userReference entity attribute valueBytes [valueType] {record layout, with optional valueType}
+timestamp|sequence|userReference object1 color red
+timestamp|sequence|userReference object1 ~~9 red {has an item with a new line, size is an optimization hint}
~~has
color~~
+~~ object1 color red {user reference with a space}
~~timestamp|sequence|userReference~~
+timestamp|sequence|userReference deletedtimestamp|sequence|userReference pointrel:deleted true {deletion}
+timestamp|sequence|userReference deletedtimestamp|sequence|userReference pointrel:deleted false {undeletion}
"""

# entity, attribute, and valueType should always be utf-8
# valueBytes is normally utf-8, but can be anything matching the valueType

# Delimiting -- use a character (~) and then zero or more (-) in the middle,
# and then the first character again to make a delimiter unique to the data.
# Sequence field should not have a pipe (|) in it.

# Placed timestamp and user in record to avoid infinite regress on metadata; also more human readable than uuid.
# Sequence is there in case multiple timestamps the same for the same user -- can put any thing in there except a pipe (|), but typically expect number
# TODO: sequence is not currently used; collisions are not checked for but should be on add.

# TODO: file locking using Java NIO?
#http://java.sun.com/developer/JDCTechTips/2002/tt0924.html
#http://www.onjava.com/pub/a/onjava/2002/10/02/javanio.html

# Requires JVM 1.5 for UUID
from java.util import UUID
from java.text import SimpleDateFormat
from java.util import TimeZone
from java.sql import Timestamp
from java.lang import System

# signature written at the start of the file
SignatureSpecifier = "Signature:"
SignatureVersion = "Pointrel20071003.0.2"
# Uniform Resource Locators (URL): http://www.ietf.org/rfc/rfc1738.txt
RepositoryReferenceScheme = "pointrel-repository://"

DefaultValueType = "pointrel:text/utf-8"

delimiterStartAndEnd = '~'
delimiterMiddle = '-'
pointrelTripleIDPrefix = "pointrel://tripleID/"
EMPTY_MARKER = "%s%s0" % (delimiterStartAndEnd, delimiterStartAndEnd)

DEFAULT_REPOSITORY_EXTENSION = ".pointrel"
DEFAULT_REPOSITORY_NAME = "repository.pointrel"

# Times in ISO 8601
# http://www.cl.cam.ac.uk/~mgk25/iso-time.html
# SimpleDateFormat needs to have a local copy in each thread if multithreaded, so shooud use this in single threasd for now
ISO8601TimestampFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
ISO8601TimestampFormat.setTimeZone(TimeZone.getTimeZone("UTC"))
  
def stringForTimestamp(timestamp):
    return ISO8601TimestampFormat.format(timestamp)

def timestampForString(timestampString):
    date = ISO8601TimestampFormat.parse(timestampString)
    timestamp = Timestamp(date.getTime())
    return timestamp

def generateUniqueReferenceForRepository():
    randomUUID = UUID.randomUUID()
    newText = RepositoryReferenceScheme + randomUUID.toString()
    return newText
    
class Record:
    def __init__(self, entity, attribute, valueBytes, valueType=None, userReference=None, timestamp=None, sequence=None, operation=None):
        self.entity = entity
        self.attribute = attribute
        self.valueBytes = valueBytes
        # content type, typically "mime:text/plain" or "pointrel:text/utf-8" [the second is the default if not specified]
        if valueType == None:
            self.valueType = DefaultValueType
        else:
            self.valueType = valueType
        
        self.position = -1
        if userReference == None:
            userReference = "anonymous"
        if timestamp == None:
            timestamp = Timestamp(System.currentTimeMillis())
        self.userReference = userReference
        # Java timestamp reference: a point in time that is time milliseconds after January 1, 1970 00:00:00 GMT.
        self.timestamp = timestamp
        if sequence == None:
            self.sequence = "0"
        else:
            self.sequence = sequence
        self.previous = None
        self.deleted = False
        self.previousWithSameEntity = None
        if operation == None:
            # only option allowed currently
            operation = '+'
        self.operation = operation
        
        self.identifierString = self.makeIdentifierString()
        
    def makeIdentifierString(self):
        timestampString = stringForTimestamp(self.timestamp)
        identifierString = timestampString + "|" + self.sequence + "|" + self.userReference
        return identifierString
                
    def makeDelimiter(self, byteString):
        # make a delimiter which is not in the string
        insideLength = 0
        while 1:
            delimiter = delimiterStartAndEnd + (delimiterMiddle * insideLength) + delimiterStartAndEnd
            if byteString.find(delimiter) == -1:
                return delimiter
            insideLength += 1

    # returns delimiter  if need to use it later
    def writeHeaderField(self, f, byteString):
        if byteString == "":
            f.write(EMPTY_MARKER)
            return None
        needsDelimiter = False
        if "\n" in byteString or " " in byteString or byteString[0] == delimiterStartAndEnd:
            needsDelimiter = True
        if needsDelimiter:
            delimiter = self.makeDelimiter(byteString)
            f.write("%s%d" % (delimiter, len(byteString)))
            return delimiter
        f.write(byteString)
        return None
        
    def writeHeaderFields(self, f, headers):
        writeLater = []
        first = True
        for byteString in headers:
            if first:
                first = False
            else:
                f.write(" ")
            delimiter = self.writeHeaderField(f, byteString)
            if delimiter:
                writeLater.append((delimiter, byteString))
        f.write("\n")
        for delimiter, byteString in writeLater:
            f.write(delimiter)
            f.write(byteString)
            f.write(delimiter)
            f.write('\n')            
    
    def write(self, f, seekToEndOfFile=True):
        # add at end of file
        if seekToEndOfFile:
            f.seek(0, 2)
        self.position = f.tell()
        if self.operation != '+':
            raise "unsupported operation", self.operation
        f.write('+')
        fields = [self.identifierString, self.entity, self.attribute, self.valueBytes]
        # implicit default of utf-8 text
        if self.valueType != DefaultValueType:
            fields.append(self.valueType)
        self.writeHeaderFields(f, fields)
        f.flush()
        return self.position
    
    def discardCharacter(self, f, expectedCharacter, position=None):
        discard = f.read(1)
        if discard != expectedCharacter:
            if position == None:
                try:
                    position = f.tell()
                except:
                    position = "UNAVAILABLE"
            context = f.read(100)
            raise 'Error, expected character "%s", got: "%s" as position: %d context afterwards: "%s"' % (expectedCharacter, discard, position, context)
                
    def discardNewline(self, f):
        # should improve this to take in account of various line endings
        discard = f.read(1)
        if discard != '\n':
            context = f.read(100)
            raise 'Error, expected newline character: "%s" context afterwards: "%s"' % (discard, context)
            
    def read(self, position, f):
        if position >= 0:
            # otherwise assume at current position
            f.seek(position)
        else:
            position = f.tell()
        self.position = position
        
        return self.readAtCurrentPosition(f)
           
    def readAtCurrentPosition(self, f):
        operation = f.read(1)

        if operation == "":
            # end of file
            self.position = None
            return None
        
        if operation == "+":
            self.operation = operation
        else:
            raise "only operation of add (+) is currently supported, got '%s'" % operation
        
        representation = f.readline()
        try:
            headerItems = representation.split()
            if len(headerItems) == 4:
                identifierHeader, entityHeader, attributeHeader, valueBytesHeader = headerItems
                valueTypeHeader = DefaultValueType
            elif len(headerItems) == 5:
                identifierHeader, entityHeader, attributeHeader, valueBytesHeader, valueTypeHeader = headerItems
            else:
                raise ValueError("wrong number of items in header -- should be four or five")
        except ValueError:
            print "Error reading triple header: %s" % representation
            print "Position", f.tell()
            print "Just before: ", f.read(100)
            raise
        
        identifierString, self.entity, self.attribute, self.valueBytes, self.valueType = self.readItems(f, [identifierHeader, entityHeader, attributeHeader, valueBytesHeader, valueTypeHeader])
        
        #user reference may be arbitrarily long and have pipes (|) in it
        self.identifierString = identifierString
        timestampString, sequenceString, userReference = identifierString.split("|", 2)
        self.timestamp = timestampForString(timestampString)
        self.sequence = sequenceString
        self.userReference = userReference
        
        return self.position
        
    def readItems(self, f, headerList):
        resultList = []
        for header in headerList:
            if header[0] != delimiterStartAndEnd:
                resultList.append(header)
            elif header == EMPTY_MARKER:
                resultList.append("")
            else:
                ignore, insideDelimiterString, lengthString = header.split(delimiterStartAndEnd)
                delimiter = delimiterStartAndEnd + insideDelimiterString + delimiterStartAndEnd
                if lengthString == "":
                    # no length specified, search on delimiter
                    raise "UNFINISHED"
                else:
                    itemLength = int(lengthString)  # jython can only support integers for now
                    for expectedCharacter in delimiter:
                        self.discardCharacter(f, expectedCharacter)
                    item = f.read(itemLength)
                    # PDF IMPROVE __ IF SOMETHING WENT WRONG HERE WITH STUFF MATCHING UP
                    # SHOULD TRY TO SEARCH ON JUST DELIMITER OR TRY OTHER ERORR CORRECTION APPROACHES
                    for expectedCharacter in delimiter:
                        self.discardCharacter(f, expectedCharacter)
                    self.discardNewline(f)
                    resultList.append(item)
        return resultList

class Repository:
    def __init__(self, fileName=DEFAULT_REPOSITORY_NAME):
        self.records = []
        # keep track of the last record referencing for a particular entity
        self.lastUser = {}
        self.fileName = fileName
        self.uniqueReferenceForRepository = None
        self.ensureFileExists()
        self.reload()
        
    def isOldSignature(self, signatureLine):
        OLD_SIGNATURE = "Pointrel20071003.0.1 Signature"
        if signatureLine[0:len(OLD_SIGNATURE)] == OLD_SIGNATURE:
            print 'File uses old signature of "%s" but program can still can read that version' % OLD_SIGNATURE
            return True
        else:
            return False
            
    def processSignatureLine(self, signatureLine):
        if self.isOldSignature(signatureLine):
            return None
        signatureParts = signatureLine.split()
        if len(signatureParts) != 3:
            raise "first line signature does not have three parts in file %s\n" % self.fileName
        signatureSpecifier, signatureVersion, uniqueReferenceForRepository = signatureParts
        if signatureSpecifier != SignatureSpecifier:
            raise "first part of signature does is not %s in file %s\n" % (SignatureSpecifier, self.fileName)
        if signatureVersion != SignatureVersion:
            raise "second part of signature does is not %s in file %s\n" % (SignatureVersion, self.fileName)
        if uniqueReferenceForRepository[0:len(RepositoryReferenceScheme)] != RepositoryReferenceScheme:
            raise "third part of signature does not start with %s as expected in file %s\n" % (RepositoryReferenceScheme, self.fileName)
        return uniqueReferenceForRepository
    
    def writeSignature(self, f, uniqueReferenceForRepository):
        f.write(SignatureSpecifier) 
        f.write(" ")
        f.write(SignatureVersion) 
        f.write(" ")
        f.write(self.uniqueReferenceForRepository)
        f.write("\n")     
           
    def ensureFileExists(self):
        # make file if does not exist
        try:
            f = open(self.fileName, "r+b")
            try:
                signatureLine = f.readline()
            finally:
                f.close()
            self.uniqueReferenceForRepository = self.processSignatureLine(signatureLine)
        except IOError:
            print "Creating repository %s" % self.fileName
            self.uniqueReferenceForRepository = generateUniqueReferenceForRepository()
            f = open(self.fileName, "w+b")
            try:
                self.writeSignature(f, self.uniqueReferenceForRepository)
            finally:
                f.close()
        
    def reload(self):
        self.records = []
        self.lastUser = {}
        self.readAllRecords()
        self.processDeletionsAndUndeletionsForNewRecords()

    def importRecordsFromAnotherRepository(self, anotherRepositoryFileName):
        existingRecordCount = len(self.records)
        anotherRepository = Repository(anotherRepositoryFileName)
        oldRecords = anotherRepository.records
        self.addRecordsFromAnotherRepository(oldRecords)
        self.processDeletionsAndUndeletionsForNewRecords(existingRecordCount)   
        
    def readAllRecords(self):
        f = open(self.fileName, "rb")
        try:
            # read signature
            signatureLine = f.readline()
            self.uniqueReferenceForRepository = self.processSignatureLine(signatureLine)
            print "loading repository", self.uniqueReferenceForRepository
            while 1:
                r = Record(None, None, None)
                r.position = f.tell()
                r.readAtCurrentPosition(f)
                if r.position == None:
                    break
                self.records.append(r)
                try:
                    oldLastUser = self.lastUser[r.entity]
                except KeyError:
                    oldLastUser = None
                r.previousWithSameEntity = oldLastUser
                self.lastUser[r.entity] = r   
        finally:
            f.close() 
            
    def writeAllRecords(self):
        fileName = self.fileName
        uniqueReferenceForRepository = self.uniqueReferenceForRepository
        #else:
        #    # generate a new uniqueReference if it isn't our existing file
        #    # might want to check if there was an old one? But then should be doing append or have opended it instead.
        #    uniqueReferenceForRepository = generateUniqueReferenceForRepository()
        f = open(fileName, "w+b")
        try:
            # write signature at start
            self.writeSignature(f, uniqueReferenceForRepository)
            for record in self.records:
                record.write(f)
        finally:
            f.close()
            
    def addRecordsFromAnotherRepository(self, oldRecords):
        # might want to add options to update timestamp or userTeference
        f = open(self.fileName, "r+b")
        try:
            for oldRecord in oldRecords:
                newRecord = Record(oldRecord.entity, oldRecord.attribute, oldRecord.valueBytes, oldRecord.valueType, oldRecord.userReference, oldRecord.timestamp)
                # records are always written to the end of the file
                position = newRecord.write(f)
                self.records.append(newRecord)
                newRecord.previousWithSameEntity = self.lastUser.get(newRecord.entity, None)
                self.lastUser[newRecord.entity] = newRecord          
        finally:
            f.close()

    def add(self, entity, attribute, valueBytes, valueType, userReference=None, timestamp=None, openFile=None):
        newRecord = None
        if openFile:
            f = openFile
        else:
            f = open(self.fileName, "r+b")
        try:
            # records are always written to end of file by default
            newRecord = Record(entity, attribute, valueBytes, valueType, userReference, timestamp)
            newRecord.write(f)
        finally:
            if not openFile:
                f.close()
        self.records.append(newRecord)
        newRecord.previousWithSameEntity = self.lastUser.get(newRecord.entity, None)
        self.lastUser[newRecord.entity] = newRecord
        return newRecord
                
    def deleteOrUndelete(self, recordToDelete, userReference=None, timestamp=None, openFile=None, deleteFlag=True):
        if recordToDelete == None:
            return None
        newRecord = None
        if openFile:
            f = openFile
        else:
            f = open(self.fileName, "r+b")
        try:
            if deleteFlag:
                newState = "true"
            else:
                newState = "false"
            newRecord = Record(pointrelTripleIDPrefix + recordToDelete.identifierString, "pointrel:deleted", newState, None, userReference, timestamp)
            newRecord.write(f)
            recordToDelete.deleted = deleteFlag
        finally:
            if not openFile:
                f.close()
        self.records.append(newRecord)
        newRecord.previousWithSameEntity = self.lastUser.get(newRecord.entity, None)
        self.lastUser[newRecord.entity] = newRecord
        return newRecord
    
    def timestampAndUserForDeletionReference(self, reference):
        timestampString, userReference = reference.split("|", 1)
        timestamp = timestampForString(timestampString)
        return timestamp, userReference
    
    def processDeletionsAndUndeletionsForNewRecords(self, startingIndex=0):
        # PDF FIX __ pointrel:deleted
        if startingIndex:
            records = self.records[startingIndex:]
        else:
            records = self.records
        for record in records:
            if record.attribute == "pointrel:deleted":
                if record.entity.find(pointrelTripleIDPrefix) != 0:
                    # maybe this should not be an error, but is one for now during testing"
                    raise "expecting be triple prefixed by", pointrelTripleIDPrefix
                identifier = record.entity[len(pointrelTripleIDPrefix):]
                # PDF fix -- should check valueType?
                if record.valueBytes == "true":
                    # delete a record
                    self.findAndSetDeletionFlag(identifier)
                elif record.valueBytes == "false":
                    # undelete a record
                    self.findAndClearDeletionFlag(identifier)
                else:
                    raise "deletion status only supported as 'true' and 'false'", record.valueBytes 
    
    def findAndSetDeletionFlag(self, identifier):
        # PDF OPTIMIZE __ LOOKUP FROM DICTIONARY?
        for record in self.records:
            if record.identifierString == identifier and not record.deleted:
                record.deleted = True
                return
        print "non-deleted item not found to delete", identifier
 
    def findAndClearDeletionFlag(self, identifier):
        # PDF OPTIMIZE __ LOOKUP FROM DICTIONARY?
        for record in self.records:
            if record.identifierString == identifier and record.deleted:
                record.deleted = False
                return
        print "deleted item not found to undelete", identifier      
            
    def read(self, position, openFile=None):
        newRecordFromDisk = None
        if openFile:
            f = openFile
        else:
            f = open(self.fileName, "r+b")
        try:
            # read record as position
            newRecordFromDisk = Record(None, None, None)
            newRecordFromDisk.read(position, f)
        finally:
            if not openFile:
                f.close()
        return newRecordFromDisk
    
    def allAttributesForEntity(self, entity, includeDeleted=False):
        attributes = {}
        record = self.lastUser.get(entity, None)
        while record:
            if includeDeleted or not record.deleted:
                attributes[record.attribute] = 1
            record = record.previousWithSameEntity    
        return attributes.keys()    
    
    def findAllRecordsForEntity(self, entity, attribute=None, includeDeleted=False):
        result = []
        record = self.lastUser.get(entity, None)
        while record:
            if includeDeleted or not record.deleted:
                if attribute == None or attribute == record.attribute:
                    result.append(record)
            record = record.previousWithSameEntity
        return result

    def findAllRecordsForEntityAttribute(self, entity, attribute, includeDeleted=False):
        result = []
        record = self.lastUser.get(entity, None)
        while record:
            if includeDeleted or not record.deleted:
                if record.attribute == attribute:
                    result.append(record) 
            record = record.previousWithSameEntity  
        return result
        
    def findLatestRecordsForAllEntityAttributes(self, entity, includeDeleted=False):
        attributes = {}
        result = []
        record = self.lastUser.get(entity, None)
        while record:
            if includeDeleted or not record.deleted:
                if record.attribute not in attributes:
                    attributes[record.attribute] = True
                    result.append(record)
            record = record.previousWithSameEntity    
        return result   
    
    def findLatestRecordForEntityAttribute(self, entity, attribute, includeDeleted=False):
        record = self.lastUser.get(entity, None)
        while record:
            if includeDeleted or not record.deleted:
                if attribute == record.attribute:
                    return record
            record = record.previousWithSameEntity 
        return None
        
    # returns just the valueBytes
    def find(self, entity, attribute, includeDeleted=False):
        record = self.findLatestRecordForEntityAttribute(entity, attribute, includeDeleted)
        if record:
            return record.valueBytes
        return None
 
def test():
    r = Repository()
    print "writing ======"
    record1 = r.add("object1", "color", "red1")
    print record1, record1.position
    record2 = r.add("object1", "has color", "red2")
    print record2, record2.position
    record3 = r.add("object1", "has\ncolor", "red3")
    print record3, record3.position
    record4 = r.add("object1", "%has-color", "red4")
    print record4, record4.position
    print "reading ====="
    record = r.read(record1.position)
    print record
    print record.position, record.entity, record.attribute, record.valueBytes, record.valueType
    record = r.read(record2.position)
    print record
    print record.position, record.entity, record.attribute, record.valueBytes, record.valueType 
    record = r.read(record3.position)
    print record
    print record.position, record.entity, record.attribute, record.valueBytes, record.valueType
    record = r.read(record4.position)
    print record
    print record.position, record.entity, record.attribute, record.valueBytes, record.valueType 
    print "done"
    print r.find("object1", "has color")
    print r.find("object1", "%has-color")
    print r.allAttributes("object1")
    print r.allValueRecords("object1", "has color")
    print [(record.valueBytes, record.timestamp) for record in r.allValueRecords("object1", "has color")]
    print "done"
    
if __name__ == "__main__":
    test()

