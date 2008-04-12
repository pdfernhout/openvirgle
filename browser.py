# Copyright Paul D. Fernhout 2007-2008
# LGPL license

import java

# Requires JVM 1.5 for UUID
from java.util import UUID
from java.lang import System, Object
from java.io import ByteArrayInputStream, File
from javax.swing import Timer
from javax.swing import JPanel, JComboBox, JButton, JFrame, JTextPane, JTextField, JScrollPane
from javax.swing import JList, DefaultListModel, JCheckBox, JLabel, JSplitPane, JOptionPane, JFileChooser
from javax.swing import JTextArea, KeyStroke, AbstractAction
from javax.swing import Box, BoxLayout
from javax.swing import JMenuItem, JCheckBoxMenuItem, JMenuBar, JMenu, JPopupMenu
from javax.swing.filechooser import FileFilter
from java.awt import BorderLayout, FlowLayout, GridLayout, GridBagLayout, Dimension, Color, Font
from java.awt.event import ActionListener, KeyEvent

from pointrel20071003 import Repository, DefaultValueType, DEFAULT_REPOSITORY_NAME
import __builtin__
import imp
import sys
import StringIO

PointrelFileTypes = [("pointrel", "Pointrel Repository (*.pointrel)")]

################# Utility classes

# http://java.sun.com/docs/books/tutorial/uiswing/misc/keybinding.html
# http://coding.derkeiler.com/Archive/Java/comp.lang.java.gui/2005-06/msg00043.html
# http://forum.java.sun.com/thread.jspa?threadID=5182659
class AddFourSpacesAction(AbstractAction):
    def actionPerformed(self, actionEvent):
        source = actionEvent.source
        source.replaceSelection(" " * 4)
                                
class FileFilterForExtension(FileFilter):
    def __init__(self, extension, description=None):
        self.extension = extension
        if description == None:
            self.descriptionForExtension = extension
        else:
            self.descriptionForExtension = description
     
    def getDescription(self):
        return self.descriptionForExtension
    
    def accept(self, f):
        if f.isDirectory():
            return True
        name = f.name.lower()
        return name[-len(self.extension):] == self.extension
        
class FileDialog:
    def __init__(self, parent, title="Choose file", loadOrSave="load"):
        self.parent = parent
        self.title = title
        self.loadOrSave = loadOrSave
        
    # example fileTypes = [("bmp", "BMP Bitmaps"), ("png", "PNG Bitmaps")]
    def go(self, fileTypes=None, default=None, directoryAllowed=False):
        fileChooser = JFileChooser()
        if self.title:
            fileChooser.setDialogTitle(self.title)
        if default:
            fileChooser.setSelectedFile(java.io.File(default))
        fileChooser.setCurrentDirectory(java.io.File("."))
        if fileTypes:
            for extension, description in fileTypes:
               fileChooser.addChoosableFileFilter(FileFilterForExtension(extension, description))            
        if self.loadOrSave == "load":
            result = fileChooser.showOpenDialog(self.parent)
        else:
            result = fileChooser.showSaveDialog(self.parent)
        if (result == JFileChooser.APPROVE_OPTION):
            fileResult = None
            fileAndMaybeDir = fileChooser.getSelectedFile().getAbsoluteFile()
            if directoryAllowed or not fileAndMaybeDir.isDirectory():
                fileResult = str(fileAndMaybeDir)
            return fileResult
        else:
            return None

class CallbackActionListener(ActionListener):
    def __init__(self, action):
        self.action = action   
    def actionPerformed(self, event):
        self.action(event)
                  
