# Notes: copied inspect.py, dis.py, and opcodes.py into Jython dir (replacing stub inspect.py)
# Opcode will not work as using JVM, but required by dis.py, which was required by inspect.py
# only want functionality of getting source lines.
# Also copied textwrap.py?

# support for using tk
import java.io
from java.lang import Class, Runnable, Thread
import javax.swing.filechooser
from javax.swing import SwingUtilities, SwingConstants, \
        AbstractAction, BorderFactory, Box, BoxLayout, ImageIcon, \
        JDialog, JFrame, JScrollPane, JPanel, JComponent, JSplitPane, JTabbedPane, \
        JColorChooser, JOptionPane, JFileChooser, \
        JTextArea, JTextField, JLabel, JPasswordField, JEditorPane, JTextPane, \
        JButton, JCheckBox, \
        JMenuItem, JCheckBoxMenuItem, JMenuBar, JMenu, JPopupMenu, KeyStroke, \
        JTree, \
        JComboBox, DefaultComboBoxModel, \
        JTable, \
        JList, ListSelectionModel, DefaultListCellRenderer, DefaultListModel, \
        JSlider, \
        TransferHandler
from javax.swing.table import DefaultTableModel, DefaultTableCellRenderer
from javax.swing.event import ChangeListener, TreeSelectionListener, ListSelectionListener, HyperlinkEvent, TableModelListener
from java.awt.event import ActionListener, MouseAdapter, MouseMotionAdapter, MouseEvent, WindowFocusListener, MouseListener, KeyAdapter, KeyEvent
from javax.swing.text.html import HTMLEditorKit, FormView, HTML
from javax.swing.text import StyleConstants
from javax.swing.tree import DefaultMutableTreeNode, DefaultTreeModel, DefaultTreeCellRenderer, TreePath
from javax.swing.border import BevelBorder

from java.awt import Color, Cursor, BorderLayout, FlowLayout, Font, Dimension, Rectangle, Component, Polygon, Point, GridLayout, GridBagLayout, BasicStroke, Toolkit
from pawt import GridBag
from java.awt.datatransfer import DataFlavor, Transferable
from java.awt.dnd import DropTarget, DnDConstants, DropTargetAdapter, DragSourceListener, \
        DragGestureListener, DragSource, DragSourceAdapter
from java.awt.image import BufferedImage

import os, os.path

#############  useful classes that are not Swing specific #########

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __repr__(self):
        return "Point(%s, %s)" % (self.x, self.y)

class MouseEvent:
    def __init__(self, isMeta, eventName, downPosition, previousPosition, currentPosition, upPosition):
        self.isMeta = isMeta
        self.eventName = eventName
        self.downPosition = downPosition
        self.previousPosition = previousPosition
        self.currentPosition = currentPosition
        self.upPosition = upPosition

   
# Support for late binding calls to methods for PrototypeMethod references passed to Swing
# This means methods edited in the system will have their changes called by Swing widgets 
# even if they are edited after the widget was created
# Example:
# Instead of: self.widget.bind("<ButtonRelease-1>", self.OnMouseEventButton1Up)
# Use:        self.widget.bind("<ButtonRelease-1>", LateBindWrapper(self, "OnMouseEventButton1Up"))

class LateBindWrapper:
    def __init__(self, receiver, methodName, methodIsOptional=0, extraArg=None):
        self.receiver = receiver
        self.methodName = methodName
        self.methodIsOptional = methodIsOptional
        self.extraArg = extraArg
        
    def __call__(self, *args, **kwargs):
        if not self.receiver.hasProperty(self.methodName):
            if not self.methodIsOptional:
                raise AttributeError, self.methodName
            return None
        function = getattr(self.receiver, self.methodName)
        if self.extraArg:
            return function(self.extraArg, *args, **kwargs)
        else:
            return function(*args, **kwargs)
   
