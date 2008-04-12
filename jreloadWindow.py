"""
ReloaderWindow

TO USE: add this code to your startup script under Jython:

    import jreloadWindow
    window = jreloadWindow.ReloaderWindow()
    window.visible = 1
    
Currently the reloader can not reload code which is the main module. 
So, you also need to import your code from some other module (like a tests.py) so the reloader can reload it as a module.
So in a tests.py or startup.py, do something like:

    import MyWindow
    MyWindow.test()
    
(or whatever makes sense for your code) and then you should be able to reload the "MyWindow" module as needed.
The system currently only reloads code files in the current directory.

Author: Paul D. Fernhout 
Copyright 2005, 2007, 2008
Released under the Python/Jython license
Version 0.1 2005-12-31 -- Initial release
Version 0.2 2006-01-14 -- Improved copying (using Michael Spencer's suggestions and code ideas) and removed custom file parsing
May now be able to do recursive updates. No longer dependent on parsing a specifically indented file.
Version 0.3 2007-08-24 added support for GTK
Version 0.4 2008-03-03 removed support for GTK for PataPata version; better error handling
Version 0.5 2008-03-24 changed from Michael Spencer's approach to Guido's xreload approach (with patches) 
to hopefully deal with number of arguemnts changing to funciton and adding method functions

Inspired by how Smalltalk handles method changes...

This does a special reload of modules to update the functions in existing classes.
In order to work as expected the reloaded module probably should not be too fancy
in terms of producing a lot of side effects in the system 
when loaded other than defining classes.

Note: this was written for Jython/Swing, 
but this technique should also work for Python with a different GUI

Note: All top level variable definitions are now updated. 
This could pose a problem for you if you store program sate in such globals in moduels you intend to reload.
One solution might be to store such global data in a special module with just globals which you never reload.

Note: You will likely still need to restart your program occasionally, 
and also  otherwise close and open windows to get changes for new components in __init__,
but maybe only one tenth the time when you can't reload
assuming most changes are adding or changing methods of windows.

Note: If your program starts behaving oddly after using the reloader, 
completely restart it to be sure it is not a reloading introduced problem.

Note: if your program uses threads or in some other way
might be doing things with the code when it is reloaded,
I am not sure what will happen.

Note: This code assumes your project runs where the source code is located. 
It only shows you modules in the current directory to reload.

Note: trying to reload the reloader window is not recommended, but may sometimes work.
Any exceptions when reloading fixes to a buggy reloader version may be confusing 
as Jython will be running the old code to load the new until it succeeeds
which may be impossible without a clean restart if you broke the reloader.
Also, any changes to the initialization of the reloader window would not
be seen until the window is closed and reopened (which currently exits the JVM).
    
"""

# PROBLEM CALLING SUPER AFTER RELOAD WITH DOUBLE UNDERSCORE (??? Need to check still happens with jreload)

from javax.swing import JFrame, JMenuBar, JMenu, JMenuItem, JList, DefaultListModel, JScrollPane, JButton, JPanel, JOptionPane
from java.awt import BorderLayout
from java.lang import System

import sys
import glob
import jreload

class ReloaderWindow(JFrame):
    def __init__(self, title="Development Reloader Window"):
        JFrame.__init__(self, title, windowClosing=self.OnClose)
        self.setBounds(0, 0, 300, 550)
            
        self.BuildWindow()

    def BuildWindow(self):
        contentPane = self.getContentPane()
        contentPane.setLayout(BorderLayout())
        self.fileListUpdateButton = JButton("Update file list", actionPerformed=self.OnUpdateFileList)
        self.fileNamesList = JList(DefaultListModel(), mouseClicked=self.mouseClicked)
        self.specialReloadButton = JButton("Special reload module (or double click)", actionPerformed=self.OnSpecialReloadOfModule)
        contentPane.add("North", self.fileListUpdateButton)
        contentPane.add("Center", JScrollPane(self.fileNamesList))
        reloadButtonPanel = JPanel(BorderLayout())
        reloadButtonPanel.add("North", self.specialReloadButton)
        contentPane.add("South", reloadButtonPanel)

        self.loadFileList()

    def loadFileList(self):
        pythonFileNames = glob.glob("./*.py")
        pythonFileNames.sort()
        localModuleNames = []
        usedModulesNames = []
        for pythonFileName in pythonFileNames:
            shortName = pythonFileName[2:-3]
            #if shortName == "reloader":
            #    continue
            if pythonFileName in sys.modules:
                usedModulesNames.apend(shortName)
            localModuleNames.append(shortName)
                
        #if not usedModulesNames:
        #    result = JOptionPane.showMessageDialog(self, "This program has no modules in use from the local directory", "No files to reload", JOptionPane.OK_OPTION)
            
        self.fileNamesList.getModel().clear()
        for moduleName in localModuleNames:
            self.fileNamesList.getModel().addElement(moduleName)
        
    def mouseClicked(self, eventOrWidget, gtkEvent=None):
        isDoubleClick = eventOrWidget.clickCount == 2
        if isDoubleClick:
            self.OnSpecialReloadOfModule(eventOrWidget)
            
    def OnUpdateFileList(self, event):
        self.loadFileList()
            
    def OnSpecialReloadOfModule(self, event):
        moduleName = self.fileNamesList.getSelectedValue()
        print "Module to reload:", moduleName
        if moduleName:
            self.SpecialReloadForModule(moduleName)
    
    def OnTestSpecialReloadOfModule(self, event):
        print "do some special test thing here if menu enabled"
        
    def OnClose(self, event):
        print "Shutting down via the reloader window"
        System.exit(0)
        
    def warningForModuleNotLoaded(self, moduleName):
        if moduleName == "reloader":
            message = "The reloader module was run directly as the main module and so can't be reloaded"
        else:
            message = "The selected module %s is not currently loaded by this program\nor it was run directly as __main__ and not imported." % moduleName
        result = JOptionPane.showMessageDialog(self, message, "Module not loaded", JOptionPane.OK_OPTION)

    def SpecialReloadForModule(self, moduleName):
        try:
            oldModule = sys.modules[moduleName]
        except KeyError:
            self.warningForModuleNotLoaded(moduleName)
            return
        print "==== starting special reload of module", moduleName
        jreload.jreload(oldModule, moduleName)
        print "\n===== done with special reload\n"  

def main():
    window = ReloaderWindow()
    window.setVisible(1)
    
if __name__ == "__main__":
    main()
    