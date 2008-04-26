print "pointrel20061224 starting"

# system of branches

RecordFieldCount = 6
RecordLength = RecordFieldCount * 19

Signature = "Pointrel20061225.0.0 Signature"
ReservedConceptsCount = 511

# Concept_Null -> 0
# Pointrel_ByteArray[256] --> 1..256
Concept_SymbolSpaceBranch = 257
Concept_SymbolRoot = 258
Concept_SymbolNext = 259
Concept_SymbolCharacter = 260

class Record:
    def __init__(self, index=0, object=0, attribute=0, value=0, follows=0):
        self.index = index
        self.object = object
        self.attribute = attribute
        self.value = value
        self.follows = follows
        self.last = 0
        
    def write(self, f, update=0):
        # update is only to be used to change last
        if update:
            f.seek(self.index * RecordLength)
        else:
            # add at end of file
            f.seek(0, 2)
            position = f.tell() 
            index = position / RecordLength
            self.index = index
        representation = "i:%016x o:%016x a:%016x v:%016x f:%016x l:%016x\n" % \
          (self.index, self.object, self.attribute, self.value, self.follows, self.last)
        f.write(representation)

    def read(self, index, f):
        f.seek(index * RecordLength)
        representation = f.readline()
        elements = representation.split()
        # strip labels
        for i in range(0, RecordFieldCount):
            elements[i] = elements[i][2:]
        # convert from hexidecimal string to long
        for i in range(0, RecordFieldCount):
            elements[i] = long(elements[i], 16)
        self.index, self.object, self.attribute, self.value, self.follows, self.last = elements

class Repository:
    def __init__(self, filename="repository.dat"):
        self.filename = filename
        # make file if does not exist
        try:
            f = open(self.filename, "r+b")
            signature = f.readline()
            f.close()
            if signature[0:len(Signature)] != Signature:
                raise "signature not as expected in file %s\n" % self.filename
        except IOError:
            print "Creating repository %s" % self.filename
            f = open(self.filename, "w+b")
            f.write(Signature) 
            f.write(" " * (RecordLength - len(Signature) - 1))
            f.write("\n")
            for i in range(ReservedConceptsCount+1):
                self.new()
            f.close()
            
    def endIndex(self, f):
        f.seek(0, 2)
        position = f.tell() 
        index = position / RecordLength
        return index      
            
    # will cache this later, obviously
    def lastRecordIndexForObject(self, object, f):
        if object == 0:
            return 0
        r = Record()
        r.read(object, f)
        return r.last
    
    def new(self):
        f = open(self.filename, "r+b")
        r = Record()
        r.write(f)
        f.close()
        return r.index     
        
    def add(self, a, b, c):
        f = open(self.filename, "r+b")
        
        # make new record
        follows = self.lastRecordIndexForObject(a, f)
        newRecord = Record(0, a, b, c, follows)
        newRecord.write(f)
        
        # Addition will be lost if interrupted here
        
        # update old Record
        oldRecord = Record()
        oldRecord.read(a, f)
        oldRecord.last = newRecord.index
        oldRecord.write(f, 1)
        f.close()
        return newRecord.index
    
    def find(self, a, b):
        c = 0
        f = open(self.filename, "r+b")
        index = self.lastRecordIndexForObject(a, f)
        r = Record()
        while index:
            r.read(index, f)
            if r.object == a and r.attribute == b:
                c = r.value
                break
            index = r.follows
        f.close()
        return c
    
    def symbolIndexForString(self, stringUTF8):
        lastSymbol = Concept_SymbolRoot
        i = len(stringUTF8) - 1
        while i >= 0:
            c = stringUTF8[i]
            i -= 1
            byteConcept = ord(c) + 1
            if byteConcept < 1 or byteConcept > 256:
                raise "character out of range"
            result = self.find(lastSymbol, byteConcept)
            if not result:
                result = self.new()
                self.add(result, Concept_SymbolCharacter, byteConcept)
                self.add(result, Concept_SymbolNext, lastSymbol)
                self.add(lastSymbol, byteConcept, result)
            lastSymbol = result
        return result
    
    def stringForSymbolIndex(self, symbolIndex):
        result = ""
        i = 0
        value = 0
        byteConcept = 0
        
        while symbolIndex != Concept_SymbolRoot:
            byteConcept = self.find(symbolIndex, Concept_SymbolCharacter)
            if byteConcept == 0:
                raise "problem in symbol table"
            value = chr(byteConcept - 1)
            result += value
            symbolIndex = self.find(symbolIndex, Concept_SymbolNext)
        return result
            
        
r = Repository()
p1 = r.add(1, 2, 3)
print "p1", p1
p2 = r.add(4, 5, 6)
print "p2", p2

p3 = r.find(1, 2)
print "find", p3

p3 = r.find(1, 2)
print "find", p3

p3 = r.find(4, 5)
print "find", p3

s1 = r.symbolIndexForString("hello")
print "hello at", s1

s2 = r.stringForSymbolIndex(s1)
print "s2", s2