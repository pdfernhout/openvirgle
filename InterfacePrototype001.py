"""
Re: Next step in information gathering
mike1937
04/21/2008 07:02 PM

I drew a picture of what I'd like a GUI interface to look like
eventually, It's messy, made worse by corruption during upload:

http://home.comcast.net/~arid_shadow/interface.png

It includes some features that I like that I have only seen alluded to
earlier:
-each wiki object is made up of a folder with many seperate files
-Automatic adding to a ontology is allowed (the vocabulary field can
also be left empty, or map to an existing one)
-Seperate pages for editting and querying
-preferably all interface is in the browser (if thats possible)
"""

from support import *
import browser

class InterfacePrototype001:
    def __init__(self):
        self.newButtonCounter = 0
        self.buildFrame()
       
    def buildFrame(self):
        self.frame = JFrame("InterfacePrototype001")
        self.frame.name = "InterfacePrototype001"
        self.frame.rootPane.putClientProperty("model", self)
        self.frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
        self.frame.setSize(800, 600)

        self.box = Box(BoxLayout.PAGE_AXIS)
        self.frame.add(self.box)

        self.box1 = JPanel() #Box(BoxLayout.LINE_AXIS)
        self.label1 = JLabel("Title")
        self.box1.add(self.label1)
        self.edit1 = JTextField(20)
        self.box1.add(self.edit1)
        
        self.box.add(self.box1)
        
        self.box2 = JPanel() #Box(BoxLayout.LINE_AXIS)
        self.label2 = JLabel("UUID")
        self.box2.add(self.label2)
        self.edit2 = JTextField(20)
        self.box2.add(self.edit2)
        
        self.box.add(self.box2)
        
        self.frame.add(self.box, BorderLayout.NORTH)
        
        self.text = JTextPane()
        self.frame.add(self.text, BorderLayout.CENTER)
        
        self.box3 = Box(BoxLayout.PAGE_AXIS)
        
        self.fileNamesList = JList(DefaultListModel())
        #self.fileNamesList.add(DynamicMouseListener())
        self.box3.add(self.fileNamesList)
        
        self.addButton = JButton("Add file")
        self.addButton.addActionListener(DynamicActionListener("addFile")) 
        self.box3.add(self.addButton)
        
        self.frame.add(self.box3, BorderLayout.EAST)

    def addFile(self, event):
        print "add file"
        dialog = browser.FileDialog(self.frame)
        fileName = dialog.go([("cad", "CAD file")])
        if not fileName:
            return
        print fileName
        self.fileNamesList.model.addElement(fileName)
        