# used to provide "components" attribute in Morph for PythonCard compatability.
class IndirectAttributeAccessor:
    def __init__(self, receiver, methodName):
        self._receiver = receiver
        self._methodName = methodName
        
    def __getattr__(self, name):
        function = getattr(self._receiver, self._methodName)
        result = function(name)
        if result == None:
            raise AttributeError, name
        return result

# Support for window management
def WorldShouldNoLongerBeUsedAsInspector(root, world):
    # make sure no one still using this window as inspector
    for window in root.openWindows:
        if window.inspectorWorld == world:
            window.inspectorWorld = None    

def WindowShouldNoLongerHaveInspector(root, windowToClose, otherWindowsToClose):
    # make sure no inspector is still hooked to this window
    for window in root.openWindows:
        #print window, window.inspectorForViewer
        # PDF FIX BROKEN
        if window.inspectorForViewer and window.inspectorForViewer == windowToClose:
            #print "found window"
            window.inspectorForViewer = None
            window._updateTitle()
            otherWindowsToClose.append(window)

def ExposeWindow(root, window):
    # keep exposed window at end of list
    root.openWindows.remove(window)
    root.openWindows.append(window)

# close a window and related inspector (and its inspector's inspector etc.)
def CloseWindow(root, window):
    otherWindowsToClose = []
    WorldShouldNoLongerBeUsedAsInspector(root, window.world)
    WindowShouldNoLongerHaveInspector(root, window, otherWindowsToClose)
    window.world.removeMorph(window)
    if window in root.openWindows:
        root.openWindows.remove(window)
    if not root.openWindows:
        print "all windows closed -- PataPata application shutting down"
        root.quit()
    # close related inspectors
    if otherWindowsToClose:
        for otherWindow in otherWindowsToClose:
            CloseWindow(root, otherWindow)

    
# debugging 
class WrappedOutput:
    def __init__(self, oldStream):
        self.oldStream = oldStream
        
    def write(self, text):
        raise "write %s" % text
        self.oldStream.write(text)
        if text == None or text == "None":
            raise "Stop"
    
    
# for tree text compoarison
# needs imporovements
def MyCompare(a, b):
    """ ensure that things with brackets sort after text """
    if type(a) in (str, unicode):
        aText = a
    else:
        aText = a.GetText()
    if type(b) in (str, unicode):
        bText = b
    else:
        bText = b.GetText()
    inheritedText = "[Inherited] "
    if not aText[0].isalnum() and not bText[0].isalnum():
        if aText.find(inheritedText) == 0 and bText.find(inheritedText) == 0:
            return MyCompare(aText[len(inheritedText):], bText[len(inheritedText):])
        return cmp(aText, bText)
    elif not aText[0].isalnum():
        return 1
    elif not bText[0].isalnum():
        return -1
    else:
        return cmp(aText, bText)
                
####################################################
         
# utility function
def GetNewText(parent, oldText="", prompt="Enter the new text", title="Text input"):
    # PDF FIX -- does not use title
    return JOptionPane.showInputDialog(parent, prompt, oldText)

def ShowMessage(parent, messageText="Something happened", title="Message"):
    JOptionPane.showMessageDialog(parent, messageText, title, JOptionPane.PLAIN_MESSAGE)

class OptionsCallbackPopupMenu:
    # options should be a list of (name, function, [arg1, [arg2]]) tuples
    def __init__(self, parent, x, y, options, world, extraOptions=None):
        self.world = world
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
        print "OnChoice", option
        if len(option) == 2:
            option[1]()
        elif len(option) == 3:
            option[1](option[2])
        elif len(option) == 4:
            option[1](option[2], option[3])
            
