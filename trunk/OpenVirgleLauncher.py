from support import *
        
# a simple window with a button that can make more buttons.
# intended as target for a JVM/Swing-specific object inspector
class MyWindow:
    def __init__(self):
        self.newButtonCounter = 0
        self.buildFrame()
        
    def buildFrame(self):
        self.frame = JFrame("Hello Jython")
        self.frame.name = "MyWindow"
        self.frame.rootPane.putClientProperty("model", self)
        self.frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
        self.frame.setSize(300, 300)

        self.box = Box(BoxLayout.PAGE_AXIS)
        self.box.name = "box"
        self.frame.add(self.box)

        self.label = JLabel("Hello Jython!", JLabel.CENTER)
        self.label.name = "label"
        self.box.add(self.label)

        self.button1 = JButton("Button one -- make another button")
        self.button1.name = "button1"
        self.button1.addActionListener(DynamicActionListener("button1_actionPerformed"))
        self.box.add(self.button1)
        
        self.button2 = JButton("Button Two -- launch3DWindow")
        self.button2.name = "button2"
        self.button2.addActionListener(DynamicActionListener("launch3DWindow"))
        self.box.add(self.button2)

        self.button3 = JButton("Button Three -- opens a new launcher window")
        self.button3.name = "button2"
        self.button3.addActionListener(DynamicActionListener("launchNewWindow"))
        self.box.add(self.button3)

    def button1_actionPerformed(self, event):
        print "button1pressed", event
        self.newButtonCounter += 1
        buttonName = "testButton%d" % self.newButtonCounter
        newButton = JButton(buttonName)
        newButton.name = buttonName
        newButton.addActionListener(DynamicActionListener("testButtonPressed"))
        newButton.addActionListener(DynamicActionListener("hello"))
        self.box.add(newButton)
        self.box.validate()

    def testButtonPressed(self, event):
        print "test button pressed, name: '%s'" % event.source.name
        button = event.source
        
    def launch3DWindow(self, event):
        import OpenVirgleVisualize
        OpenVirgleVisualize.test()
        
    def launchNewWindow(self, event):
        window = MyWindow()
        window.frame.visible = 1
        
def test():
    window = MyWindow()
    window.frame.visible = 1

if __name__ == "__main__":
    test()