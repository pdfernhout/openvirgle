print "pointrel20061224 starting"

# system of branches

RecordLength = 8 * 19
Signature = "Pointrel20062412.0.0 Signature"
ReservedConceptsCount = 511

# Concept_Null -> 0
# Pointrel_ByteArray[256] --> 1..256
Concept_SymbolSpaceBranch = 257
Concept_SymbolRoot = 258
Concept_SymbolNext = 259
Concept_SymbolCharacter = 260

class Record:
    def __init__(self, index=0, branch=0, follows=0, a=0, b=0, c=0, user=0, timestamp=0):
        self.index = index
        self.branch = branch
        self.follows = follows
        self.a = a
        self.b = b
        self.c = c
        self.user = user
        self.timestamp = timestamp
        
    def write(self, f):
        f.seek(0, 2)
        absolutePosition = f.tell()
        if self.index * RecordLength != absolutePosition:
            print "positions", self.index * RecordLength, absolutePosition
            raise "not in correct position to append record"
        representation = "i:%016x r:%016x f:%016x a:%016x b:%016x c:%016x u:%016x t:%016x\n" % \
          (self.index, self.branch, self.follows, self.a, self.b, self.c, self.user, self.timestamp)
        f.write(representation)

    def read(self, index, f):
        f.seek(index * 8 * 19)
        representation = f.readline()
        elements = representation.split()
        # strip labels
        for i in range(0, 8):
            elements[i] = elements[i][2:]
        # convert from hexidecimal string to long
        for i in range(0, 8):
            elements[i] = long(elements[i], 16)
        self.index, self.branch, self.follows, self.a, self.b, self.c, self.user, self.timestamp = elements

class Repository:
    def __init__(self, filename="repository.dat"):
        self.filename = filename
        # make file if does not exist
        try:
            f = open(self.filename, "r+b")
            f.close()
        except:
            print "Creating repository %s" % self.filename
            f = open(self.filename, "w+b")
            f.write(Signature) 
            f.write(" " * (RecordLength - len(Signature) - 1))
            f.write("\n")
            for i in range(ReservedConceptsCount):
                self.add(0, 0, 0, 0)
            f.close()
            
    def endIndex(self, f):
        f.seek(0, 2)
        position = f.tell() 
        index = position / RecordLength
        return index      
            
    # will cache this later, obviously
    def lastRecordIndexForBranch(self, branch, f):
        index = self.endIndex(f)
        r = Record()
        while index > 1:
            index -= 1
            r.read(index, f)
            if r.branch == branch:
                return index
        return 0
        
    def add(self, branch, a, b, c):
        f = open(self.filename, "r+b")
        index = self.endIndex(f)
        follows = self.lastRecordIndexForBranch(branch, f)
        r = Record(index, branch, follows, a, b, c)
        r.write(f)
        f.close()
        return index
    
    def find(self, branch, a, b):
        c = 0
        f = open(self.filename, "r+b")
        index = self.lastRecordIndexForBranch(branch, f)
        r = Record()
        while index:
            r.read(index, f)
            if r.a == a and r.b == b:
                c = r.c
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
            result = self.find(Concept_SymbolSpaceBranch, lastSymbol, byteConcept)
            if not result:
                result = self.add(Concept_SymbolSpaceBranch, 0, 0, 0)
                self.add(Concept_SymbolSpaceBranch, result, Concept_SymbolCharacter, byteConcept)
                self.add(Concept_SymbolSpaceBranch, result, Concept_SymbolNext, lastSymbol)
                self.add(Concept_SymbolSpaceBranch, lastSymbol, byteConcept, result)
            lastSymbol = result
        return result
    
    def stringForSymbolIndex(self, symbolIndex):
        result = ""
        i = 0
        value = 0
        byteConcept = 0
        
        while symbolIndex != Concept_SymbolRoot:
            byteConcept = self.find(Concept_SymbolSpaceBranch, symbolIndex, Concept_SymbolCharacter)
            if byteConcept == 0:
                raise "problem in symbol table"
            value = chr(byteConcept - 1)
            result += value
            symbolIndex = self.find(Concept_SymbolSpaceBranch, symbolIndex, Concept_SymbolNext)
        return result
            
        
r = Repository()
p1 = r.add(1000, 1, 2, 3)
print "p1", p1
p2 = r.add(1001, 4, 5, 6)
print "p2", p2

p3 = r.find(1000, 1, 2)
print "find", p3

p3 = r.find(1001, 1, 2)
print "find", p3

p3 = r.find(1001, 4, 5)
print "find", p3

s1 = r.symbolIndexForString("hello")
print "hello at", s1

s2 = r.stringForSymbolIndex(s1)
print "s2", s2