def BindCommonEvents(morph, subwidget=None):
    if subwidget:
        widget = subwidget
    else:
        widget = morph.widget
    # PDF FIX PORT
    """
    widget.bind("<FocusIn>", LateBindWrapper(morph, "gainFocus"))
    widget.bind("<FocusOut>", LateBindWrapper(morph, "loseFocus"))
    widget.bind("<Enter>", LateBindWrapper(morph, "mouseEnter"))
    widget.bind("<Leave>", LateBindWrapper(morph, "mouseLeave"))
    $$widget.bind("<Motion>", LateBindWrapper(morph, "mouseMove"))
    $$widget.bind("<ButtonPress-1>", LateBindWrapper(morph, "mouseDown"))
    $$widget.bind("<ButtonRelease-1>", LateBindWrapper(morph, "mouseUp"))
    $$widget.bind("<B1-Motion>", LateBindWrapper(morph, "mouseDrag"))
    widget.bind("<Double-Button-1>", LateBindWrapper(morph, "mouseDoubleClick"))
    widget.bind("<ButtonPress-2>", LateBindWrapper(morph, "mouseMiddleDown"))
    widget.bind("<ButtonRelease-2>", LateBindWrapper(morph, "mouseMiddleUp"))
    widget.bind("<Double-Button-2>", LateBindWrapper(morph, "mouseMiddleDoubleClick"))
    # these three may depend on meaning of context -- maybe mouse plus another key on Mac?
    $$widget.bind("<ButtonPress-3>", LateBindWrapper(morph, "mouseContextDown"))
    $$widget.bind("<ButtonRelease-3>", LateBindWrapper(morph, "mouseContextUp"))
    widget.bind("<Double-Button-3>", LateBindWrapper(morph, "mouseContextDoubleClick"))
    """

    widget.addMouseMotionListener(CallbackMouseMotionListener("", LateBindWrapper(morph, "mouseMove"), LateBindWrapper(morph, "mouseDrag")))
    widget.addMouseListener(CallbackLeftMouseButtonListener("", LateBindWrapper(morph, "mouseDown"), LateBindWrapper(morph, "mouseUp")))
    widget.addMouseListener(CallbackRightMouseButtonListener("", LateBindWrapper(morph, "mouseContextDown"), LateBindWrapper(morph, "mouseContextUp")))
    widget.mouseEntered = LateBindWrapper(morph, "mouseEnter")
    widget.mouseExited = LateBindWrapper(morph, "mouseLeave")
            
# PDF FIX UNFINISHED

class MyTreeNodeWithItem(DefaultMutableTreeNode):
    def __init__(self, item):
        self.item = item
        self.userObject = item.GetText()
        self.areChildrenDefined = 0
        
    def getChildCount(self):
        if not self.areChildrenDefined:
            self.defineChildNodes()
        return DefaultMutableTreeNode.getChildCount(self)
    
    def defineChildNodes(self):
        self.areChildrenDefined = 1
        if self.item.IsExpandable():
            childItems = self.item.GetSubList()
            for item in childItems:
                newNode = MyTreeNodeWithItem(item)
                #newNode.setParent(self)
                self.add(newNode)
                
    def collapsed(self, tree):
        self.removeAllChildren()
        self.areChildrenDefined = 0
        tree.model.nodeStructureChanged(self)

