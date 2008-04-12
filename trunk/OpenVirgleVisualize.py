# functions of jGL:
# http://www.cmlab.csie.ntu.edu.tw/~robin/JavaGL/Support.html
# starting point example: 
# http://www.cmlab.csie.ntu.edu.tw/~robin/JavaGL/Example-app/index.html
# http://www.cmlab.csie.ntu.edu.tw/~robin/JavaGL/Example-app/texgen.java

from javax.swing import JFrame, SwingUtilities, JPanel
from java.lang import System
from java.awt import Color, BasicStroke
from java.awt.event import MouseEvent
from java.awt import Image

from jgl import GL, GLU, GLAUX, GLUT

import math
from jarray import *

# Problem: 3D window endlessly refreshes

class teapotCanvas(JPanel):
    def __init__(self):
        JPanel.__init__(self)
        
        self.myGL = GL()
        self.myGLU = GLU(self.myGL)
        self.myAUX = GLAUX(self.myGL)
        self.myGLUT = GLUT(self.myGL)
        
        self.myAUX.auxInitPosition(0, 0, 208, 227)
        self.myAUX.auxInitWindow(self)
        
        myGL = self.myGL

        myGL.glClearColor(0.0, 0.0, 0.0, 0.0)
        myGL.glEnable(GL.GL_DEPTH_TEST)
        myGL.glShadeModel(GL.GL_SMOOTH)
    
        myGL.glEnable(GL.GL_TEXTURE_GEN_S)
        #myGL.glEnable(GL.GL_TEXTURE_1D)
        myGL.glEnable(GL.GL_CULL_FACE)
        myGL.glEnable(GL.GL_LIGHTING)
        myGL.glEnable(GL.GL_LIGHT0)
        myGL.glEnable(GL.GL_AUTO_NORMAL)
        myGL.glEnable(GL.GL_NORMALIZE)
        myGL.glFrontFace(GL.GL_CW)
        myGL.glCullFace(GL.GL_BACK)
        myGL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 64.0)
        
        self.componentResized = self.OnComponentResized
        
        #self.myReshape(208, 227)
        #self.display()
        
    def myReshape(self, w, h):
        print "myReshape"
        myGL = self.myGL
        myGL.glViewport(0, 0, w, h)
        myGL.glMatrixMode(GL.GL_PROJECTION)
        myGL.glLoadIdentity()
        if (w <= h):
            myGL.glOrtho (-3.5, 3.5, -3.5 * h / w, 3.5 * h / w, -3.5, 3.5)
        else:
            myGL.glOrtho (-3.5 * w / h, 3.5 * w / h, -3.5, 3.5, -3.5, 3.5)

        myGL.glMatrixMode(GL.GL_MODELVIEW)
        myGL.glLoadIdentity()

    def paintComponent(self, g):
        print "paintComponent"
        # note funky way jython calls to super in Java need to be made with double underscore
        self.super__paintComponent(g)
        self.myReshape(self.size.width, self.size.height)
        self.display()
        # next line makes paint event?
        self.myGL.glXSwapBuffers(g, self)

    def display(self):
        print "display"
        #self.myGL.glXMakeCurrent(self, 0, 0)
        myGL = self.myGL
         
        myGL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
    
        myGL.glPushMatrix()
        myGL.glRotatef(45.0, 0.0, 0.0, 1.0)
        self.myGLUT.glutSolidTeapot(2.0)
        myGL.glPopMatrix()
        myGL.glFlush()

        #myGL.glXSwapBuffers(dc, self)
        #self.myGLUT.glutPostRedisplay()
        
    def OnComponentResized(self, e):
        print "OnComponentResized"
        #self.myReshape(self.size.width, self.size.height)
        #self.display()
        self.repaint()
        
def test():
    mainFrame = JFrame()
    mainFrame.setSize(208, 227)
    mainCanvas = teapotCanvas()
    mainFrame.add(mainCanvas)
    mainFrame.setVisible(1)