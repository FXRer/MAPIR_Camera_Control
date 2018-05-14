import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from MAC_dockwidget import *
"""
This is the main function that runs the MAPIR widget, it instantiates a QT app object and then a
MAPIR PRocessing Dock Widget from the MAPIR_Processing_dockwidget.py file, this object is then displayed to the user

*Note: The code that is commented out is so display a loading screen to the user (doesn't work yet) and there needs to
be a cancel button added to this code
"""
if __name__ == "__main__":
        try:

                app = QApplication(sys.argv) #instantiate QT app object

                #splash_pix = QPixmap(os.path.dirname(os.path.realpath(__file__)) + 'lut_legend_rgb.jpg')

                #splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
                #splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
                #splash.setEnabled(True)
                #progressBar = QProgressBar(splash)
                #progressBar.setMaximum(30)
                #progressBar.setGeometry(0, splash_pix.height() - 50, splash_pix.width(), 20)
                #splash.show()
                #for i in range(1, 31):
                #       progressBar.setValue(i)
                #       t = time.time()
                #       while time.time() < t + 0.1:
                #               app.processEvents()


                '''create a processing dock widget app
                the app is defined in the MAPIR_PRocessing_dockwidget.py file'''
                myapp = MAPIR_ProcessingDockWidget() #instantiate a dockwidget app
                myapp.show() #Show the MAPIR gui
                #splash.finish(myapp) #end the loading screen

        except Exception as e:
                print(e)
        sys.exit(app.exec_())