# Support for an inspector tree node
class PrototypeInspectorTreeItem:
#class PrototypeInspectorTreeItem(TreeWidget.TreeItem):
    def __init__(self, parentObject, key, childObject, inheritedFlag):
        self.parentObject = parentObject
        self.key = key
        self.childObject = childObject
        self.inheritedFlag = inheritedFlag
        
    def __str__(self):
        return self.GetText()

    def GetText(self):
        childObject = self.childObject
        extra = ""
        if not hasattr(childObject, "__class__"):
             extra = " : " + `childObject`
        elif not hasattr(childObject, "__dict__") and not type(childObject) in [dict, list]:
            extra = " : " + `childObject`
        elif isinstance(childObject, PrototypeClass):
            extra = " : <Prototype %s> %s" % (`id(childObject)`, childObject.traits)
        elif isinstance(childObject, PrototypeMethod):
            #extra = " : <PrototypeMethod %s>" % childObject.source.split("\n")[0]
            extra = " : <PrototypeMethod %s>" % id(childObject)
        else:
            name = "%s" % childObject.__class__
            unwantedPrefix = "__main__."
            if name.find(unwantedPrefix) == 0:
                name = name[len(unwantedPrefix):]
            extra = " : %s" % name
        if len(extra) > 40:
            extra = extra[:40] + "..."
        result = "%s" % self.key + extra
        if self.inheritedFlag:
            result = "[Inherited] " + result
        return result
    
    def IsEditable(self):
        return 0
    
    def SetText(self, text):
        pass

    def GetIconName(self):
        if not self.IsExpandable():
            return "python" # XXX wish there was a "file" icon

    def IsExpandable(self):
        childObject = self.childObject
        result = (hasattr(childObject, "__dict__") and not isinstance(childObject, PrototypeMethod)) or (type(childObject) in [list, dict])
        return result
    
    def GetSubList(self):
        result = []
        nonInheritedNames = None
        itemObject = self.childObject
        if type(itemObject) == dict:
            names = itemObject.keys()
            names.sort()
        elif type(itemObject) == list:
            names = range(len(itemObject))
        elif isinstance(itemObject, PrototypeClass):
            properties = itemObject.allProperties()
            names = properties.keys()
            names.sort()
            nonInheritedNames = itemObject._attributes.keys()
            nonInheritedNames.sort()
        else:
            names = itemObject.__dict__.keys()
            names.sort()
        for key in names:
            if type(itemObject) in [list, dict]:
                childObject = itemObject[key]
            else:
                # hide the world pointer in all objects, plus other clutter
                if key == "world":
                    continue
                elif key in ["function", "prototypeHoldingTheFunction"] and isinstance(itemObject, PrototypeMethod):
                    continue
                try:
                    childObject = getattr(itemObject, key)
                except AttributeError:
                    # case where property exists, but not local or inherited
                    print "missing property definition for ", key
                    continue
            inheritedFlag = 0
            if nonInheritedNames:
                inheritedFlag = not (key in nonInheritedNames)
            store = PrototypeInspectorTreeItem(itemObject, key, childObject, inheritedFlag)
            result.append(store)
        result.sort(MyCompare)
        return result

# support function to look through children of a tree node and find a match for the key
def InspectorTree_FindChildNodeWithKey(treeMorph, parentNode, key):
    for index in range(0, parentNode.getChildCount()):
        childNode = parentNode.getChildAt(index)
        if childNode.item.key == key:
            return childNode
    return None

def InspectorTree_ScrollToAndSelectChildNodeWithKey(treeMorph, parentNode, key, collapseAndExpandParent=1):
    if collapseAndExpandParent:
        path = TreePath(parentNode.getPath())
        treeMorph._tree.collapsePath(path)
        parentNode.collapsed(treeMorph._tree)
        treeMorph._tree.expandPath(path)
    newNode = InspectorTree_FindChildNodeWithKey(treeMorph, parentNode, key)
    path = TreePath(newNode.getPath())
    treeMorph._tree.makeVisible(path)
    treeMorph._tree.setSelectionPath(path)

def InspectorTree_ScrollToAndSelectNode(treeMorph, node, collapseAndExpandNode=1):
    if collapseAndExpandNode:
        if collapseAndExpandNode != "expandOnly":
            treeMorph._tree.collapsePath(TreePath(node.getPath()))
            node.collapsed(treeMorph._tree)
        treeMorph._tree.expandPath(TreePath(node.getPath()))
    path = TreePath(node.getPath())
    treeMorph._tree.makeVisible(path)
    treeMorph._tree.setSelectionPath(path)
    
def InspectorTree_FindChildNodeWithValue(treeMorph, parentNode, value):
    for index in range(0, parentNode.getChildCount()):
        childNode = parentNode.getChildAt(index)
        if childNode.item.childObject == value:
            return childNode
    return None
  
def InspectorTree_CollapseAndExpandNode(treeMorph, node):
    path = TreePath(node.getPath())
    treeMorph._tree.collapsePath(path)
    node.collapsed(treeMorph._tree)
    treeMorph._tree.expandPath(path)
    