class OptionsCallbackPopupMenu:
    # options should be a list of (name, function, [arg1, [arg2]]) tuples
    def __init__(self, parent, x, y, options, extraOptions=None):
        self.popupMenu = JPopupMenu()
        self.options = options
        self.addToMenuForOptions(options)
        if extraOptions:
           self.addToMenuForOptions(extraOptions)
        self.popupMenu.show(parent, x, y) 
            
    def addToMenuForOptions(self, options, menu=None):
        if not menu:
            menu = self.popupMenu
        for option in options:
            if not option or not option[0]:
                menu.addSeparator()
            else:
                if type(option[1]) in [tuple, list]:
                    # nested menu
                    submenu = JMenu(option[0])
                    self.addToMenuForOptions(option[1], submenu)
                    menu.add(submenu)
                else:
                    menuItem = JMenuItem(option[0], actionPerformed=lambda event, option=option: self.OnChoice(option))
                    menu.add(menuItem)
                    
    def OnChoice(self, option):
        if len(option) == 2:
            option[1]()
        elif len(option) == 3:
            option[1](option[2])
        elif len(option) == 4:
            option[1](option[2], option[3])
            
##########################################                    
class EditorPanel_abstract(JPanel):
    def __init__(self, browser, valueType):
        JPanel.__init__(self)
        self.browser = browser
        self.valueType = valueType
        self.internalValueChanging = True
        self.basicInitialization()
        self.makeComponents()
        self.originalValueBytes = ""
        self.valueType = valueType
        self.internalValueChanging = False
        
    def isChangedFromOriginal(self):
        return self.originalValueBytes != self.getCurrentValueBytes()

    def getCurrentValueBytes(self):
        return self.basicGetCurrentValueBytes()
        
    def setCurrentValueBytes(self, newValueBytes):
        self.originalValueBytes = newValueBytes
        self.internalValueChanging = True
        self.basicSetCurrentValueBytes(newValueBytes)
        self.internalValueChanging = False
        
    def recordChanged(self, newRecord):
        self.basicRecordChanged(newRecord)
        
    # methods to override
    
    def basicInitialization(self):
        pass
    
    def makeComponents(self):
        # subclass should override
        pass
        
    def basicRecordChanged(self, newRecord):
        pass
        
    def basicGetCurrentValueBytes(self):
        # subclass should override if editable
        return self.originalValueBytes
        
    def basicSetCurrentValueBytes(self, newValueBytes):
        # subclass should override
        pass

        
class EditorPanel_text_utf_8(EditorPanel_abstract):
    
    def basicRecordChanged(self, newRecord):
        self.textEditor.caretPosition = 0
        self.saveButton.background = self.normalSaveButtonColor
    
    def makeComponents(self):
        # text specific operations
        self.randomUUIDButton = JButton("Generate random UUID", actionPerformed=self.randomUUIDPressed)
        self.clearButton = JButton("Clear", actionPerformed=self.clearPressed)
        self.runButton = JButton("Run as Jython", actionPerformed=self.runPressed)
        self.revertButton = JButton("Revert", actionPerformed=self.revertPressed)

        self.buttonPanel = Box(BoxLayout.X_AXIS) 
        self.buttonPanel.add(Box.createRigidArea(Dimension(5,0)))
        self.buttonPanel.add(self.randomUUIDButton)
        self.buttonPanel.add(Box.createRigidArea(Dimension(5,0)))
        self.buttonPanel.add(self.clearButton)
        self.buttonPanel.add(Box.createRigidArea(Dimension(5,0)))
        self.buttonPanel.add(self.runButton)
        self.buttonPanel.add(Box.createRigidArea(Dimension(5,0)))
        self.buttonPanel.add(self.revertButton)
        self.buttonPanel.add(Box.createRigidArea(Dimension(5,0)))
 
        self.textEditor = JTextPane()
        self.textEditor.setFont(Font("monospaced", Font.PLAIN, 12))
        #self.textEditor.setTabSize(4) # still inserts tabs instead of spaces
        TabKeyStroke = KeyStroke.getKeyStroke(KeyEvent.VK_TAB, 0, False)
        MyTabActionKey = Object()
        self.textEditor.getInputMap().put(TabKeyStroke, MyTabActionKey)
        actionMap = self.textEditor.getActionMap()
        actionMap.put(MyTabActionKey, AddFourSpacesAction())
        
        self.layout = BorderLayout()
        self.add(self.buttonPanel, BorderLayout.NORTH)
        self.add(JScrollPane(self.textEditor), BorderLayout.CENTER)
        
    def basicGetCurrentValueBytes(self):
        return self.textEditor.text
        
    def basicSetCurrentValueBytes(self, newValueBytes):
        self.textEditor.text = newValueBytes
        self.textEditor.caretPosition = 0
        
    # extra functionality
    def runPressed(self, event):
        print "run pressed"
        codeText = self.getCurrentValueBytes()
        print "=== run code ==="
        exec "from token import *"
        #print codeText
        self.browser.oldimport = __builtin__.__import__
        self.browser.contextUUID = self.browser.entitiesList.selectedValue
        __builtin__.__import__ = self.browser.importCodeFromRepository
        self.browser.importLevel = 0
        try:
            try:
                someGlobals = {"currentBrowser": self.browser, "contextUUID": self.browser.entitiesList.selectedValue}
                exec codeText in someGlobals
            except SyntaxError, e:
                print e
                #print "fileName", e.fileName
                #print "lineno", e.lineno
                print "offset:", e.offset
                print "text:", e.text
                lines = codeText.split('\n')
                position = 0
                for i in range(e.lineno - 1):
                    position += len(lines[i]) + 1
                position += e.offset
                self.textEditor.caretPosition = position
                self.textEditor.requestFocus()
            print "=== done ==="
        finally:
            __builtin__.__import__ = self.browser.oldimport
        
    def randomUUIDPressed(self, event):
        randomUUID = UUID.randomUUID()
        newText = "uuid://" + randomUUID.toString()
        self.textEditor.text = newText
 
    def clearPressed(self, event):
        #self.browser.setCurrentAttributeName("")
        self.textEditor.text = ""

    def revertPressed(self, event):
        self.textEditor.text = self.originalValueBytes

