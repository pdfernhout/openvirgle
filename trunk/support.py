from javax.swing import JFrame, Box, BoxLayout, JLabel, JButton, JList, DefaultListModel, JScrollPane, JTree
from javax.swing import JPopupMenu, JMenuItem, JOptionPane
from javax.swing import Timer
from java.awt import Frame
from java.lang import System
from javax.swing.tree import DefaultMutableTreeNode, DefaultTreeModel, DefaultTreeCellRenderer, TreePath, TreeModel
from javax.swing.event import TreeModelEvent
import java.lang 

from listeners import *

class NamedItem(java.lang.Object):
    def __init__(self, name, item):
        self.name = name
        self.item = item
        
    def toString(self):
        return self.name