# for CallbackRunnable to be able to get None parameters
class NoParamSpecified:
    pass

class CallbackRunnable(Runnable):
    def __init__(self, callback, param1=NoParamSpecified, param2=NoParamSpecified):
        self.callback = callback
        self.param1 = param1  
        self.param2 = param2  
    def run(self):
        if self.param1 == NoParamSpecified:
            self.callback()
        else:
            if self.param2 == NoParamSpecified:
                self.callback(self.param1)
            else:
                self.callback(self.param1, self.param2)
    def invokeLater(self):
        SwingUtilities.invokeLater(self)
        
########## Newer

def GetNativeFont(font):
    name = font[0]
    # PDF FINISH -- style not handled
    style = Font.PLAIN
    size = font[1]
    return Font(name, style, size)
    
def GetWidthAndHeightForTextInFont(text, font):
    try:
        # idea from: http://today.java.net/pub/a/today/2004/04/22/images.html?page=last
        buffer = BufferedImage(1, 1, BufferedImage.TYPE_INT_RGB)
        g2 = buffer.createGraphics()
        # PDF IMPROVE the correspondance of hints to what is actually used
        #g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON)
        fc = g2.getFontRenderContext()
        bounds = font.getStringBounds(text, fc)
        # HAD FUNKY ERROR WITH COMMA AND getWidth: return int(bounds.geWidth()), int(bounds,getHeight())
        return int(bounds.width), int(bounds.height)
    except:
        print "GetWidthAndHeightForTextInFont exception"
        raise
    
def hexToColor(text):
    r = int(text[0:2], 16)
    g = int(text[2:4], 16)
    b = int(text[4:6], 16)
    return Color(r, g, b)

colorsLookupDictionary = {
    #java colors
    'white': Color.white,
    'black': Color.black,
    'blue': Color.blue,
    'cyan': Color.cyan,
    'dark gray': Color.darkGray,
    'gray': Color.gray,
    'grey': Color.gray,
    'green': Color.green,
    'light gray': Color.lightGray,
    'light grey': Color.lightGray,
    'magenta': Color.magenta,
    'orange': Color.orange,
    'pink': Color.pink,
    'red': Color.red,
    'yellow': Color.yellow,
    # other colors
    'light blue': hexToColor("C0D9D9"),
    'green yellow': hexToColor("93DB70"),
    'medium violet red': hexToColor("DB7093"), 
    'medium goldenrod': hexToColor("EAEAAE"), 
    'plum': hexToColor("EAADEA"), 
    'tan': hexToColor("DB9370"), 
    'turquoise': hexToColor("ADEAEA"), 
    'spring green': hexToColor("00FF7F"), 
    'orange red': hexToColor("FF2400"), 
    'goldenrod': hexToColor("DBDB70"), 
    'purple': hexToColor("800080"), 
    'light purple': hexToColor("C000C0"), 
    'sienna': hexToColor("A0522D"), 
    'slate blue': hexToColor("007FFF"), 
    'sea green': hexToColor("238E68"), 
    'very light gray': hexToColor("CDCDCD"),
    'gold': hexToColor("FFD700"), 
    'violet red': hexToColor("CC3299"), 
    'coral': hexToColor("FF7F00"),
    'light steel blue': hexToColor("8F8FBD"),
    'silver': hexToColor("E6E8FA"),
    'dark turquoise': hexToColor("7093DB"),
    'light wood': hexToColor("E9C2A6"),
    'feldspar': hexToColor("D19275"),
    'thistle': hexToColor("D8BFD8"),
    'khaki': hexToColor("F0E68C"), 
    'cool copper': hexToColor("D98719"),
    'firebrick': hexToColor("B22222"), 
    'forest green': hexToColor("238E23"),
    'steel blue': hexToColor("236B8E"),
    }

def colorFromName(name):
    name = name.lower()
    return colorsLookupDictionary[name]

