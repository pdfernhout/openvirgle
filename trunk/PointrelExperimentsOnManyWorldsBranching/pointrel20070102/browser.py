from mySwingSupport import *

from pointrel20070102 import Repository

class Browser:
    def __init__(self):
        self.selectedNode = "root"
                
        self.window = JFrame("Pointrel browser", windowClosing=self.exit)
        self.window.contentPane.layout = BorderLayout() # redundant as the default
        self.window.bounds = (100, 100, 800, 600)
                
        self.pathList = JList(DefaultListModel(), mouseClicked=self.pathListClicked)
        self.pathList.model.addElement("root")
        self.attributesList = JList(DefaultListModel(), mouseClicked=self.attributesListClicked)
        
        self.listPanel = JPanel(layout=GridLayout(1, 2))
        self.listPanel.add(JScrollPane(self.pathList))
        self.listPanel.add(JScrollPane(self.attributesList))
        
        self.currentEditor = JTextPane()
        
        self.updateButton = JButton("update", actionPerformed=self.updatePressed)
        self.saveButton = JButton("save", actionPerformed=self.savePressed)
        self.newAttributeTextField = JTextField(preferredSize=(100,20))
        self.addAttributeButton = JButton("new attribute", actionPerformed=self.addAttributePressed)

        self.buttonPanel = Box(BoxLayout.X_AXIS) 
        self.buttonPanel.add(self.updateButton)
        self.buttonPanel.add(self.saveButton)
        self.buttonPanel.add(self.newAttributeTextField)
        self.buttonPanel.add(self.addAttributeButton)
        
        self.editorPanel = JPanel(layout=BorderLayout())
        self.editorPanel.add(JScrollPane(self.currentEditor), BorderLayout.CENTER)
        self.editorPanel.add(self.buttonPanel, BorderLayout.NORTH)
        
        self.browserPanel = JPanel(layout=GridLayout(2, 1)) # Box(BoxLayout.Y_AXIS)
        self.browserPanel.add(self.listPanel)
        self.browserPanel.add(self.editorPanel)
        
        self.window.contentPane.add(self.browserPanel, BorderLayout.CENTER)
        
        self.window.show()
        
    def exit(self, event=None):
        java.lang.System.exit(0)
        
    def updatePressed(self, event):
        print "update pressed"
        
    def savePressed(self, event):
        print "save pressed"
        r = Repository()
        selectedNode = self.pathList.selectedValue
        if selectedNode:
            selectedID = r.symbolIndexForString(selectedNode)
            attributeName = self.attributesList.selectedValue
            if attributeName:
                attributeID = r.symbolIndexForString(attributeName)
                attributeValue = self.currentEditor.text
                valueID = r.symbolIndexForString(attributeValue)
                result = r.add(selectedID, attributeID, valueID)
                print "Result", result
        
    def addAttributePressed(self, event):
        print "add atribute pressed"
        selectedNode = self.pathList.selectedValue
        if selectedNode:
            attributeName = self.newAttributeTextField.text
            if attributeName:
                attributeValue = self.currentEditor.text
                print "attributeName", attributeName
                print "value", attributeValue
                r = Repository()
                selectedID = r.symbolIndexForString(selectedNode) 
                attributeID = r.symbolIndexForString(attributeName)
                valueID = r.symbolIndexForString(attributeValue)
                result = r.add(selectedID, attributeID, valueID)
                print "Result", result
                # refresh list
                self.pathListClicked(None)
        
    def pathListClicked(self, event):
        print "path changed"
        selectedNode = self.pathList.selectedValue
        if selectedNode:
            r = Repository()
            model = self.attributesList.model 
            model.clear()
            if selectedNode:
                selectedID = r.symbolIndexForString(selectedNode)
                attributes = r.collectAttributes(selectedID)
                print attributes
                
                for attribute in attributes:
                    attributeName = r.stringForSymbolIndex(attribute)
                    model.addElement(attributeName)
        
    def attributesListClicked(self, event):
        print "attributesListClicked"
        print dir(event)
        print event.class

        selectedNode = self.pathList.selectedValue
        if selectedNode:
            attributeName = self.attributesList.selectedValue
            print "attributeName", attributeName
            if attributeName:
                r = Repository()
                selectedID = r.symbolIndexForString(selectedNode) 
                attributeID = r.symbolIndexForString(attributeName)
                attributeValueID = r.find(selectedID, attributeID)
                print "Result", attributeValueID
                if attributeValueID:
                    attributeValue = r.stringForSymbolIndex(attributeValueID)
                    print "attributeValue", attributeValue
                else:
                    attributeValue = "PROBLEM"
                self.currentEditor.text = attributeValue
        
                if event.clickCount == 2:
                    print "double click"
                    self.pathList.model.addElement(attributeValue)
            
                
def test():
    if 1:
        import reloader
        window = reloader.ReloaderWindow()
        window.setVisible(1)
    b = Browser()    

if __name__ == "__main__":
    test()

    