class Browser:
    def __init__(self, repository):
        self.repository = repository
        # want a better solution, with domains, perhaps user specifies
        self.currentUserReference = System.getProperty("user.name")
        
        self.currentRecord = None
                
        self.window = JFrame("Pointrel browser", windowClosing=self.exit)
        self.window.contentPane.layout = BorderLayout() # redundant as the default
        self.window.bounds = (100, 100, 800, 600)
        
        self.menuBar = JMenuBar()
        self.window.JMenuBar = self.menuBar
        fileMenu = JMenu("File")
        fileMenu.add(JMenuItem("Open...", actionPerformed=self.open))
        fileMenu.add(JMenuItem("Reload", actionPerformed=self.reloadPressed))
        fileMenu.addSeparator()
        fileMenu.add(JMenuItem("Import from other repository...", actionPerformed=self.importFromOtherRepository))
        fileMenu.addSeparator()
        fileMenu.add(JMenuItem("Close", actionPerformed=self.close))
        self.menuBar.add(fileMenu)

        exportMenu = JMenu("Export")
        exportMenu.add(JMenuItem("Choose current export file...", actionPerformed=self.exportChooseCurrentFile))
        exportMenu.addSeparator()        
        exportMenu.add(JMenuItem("Export selected record", actionPerformed=self.exportSelectedRecord))
        exportMenu.add(JMenuItem("Export record history for selected attribute", actionPerformed=self.exportAllRecordsForSelectedAttribute))
        exportMenu.addSeparator()
        exportMenu.add(JMenuItem("Export current records for all attributes of selected entity", actionPerformed=self.exportLatestRecordsForSelectedEntity))
        exportMenu.add(JMenuItem("Export entire record history for all attributes of selected entity", actionPerformed=self.exportAllRecordsForSelectedEntity))
        self.menuBar.add(exportMenu)
        
        self.exportFileName = "export.pointrel"

        #self.reloadButton = JButton("Reload Repository", actionPerformed=self.reloadPressed)
                        
        self.entitiesList = JList(DefaultListModel(), mouseClicked=self.entitiesListClicked)
        self.entitiesList.model.addElement("root")
        self.entitiesList.mousePressed = self.entitiesListMousePressed
        self.entitiesList.mouseReleased = self.entitiesListMousePressed
        
        self.attributesList = JList(DefaultListModel(), mouseClicked=self.attributesListClicked)
        
        self.versionsList = JList(DefaultListModel(), mouseClicked=self.versionsListClicked)
        
        self.listPanel = JPanel(layout=GridLayout(1, 2))
        self.listPanel.add(JScrollPane(self.entitiesList))
        self.listPanel.add(JScrollPane(self.attributesList))
        self.listPanel.add(JScrollPane(self.versionsList))
        
        self.navigationPanel = JPanel(layout=BorderLayout())
        #self.navigationPanel.add(self.reloadButton, BorderLayout.NORTH)
        self.navigationPanel.add(self.listPanel, BorderLayout.CENTER)
                
        self.entityTextField = JTextField(preferredSize=(200,20))
        self.attributeTextField = JTextField(preferredSize=(200,20))
        self.deletedButton = JCheckBox("Deleted", actionPerformed=self.deletedPressed)
        
        # only one right now -- and no support for switching editor panels yet
        examples = ["pointrel:text/utf-8", ]
        self.valueTypeComboBox = JComboBox(examples, preferredSize=(200,20), editable=True)

        self.attributePanel = Box(BoxLayout.X_AXIS) 
        self.attributePanel.add(Box.createRigidArea(Dimension(5,0)))
        self.attributePanel.add(JLabel("Entity:"))
        self.attributePanel.add(Box.createRigidArea(Dimension(2,0)))
        self.attributePanel.add(self.entityTextField)
        self.attributePanel.add(Box.createRigidArea(Dimension(5,0)))
        self.attributePanel.add(JLabel("Attribute:"))
        self.attributePanel.add(Box.createRigidArea(Dimension(2,0)))
        self.attributePanel.add(self.attributeTextField)
        self.attributePanel.add(Box.createRigidArea(Dimension(5,0)))
        self.attributePanel.add(JLabel("Value type:"))
        self.attributePanel.add(Box.createRigidArea(Dimension(2,0)))
        self.attributePanel.add(self.valueTypeComboBox)
        self.attributePanel.add(Box.createRigidArea(Dimension(5,0)))
        self.attributePanel.add(self.deletedButton)
        self.attributePanel.add(Box.createRigidArea(Dimension(5,0)))
        
        self.showAllDeletedButton = JCheckBox("Show all deleted", actionPerformed=self.showAllDeletedPressed)
        self.statusText = JTextField(preferredSize=(100,20))
        self.saveButton = JButton("Save", actionPerformed=self.savePressed)
        self.normalSaveButtonColor = self.saveButton.background
        self.changedSaveButtonColor = Color.YELLOW

        self.statusPanel = Box(BoxLayout.X_AXIS)
        self.statusPanel.add(Box.createRigidArea(Dimension(5,0)))
        self.statusPanel.add(self.showAllDeletedButton)
        self.statusPanel.add(Box.createRigidArea(Dimension(25,0)))
        self.statusPanel.add(JLabel("Message:") )
        self.statusPanel.add(Box.createRigidArea(Dimension(2,0)))
        self.statusPanel.add(self.statusText) 
        self.statusPanel.add(Box.createRigidArea(Dimension(5,0)))
        self.statusPanel.add(self.saveButton)
        self.statusPanel.add(Box.createRigidArea(Dimension(1,0)))       
        
        self.currentEditorPanel = EditorPanel_text_utf_8(self, "pointrel:text/utf-8")
        
        self.topPanel = Box(BoxLayout.Y_AXIS)
        self.topPanel.add(Box.createRigidArea(Dimension(0,5))) 
        self.topPanel.add(self.attributePanel)
        self.topPanel.add(Box.createRigidArea(Dimension(0,5))) 
        
        self.editorPanel = JPanel(layout=BorderLayout())
        self.editorPanel.add(self.topPanel, BorderLayout.NORTH)
        self.editorPanel.add(self.currentEditorPanel, BorderLayout.CENTER)
        self.editorPanel.add(self.statusPanel, BorderLayout.SOUTH)
        
        self.browserPanel = JSplitPane(JSplitPane.VERTICAL_SPLIT)
        self.browserPanel.add(self.navigationPanel)
        self.browserPanel.add(self.editorPanel)
        
        self.window.contentPane.add(self.browserPanel, BorderLayout.CENTER)
        
        self.setTitleForRepository()
        self.window.show()
        
        # background timer for updating save button color
        self.timer = Timer(1000, CallbackActionListener(self.timerEvent))
        self.timer.initialDelay = 1000
        self.timer.start()
        
    def close(self, event):
        System.exit(0)
        
    def open(self, event):
        dialog = FileDialog(self.window)
        fileName = dialog.go(PointrelFileTypes)
        if not fileName:
            return
        repository = Repository(fileName)
        self.repository = repository
        self.currentRecord = None
        self.clearAllEntityNames()
        self.refreshBrowser()
        self.setTitleForRepository()
        
    def setTitleForRepository(self):
        self.window.title = "Pointrel browser on %s" % self.repository.fileName

    def setStatus(self, messageText):
        self.statusText.text = messageText
        
    def getCurrentEntityName(self):
        return self.entityTextField.text

    def setCurrentEntityName(self, newAttributeName):
        self.entityTextField.text = newAttributeName
           
    def getCurrentAttributeName(self):
        return self.attributeTextField.text

    def setCurrentAttributeName(self, newAttributeName):
        self.attributeTextField.text = newAttributeName
           
    def getCurrentValueType(self):
        #return self.valueTypeComboBox.selectedItem
        return self.valueTypeComboBox.editor.editorComponent.text
    
    def setCurrentValueType(self, newValueType):
        self.valueTypeComboBox.selectedItem = newValueType
        # PDF FIX __ NEED TO CHANGE EDITOR TYPE
            
    def reportStatistics(self):
        contents = self.currentEditorPanel.getCurrentValueBytes()
        words = len(contents.split())
        lines = contents.count('\n')
        characters = len(contents)
        report = "%d lines; %d words; %d characters" % (lines, words, characters)
        self.setStatus(report)
        
    def timerEvent(self, event):
        self.manageSaveButtonColor()
        self.reportStatistics()
        
    def exit(self, event=None):
        System.exit(0)
        
    def reloadPressed(self, event):
        print "reloading repository; ", 
        self.repository.reload()
        self.refreshBrowser()
        print "done"
        
    def importCodeFromRepository(self, name, globals=None, locals=None, fromlist=None):
        # seems to fail with stack overflow if print while importing while trying jconsole (it reassigns stdio)
        debug = 0
        self.importLevel += 1
        if debug: print "  " * self.importLevel,
        if debug: print "importCodeFromRepository", name
        try:
            if debug: print "  " * self.importLevel,
            if debug: print "  globals: ", globals
            if debug: print "  " * self.importLevel,
            if debug: print "  locals", locals
            if debug: print "  " * self.importLevel,
            if debug: print "  fromlist", fromlist
        except UnboundLocalError:
            if debug: print "  " * self.importLevel,
            if debug: print "unbound error"
        # Fast path: see if the module has already been imported.
        # though this is wrong -- as need to check repository if code has been changed
        # broken as does not consider fromlist
        #try:
        #    return sys.modules[name]
        #except KeyError:
        #    pass
        # check if local module
        record = self.repository.findLatestRecordForEntityAttribute(self.contextUUID, name + ".py")
        if record:
            if debug: print "  " * self.importLevel,
            if debug: print "  Loading from repository"
            #file = StringIO.StringIO(record.valueBytes)
            #try:
            #module = imp.load_source(name, name, file)
            #print module
            modifiedName = self.contextUUID[7:] + "." + name
            modifiedName = modifiedName.replace("-", "_")
            if debug: print "modifiedName", modifiedName
            if debug: print "sys.module.items", sys.modules.items()
            try:
                module = sys.modules[modifiedName]
            except KeyError:
                module = None
            # use the latest if this one is not
            if module:
                if module.__pointrelIdentifier__ != record.identifierString:
                    module = None
            if not module:
                file = ByteArrayInputStream(record.valueBytes)
                module = imp.load_module(modifiedName, file, modifiedName + ".py", (".py", "r", imp.PY_SOURCE))
                module.__pointrelIdentifier__ = record.identifierString
            if fromlist:
                if debug: print "  " * self.importLevel,
                if debug: print "processing fromlist"
                for fromItemName in fromlist:
                    if debug: print "  " * self.importLevel,
                    if debug: print "fromitemname", fromItemName
                    if fromItemName == "*":
                        for moduleItemName in dir(module):
                            if debug: print "  " * self.importLevel,
                            if debug: print "moduleItemName", moduleItemName
                            if moduleItemName[1] != '_':
                                result = getattr(module, moduleItemName)
                                #print "  " * self.importLevel,
                                #print "result", result
                                #print "  " * self.importLevel,
                                #print "globals", globals
                                globals[moduleItemName] = result
                    else:
                        result = getattr(module, fromItemName)
                        globals[fromItemName] = result
                        if debug: print "finished set", fromItemName
                
            #finally:
            #    file.close()
            if debug: print "  " * self.importLevel,
            if debug: print "  Done loading"
            self.importLevel -= 1
            result = module
        else:
            if debug: print "  " * self.importLevel,
            if debug: print "default loading", name, fromlist
            try:
                result = self.oldimport(name, globals, locals, fromlist)
            except UnboundLocalError:
                # deal with strange Jython error
                result = self.oldimport(name)
            self.importLevel -= 1
        return result
    
    def importFromOtherRepository(self, event):
        dialog = FileDialog(self.window, loadOrSave="load")
        fileName = dialog.go(PointrelFileTypes)
        if not fileName:
            return
        
        print "Importing from: ", fileName
        self.repository.importRecordsFromAnotherRepository(fileName)
        print "Done with import"
        
        self.refreshBrowser()
    
    def exportChooseCurrentFile(self, event):
        dialog = FileDialog(self.window, loadOrSave="save")
        fileName = dialog.go(PointrelFileTypes)
        if not fileName:
            return
        self.exportFileName = fileName
        print "File selected for exports:", self.exportFileName
             
    def exportSelectedRecord(self, event):
        if not self.currentRecord:
            print "No record selected"
            return
        oldRecords = [self.currentRecord]
        print "Exporting current record to repository %s" % self.exportFileName
        repository = Repository(self.exportFileName)
        repository.addRecordsFromAnotherRepository(oldRecords)
        print "Done"
    
    def exportAllRecordsForSelectedAttribute(self, event):
        entityName = self.getCurrentEntityName()
        if not entityName:
           print "No entity selected" 
           return
        attributeName = self.getCurrentAttributeName()
        if not attributeName:
           print "No attribute selected"   
           return   
        print "Exporting all records for entity '%s' attribute '%s' to repository %s" % (entityName, attributeName, self.exportFileName)
        oldRecords = self.repository.findAllRecordsForEntityAttribute(entityName, attributeName)
        oldRecords.reverse()
        repository = Repository(self.exportFileName)
        repository.addRecordsFromAnotherRepository(oldRecords)
        print "Done"
            
    def exportLatestRecordsForSelectedEntity(self, event):
        entityName = self.getCurrentEntityName()
        if not entityName:
           print "No entity selected" 
           return
        print "Exporting latest records for all entity '%s' attributes to repository %s" % (entityName, self.exportFileName)
        oldRecords = self.repository.findLatestRecordsForAllEntityAttributes(entityName)
        oldRecords.reverse()
        repository = Repository(self.exportFileName)
        repository.addRecordsFromAnotherRepository(oldRecords)
        print "Done"
        
    def exportAllRecordsForSelectedEntity(self, event):
        entityName = self.getCurrentEntityName()
        if not entityName:
           print "No entity selected" 
           return
        print "Exporting all records for entity '%s' to repository %s" % (entityName, self.exportFileName)
        oldRecords = self.repository.findAllRecordsForEntity(entityName)
        oldRecords.reverse()
        repository = Repository(self.exportFileName)
        repository.addRecordsFromAnotherRepository(oldRecords)
        print "Done"
               
    def setCurrentRecord(self, aRecord):
        self.currentRecord = aRecord
        if aRecord:
            self.setCurrentEntityName(aRecord.entity)
            self.entityTextField.caretPosition = 0
            self.setCurrentAttributeName(aRecord.attribute)
            self.attributeTextField.caretPosition = 0
            self.setCurrentValueType(aRecord.valueType)
            self.currentEditorPanel.setCurrentValueBytes(aRecord.valueBytes)
            self.deletedButton.model.setSelected(aRecord.deleted)
        else:
            entityName = self.entitiesList.selectedValue
            if entityName == None:
                entityName = ""
            self.setCurrentEntityName(entityName)
            self.entityTextField.caretPosition = 0
            self.setCurrentAttributeName("")
            self.setCurrentValueType(DefaultValueType)
            self.currentEditorPanel.setCurrentValueBytes("") 
            self.deletedButton.model.selected = False
                
    def manageSaveButtonColor(self):
        if self.isCurrentRecordChanged():
            self.saveButton.background = self.changedSaveButtonColor
        else:
            self.saveButton.background = self.normalSaveButtonColor
            
    def isCurrentRecordChanged(self):
        if not self.currentRecord:
            if self.getCurrentAttributeName() or self.currentEditorPanel.getCurrentValueBytes():
                return True
            return False
        if self.getCurrentEntityName() != self.currentRecord.entity:
            return True
        if self.getCurrentAttributeName() != self.currentRecord.attribute:
            return True
        if self.getCurrentValueType() != self.currentRecord.valueType:
            return True
        if self.currentEditorPanel.isChangedFromOriginal():
             return True
        # funky comparison because may be booleans and integers?
        # decided not to test as not really linked to save button
        #if (self.deletedButton.model.selected and not self.currentRecord.deleted) or (not self.deletedButton.model.selected and self.currentRecord.deleted):
        #    return True
        return False

    def deletedPressed(self, event):
        deleteFlag = self.deletedButton.model.selected
        if self.currentRecord == None:
            return 
        self.repository.deleteOrUndelete(self.currentRecord, self.currentUserReference, deleteFlag=deleteFlag)
        if not self.isDeletedViewable():
            self.refreshBrowser()
            
    def refreshBrowser(self):
        entityName = self.entitiesList.selectedValue
        attributeName = self.attributesList.selectedValue
        versionName = self.versionsList.selectedValue
        self.entitiesListClicked(None, entityName, attributeName, versionName)
                    
    def showAllDeletedPressed(self, event):
        self.refreshBrowser()
        
    def isDeletedViewable(self):
        return self.showAllDeletedButton.model.selected
                  
    def savePressed(self, event):
        #entityName = self.entitiesList.selectedValue
        entityName = self.getCurrentEntityName()
        if entityName:
            attributeName = self.getCurrentAttributeName()
            if attributeName:
                attributeValue = self.currentEditorPanel.getCurrentValueBytes()
                attributeType = self.getCurrentValueType()
                newRecord = self.repository.add(entityName, attributeName, attributeValue, attributeType, self.currentUserReference)
                self.setCurrentRecord(newRecord)
                self.entitiesListClicked(None, self.entitiesList.selectedValue, attributeName)
                # refresh list if changed
                if attributeName != self.attributesList.selectedValue:
                    # ? self.attributesList.model.addElement(attributeName)
                    # need to select new version
                    self.entitiesListClicked(None)
                        
    def test(self):
        print "test OK"

    def clearAllEntityNames(self):
        self.entitiesList.model.clear()
        self.addEntityNameToEntitiesList("root")
            
    def deleteEntityNameFromList(self):
        entityName = self.entitiesList.selectedValue
        if entityName:
           self.entitiesList.model.removeElement(entityName)
            
    def addEntitytNameToList(self):
        entityName = JOptionPane.showInputDialog("Enter an entity name: ")
        if entityName:
            self.addEntityNameToEntitiesList(entityName)
            
    def addAllEntityNamesToList(self, addMeta):
        entityNames = self.repository.lastUser.keys()
        entityNames.sort()
        for entityName in entityNames:
            if addMeta or entityName.find("pointrel://tripleID/") != 0:
                self.addEntityNameToEntitiesList(entityName)
           
    def entitiesListMousePressed(self, event):
        if event.isPopupTrigger():
            # options should be a list of (name, function, [arg1, [arg2]]) tuples
            options = [
                       ("add to list..", self.addEntitytNameToList),
                       ("delete from list", self.deleteEntityNameFromList), 
                       (None),
                       ("clear", self.clearAllEntityNames), 
                       (None),
                       ("add all except meta", self.addAllEntityNamesToList, False), 
                       ("add all", self.addAllEntityNamesToList, True), 
                       ]
            menu = OptionsCallbackPopupMenu(event.component, event.x, event.y, options)

    def entitiesListClicked(self, event, entityName=None, attributeName=None, versionName=None):
        if event:
            self.setCurrentRecord(None)
        if entityName:
            self.entitiesList.setSelectedValue(entityName, True)
        else:
            entityName = self.entitiesList.selectedValue
        if entityName:
            self.versionsList.model.clear()
            model = self.attributesList.model 
            model.clear()
            attributes = self.repository.allAttributesForEntity(entityName, self.isDeletedViewable())
            attributes.sort()
            for attribute in attributes:
                model.addElement(attribute)
            if attributeName:
                self.attributesList.setSelectedValue(attributeName, True)
                self.attributesListClicked(None, versionName)
        
    def attributesListClicked(self, event, versionName=None):
        if event:
            self.setCurrentRecord(None)
        entityName = self.entitiesList.selectedValue
        if entityName:
            attributeName = self.attributesList.selectedValue
            if event:
                self.setCurrentAttributeName(attributeName)
            if attributeName:
                model = self.versionsList.model 
                model.clear()
                versions = self.repository.findAllRecordsForEntityAttribute(entityName, attributeName, self.isDeletedViewable())
                for version in versions:
                    versionDescription = "%s %s" % (version.timestamp, version.userReference)
                    model.addElement(versionDescription)
                selectedRecord = None
                if versions:
                    if versionName == None or not model.contains(versionName):
                        self.versionsList.selectedIndex = 0
                        selectedRecord = versions[0]
                    else:
                        versionIndex = model.indexOf(versionName)
                        self.versionsList.selectedIndex = versionIndex
                        selectedRecord = versions[versionIndex]
                self.setCurrentRecord(selectedRecord)
        
                if event and event.clickCount == 2:
                    self.followResource(self.currentRecord)
            else:
                self.setCurrentRecord(None)
        else:
            self.setCurrentRecord(None)
                    
    def versionsListClicked(self, event):
        entityName = self.entitiesList.selectedValue
        if entityName:
            attributeName = self.attributesList.selectedValue
            if event:
                self.setCurrentAttributeName(attributeName)
            if attributeName:
                index = self.versionsList.selectedIndex
                versions = self.repository.findAllRecordsForEntityAttribute(entityName, attributeName, self.isDeletedViewable())
                if versions:
                    versionRecord = versions[index]
                    self.setCurrentRecord(versionRecord)

                    if event and event.clickCount == 2:
                        self.followResource(versionRecord)
                else:
                    self.setCurrentRecord(None)
                    
    def followResource(self, record):
        if not record:
            return
        if '\n' in record.valueBytes:
            print "not following a resource with a newline"
            return
        self.addEntityNameToEntitiesList(record.valueBytes)

    def addEntityNameToEntitiesList(self, entityName):
        self.entitiesList.model.addElement(entityName)
        self.entitiesList.selectedIndex = self.entitiesList.model.size() - 1
        self.entitiesListClicked(None)
        self.setCurrentRecord(None)
                
def test():
    fileName = File(DEFAULT_REPOSITORY_NAME).absolutePath
    #print "fileName", fileName
    repository = Repository(fileName)
    b = Browser(repository)    

if __name__ == "__main__":
    test()

    