def colorName(color):
    for colorName in colorsLookupDictionary.keys():
        if colorsLookupDictionary[colorName] == color:
            return colorName
    return ""

def GetNativeColor(nameOrTuple):
    if type(nameOrTuple) == tuple:
        return Color(nameOrTuple[0], nameOrTuple[1], nameOrTuple[2])
    else:
        if nameOrTuple and nameOrTuple[0] == '#':
            return hexToColor(nameOrTuple[1:7])
        try:
            return colorFromName(nameOrTuple)
        except KeyError:
            # try to return a system color
            return Color.getColor(nameOrTuple)

###########

# PDF IMPORVE __ WHEN DRAG THIS< OBJECTS DISAPEAR __ NEED TO BE KEPT COPIED AT MORPH?
class MyImageCanvas(JComponent):
    def __init__(self, backdropImage, cursorImage):
        # PDF RESOLVE NAME images are actually expected to be icons...
        self.clearImages()
        self.backdropImage = backdropImage
        self.cursorImage = cursorImage
        self.doubleBuffered = 1
       
    def paintComponent(self, g):
        #JComponent.paintComponent(self, g)

        #draw entire component with background
        g.setColor(self.backgroundColor)
        g.fillRect(0, 0, self.getWidth(), self.getHeight())

        if self.backdropImage:
            self.backdropImage.paintIcon(self, g, 0, 0)
            #g.drawImage(self.backdropImage, 0, 0, self)
            
        for image, position in self.otherImagesWithPosition:
            image.paintIcon(self, g, position[0], position[1])
            #g.drawImage(image, position[0], position[1], self)

        if self.cursorImage:
            x = self.cursorImagePosition[0] - self.cursorOriginOffset[0]
            y = self.cursorImagePosition[1] - self.cursorOriginOffset[1]
            self.cursorImage.paintIcon(self, g, x, y)
            #g.drawImage(self.cursorImage, x, y, self)

    def getPreferredSize(self):
        if self.backdropImage:
            try:
                return (self.backdropImage.iconWidth, self.backdropImage.iconHeight)
            except:
                print "problem"
        return (100, 100)

    def getMinimumSize(self):
        return self.getPreferredSize()
        
    def clearImages(self):
        self.backdropImage = None
        self.cursorImage = None
        self.cursorImagePosition = (0, 0)
        self.cursorOriginOffset = (0, 0)
        self.backgroundColor = Color.white
        # list of tuples as (image, position)
        self.otherImagesWithPosition = []
        
    def addOtherImage(self, image, position):
        self.otherImagesWithPosition.append((image, position))
        self.repaint()
 
    def clearOtherImages(self):
        self.otherImagesWithPosition = []
        self.repaint()
        
###############

# callbacks that check for the metaKey 

def IsEventMatchForFilter(event, filter):
    #print "IsEventMatchForFilter", filter, event
    modifiers = event.getModifiersExText(event.getModifiersEx())
    items = modifiers.split("+")
    if filter == "":
        if "Alt" in items: return 0
        if "Ctrl" in items: return 0
        if "Shift" in items: return 0
        return 1
    elif filter == "Alt":
        if "Ctrl" in items: return 0
        if "Shift" in items: return 0
        if "Alt" in items: return 1
        return 0
    elif filter == "Control":
        if "Shift" in items: return 0
        if "Alt" in items: return 0
        if "Ctrl" in items: return 1
        return 0
    elif filter == "Shift":
        if "Alt" in items: return 0
        if "Ctrl" in items: return 0
        if "Shift" in items: return 1
        return 0
    elif filter == "Shift-Control":
        if "Alt" in items: return 0
        if "Ctrl" in items and "Shift" in items: return 1
        return 0
    return 0

class CallbackLeftMouseButtonListener(MouseAdapter):
    def __init__(self, modifiersFilter, callbackOnDown, callbackOnUp):
        self.modifiersFilter = modifiersFilter
        self.callbackOnDown = callbackOnDown
        self.callbackOnUp = callbackOnUp
    def mousePressed(self, event):
        if self.callbackOnDown and IsEventMatchForFilter(event, self.modifiersFilter):
            if SwingUtilities.isLeftMouseButton(event):
                self.callbackOnDown(event)
    def mouseReleased(self, event):
        if self.callbackOnUp and IsEventMatchForFilter(event, self.modifiersFilter):
            if SwingUtilities.isLeftMouseButton(event):
                self.callbackOnUp(event)
            
class CallbackRightMouseButtonListener(MouseAdapter):
    def __init__(self, modifiersFilter, callbackOnDown, callbackOnUp):
        self.modifiersFilter = modifiersFilter
        self.callbackOnDown = callbackOnDown
        self.callbackOnUp = callbackOnUp
    def mousePressed(self, event):
        if self.callbackOnDown and IsEventMatchForFilter(event, self.modifiersFilter):
            if SwingUtilities.isRightMouseButton(event):
                self.callbackOnDown(event)
    def mouseReleased(self, event):
        if self.callbackOnUp and IsEventMatchForFilter(event, self.modifiersFilter):
            if SwingUtilities.isRightMouseButton(event):
                self.callbackOnUp(event)
            
class CallbackMouseMotionListener(MouseMotionAdapter):
    def __init__(self, modifiersFilter, callback, draggedCallback=None):
        self.modifiersFilter = modifiersFilter
        self.callback = callback   
        self.draggedCallback = draggedCallback
    def mouseMoved(self, event):
        if self.callback and IsEventMatchForFilter(event, self.modifiersFilter):
            self.callback(event)
    def mouseDragged(self, event):
        if IsEventMatchForFilter(event, self.modifiersFilter):
            if self.draggedCallback:
                self.draggedCallback(event)
            else:
                self.callback(event)
                
class CallbackKeyListener(KeyAdapter):
    def __init__(self, pressedCallback, releasedCallback):
        self.pressedCallback = pressedCallback   
        self.releasedCallback = releasedCallback
    def keyPressed(self, event):
        print "CallbackKeyListener", event
        if self.pressedCallback:
            self.pressedCallback(event)
    def keyReleased(self, event):
        print "CallbackKeyListener", event
        if self.releasedCallback:
            self.releasedCallback(event)
            
####

class FileDialog:
    def __init__(self, parent, title="Choose file", loadOrSave="load"):
        self.parent = parent
        self.title = title
        self.loadOrSave = loadOrSave
        
    def go(self, pattern="*.py", default=None):
        fileChooser = JFileChooser()
        if self.title:
            fileChooser.setDialogTitle(self.title)
        if default:
            fileChooser.setSelectedFile(java.io.File(default))
        fileChooser.setCurrentDirectory(java.io.File("."))
        if self.loadOrSave == "load":
            result = fileChooser.showOpenDialog(self.parent)
        else:
            result = fileChooser.showSaveDialog(self.parent)
        if (result == JFileChooser.APPROVE_OPTION):
            fileResult = None
            fileAndMaybeDir = fileChooser.getSelectedFile().getAbsoluteFile()
            if not fileAndMaybeDir.isDirectory():
                fileResult = str(fileAndMaybeDir)
            return fileResult
        else:
            return None

#### COMMON

# Cursor
def Common_GetCursor(widget):
    return widget.getCursor()

def Common_SetCursor(widget, cursor):
    widget.setCursor(cursor)
    
def Common_SetCursorByName(widget, cursorName):
    if cursorName == "normal":
        raise "unfinished"
    elif cursorName == "cross":
        newCursor = Cursor(Cursor.CROSSHAIR_CURSOR)
    else:
        raise "Unsupported cursor name"
    self.widget.setCursor(newCursor)

# Image
def Common_LoadImage(fileName):
    return ImageIcon(fileName)
    
def Common_ImageWidth(image):
    return image.iconWidth

def Common_ImageHeight(image):
    return image.iconHeight

# Native Event
def Common_NativeEventPositionInWindow(event):
    return event.x, event.y
