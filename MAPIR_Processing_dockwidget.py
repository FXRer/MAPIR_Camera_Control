# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MAPIR_ProcessingDockWidget
                                 A QGIS plugin
 Widget for processing images captured by MAPIR cameras
                             -------------------
        begin                : 2016-09-26
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Peau Productions
        email                : ethan@peauproductions.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import warnings
warnings.filterwarnings("ignore")

os.umask(0)
from LensLookups import *
import datetime
import sys
import shutil
import platform
import itertools
import ctypes
import string
import PIL
import bitstring
from PyQt5 import QtCore, QtGui, QtWidgets

import PyQt5.uic as uic

import numpy as np
import subprocess
import cv2
import copy
import hid
import time

from osgeo import gdal
import glob

from MAPIR_Enums import *
from MAPIR_Defaults import *
from MAPIR_kernel_subclasses import *
from Calculator import *
from LUT_Dialog import *
from Vignette import *
from BandOrder import *
from ViewerSave_Dialog import *
import xml.etree.ElementTree as ET
import KernelConfig
from MAPIR_Converter import *
from Exposure import *
# import KernelBrowserViewer

modpath = os.path.dirname(os.path.realpath(__file__))

# print(str(modpath))
if not os.path.exists(modpath + os.sep + "instring.txt"):
    istr = open(modpath + os.sep + "instring.txt", "w")
    istr.close()



all_cameras = [] #initialize camera variable as empty list

"""
One big issue is that every time you call any .exe in Windows a command window is pulled up each time

In order to address this we will create a variable: 'si' which stands for system information

When si is declared it pulls up the generic startup info from the system, then one of the flags in si can be set to
suppress the popping up of a window each time an exe is called

Now that si exists with the suppressed pop ups it can be passed to other functions as a substitute for the default
system information to avoid having to write this code everytime
"""
if sys.platform ==  'darwin':
    import gdal
elif sys.platform == "win32":
    import win32api
    from osgeo import gdal
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW


"""exiftool is crossplatform, needs to be cosnumed in 3 differeent wased based on which OS is being used
on mac use homebrew
"""

# if sys.platform == "win32":
#       import exiftool
#       exiftool.executable = modpath + os.sep + "exiftool.exe"


class MAPIR_ProcessingDockWidget(QtWidgets.QMainWindow, FORM_CLASS):
    """
    class MAPIR_ProcessingDockWidget is the largest class within the widget program and contains the hard-coded constants,
    the code to generate the widget, and the code for most of the tabs within the widget
    """

    # eFilter = mousewheelFilter()
    USB_MAX_BUF_LEN = 512 #max length of buffer possible to send to usb
    camera = 0
    poll = [] #poll is an empty list
    capturing = False #by default camera is not capturing
    dialog = None
    imcols = 4608 #number of columns
    imrows = 3456 #number of rows
    imsize = imcols * imrows
    closingPlugin = QtCore.pyqtSignal()
    firstpass = True
    useqr = False

    qrcoeffs = []  # Red Intercept, Red Slope,  Green Intercept, Green Slope, Blue Intercept, Blue Slope
    qrcoeffs2 = []
    qrcoeffs3 = []
    qrcoeffs4 = []
    qrcoeffs5 = []
    qrcoeffs6 = []
    coords = []
    # drivesfound = []
    ref = ""
    #generate an empty list of size 65535, using range()
    imkeys = np.array(list(range(0, 65536)))  #65536 =  MAX_UINT16 + 1
    weeks = 0
    days = 0
    hours = 0
    minutes = 0
    seconds = 1
    conv = None
    kcr = None
    analyze_bands = []
    modalwindow = None
    calcwindow = None
    LUTwindow = None
    M_Shutter_Window = None
    A_Shutter_Window = None
    Bandwindow = None
    Advancedwindow = None
    rdr = []
    ManualExposurewindow = None
    AutoExposurewindow = None

    VigWindow = None
    ndvipsuedo = None
    savewindow = None
    index_to_save = None
    LUT_to_save = None
    LUT_Min = -1.0
    LUT_Max = 1.0
    array_indicator = False
    seed_pass = False
    transferoutfolder = None
    yestransfer = False
    yesdelete = False
    selection_made = False
    POLL_TIME = 3000
    # SLOW_POLL = 10000
    slow = 0
    regs = [0] * eRegister.RG_SIZE.value
    paths = []
    pathnames = []
    driveletters = []
    source = 0
    evt = 0
    info = 0
    VENDOR_ID = 0x525
    PRODUCT_ID = 0xa4ac
    BUFF_LEN = USB_MAX_BUF_LEN
    SET_EVENT_REPORT = 1
    SET_COMMAND_REPORT = 3
    SET_REGISTER_WRITE_REPORT = 5
    SET_REGISTER_BLOCK_WRITE_REPORT = 7
    SET_REGISTER_READ_REPORT = 9
    SET_REGISTER_BLOCK_READ_REPORT = 11
    SET_CAMERA = 13
    display_image = None
    display_image_original = None
    displaymax = None
    displaymin = None
    mapscene = None
    frame = None
    legend_frame = None
    legend_scene = None
    image_loaded = False
    # mMutex = QMutex()
    regs = []
    paths_1_2 = []
    paths_3_0 = []
    paths_14_0 = []
    ISO_VALS = (1,2,4,8,16,32)
    lensvals = None

    cancelButtonPressed = False

    #dictionary containing the band names for the varying filters
    BandNames = {
        "RGB": [644, 0, 0],
        "405": [405, 0, 0],
        "450": [450, 0, 0],
        "490": [490, 0, 0],
        "518": [518, 0, 0],
        "550": [550, 0, 0],
        "590": [590, 0, 0],
        "615": [615, 0, 0],
        "632": [632, 0, 0],
        "650": [650, 0, 0],
        "685": [685, 0, 0],
        "725": [725, 0, 0],
        "780": [780, 0, 0],
        "808": [808, 0, 0],
        "850": [850, 0, 0],
        "880": [880, 0, 0],
        "940": [940, 0, 0],
        "945": [945, 0, 0],
        "UVR": [870, 0, 395],
        "NGB": [850, 550, 475],
        "RGN": [660, 550, 850],
        "OCN": [615, 490, 808],

    }
    #list containing the names of the dictionary refValues
    refindex = ["oldrefvalues", "newrefvalues"]
    refvalues = {
        "oldrefvalues": {
            "660/850": [[0.87032549, 0.52135779, 0.23664799], [0, 0, 0], [0.8463514, 0.51950608, 0.22795518]],
            "446/800": [[0.8419608509, 0.520440145, 0.230113958], [0, 0, 0],
                        [0.8645652801, 0.5037779363, 0.2359041624]],
            "850": [[0.8463514, 0.51950608, 0.22795518], [0, 0, 0], [0, 0, 0]],
            "650": [[0.87032549, 0.52135779, 0.23664799], [0, 0, 0], [0, 0, 0]],
            "550": [[0, 0, 0], [0.87415089, 0.51734381, 0.24032515], [0, 0, 0]],
            "450": [[0, 0, 0], [0, 0, 0], [0.86469794, 0.50392915, 0.23565447]],
            "Mono450": [0.8634818638, 0.5024087105, 0.2351860396],
            "Mono550": [0.8740616379, 0.5173070235, 0.2402423818],
            "Mono650": [0.8705783136, 0.5212290524, 0.2366437854],
            "Mono725": [0.8606071247, 0.521474266, 0.2337744252],
            "Mono808": [0.8406184266, 0.5203405498, 0.2297701185],
            "Mono850": [0.8481919553, 0.519491643, 0.2278713071],
            "Mono405": [0.8556905469, 0.4921243183, 0.2309899254],
            "Mono518": [0.8729814889, 0.5151370187, 0.2404729692],
            "Mono632": [0.8724034645, 0.5209649915, 0.2374529161],
            "Mono590": [0.8747043911, 0.5195596573, 0.2392049856],
            "550/660/850": [[0.8474610999, 0.5196055607, 0.2279922965], [0.8699940018, 0.5212235151, 0.2364397706],
                            [0.8740311726, 0.5172611881, 0.2402870156]]

        },
        #look up table for new reference values off new target, the values are based offset
        #of weighted averages
        "newrefvalues": {
            "660/850": [[0.87032549, 0.52135779, 0.23664799], [0, 0, 0],
                        [0.8653063177, 0.2798126291, 0.2337498097, 0.0193295348]],
            "446/800": [[0.7882333002, 0.2501235178, 0.1848459584, 0.020036883], [0, 0, 0],
                        [0.8645652801, 0.5037779363, 0.2359041624]],
            "850": [[0.8649280907, 0.2800907016, 0.2340131491, 0.0195446727], [0, 0, 0], [0, 0, 0]],
            "650": [[0.8773469949, 0.2663571183, 0.199919444, 0.0192325637], [0, 0, 0], [0, 0, 0]],
            "550": [[0, 0, 0], [0.8686559344, 0.2655697585, 0.1960837144, 0.0195629009], [0, 0, 0]],
            "450": [[0, 0, 0], [0, 0, 0], [0.7882333002, 0.2501235178, 0.1848459584, 0.020036883]],
            "Mono405": [0.6959473282, 0.2437485737, 0.1799017476, 0.0205591758],
            "Mono450": [0.7882333002, 0.2501235178, 0.1848459584, 0.020036883],
            "Mono490": [0.8348841674, 0.2580074987, 0.1890252099, 0.01975703],
            "Mono518": [0.8572181897, 0.2628629357, 0.192259471, 0.0196629792],
            "Mono550": [0.8686559344, 0.2655697585, 0.1960837144, 0.0195629009],
            "Mono590": [0.874586922, 0.2676592931, 0.1993779934, 0.0193745668],
            "Mono615": [0.8748454449, 0.2673426216, 0.1996415667, 0.0192891156],
            "Mono632": [0.8758224323, 0.2670055225, 0.2023045295, 0.0192596465],
            "Mono650": [0.8773469949, 0.2663571183, 0.199919444, 0.0192325637],
            "Mono685": [0.8775925081, 0.2648548355, 0.1945563456, 0.0192860556],
            "Mono725": [0.8756774317, 0.266883373, 0.21603525, 0.194527158],
            "Mono780": [0.8722125382, 0.2721842015, 0.2238493387, 0.0196295938],
            "Mono808": [0.8699458632, 0.2780141682, 0.2283300902, 0.0216592377],
            "Mono850": [0.8649280907, 0.2800907016, 0.2340131491, 0.0195446727],
            "Mono880": [0.8577996233, 0.2673899041, 0.2371926238, 0.0202034892],
            "Mono945": [85.10570936, 0.2879122882, 0.24298, 0.0203548055],
            "550/660/850": [[0.8689592421, 0.2656248359, 0.1961875592, 0.0195576511],
                            [0.8775934407, 0.2661207692, 0.1987265874, 0.0192249327],
                            [0.8653063177, 0.2798126291, 0.2337498097, 0.0193295348]],
            "490/615/808": [[0.8414604806, 0.2594283565, 0.1897271608, 0.0197180224],
                            [0.8751529643, 0.2673261446, 0.2007025375, 0.0192817427],
                            [0.868782908, 0.27845399, 0.2298671821, 0.0211305297]],
            "475/550/850": [[0.8348841674, 0.2580074987, 0.1890252099, 0.01975703],
                            [0.8689592421, 0.2656248359, 0.1961875592, 0.0195576511],
                            [0.8653063177, 0.2798126291, 0.2337498097, 0.0193295348]]


        }}
    #dict containing min and max vales for RBG
    pixel_min_max = {"redmax": 0.0, "redmin": 65535.0,
                     "greenmax": 0.0, "greenmin": 65535.0,
                     "bluemax": 0.0, "bluemin": 65535.0}
    multiplication_values = {"Red": [0.00],
                             "Green": [0.00],
                             "Blue": [0.00],
                             "Mono": [0.00]}
    monominmax = {"min": 65535.0, "max": 0.0}

    def __init__(self, parent=None):
        """Constructor."""
        super(MAPIR_ProcessingDockWidget, self).__init__(parent)

        self.setupUi(self)
        try:
            #set legend equal to lut_legend.jpg
            legend = cv2.imread(os.path.dirname(__file__) + "/lut_legend.jpg")
            legh, legw = legend.shape[:2] #find legend height and width
            self.legend_frame = QtGui.QImage(legend.data, legw, legh, legw, QtGui.QImage.Format_Grayscale8)
            self.LUTGraphic.setPixmap(QtGui.QPixmap.fromImage(
                QtGui.QImage(self.legend_frame)))
            self.LegendLayout_2.hide()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))

    def exitTransfer(self, drv='C'):
        #tmtf is a blank file that the camera is looking for, when it reads tmtf it stops transfer mode
        tmtf = r":/dcim/tmtf.txt" #location of tmtf file that allows you to  exit transfer mode

        if drv == 'C': #start at C, loop through drives for dcim folder
            while drv is not '[':
                if os.path.isdir(drv + r":/dcim/"):
                    try:
                        if not os.path.exists(drv + tmtf):
                            self.KernelLog.append("Camera mounted at drive " + drv + " leaving transfer mode")
                            file = open(drv + tmtf, "w")
                            file.close()
                    except:
                        self.KernelLog.append("Error disconnecting drive " + drv)

                drv = chr(ord(drv) + 1)
        else:
            if os.path.isdir(drv + r":/dcim/"):
                try:
                    if not os.path.exists(drv + tmtf):
                        self.KernelLog.append("Camera mounted at drive " + drv + " leaving transfer mode")
                        file = open(drv + tmtf, "w")
                        file.close()
                except:
                    self.KernelLog.append("Error disconnecting drive " + drv)

    #Kernel refresh and kernel connect both call connect kernels
    def on_KernelRefreshButton_released(self):
        # self.exitTransfer()
        self.ConnectKernels()
    def on_KernelConnect_released(self):
        """ on KernelConnect_released calls ConnectKernels when the kernel connect button is clicked """
        # self.exitTransfer()
        self.ConnectKernels()
    def ConnectKernels(self):
        """ ConnectKernels is used to connect to the kernel cameras using hidapi
        """
        self.KernelLog.append(' ') #add ' ' to the kernel log
        all_cameras = hid.enumerate(self.VENDOR_ID, self.PRODUCT_ID)
        #find the cameras
        if all_cameras == []:

            self.KernelLog.append("No cameras found! Please check your USB connection and try again.")
        else:
            self.paths.clear()
            self.pathnames.clear()

            for cam in all_cameras:

                if cam['product_string'] == 'HID Gadget':
                    self.paths.append(cam['path']) #adding the path to a list of paths
                    QtWidgets.QApplication.processEvents()

            self.KernelCameraSelect.blockSignals(True)
            self.KernelCameraSelect.clear()
            self.KernelCameraSelect.blockSignals(False)

            try:
                for i, path in enumerate(self.paths):
                    QtWidgets.QApplication.processEvents()
                    self.camera = path
                    buf = [0] * 512
                    buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
                    buf[1] = eRegister.RG_MEDIA_FILE_NAME_A.value
                    buf[2] = 3 #cameras name is a 3 character string = 3 bytes

                    res = self.writetokernel(buf) #write buffer to kernel

                    item = chr(res[2]) + chr(res[3]) + chr(res[4]) #send 2,3, and 4th index

                    self.KernelLog.append("Found Camera: " + str(item))
                    QtWidgets.QApplication.processEvents()

                    self.pathnames.append(item)
                    self.KernelCameraSelect.blockSignals(True)

                    self.KernelCameraSelect.addItem(item)
                    self.KernelCameraSelect.blockSignals(False)

                self.camera = self.paths[0]

                try:
                    # self.KernelLog.append("Updating UI")
                    self.KernelUpdate()
                    QtWidgets.QApplication.processEvents()
                except Exception as e:
                    exc_type, exc_obj,exc_tb = sys.exc_info()
                    print(e)
                    print("Line: " + str(exc_tb.tb_lineno))
                    QtWidgets.QApplication.processEvents()
            except Exception as e:
                exc_type, exc_obj,exc_tb = sys.exc_info()
                self.KernelLog.append("Error: (" + str(e) + ' Line: ' + str(exc_tb.tb_lineno) +  ") connecting to camera, please ensure all cameras are connected properly and not in transfer mode.")
                QtWidgets.QApplication.processEvents()

    def UpdateLensID(self):
        buf = [0] * 512
        buf[0] = self.SET_REGISTER_WRITE_REPORT
        buf[1] = eRegister.RG_LENS_ID.value
        buf[2] = DROPDOW_2_LENS.get((self.KernelFilterSelect.currentText(), self.KernelLensSelect.currentText()), 255)

        self.writetokernel(buf) #write buffer to kernel camera
    def on_KernelLensSelect_currentIndexChanged(self, int = 0):
        try:
            self.UpdateLensID()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.KernelLog.append("Error: " + e)
    def on_KernelFilterSelect_currentIndexChanged(self, int = 0):
        try:
            # threeletter = self.KernelFilterSelect.currentText()
            # buf = [0] * 512
            # buf[0] = self.SET_REGISTER_BLOCK_WRITE_REPORT
            # buf[1] = eRegister.RG_MEDIA_FILE_NAME_A.value
            # buf[2] = 3
            # buf[3] = ord(threeletter[0])
            # buf[4] = ord(threeletter[1])
            # buf[5] = ord(threeletter[2])
            # res = self.writetokernel(buf) #write buffer to kernel
            self.UpdateLensID()
            self.KernelUpdate()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.KernelLog.append("Error: " + e)
    def on_KernelCameraSelect_currentIndexChanged(self, int = 0):
        self.camera = self.paths[self.KernelCameraSelect.currentIndex()]
        self.KernelFilterSelect.blockSignals(True)
        self.KernelFilterSelect.setCurrentIndex(self.KernelFilterSelect.findText(self.KernelCameraSelect.currentText()))
        self.KernelFilterSelect.blockSignals(False)
        if not self.KernelTransferButton.isChecked():
            try:
                self.KernelUpdate()
            except Exception as e:
                exc_type, exc_obj,exc_tb = sys.exc_info()
                self.KernelLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
    # def on_KernelArraySelect_currentIndexChanged(self, int = 0):
    #     if self.KernelArraySelect.currentIndex() == 0:
    #         self.array_indicator = False
    #         self.KernelCameraSelect.setEnabled(True)
    #     else:
    #         self.array_indicator = True
    #         self.KernelCameraSelect.setEnabled(False)
    def on_VignetteButton_released(self):
        #action taken on vignette button being released
        if self.VigWindow == None:
            self.VigWindow = Vignette(self)
            #VigWindow is now an object of type Vignette
        self.VigWindow.resize(385, 160) #resize
        self.VigWindow.show() #display

    def on_KernelBrowserButton_released(self):

        #the following lines populate the browse bar with the corresponding path to the selected file
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.KernelBrowserFile.setText(QtWidgets.QFileDialog.getOpenFileName(directory=instring.read())[0])
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.KernelBrowserFile.text())
        try:
            # self.KernelViewer.verticalScrollBar().blockSignals(True)
            # self.KernelViewer.horizontalScrollBar().blockSignals(True)

            # self.KernelViewer.installEventFilter(self.eFilter)
            if os.path.exists(self.KernelBrowserFile.text()):
                self.display_image = cv2.imread(self.KernelBrowserFile.text(), -1)
                # if self.display_image == None:
                #     self.display_image = gdal.Open(self.KernelBrowserFile.text())
                #     self.display_image = np.array(self.display_image.GetRasterBand(1).ReadAsArray())
                if self.display_image.dtype == np.dtype("uint16"):
                    self.display_image = self.display_image / MAPIR_aults.UINT16MAX_FLOAT
                    self.display_image = self.display_image * 255.0
                    self.display_image = self.display_image.astype("uint8")
                # self.imkeys = np.array(list(range(0, 65536)))
                self.displaymin = self.display_image.min()
                self.displaymax = int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(self.display_image))], self.display_image)[0])


                self.display_image[self.display_image > self.displaymax] = self.displaymax
                self.display_image[self.display_image < self.displaymin] = self.displaymin
                if len(self.display_image.shape) > 2:
                    self.display_image = cv2.cvtColor(self.display_image, cv2.COLOR_BGR2RGB)
                else:
                    self.display_image = cv2.cvtColor(self.display_image, cv2.COLOR_GRAY2RGB)
                    #convert image to RGB before displaying
                self.display_image_original = copy.deepcopy(self.display_image)
                h, w = self.display_image.shape[:2] #extract height and width



                # self.image_loaded = True

                # self.display_image = ((self.display_image - self.display_image.min())/(self.display_image.max() - self.display_image.min())) * 255.0


                # browser_w = self.KernelViewer.width()
                # browser_h = self.KernelViewer.height()

                self.image_loaded = True
                self.stretchView()
                self.ViewerCalcButton.blockSignals(True)
                self.LUTButton.blockSignals(True)
                self.LUTBox.blockSignals(True)
                self.ViewerIndexBox.blockSignals(True)
                self.ViewerStretchBox.blockSignals(True)

                self.ViewerCalcButton.setEnabled(True)
                self.LUTButton.setEnabled(False)
                self.LUTBox.setEnabled(False)
                self.LUTBox.setChecked(False)
                self.ViewerIndexBox.setEnabled(False)
                self.ViewerIndexBox.setChecked(False)
                self.ViewerStretchBox.setChecked(True)

                self.ViewerCalcButton.blockSignals(False)
                self.LUTButton.blockSignals(False)
                self.LUTBox.blockSignals(False)
                self.ViewerIndexBox.blockSignals(False)
                self.ViewerStretchBox.blockSignals(False)

                self.savewindow = None
                self.LUTwindow = None
                self.LUT_to_save = None
                self.LUT_Max = 1.0
                self.LUT_Min = -1.0
                self.updateViewer(keepAspectRatio=True)

        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(str(e) + ' Line: ' + str(exc_tb.tb_lineno))

    def on_ViewerStretchBox_toggled(self):
        self.stretchView()
    def stretchView(self):
        """equalizing the historgram, stretching the image to its min and max, allows you to see very dark Images
        by introudcing more contrast
        """
        try:
            if self.image_loaded:
                if self.ViewerStretchBox.isChecked():
                    h, w = self.display_image.shape[:2]

                    if len(self.display_image.shape) > 2:
                        self.display_image[:, :, 0] = cv2.equalizeHist(self.display_image[:, :, 0])
                        self.display_image[:, :, 1] = cv2.equalizeHist(self.display_image[:, :, 1])
                        self.display_image[:, :, 2] = cv2.equalizeHist(self.display_image[:, :, 2])
                    else:
                        self.display_image = cv2.equalizeHist(self.display_image)
                    if not (self.ViewerIndexBox.isChecked() or self.LUTBox.isChecked()):
                        self.LegendLayout_2.hide()
                        if len(self.display_image.shape) > 2:
                            self.frame = QtGui.QImage(self.display_image.data, w, h, w * 3, QtGui.QImage.Format_RGB888)
                        else:
                            self.frame = QtGui.QImage(self.display_image.data, w, h, w, QtGui.QImage.Format_RGB888)
                else:
                    if not (self.ViewerIndexBox.isChecked() or self.LUTBox.isChecked()):
                        self.LegendLayout_2.hide()
                        h, w = self.display_image_original.shape[:2]
                        if len(self.display_image_original.shape) > 2:
                            self.frame = QtGui.QImage(self.display_image_original.data, w, h, w * 3, QtGui.QImage.Format_RGB888)
                        else:
                            self.frame = QtGui.QImage(self.display_image_original.data, w, h, w, QtGui.QImage.Format_RGB888)
                self.updateViewer(keepAspectRatio=False)
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))

    def on_ViewerIndexBox_toggled(self):
        self.applyRaster()
    def applyRaster(self):
        """
        handles the ndvi caclulation on the view tab
        """
        try:
            h, w = self.display_image.shape[:2]
            if self.LUTBox.isChecked():
                pass
            else:
                if self.ViewerIndexBox.isChecked():
                    self.frame = QtGui.QImage(self.calcwindow.ndvi.data, w, h, w, QtGui.QImage.Format_Grayscale8)
                    legend = cv2.imread(os.path.dirname(__file__) + r'\lut_legend.jpg', 0).astype("uint8")
                    # legend = cv2.cvtColor(legend, cv2.COLOR_GRAY2RGB)
                    legh, legw = legend.shape[:2]

                    self.legend_frame = QtGui.QImage(legend.data, legw, legh, legw, QtGui.QImage.Format_Grayscale8)
                    self.LUTGraphic.setPixmap(QtGui.QPixmap.fromImage(
                        QtGui.QImage(self.legend_frame)))
                    self.LegendLayout_2.show()
                else:
                    self.LegendLayout_2.hide()
                    self.frame = QtGui.QImage(self.display_image.data, w, h, w * 3, QtGui.QImage.Format_RGB888)
                self.updateViewer(keepAspectRatio=False)
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))
    def updateViewer(self, keepAspectRatio = True):



     def updateViewer(self, keepAspectRatio = True):
        #refreshes the image on viewer
        self.mapscene = QtWidgets.QGraphicsScene()

        self.mapscene.addPixmap(QtGui.QPixmap.fromImage(
            QtGui.QImage(self.frame)))

        self.KernelViewer.setScene(self.mapscene)
        if keepAspectRatio:
            self.KernelViewer.fitInView(self.mapscene.sceneRect(), QtCore.Qt.KeepAspectRatio)
        self.KernelViewer.setFocus()
        # self.KernelViewer.setWheelAction(2)
        QtWidgets.QApplication.processEvents()

    def on_LUTBox_toggled(self):
        #apply LUT when the box is toggled
        #if the LUT box is toggled then apply LUT
        self.applyLUT()

    def applyLUT(self):
        """applyLUT is the function declaration that contains the infromation to
        apply a LUT """
        try:
            h, w = self.display_image.shape[:2] #get hieght and width
            if self.LUTBox.isChecked(): #check if the LUTBox is checked
                if self.LUTwindow.ClipOption.currentIndex() == 1:
                    self.frame = QtGui.QImage(self.ndvipsuedo.data, w, h, w * 4, QtGui.QImage.Format_RGBA8888)
                else:
                    self.frame = QtGui.QImage(self.ndvipsuedo.data, w, h, w * 3, QtGui.QImage.Format_RGB888)

                legend = cv2.imread(os.path.dirname(__file__) + r'\lut_legend_rgb.jpg', -1).astype("uint8")
                legend = cv2.cvtColor(legend, cv2.COLOR_BGR2RGB)
                legh, legw = legend.shape[:2] #find length and width of the legend
                self.legend_frame = QtGui.QImage(legend.data, legw, legh, legw * 3, QtGui.QImage.Format_RGB888)
                self.LUTGraphic.setPixmap(QtGui.QPixmap.fromImage(
                    QtGui.QImage(self.legend_frame)))
                self.LegendLayout_2.show() #show the legend 2 layout, this code seems to be unfinished

            else:
                legend = cv2.imread(os.path.dirname(__file__) + r'\lut_legend.jpg', 0).astype("uint8")
                # legend = cv2.cvtColor(legend, cv2.COLOR_GRAY2RGB)
                legh, legw = legend.shape[:2]
                self.legend_frame = QtGui.QImage(legend.data, legw, legh, legw, QtGui.QImage.Format_Grayscale8)
                self.LUTGraphic.setPixmap(QtGui.QPixmap.fromImage(
                    QtGui.QImage(self.legend_frame)))


                if self.ViewerIndexBox.isChecked():
                    #display legend layour 2 if viewer index box is checked
                    self.LegendLayout_2.show()
                    self.frame = QtGui.QImage(self.calcwindow.ndvi.data, w, h, w, QtGui.QImage.Format_Grayscale8)
                else:
                    self.LegendLayout_2.hide()
                    self.frame = QtGui.QImage(self.display_image.data, w, h, w * 3, QtGui.QImage.Format_RGB888)
            self.updateViewer(keepAspectRatio=False)

            QtWidgets.QApplication.processEvents()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))

    def on_ViewerSaveButton_released(self):

        if self.savewindow == None:
            self.savewindow = SaveDialog(self)
        self.savewindow.resize(385, 110)
        self.savewindow.exec_()



        QtWidgets.QApplication.processEvents()

    def on_LUTButton_released(self):
        if self.LUTwindow == None:
            self.LUTwindow = Applicator(self)
        self.LUTwindow.resize(385, 160)
        self.LUTwindow.show()

        QtWidgets.QApplication.processEvents()

    def on_ViewerCalcButton_released(self):
        if self.LUTwindow == None:
            self.calcwindow = Calculator(self) #pass the calculator a new version of itself (a Q object) to the display
        self.calcwindow.resize(385, 250)
        self.calcwindow.show()
        QtWidgets.QApplication.processEvents()
    def on_ZoomIn_released(self):
        if self.image_loaded == True:
            try:
                # self.KernelViewer.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
                factor = 1.15
                self.KernelViewer.scale(factor, factor)
            except Exception as e:
                exc_type, exc_obj,exc_tb = sys.exc_info()
                print(e)
                print("Line: " + str(exc_tb.tb_lineno))
    def on_ZoomOut_released(self):
        if self.image_loaded == True:
            try:
                # self.KernelViewer.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
                factor = 1.15
                self.KernelViewer.scale(1/factor, 1/factor)
            except Exception as e:
                exc_type, exc_obj,exc_tb = sys.exc_info()
                print(e)
                print("Line: " + str(exc_tb.tb_lineno))
    def on_ZoomToFit_released(self):
        self.mapscene = QtWidgets.QGraphicsScene()
        self.mapscene.addPixmap(QtGui.QPixmap.fromImage(
            QtGui.QImage(self.frame)))

        self.KernelViewer.setScene(self.mapscene)
        self.KernelViewer.fitInView(self.mapscene.sceneRect(), QtCore.Qt.KeepAspectRatio)
        self.KernelViewer.setFocus()
        QtWidgets.QApplication.processEvents()

    def resizeEvent(self, event):
        # redraw the image in the viewer every time the window is resized
        if self.image_loaded == True:
            self.mapscene = QtWidgets.QGraphicsScene()
            self.mapscene.addPixmap(QtGui.QPixmap.fromImage(
                QtGui.QImage(self.frame)))

            self.KernelViewer.setScene(self.mapscene)

            self.KernelViewer.setFocus()
            QtWidgets.QApplication.processEvents()
        print("resize")

    def KernelUpdate(self):
        """ Kernel update populates the memory of the buffer """
        try:
            #this block of code prevents all these these from sending signals during the update to prevent errors from occuring
            self.KernelExposureMode.blockSignals(True)
            self.KernelVideoOut.blockSignals(True)
            self.KernelFolderCount.blockSignals(True)
            self.KernelBeep.blockSignals(True)
            self.KernelPWMSignal.blockSignals(True)
            self.KernelLensSelect.blockSignals(True)


            buf = [0] * 512
            buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
            buf[1] = eRegister.RG_CAMERA_SETTING.value
            buf[2] = eRegister.RG_SIZE.value

            res = self.writeToKernel(buf)[2:]
            self.regs = res

            shutter = self.getRegister(eRegister.RG_SHUTTER.value)
            if shutter == 0:
                self.KernelExposureMode.setCurrentIndex(0)
                self.KernelMESettingsButton.setEnabled(False)
                self.KernelAESettingsButton.setEnabled(True)
            else:
                self.KernelExposureMode.setCurrentIndex(1)
                self.KernelMESettingsButton.setEnabled(True)
                self.KernelAESettingsButton.setEnabled(False)

            dac = self.getRegister(eRegister.RG_DAC.value)

            hdmi = self.getRegister(eRegister.RG_HDMI.value)

            if hdmi == 1 and dac == 1:
                self.KernelVideoOut.setCurrentIndex(3)
            elif hdmi == 0 and dac == 1:
                self.KernelVideoOut.setCurrentIndex(2)
            elif hdmi == 1 and dac == 0:
                self.KernelVideoOut.setCurrentIndex(1)
            else:
                self.KernelVideoOut.setCurrentIndex(0)

            #enable media
            media = self.getRegister(eRegister.RG_MEDIA_FILES_CNT.value)
            self.KernelFolderCount.setCurrentIndex(media)
            #enable beeping
            beep = self.getRegister(eRegister.RG_BEEPER_ENABLE.value)
            if beep != 0:
                self.KernelBeep.setChecked(True)
            else:
                self.KernelBeep.setChecked(False)

            pwm = self.getRegister(eRegister.RG_PWM_TRIGGER.value)
            if pwm != 0:
                self.KernelPWMSignal.setChecked(True)
            else:
                self.KernelPWMSignal.setChecked(False)

            self.KernelPanel.clear()
            self.KernelPanel.append("Hardware ID: " + str(self.getRegister(eRegister.RG_HARDWARE_ID.value)))
            self.KernelPanel.append("Firmware version: " + str(self.getRegister(eRegister.RG_FIRMWARE_ID.value)))
            self.KernelPanel.append("Sensor: " + str(self.getRegister(eRegister.RG_SENSOR_ID.value)))
            self.KernelPanel.append("Lens: " + str(LENS_LOOKUP.get(self.getRegister(eRegister.RG_LENS_ID.value), 255)[0][0]))


            buf = [0] * 512
            buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
            buf[1] = eRegister.RG_CAMERA_ID.value
            buf[2] = 6
            st = self.writeToKernel(buf)
            serno = str(chr(st[2]) + chr(st[3]) + chr(st[4]) + chr(st[5]) + chr(st[6]) + chr(st[7]))
            self.KernelPanel.append("Serial #: " + serno)

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_READ_REPORT
            buf[1] = eRegister.RG_CAMERA_ARRAY_TYPE.value
            artype = self.writeToKernel(buf)[2]
            self.KernelPanel.append("Array Type: " + str(artype))
            buf = [0] * 512
            buf[0] = self.SET_REGISTER_READ_REPORT
            buf[1] = eRegister.RG_CAMERA_LINK_ID.value
            arid = self.writeToKernel(buf)[2]
            self.KernelPanel.append("Array ID: " + str(arid))
            if arid == 0:
                self.MasterCameraLabel.setText("Master")
            else:
                self.MasterCameraLabel.setText("Slave")
            self.KernelExposureMode.blockSignals(False)
            self.KernelVideoOut.blockSignals(False)
            self.KernelFolderCount.blockSignals(False)
            self.KernelBeep.blockSignals(False)
            self.KernelPWMSignal.blockSignals(False)
            self.KernelLensSelect.blockSignals(False)
            QtWidgets.QApplication.processEvents()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.KernelLog.append("Error: (" + str(e) + ' Line: ' + str(
                exc_tb.tb_lineno) + ") updating interface.")

    def on_KernelFolderButton_released(self):

        #when the kernel folder button is released get the existing directory
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.KernelTransferFolder.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.KernelTransferFolder.text())

    cancel_auto = False
    def on_KernelAutoCancel_released(self):
        self.cancel_auto = True
    # def on_KernelAutoTransfer_released(self):
    #
    #      Add the auto transfer check.

    #following code is to dictate the actions taken when kernel buttons 1-6 are released
    def on_KernelBandButton1_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            #get the existing directory string
            self.KernelBand1.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.KernelBand1.text()) #write out the text

    def on_KernelBandButton2_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.KernelBand2.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.KernelBand2.text())

    def on_KernelBandButton3_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.KernelBand3.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.KernelBand3.text())

    def on_KernelBandButton4_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.KernelBand4.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.KernelBand4.text())

    def on_KernelBandButton5_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.KernelBand5.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.KernelBand5.text())
    def on_KernelBandButton6_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.KernelBand6.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.KernelBand6.text())

    def on_KernelRenameOutputButton_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.KernelRenameOutputFolder.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.KernelRenameOutputFolder.text())
    def on_KernelRenameButton_released(self):
        try:
            #create six folders that are all empty intially
            folder1 = []
            folder2 = []
            folder3 = []
            folder4 = []
            folder5 = []
            folder6 = []

            #add data into folders with appropriate format
            if len(self.KernelBand1.text()) > 0:
                #note that there is a "?" character because it is a wild card
                #case (i.e. incase there is an extra "f" at the end of tif)
                folder1.extend(glob.glob(self.KernelBand1.text() + os.sep + "*.tif?"))
                folder1.extend(glob.glob(self.KernelBand1.text() + os.sep + "*.jpg"))
                folder1.extend(glob.glob(self.KernelBand1.text() + os.sep + "*.jpeg"))
            if len(self.KernelBand2.text()) > 0:
                folder2.extend(glob.glob(self.KernelBand2.text() + os.sep + "*.tif?"))
                folder2.extend(glob.glob(self.KernelBand2.text() + os.sep + "*.jpg"))
                folder2.extend(glob.glob(self.KernelBand2.text() + os.sep + "*.jpeg"))
            if len(self.KernelBand3.text()) > 0:
                folder3.extend(glob.glob(self.KernelBand3.text() + os.sep + "*.tif?"))
                folder3.extend(glob.glob(self.KernelBand3.text() + os.sep + "*.jpg"))
                folder3.extend(glob.glob(self.KernelBand3.text() + os.sep + "*.jpeg"))
            if len(self.KernelBand4.text()) > 0:
                folder4.extend(glob.glob(self.KernelBand4.text() + os.sep + "*.tif?"))
                folder4.extend(glob.glob(self.KernelBand4.text() + os.sep + "*.jpg"))
                folder4.extend(glob.glob(self.KernelBand4.text() + os.sep + "*.jpeg"))
            if len(self.KernelBand5.text()) > 0:
                folder5.extend(glob.glob(self.KernelBand5.text() + os.sep + "*.tif?"))
                folder5.extend(glob.glob(self.KernelBand5.text() + os.sep + "*.jpg"))
                folder5.extend(glob.glob(self.KernelBand5.text() + os.sep + "*.jpeg"))
            if len(self.KernelBand6.text()) > 0:
                folder6.extend(glob.glob(self.KernelBand6.text() + os.sep + "*.tif?"))
                folder6.extend(glob.glob(self.KernelBand6.text() + os.sep + "*.jpg"))
                folder6.extend(glob.glob(self.KernelBand6.text() + os.sep + "*.jpeg"))
            folder1.sort()
            folder2.sort()
            folder3.sort()
            folder4.sort()
            folder5.sort()
            folder6.sort()
            outfolder = self.KernelRenameOutputFolder.text()
            if not os.path.exists(outfolder):
                os.mkdir(outfolder)
            #all folders is a list containing each of the folders
            all_folders = [folder1, folder2, folder3, folder4, folder5, folder6]
            underscore = 1
            for folder in all_folders:

                counter = 1

                if len(folder) > 0:
                    if self.KernelRenameMode.currentIndex() == 0:
                        for tiff in folder:
                            shutil.copyfile(tiff, outfolder + os.sep + "IMG_" + str(counter).zfill(5) + '_' + str(
                                underscore) + '.' + tiff.split('.')[1])
                            counter = counter + 1 #iterate counter
                        underscore = underscore + 1 #iterate underscore
                    elif self.KernelRenameMode.currentIndex() == 2:
                        for tiff in folder:
                            shutil.copyfile(tiff, outfolder + os.sep + str(self.KernelRenamePrefix.text()) + tiff.split(os.sep)[-1])
                            counter = counter + 1
                        underscore = underscore + 1
            self.KernelLog.append("Finished Renaming All Files.")
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e) #print exception
            print("Line: " + str(exc_tb.tb_lineno))

    def getXML(self):
        buf = [0] * 512
        buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
        buf[1] = eRegister.RG_MEDIA_FILE_NAME_A.value
        buf[2] = 3
        res = self.writetokernel(buf) #write buffer to kernel

        filt = chr(res[2]) + chr(res[3]) + chr(res[4])

        buf = [0] * 512
        buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
        buf[1] = eRegister.RG_CAMERA_SETTING.value
        buf[2] = eRegister.RG_SIZE.value

        res = self.writetokernel(buf) #write buffer to kernel
        self.regs = res[2:]
        sens = str(self.getRegister(eRegister.RG_SENSOR_ID.value))
        lens = str(self.getRegister(eRegister.RG_LENS_ID.value))

        buf = [0] * 512
        buf[0] = self.SET_REGISTER_READ_REPORT
        buf[1] = eRegister.RG_CAMERA_ARRAY_TYPE.value
        artype = str(self.writeToKernel(buf)[2])

        buf = [0] * 512
        buf[0] = self.SET_REGISTER_READ_REPORT
        buf[1] = eRegister.RG_CAMERA_LINK_ID.value
        arid = str(self.writeToKernel(buf)[2])

        return (filt, sens, lens, arid, artype)

    def on_KernelMatrixButton_toggled(self):
        buf = [0] * 512
        buf[0] = self.SET_REGISTER_BLOCK_WRITE_REPORT
        buf[1] = eRegister.RG_COLOR_GAMMA_START.value
        buf[2] = 192
        try:
            if self.KernelMatrixButton.isChecked():
                mtx = (np.array([3.2406,-1.5372,-0.498,-0.9689,1.8756,0.0415,0.0557,-0.2040,1.0570]) * 16384.0).astype("uint32")
                offset = (np.array([0.0, 0.0, 0.0])).astype("uint32")
                gamma = (np.array([7.0,0.0,6.5,3.0,6.0,8.0,5.5,13.0,5.0,22.0,4.5,38.0,3.5,102.0,2.5,230.0,1.75,422.0,1.25,679.0,0.875,1062.0,0.625, 1575.0]) * 16.0).astype("uint32")
                # buf[3::] = struct.pack("<36i", *(mtx.tolist() + offset.tolist() + gamma.tolist()))
            else:
                mtx = (np.array([1.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.0]) * 16384.0).astype("uint32")
                offset = (np.array([0.0, 0.0, 0.0])).astype("uint32")
                gamma = (np.array([1.0,0.0,1.0,0.0,1.0,0.0,1.0,0.0,1.0,0.0,1.0,0.0,1.0,0.0,1.0,0.0,1.0,0.0,1.0,0.0,1.0,0.0,1.0,0.0]) * 16.0).astype("uint32")
            buf[3::] = struct.pack("<36L", *(mtx.tolist() + gamma.tolist() + offset.tolist()))

            # for i in range(len(buf)):
            #     buf[i] = int(buf[i])
            self.writetokernel(buf) #write buffer to kernel
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.KernelLog.append("Error: " + str(e) + ' Line: ' + str(exc_tb.tb_lineno))
    #find all availiable drivers
    def getAvailableDrives(self):
        if 'Windows' not in platform.system():
            return []
        drive_bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
        return list(itertools.compress(string.ascii_uppercase, map(lambda x: ord(x) - ord('0'), bin(drive_bitmask)[:1:-1])))
    def on_KernelTransferButton_toggled(self):
        self.KernelLog.append(' ')
        currentcam = None
        try:
            if not self.camera:
                raise ValueError('Device not found')
            else:
                currentcam = self.camera

            if self.KernelTransferButton.isChecked():
                self.driveletters.clear()
                try:

                    for place, cam in enumerate(self.paths):
                        self.camera = cam
                        QtWidgets.QApplication.processEvents()
                        numds = win32api.GetLogicalDriveStrings().split(':\\\x00')[:-1]

                        # time.sleep(2)
                        xmlret = self.getXML()
                        buf = [0] * 512
                        buf[0] = self.SET_COMMAND_REPORT
                        buf[1] = eCommand.CM_TRANSFER_MODE.value
                        self.writetokernel(buf) #write buffer to kernel
                        self.KernelLog.append("Camera " + str(self.pathnames[self.paths.index(cam)]) + " entering Transfer mode")
                        QtWidgets.QApplication.processEvents()
                        treeroot = ET.parse(modpath + os.sep + "template.kernelconfig")
                        treeroot.find("Filter").text = xmlret[0]
                        treeroot.find("Sensor").text = xmlret[1]
                        treeroot.find("Lens").text = xmlret[2]
                        treeroot.find("ArrayID").text = xmlret[3]
                        treeroot.find("ArrayType").text = xmlret[4]
                        keep_looping = True
                        while keep_looping:
                            numds = set(numds)
                            numds1 = set(win32api.GetLogicalDriveStrings().split(':\\\x00')[:-1])
                            if numds == numds1:
                                pass
                            else:

                                drv = list(numds1 - numds)[0]
                                if len(drv) == 1:
                                    self.driveletters.append(drv)

                                    self.KernelLog.append("Camera " + str(self.pathnames[self.paths.index(cam)]) + " successfully connected to drive " + drv + ":" + os.sep)
                                    files = glob.glob(drv + r":" + os.sep + r"dcim/*/*.[tm]*", recursive=True)
                                    folders = glob.glob(drv + r":" + os.sep + r"dcim/*/")
                                    if folders:
                                        for fold in folders:
                                            if os.path.exists(fold + str(self.pathnames[self.paths.index(cam)]) + ".kernelconfig"):
                                                os.unlink(fold + str(self.pathnames[self.paths.index(cam)]) + ".kernelconfig")
                                            treeroot.write(fold + str(self.pathnames[self.paths.index(cam)]) + ".kernelconfig")
                                    else:
                                        if not os.path.exists(drv + r":" + os.sep + r"dcim" + os.sep + str(self.pathnames[self.paths.index(cam)])):
                                            os.mkdir(drv + r":" + os.sep + r"dcim")
                                            os.mkdir(drv + r":" + os.sep + r"dcim" + os.sep + str(self.pathnames[self.paths.index(cam)]))
                                        treeroot.write(
                                            drv + r":" + os.sep + r"dcim" + os.sep + str(self.pathnames[self.paths.index(cam)]) + ".kernelconfig")
                                    # os.unlink(files[-1])
                                    keep_looping = False
                                # time.sleep(15)


                                else:
                                    numds = win32api.GetLogicalDriveStrings().split(':\\\x00')[:-1]
                                QtWidgets.QApplication.processEvents()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    self.KernelLog.append(str(e))
                    self.KernelLog.append("Line: " + str(exc_tb.tb_lineno))
                    QtWidgets.QApplication.processEvents()
                    self.camera = currentcam

                self.camera = currentcam


                self.modalwindow = KernelTransfer(self)
                self.modalwindow.resize(400, 200) #resize the window
                self.modalwindow.exec_()
                # self.KernelLog.append("We made it out of transfer window")
                if self.yestransfer:
                    # self.KernelLog.append("Transfer was enabled")
                    for place, drv in enumerate(self.driveletters):
                        ix = place + 1
                        self.KernelLog.append("Extracting images from Camera " + str(ix) + " of " + str(len(self.driveletters)) + ", at drive " + drv + r':')
                        QtWidgets.QApplication.processEvents()
                        if os.path.isdir(drv + r":" + os.sep + r"dcim"):
                            # try:
                            folders = glob.glob(drv + r":" + os.sep + r"dcim/*/")
                            files = glob.glob(drv + r":" + os.sep + r"dcim/*/*", recursive=True)
                            threechar = ''
                            try:
                                threechar = files[0].split(os.sep)[-1][1:4]
                            except Exception as e:
                                self.KernelLog.append(r"No files detected in drive " + drv + r'. Moving to next camera.')
                                pass
                            for fold in folders:


                                if os.path.exists(self.transferoutfolder + os.sep + threechar):
                                    foldercount = 1
                                    endloop = False
                                    while endloop is False:
                                        outdir = self.transferoutfolder + os.sep + threechar + '_' + str(foldercount)
                                        if os.path.exists(outdir):
                                            foldercount += 1
                                        else:
                                            shutil.copytree(fold, outdir)
                                            endloop = True
                                else:
                                    outdir = self.transferoutfolder + os.sep + threechar
                                    shutil.copytree(fold, outdir)
                                QtWidgets.QApplication.processEvents()
                                # for file in files:
                                #     # if file.split(os.sep)[-1][1:4] == threechar:

                                # else:
                                #     threechar = file.split(os.sep)[-1][1:4]
                                #     os.mkdir(self.transferoutfolder + os.sep + threechar)
                                #     shutil.copy(file, self.transferoutfolder + os.sep + threechar)
                                QtWidgets.QApplication.processEvents()
                            if threechar:
                                self.KernelLog.append("Finished extracting images from Camera " + str(threechar) + " number " + str(place + 1) + " of " + str(len(self.driveletters)) + ", at drive " + drv + r':')
                            QtWidgets.QApplication.processEvents()
                        else:
                            self.KernelLog.append("No DCIM folder found in drive " + str(drv) + r":")
                            QtWidgets.QApplication.processEvents()
                    self.yestransfer = False
                if self.yesdelete:
                    for drv in self.driveletters:
                        if os.path.isdir(drv + r":" + os.sep + r"dcim"):
                            # try:
                            files = glob.glob(drv + r":" + os.sep + r"dcim/*/*")
                            self.KernelLog.append("Deleting files from drive " + str(drv))
                            for file in files:
                                os.unlink(file)
                            self.KernelLog.append("Finished deleting files from drive " + str(drv))
                    self.yesdelete = False
                    # self.modalwindow = KernelDelete(self)
                    # self.modalwindow.resize(400, 200) #resize the window
                    # self.modalwindow.exec_()

            else:
                for place, cam in enumerate(self.paths):
                    try:
                        self.camera = cam
                        self.exitTransfer(self.driveletters[place])
                    except:

                        pass
            self.camera = currentcam
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            # self.exitTransfer()
            # self.KernelTransferButton.setChecked(False)
            self.KernelLog.append("Error: " + str(e) + ' Line: ' + str(exc_tb.tb_lineno))
            QtWidgets.QApplication.processEvents()
            self.camera = currentcam


    def on_KernelExposureMode_currentIndexChanged(self, int = 0):
        # self.KernelExposureMode.blockSignals(True)
        if self.KernelExposureMode.currentIndex() == 1: #Manual

            self.KernelMESettingsButton.setEnabled(True)
            self.KernelAESettingsButton.setEnabled(False)

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_SHUTTER.value
            buf[2] = 9

            res = self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_ISO.value
            buf[2] = 1

            res = self.writetokernel(buf) #write buffer to kernel

            QtWidgets.QApplication.processEvents()
        else: #Auto

            self.KernelMESettingsButton.setEnabled(False)
            self.KernelAESettingsButton.setEnabled(True)

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_SHUTTER.value
            buf[2] = 0

            res = self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_AE_SELECTION.value
            # buf[2] = self.AutoAlgorithm.currentIndex()
            res = self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_AE_MAX_SHUTTER.value
            # buf[2] = self.AutoMaxShutter.currentIndex()

            res = self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_AE_MIN_SHUTTER.value
            # buf[2] = self.AutoMinShutter.currentIndex()

            res = self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_AE_MAX_GAIN.value
            # buf[2] = self.AutoMaxISO.currentIndex()

            res = self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_AE_F_STOP.value
            # buf[2] = self.AutoFStop.currentIndex()

            res = self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_AE_GAIN.value
            # buf[2] = self.AutoGain.currentIndex()

            res = self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512
            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_AE_SETPOINT.value
            # buf[2] = self.AutoSetpoint.currentIndex()

            res = self.writetokernel(buf) #write buffer to kernel

            QtWidgets.QApplication.processEvents()
        # self.KernelExposureMode.blockSignals(False)
    def on_KernelAESettingsButton_released(self):
        self.A_Shutter_Window = A_EXP_Control(self)
        self.A_Shutter_Window.resize(350, 350)
        self.A_Shutter_Window.exec_()
        # self.KernelUpdate()
    def on_KernelMESettingsButton_released(self):
        self.M_Shutter_Window = M_EXP_Control(self)
        self.M_Shutter_Window.resize(250, 125)
        self.M_Shutter_Window.exec_()
        # self.KernelUpdate()


    def on_KernelCaptureButton_released(self):
        # if self.KernelCameraSelect.currentIndex() == 0:
        for cam in self.paths:
            self.camera = cam
            self.captureImage()
        self.camera = self.paths[0]
        # else:
        #     self.captureImage()
    def captureImage(self):
        try:
            buf = [0] * 512

            buf[0] = self.SET_COMMAND_REPORT
            if self.KernelCaptureMode.currentIndex() == 0:
                buf[1] = eCommand.CM_CAPTURE_PHOTO.value

            elif self.KernelCaptureMode.currentIndex() == 1:
                buf[1] = eCommand.CM_CONTINUOUS.value

            elif self.KernelCaptureMode.currentIndex() == 2:
                buf[1] = eCommand.CM_TIME_LAPSE.value

            elif self.KernelCaptureMode.currentIndex() == 3:
                buf[1] = eCommand.CM_RECORD_VIDEO.value

            elif self.KernelCaptureMode.currentIndex() == 4:
                buf[1] = eCommand.CM_RECORD_LOOPING_VIDEO.value

            else:
                self.KernelLog.append("Invalid capture mode.")

            if self.capturing == False:
                buf[2] = 1
                self.capturing = True

            else:
                buf[2] = 0
                self.capturing = False

            res = self.writetokernel(buf) #write buffer to kernel #write buffer to kernel
            self.KernelUpdate()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))

    def getRegister(self, code):
        #get the register (software interface to a hardware device)
        if code < eRegister.RG_SIZE.value:
            return self.regs[code]
        else:
            return 0

    def setRegister(self, code, value):
        if code >= eRegister.RG_SIZE.value:
            return False
        elif value == self.regs[code]:
            return False
        else:
            self.regs[code] = value
            return True
    def on_TestButton_released(self):
        buf = [0] * 512
        buf[0] = self.SET_COMMAND_REPORT
        buf[1] = eRegister.RG_CAMERA_ARRAY_TYPE.value
        artype = self.writetokernel(buf) #write buffer to kernel[2]
        print(artype)
        try:
            self.KernelUpdate()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))
    def writeToKernel(self, buffer):
        """
        def writeToKernel(self,buffer) is the function declaration for the write to kernel function

        The function is passed an object (self) along with the buffer that it is writing into the
        kernel camera
        """
        try:
            dev = hid.device() #dev is interfacing with the camera through USB by calling hid.device()
            dev.open_path(self.camera) #opening a path to write to the camera, now this is a camera device
            q = dev.write(buffer) #write the buffer to the camera
            if buffer[0] == self.SET_COMMAND_REPORT and buffer[1] == eCommand.CM_TRANSFER_MODE.data:
                dev.close()
                return q
            else: #if the buffer is not being closed read the length of the buffer???
                r = dev.read(self.BUFF_LEN)
                dev.close()
                return r #return the length????
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.KernelLog.append("Error: " + str(e) + ' Line: ' + str(exc_tb.tb_lineno))


    def on_KernelBeep_toggled(self):
        """def on_KernelBeep_toggled(self)
        is passed an object(self) and enables the beeper???"""
        buf = [0] * 512

        buf[0] = self.SET_REGISTER_WRITE_REPORT
        buf[1] = eRegister.RG_BEEPER_ENABLE.value
        if self.KernelBeep.isChecked():
            buf[2] = 1
        else:
            buf[2] = 0

        res = self.writetokernel(buf) #write buffer to kernel
        try:
            self.KernelUpdate()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))

    def on_KernelPWMSignal_toggled(self):
        """def on_KernelPWMSignal_toggled(self)
        is passed an object(self) """
        buf = [0] * 512

        buf[0] = self.SET_REGISTER_WRITE_REPORT
        buf[1] = eRegister.RG_PWM_TRIGGER.value
        if self.KernelPWMSignal.isChecked():
            buf[2] = 1
        else:
            buf[2] = 0

        res = self.writetokernel(buf) #write buffer to kernel
        try:
            self.KernelUpdate()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))

    def on_KernelAdvancedSettingsButton_released(self):
        """def on_KernelAdvancedSettingsButton_released(self)

        is passed an object(self), it resizes the window"""
        self.Advancedwindow = AdvancedOptions(self)
        self.Advancedwindow.resize(400, 200) #resize the window
        self.Advancedwindow.exec_()


    def on_KernelFolderCount_currentIndexChanged(self, int = 0):
        """def on_KernelFolderCount_currentIndexChanged(self)
        is passed an object(self), """
        buf = [0] * 512
        buf[0] = self.SET_REGISTER_WRITE_REPORT
        buf[1] = eRegister.RG_MEDIA_FILES_CNT.value
        buf[2] = self.KernelFolderCount.currentIndex()

        self.writetokernel(buf) #write buffer to kernel
        try:
            self.KernelUpdate()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))

    def on_KernelVideoOut_currentIndexChanged(self, int = 0):
        """def on_KernelVideoOut_currentIndexChanged(self)

        is passed an object(self) and an int = 0 """
        if self.KernelVideoOut.currentIndex() == 0:  # No Output
            buf = [0] * 512

            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_DAC.value  # DAC Register
            buf[2] = 0
            self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512

            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_HDMI.value  # HDMI Register
            buf[2] = 0
            self.writetokernel(buf) #write buffer to kernel
        elif self.KernelVideoOut.currentIndex() == 1:  # HDMI
            buf = [0] * 512

            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_DAC.value  # DAC Register
            buf[2] = 0
            self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512

            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_HDMI.value  # HDMI Register
            buf[2] = 1
            self.writetokernel(buf) #write buffer to kernel
        elif self.KernelVideoOut.currentIndex() == 2:  # SD( DAC )
            buf = [0] * 512

            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_DAC.value  # DAC Register
            buf[2] = 1
            self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512

            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_HDMI.value  # HDMI Register
            buf[2] = 0
            self.writetokernel(buf) #write buffer to kernel
        else:  # Both outputs
            buf = [0] * 512

            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_DAC.value  # DAC Register
            buf[2] = 1
            self.writetokernel(buf) #write buffer to kernel

            buf = [0] * 512

            buf[0] = self.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_HDMI.value  # HDMI Register
            buf[2] = 1
            self.writetokernel(buf) #write buffer to kernel
        # self.camera.close()
        try:
            self.KernelUpdate()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))

    def on_KernelIntervalButton_released(self):

        """
        Interval Button sets the interval time for kernel
        """
        self.modalwindow = KernelModal(self)
        self.modalwindow.resize(400, 200) #resize the window
        self.modalwindow.exec_()

        num = self.seconds % 168
        if num == 0:
            num = 1
        self.seconds = num
        try:
            self.KernelUpdate()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))

    def on_KernelCANButton_released(self):
        """

        """
        self.modalwindow = KernelCAN(self)
        self.modalwindow.resize(400, 200) #resize the window
        self.modalwindow.exec_()

    def on_KernelTimeButton_released(self):
        self.modalwindow = KernelTime(self)
        self.modalwindow.resize(400, 200) #resize the window
        self.modalwindow.exec_()


    def writeToIntervalLine(self):
        self.KernelIntervalLine.clear()
        self.KernelIntervalLine.setText(
            str(self.weeks) + 'w, ' + str(self.days) + 'd, ' + str(self.hours) + 'h, ' + str(self.minutes) + 'm,' + str(
                self.seconds) + 's')

    #########Pre-Process Steps: Start#################
    def on_PreProcessFilter_currentIndexChanged(self):
        if (self.PreProcessCameraModel.currentIndex() == 2 and self.PreProcessFilter.currentIndex() == 2) or (self.PreProcessCameraModel.currentIndex() == 3 and self.PreProcessFilter.currentIndex() == 0):
            self.PreProcessColorBox.setEnabled(True)
        elif self.PreProcessCameraModel.currentIndex() == 1:
            if self.PreProcessFilter.currentIndex() in [2, 4, 6, 9, 10, 12]:
                self.PreProcessVignette.setEnabled(True)
            else:
                self.PreProcessVignette.setChecked(False)
                self.PreProcessVignette.setEnabled(False)
        else:
            self.PreProcessColorBox.setChecked(False)
            self.PreProcessColorBox.setEnabled(False)
    def on_PreProcessCameraModel_currentIndexChanged(self, int):
        """
        on the process tab this function populates the filter dropdown with all of the filter options, the camera model
        is pre-populated, however the filter options vary between cameras and thus need a function to populate the list
        """
        self.PreProcessVignette.setChecked(False)
        self.PreProcessVignette.setEnabled(False)
        if self.PreProcessCameraModel.currentIndex() == 0 or self.PreProcessCameraModel.currentIndex() == 1:


            self.PreProcessFilter.clear()
            self.PreProcessFilter.addItems(["405", "450", "490", "518", "550", "590", "615", "632", "650", "685", "725", "780", "808", "850", "880","940","945"])
            self.PreProcessFilter.setEnabled(True)
            self.PreProcessLens.clear()
            self.PreProcessLens.setEnabled(False)
        elif self.PreProcessCameraModel.currentIndex() == 2:
            self.PreProcessFilter.clear()
            self.PreProcessFilter.addItems(
                ["550/660/850", "475/550/850", "644 (RGB)", "850"])
            self.PreProcessFilter.setEnabled(True)
            self.PreProcessLens.clear()
            self.PreProcessLens.setEnabled(False)
        elif self.PreProcessCameraModel.currentIndex() == 3:
            self.PreProcessFilter.clear()
            self.PreProcessFilter.addItems(["RGB", "RGN", "NGB", "NIR", "OCN"])
            self.PreProcessFilter.setEnabled(True)
            self.PreProcessLens.clear()
            self.PreProcessLens.addItems(["3.37mm (Survey3W)", "8.25mm (Survey3N)"])
            self.PreProcessLens.setEnabled(True)
        elif self.PreProcessCameraModel.currentIndex() == 4:
            self.PreProcessFilter.clear()
            self.PreProcessFilter.addItems(["Red + NIR (NDVI)", "NIR", "Red", "Green", "Blue", "RGB"])
            self.PreProcessFilter.setEnabled(True)
            self.PreProcessLens.clear()
            self.PreProcessLens.addItems(["3.97mm"])
            self.PreProcessLens.setEnabled(False)
        elif self.PreProcessCameraModel.currentIndex() == 5:
            self.PreProcessFilter.clear()
            self.PreProcessFilter.addItems(["Blue + NIR (NDVI)"])
            self.PreProcessFilter.setEnabled(False)
            self.PreProcessLens.clear()
            self.PreProcessLens.addItems(["3.97mm"])
            self.PreProcessLens.setEnabled(False)
        elif self.PreProcessCameraModel.currentIndex() == 6:
            self.PreProcessFilter.clear()
            self.PreProcessFilter.addItems(["Red + NIR (NDVI)"])
            self.PreProcessFilter.setEnabled(False)
            self.PreProcessLens.clear()
            self.PreProcessLens.addItems(["3.97mm"])
            self.PreProcessLens.setEnabled(False)
        elif self.PreProcessCameraModel.currentIndex() == 7:
            self.PreProcessFilter.clear()
            self.PreProcessFilter.addItems(["RGN"])
            self.PreProcessFilter.setEnabled(False)
            self.PreProcessLens.clear()
            self.PreProcessLens.addItems(["3.97mm"])
            self.PreProcessLens.setEnabled(False)
        elif self.PreProcessCameraModel.currentIndex() > 7:
            self.PreProcessFilter.clear()
            self.PreProcessFilter.addItems(["Red + NIR (NDVI)"])
            self.PreProcessFilter.setEnabled(False)
            self.PreProcessLens.clear()
            self.PreProcessLens.addItems(["3.97mm"])
            self.PreProcessLens.setEnabled(False)
        else:
            self.PreProcessLens.clear()
            self.PreProcessFilter.setEnabled(False)
            self.PreProcessLens.clear()
            self.PreProcessLens.setEnabled(False)

    def on_CalibrationCameraModel_currentIndexChanged(self, int):
        """
        on the calibrate tab this function populates the filter dropdown with all of the filter options, the camera model
        is pre-populated, however the filter options vary between cameras and thus need a function to populate the list
        """
        if self.CalibrationCameraModel.currentIndex() == 0 or self.CalibrationCameraModel.currentIndex() == 1:
            self.CalibrationFilter.clear()
            self.CalibrationFilter.addItems(["405", "450", "490", "518", "550", "590", "615", "632", "650", "685", "725", "780", "808", "850", "880","940","945"])
            self.CalibrationFilter.setEnabled(True)
            self.CalibrationLens.clear()
            self.CalibrationLens.setEnabled(False)
        elif self.CalibrationCameraModel.currentIndex() == 2:
            self.CalibrationFilter.clear()
            self.CalibrationFilter.addItems(
                ["550/660/850", "475/550/850", "644 (RGB)", "850"])
            self.CalibrationFilter.setEnabled(True)
            self.CalibrationLens.clear()
            self.CalibrationLens.setEnabled(False)
        elif self.CalibrationCameraModel.currentIndex() == 3:
            self.CalibrationFilter.clear()
            self.CalibrationFilter.addItems(["RGB", "RGN", "NGB", "NIR", "OCN" ])
            self.CalibrationFilter.setEnabled(True)
            self.CalibrationLens.clear()
            self.CalibrationLens.addItems([" 3.37mm (Survey3W)", "8.25mm (Survey3N)"])
            self.CalibrationLens.setEnabled(True)
        elif self.CalibrationCameraModel.currentIndex() == 4:
            self.CalibrationFilter.clear()
            self.CalibrationFilter.addItems(["Red + NIR (NDVI)", "NIR", "Red", "Green", "Blue", "RGB"])
            self.CalibrationFilter.setEnabled(True)
            self.CalibrationLens.clear()
            self.CalibrationLens.addItems(["3.97mm"])
            self.CalibrationLens.setEnabled(False)
        elif self.CalibrationCameraModel.currentIndex() == 5:
            self.CalibrationFilter.clear()
            self.CalibrationFilter.addItems(["Blue + NIR (NDVI)"])
            self.CalibrationFilter.setEnabled(False)
            self.CalibrationLens.clear()
            self.CalibrationLens.addItems(["3.97mm"])
            self.CalibrationLens.setEnabled(False)
        elif self.CalibrationCameraModel.currentIndex() == 5:
            self.CalibrationFilter.clear()
            self.CalibrationFilter.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter.setEnabled(False)
            self.CalibrationLens.clear()
            self.CalibrationLens.addItems(["3.97mm"])
            self.CalibrationLens.setEnabled(False)

        elif self.CalibrationCameraModel.currentIndex() == 6:
            self.CalibrationFilter.clear()
            self.CalibrationFilter.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter.setEnabled(False)
            self.CalibrationLens.clear()
            self.CalibrationLens.addItems(["3.97mm"])
            self.CalibrationLens.setEnabled(False)

        elif self.CalibrationCameraModel.currentIndex() == 7:
            self.CalibrationFilter.clear()
            self.CalibrationFilter.addItems(["RGN"])
            self.CalibrationFilter.setEnabled(False)
            self.CalibrationLens.clear()
            self.CalibrationLens.addItems(["3.97mm"])
            self.CalibrationLens.setEnabled(False)
        elif self.CalibrationCameraModel.currentIndex() > 7:
            self.CalibrationFilter.clear()
            self.CalibrationFilter.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter.setEnabled(False)
            self.CalibrationLens.clear()
            self.CalibrationLens.addItems(["3.97mm"])
            self.CalibrationLens.setEnabled(False)


        else:
            self.CalibrationLens.clear()
            self.CalibrationFilter.setEnabled(False)
            self.CalibrationLens.clear()
            self.CalibrationLens.setEnabled(False)

    def on_CalibrationCameraModel_2_currentIndexChanged(self, int):
        """
        on the calibrate tab this function populates the filter dropdown with all of the filter options, the camera model
        is pre-populated, however the filter options vary between cameras and thus need a function to populate the list
        """
        if self.CalibrationCameraModel_2.currentIndex() == 0 or self.CalibrationCameraModel_2.currentIndex() == 1:
            self.CalibrationFilter_2.clear()
            self.CalibrationFilter_2.addItems(
                ["405", "450", "490", "518", "550", "590", "615", "632", "650", "685", "725", "780", "808", "850",
                 "880","940","945"])
            self.CalibrationFilter_2.setEnabled(True)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.setEnabled(False)
        elif self.CalibrationCameraModel_2.currentIndex() == 2:
            self.CalibrationFilter_2.clear()
            self.CalibrationFilter_2.addItems(
                ["550/660/850", "475/550/850", "644 (RGB)", "850"])
            self.CalibrationFilter_2.setEnabled(True)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.setEnabled(False)
        elif self.CalibrationCameraModel_2.currentIndex() == 3:
            self.CalibrationFilter_2.clear()
            self.CalibrationFilter_2.addItems(["RGB", "RGN", "NGB", "NIR", "OCN"])
            self.CalibrationFilter_2.setEnabled(True)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.addItems([" 3.37mm (Survey3W)", "8.25mm (Survey3N)"])
            self.CalibrationLens_2.setEnabled(True)
        elif self.CalibrationCameraModel_2.currentIndex() == 4:
            self.CalibrationFilter_2.clear()
            self.CalibrationFilter_2.addItems(["Red + NIR (NDVI)", "NIR", "Red", "Green", "Blue", "RGB"])
            self.CalibrationFilter_2.setEnabled(True)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.addItems(["3.97mm"])
            self.CalibrationLens_2.setEnabled(False)
        elif self.CalibrationCameraModel_2.currentIndex() == 5:
            self.CalibrationFilter_2.clear()
            self.CalibrationFilter_2.addItems(["Blue + NIR (NDVI)"])
            self.CalibrationFilter_2.setEnabled(False)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.addItems(["3.97mm"])
            self.CalibrationLens_2.setEnabled(False)
        elif self.CalibrationCameraModel_2.currentIndex() == 5:
            self.CalibrationFilter_2.clear()
            self.CalibrationFilter_2.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_2.setEnabled(False)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.addItems(["3.97mm"])
            self.CalibrationLens_2.setEnabled(False)

        elif self.CalibrationCameraModel_2.currentIndex() == 6:
            self.CalibrationFilter_2.clear()
            self.CalibrationFilter_2.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_2.setEnabled(False)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.addItems(["3.97mm"])
            self.CalibrationLens_2.setEnabled(False)

        elif self.CalibrationCameraModel_2.currentIndex() == 7:
            self.CalibrationFilter_2.clear()
            self.CalibrationFilter_2.addItems(["RGN"])
            self.CalibrationFilter_2.setEnabled(False)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.addItems(["3.97mm"])
            self.CalibrationLens_2.setEnabled(False)
        elif self.CalibrationCameraModel_2.currentIndex() > 7:
            self.CalibrationFilter_2.clear()
            self.CalibrationFilter_2.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_2.setEnabled(False)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.addItems(["3.97mm"])
            self.CalibrationLens_2.setEnabled(False)


        else:
            self.CalibrationLens_2.clear()
            self.CalibrationFilter_2.setEnabled(False)
            self.CalibrationLens_2.clear()
            self.CalibrationLens_2.setEnabled(False)

    def on_CalibrationCameraModel_3_currentIndexChanged(self, int):
        """
        on the calibrate tab this function populates the filter dropdown with all of the filter options, the camera model
        is pre-populated, however the filter options vary between cameras and thus need a function to populate the list
        """
        if self.CalibrationCameraModel_3.currentIndex() == 0 or self.CalibrationCameraModel_3.currentIndex() == 1:
            self.CalibrationFilter_3.clear()
            self.CalibrationFilter_3.addItems(
                ["405", "450", "490", "518", "550", "590", "615", "632", "650", "685", "725", "780", "808", "850",
                 "880","940","945"])
            self.CalibrationFilter_3.setEnabled(True)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.setEnabled(False)
        elif self.CalibrationCameraModel_3.currentIndex() == 2:
            self.CalibrationFilter_3.clear()
            self.CalibrationFilter_3.addItems(
                ["550/660/850", "475/550/850", "644 (RGB)", "850"])
            self.CalibrationFilter_3.setEnabled(True)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.setEnabled(False)
        elif self.CalibrationCameraModel_3.currentIndex() == 3:
            self.CalibrationFilter_3.clear()
            self.CalibrationFilter_3.addItems(["RGB", "RGN", "NGB", "NIR", "OCN"])
            self.CalibrationFilter_3.setEnabled(True)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.addItems([" 3.37mm (Survey3W)", "8.25mm (Survey3N)"])
            self.CalibrationLens_3.setEnabled(True)
        elif self.CalibrationCameraModel_3.currentIndex() == 4:
            self.CalibrationFilter_3.clear()
            self.CalibrationFilter_3.addItems(["Red + NIR (NDVI)", "NIR", "Red", "Green", "Blue", "RGB"])
            self.CalibrationFilter_3.setEnabled(True)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.addItems(["3.97mm"])
            self.CalibrationLens_3.setEnabled(False)
        elif self.CalibrationCameraModel_3.currentIndex() == 5:
            self.CalibrationFilter_3.clear()
            self.CalibrationFilter_3.addItems(["Blue + NIR (NDVI)"])
            self.CalibrationFilter_3.setEnabled(False)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.addItems(["3.97mm"])
            self.CalibrationLens_3.setEnabled(False)
        elif self.CalibrationCameraModel_3.currentIndex() == 5:
            self.CalibrationFilter_3.clear()
            self.CalibrationFilter_3.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_3.setEnabled(False)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.addItems(["3.97mm"])
            self.CalibrationLens_3.setEnabled(False)

        elif self.CalibrationCameraModel_3.currentIndex() == 6:
            self.CalibrationFilter_3.clear()
            self.CalibrationFilter_3.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_3.setEnabled(False)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.addItems(["3.97mm"])
            self.CalibrationLens_3.setEnabled(False)

        elif self.CalibrationCameraModel_3.currentIndex() == 7:
            self.CalibrationFilter_3.clear()
            self.CalibrationFilter_3.addItems(["RGN"])
            self.CalibrationFilter_3.setEnabled(False)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.addItems(["3.97mm"])
            self.CalibrationLens_3.setEnabled(False)
        elif self.CalibrationCameraModel_3.currentIndex() > 7:
            self.CalibrationFilter_3.clear()
            self.CalibrationFilter_3.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_3.setEnabled(False)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.addItems(["3.97mm"])
            self.CalibrationLens_3.setEnabled(False)


        else:
            self.CalibrationLens_3.clear()
            self.CalibrationFilter_3.setEnabled(False)
            self.CalibrationLens_3.clear()
            self.CalibrationLens_3.setEnabled(False)

    def on_CalibrationCameraModel_4_currentIndexChanged(self, int):
        """
        on the calibrate tab this function populates the filter dropdown with all of the filter options, the camera model
        is pre-populated, however the filter options vary between cameras and thus need a function to populate the list
        """
        if self.CalibrationCameraModel_4.currentIndex() == 0 or self.CalibrationCameraModel_4.currentIndex() == 1:
            self.CalibrationFilter_4.clear()
            self.CalibrationFilter_4.addItems(
                ["405", "450", "490", "518", "550", "590", "615", "632", "650", "685", "725", "780", "808", "850",
                 "880","940","945"])
            self.CalibrationFilter_4.setEnabled(True)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.setEnabled(False)
        elif self.CalibrationCameraModel_4.currentIndex() == 2:
            self.CalibrationFilter_4.clear()
            self.CalibrationFilter_4.addItems(
                ["550/660/850", "475/550/850", "644 (RGB)", "850"])
            self.CalibrationFilter_4.setEnabled(True)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.setEnabled(False)
        elif self.CalibrationCameraModel_4.currentIndex() == 3:
            self.CalibrationFilter_4.clear()
            self.CalibrationFilter_4.addItems(["RGB", "RGN", "NGB", "NIR", "OCN"])
            self.CalibrationFilter_4.setEnabled(True)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.addItems([" 3.37mm (Survey3W)", "8.25mm (Survey3N)"])
            self.CalibrationLens_4.setEnabled(True)
        elif self.CalibrationCameraModel_4.currentIndex() == 4:
            self.CalibrationFilter_4.clear()
            self.CalibrationFilter_4.addItems(["Red + NIR (NDVI)", "NIR", "Red", "Green", "Blue", "RGB"])
            self.CalibrationFilter_4.setEnabled(True)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.addItems(["3.97mm"])
            self.CalibrationLens_4.setEnabled(False)
        elif self.CalibrationCameraModel_4.currentIndex() == 5:
            self.CalibrationFilter_4.clear()
            self.CalibrationFilter_4.addItems(["Blue + NIR (NDVI)"])
            self.CalibrationFilter_4.setEnabled(False)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.addItems(["3.97mm"])
            self.CalibrationLens_4.setEnabled(False)
        elif self.CalibrationCameraModel_4.currentIndex() == 5:
            self.CalibrationFilter_4.clear()
            self.CalibrationFilter_4.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_4.setEnabled(False)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.addItems(["3.97mm"])
            self.CalibrationLens_4.setEnabled(False)

        elif self.CalibrationCameraModel_4.currentIndex() == 6:
            self.CalibrationFilter_4.clear()
            self.CalibrationFilter_4.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_4.setEnabled(False)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.addItems(["3.97mm"])
            self.CalibrationLens_4.setEnabled(False)

        elif self.CalibrationCameraModel_4.currentIndex() == 7:
            self.CalibrationFilter_4.clear()
            self.CalibrationFilter_4.addItems(["RGN"])
            self.CalibrationFilter_4.setEnabled(False)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.addItems(["3.97mm"])
            self.CalibrationLens_4.setEnabled(False)
        elif self.CalibrationCameraModel_4.currentIndex() > 7:
            self.CalibrationFilter_4.clear()
            self.CalibrationFilter_4.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_4.setEnabled(False)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.addItems(["3.97mm"])
            self.CalibrationLens_4.setEnabled(False)


        else:
            self.CalibrationLens_4.clear()
            self.CalibrationFilter_4.setEnabled(False)
            self.CalibrationLens_4.clear()
            self.CalibrationLens_4.setEnabled(False)

    def on_CalibrationCameraModel_5_currentIndexChanged(self, int):
        """
        on the calibrate tab this function populates the filter dropdown with all of the filter options, the camera model
        is pre-populated, however the filter options vary between cameras and thus need a function to populate the list
        """
        if self.CalibrationCameraModel_5.currentIndex() == 0 or self.CalibrationCameraModel_5.currentIndex() == 1:
            self.CalibrationFilter_5.clear()
            self.CalibrationFilter_5.addItems(
                ["405", "450", "490", "518", "550", "590", "615", "632", "650", "685", "725", "780", "808", "850",
                 "880","940","945"])
            self.CalibrationFilter_5.setEnabled(True)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.setEnabled(False)
        elif self.CalibrationCameraModel_5.currentIndex() == 2:
            self.CalibrationFilter_5.clear()
            self.CalibrationFilter_5.addItems(
                ["550/660/850", "475/550/850", "644 (RGB)", "850"])
            self.CalibrationFilter_5.setEnabled(True)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.setEnabled(False)
        elif self.CalibrationCameraModel_5.currentIndex() == 3:
            self.CalibrationFilter_5.clear()
            self.CalibrationFilter_5.addItems(["RGB", "RGN", "NGB", "NIR", "OCN"])
            self.CalibrationFilter_5.setEnabled(True)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.addItems([" 3.37mm (Survey3W)", "8.25mm (Survey3N)"])
            self.CalibrationLens_5.setEnabled(True)
        elif self.CalibrationCameraModel_5.currentIndex() == 4:
            self.CalibrationFilter_5.clear()
            self.CalibrationFilter_5.addItems(["Red + NIR (NDVI)", "NIR", "Red", "Green", "Blue", "RGB"])
            self.CalibrationFilter_5.setEnabled(True)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.addItems(["3.97mm"])
            self.CalibrationLens_5.setEnabled(False)
        elif self.CalibrationCameraModel_5.currentIndex() == 5:
            self.CalibrationFilter_5.clear()
            self.CalibrationFilter_5.addItems(["Blue + NIR (NDVI)"])
            self.CalibrationFilter_5.setEnabled(False)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.addItems(["3.97mm"])
            self.CalibrationLens_5.setEnabled(False)
        elif self.CalibrationCameraModel_5.currentIndex() == 5:
            self.CalibrationFilter_5.clear()
            self.CalibrationFilter_5.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_5.setEnabled(False)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.addItems(["3.97mm"])
            self.CalibrationLens_5.setEnabled(False)

        elif self.CalibrationCameraModel_5.currentIndex() == 6:
            self.CalibrationFilter_5.clear()
            self.CalibrationFilter_5.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_5.setEnabled(False)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.addItems(["3.97mm"])
            self.CalibrationLens_5.setEnabled(False)

        elif self.CalibrationCameraModel_5.currentIndex() == 7:
            self.CalibrationFilter_5.clear()
            self.CalibrationFilter_5.addItems(["RGN"])
            self.CalibrationFilter_5.setEnabled(False)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.addItems(["3.97mm"])
            self.CalibrationLens_5.setEnabled(False)
        elif self.CalibrationCameraModel_5.currentIndex() > 7:
            self.CalibrationFilter_5.clear()
            self.CalibrationFilter_5.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_5.setEnabled(False)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.addItems(["3.97mm"])
            self.CalibrationLens_5.setEnabled(False)


        else:
            self.CalibrationLens_5.clear()
            self.CalibrationFilter_5.setEnabled(False)
            self.CalibrationLens_5.clear()
            self.CalibrationLens_5.setEnabled(False)

    def on_CalibrationCameraModel_6_currentIndexChanged(self, int):
        """
        on the calibrate tab this function populates the filter dropdown with all of the filter options, the camera model
        is pre-populated, however the filter options vary between cameras and thus need a function to populate the list
        """
        if self.CalibrationCameraModel_6.currentIndex() == 0 or self.CalibrationCameraModel_6.currentIndex() == 1:
            self.CalibrationFilter_6.clear()
            self.CalibrationFilter_6.addItems(
                ["405", "450", "490", "518", "550", "590", "615", "632", "650", "685", "725", "780", "808", "850",
                 "880","940","945"])
            self.CalibrationFilter_6.setEnabled(True)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.setEnabled(False)
        elif self.CalibrationCameraModel_6.currentIndex() == 2:
            self.CalibrationFilter_6.clear()
            self.CalibrationFilter_6.addItems(
                ["550/660/850", "475/550/850", "644 (RGB)", "850"])
            self.CalibrationFilter_6.setEnabled(True)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.setEnabled(False)
        elif self.CalibrationCameraModel_6.currentIndex() == 3:
            self.CalibrationFilter_6.clear()
            self.CalibrationFilter_6.addItems(["RGB", "RGN", "NGB", "NIR", "OCN"])
            self.CalibrationFilter_6.setEnabled(True)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.addItems([" 3.37mm (Survey3W)", "8.25mm (Survey3N)"])
            self.CalibrationLens_6.setEnabled(True)
        elif self.CalibrationCameraModel_6.currentIndex() == 4:
            self.CalibrationFilter_6.clear()
            self.CalibrationFilter_6.addItems(["Red + NIR (NDVI)", "NIR", "Red", "Green", "Blue", "RGB"])
            self.CalibrationFilter_6.setEnabled(True)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.addItems(["3.97mm"])
            self.CalibrationLens_6.setEnabled(False)
        elif self.CalibrationCameraModel_6.currentIndex() == 5:
            self.CalibrationFilter_6.clear()
            self.CalibrationFilter_6.addItems(["Blue + NIR (NDVI)"])
            self.CalibrationFilter_6.setEnabled(False)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.addItems(["3.97mm"])
            self.CalibrationLens_6.setEnabled(False)
        elif self.CalibrationCameraModel_6.currentIndex() == 5:
            self.CalibrationFilter_6.clear()
            self.CalibrationFilter_6.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_6.setEnabled(False)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.addItems(["3.97mm"])
            self.CalibrationLens_6.setEnabled(False)

        elif self.CalibrationCameraModel_6.currentIndex() == 6:
            self.CalibrationFilter_6.clear()
            self.CalibrationFilter_6.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_6.setEnabled(False)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.addItems(["3.97mm"])
            self.CalibrationLens_6.setEnabled(False)

        elif self.CalibrationCameraModel_6.currentIndex() == 7:
            self.CalibrationFilter_6.clear()
            self.CalibrationFilter_6.addItems(["RGN"])
            self.CalibrationFilter_6.setEnabled(False)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.addItems(["3.97mm"])
            self.CalibrationLens_6.setEnabled(False)
        elif self.CalibrationCameraModel_6.currentIndex() > 7:
            self.CalibrationFilter_6.clear()
            self.CalibrationFilter_6.addItems(["Red + NIR (NDVI)"])
            self.CalibrationFilter_6.setEnabled(False)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.addItems(["3.97mm"])
            self.CalibrationLens_6.setEnabled(False)


        else:
            self.CalibrationLens_6.clear()
            self.CalibrationFilter_6.setEnabled(False)
            self.CalibrationLens_6.clear()
            self.CalibrationLens_6.setEnabled(False)



    def on_PreProcessInButton_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            folder = QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read())
            self.PreProcessInFolder.setText(folder)
            self.PreProcessOutFolder.setText(folder)
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.PreProcessInFolder.text())

    def on_PreProcessOutButton_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.PreProcessOutFolder.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.PreProcessOutFolder.text())

    def on_VignetteFileSelectButton_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.VignetteFileSelect.setText(QtWidgets.QFileDialog.getOpenFileName(directory=instring.read())[0])
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.VignetteFileSelect.text())

    def on_PreProcessButton_released(self):
        #calls preprocesshelper
        if self.PreProcessCameraModel.currentIndex() == -1:
            self.PreProcessLog.append("Attention! Please select a camera model.\n")
        else:
            # self.PreProcessLog.append(r'Extracting vignette corection data')


            infolder = self.PreProcessInFolder.text()
            if len(infolder) == 0:
                self.PreProcessLog.append("Attention! Please select an input folder.\n")
                return 0
            outdir = self.PreProcessOutFolder.text()
            if len(outdir) == 0:
                self.PreProcessLog.append("Attention! No Output folder selected, creating output under input folder.\n")
                outdir = infolder
            foldercount = 1
            endloop = False
            while endloop is False:
                outfolder = outdir + os.sep + "Processed_" + str(foldercount)
                if os.path.exists(outfolder):
                    foldercount += 1
                else:
                    os.mkdir(outfolder)
                    endloop = True

            # self.PreProcessLog.append("Input folder: " + infolder)
            # self.PreProcessLog.append("Output folder: " + outfolder)
            try:
                self.preProcessHelper(infolder, outfolder)
            except Exception as e:
                exc_type, exc_obj,exc_tb = sys.exc_info()
                self.PreProcessLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
            self.PreProcessLog.append("Finished Processing Images.")
            # if os.path.exists(modpath + os.sep + 'Vig'):
            #     shutil.rmtree(modpath + os.sep + 'Vig')

                # Pre-Process Steps: End

                # Calibration Steps: Start

    #these calibrate buttons are used to display the pathname when the browse button is clicked
    def on_CalibrationInButton_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationInFolder.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            #clears the instring file, moves the cursor to the beginning, and then writes the line that was just found
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationInFolder.text())
    def on_CalibrationInButton_2_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationInFolder_2.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationInFolder_2.text())
    def on_CalibrationInButton_3_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationInFolder_3.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationInFolder_3.text())
    def on_CalibrationInButton_4_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationInFolder_4.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationInFolder_4.text())
    def on_CalibrationInButton_5_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationInFolder_5.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationInFolder_5.text())
    def on_CalibrationInButton_6_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationInFolder_6.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationInFolder_6.text())


    def on_CalibrationQRButton_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationQRFile.setText(QtWidgets.QFileDialog.getOpenFileName(directory=instring.read())[0])
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationQRFile.text())
    def on_CalibrationQRButton_2_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationQRFile_2.setText(QtWidgets.QFileDialog.getOpenFileName(directory=instring.read())[0])
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationQRFile_2.text())
    def on_CalibrationQRButton_3_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationQRFile_3.setText(QtWidgets.QFileDialog.getOpenFileName(directory=instring.read())[0])
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationQRFile_3.text())
    def on_CalibrationQRButton_4_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationQRFile_4.setText(QtWidgets.QFileDialog.getOpenFileName(directory=instring.read())[0])
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationQRFile_4.text())
    def on_CalibrationQRButton_5_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationQRFile_5.setText(QtWidgets.QFileDialog.getOpenFileName(directory=instring.read())[0])
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationQRFile_5.text())
    def on_CalibrationQRButton_6_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.CalibrationQRFile_6.setText(QtWidgets.QFileDialog.getOpenFileName(directory=instring.read())[0])
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.CalibrationQRFile_6.text())

    def on_CalibrationGenButton_released(self):
        #Throws error at user if they do not select a camera
        try:
            if self.CalibrationCameraModel.currentIndex() == -1:
                self.CalibrationLog.append("Attention! Please select a camera model.\n")
            elif len(self.CalibrationQRFile.text()) > 0:
                self.findQR(self.CalibrationQRFile.text(), [self.CalibrationCameraModel.currentIndex(), self.CalibrationFilter.currentIndex(), self.CalibrationLens.currentIndex()])
                self.qrcoeffs = copy.deepcopy(self.multiplication_values["Mono"])
                self.useqr = True
            else:
                self.CalibrationLog.append("Attention! Please select a target image.\n")
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.CalibrationLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
    def on_CalibrationGenButton_2_released(self):
        #Throws error at user if they do not select a camera
        try:
            if self.CalibrationCameraModel_2.currentIndex() == -1:
                self.CalibrationLog.append("Attention! Please select a camera model.\n")
            elif len(self.CalibrationQRFile_2.text()) > 0:

                self.findQR(self.CalibrationQRFile_2.text(), [self.CalibrationCameraModel_2.currentIndex(), self.CalibrationFilter_2.currentIndex(), self.CalibrationLens_2.currentIndex()])
                self.qrcoeffs2 = copy.deepcopy(self.multiplication_values["Mono"])
                self.useqr = True
            else:
                self.CalibrationLog.append("Attention! Please select a target image.\n")
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.CalibrationLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))

    def on_CalibrationGenButton_3_released(self):
        #Throws error at user if they do not select a camera

        try:
            if self.CalibrationCameraModel_3.currentIndex() == -1:
                self.CalibrationLog.append("Attention! Please select a camera model.\n")
            elif len(self.CalibrationQRFile_3.text()) > 0:
                self.findQR(self.CalibrationQRFile_3.text(), [self.CalibrationCameraModel_3.currentIndex(), self.CalibrationFilter_3.currentIndex(), self.CalibrationLens_3.currentIndex()])
                self.qrcoeffs3 = copy.deepcopy(self.multiplication_values["Mono"])
                self.useqr = True
            else:
                self.CalibrationLog.append("Attention! Please select a target image.\n")
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.CalibrationLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))

    def on_CalibrationGenButton_4_released(self):
        #Throws error at user if they do not select a camera

        try:
            if self.CalibrationCameraModel_4.currentIndex() == -1:
                self.CalibrationLog.append("Attention! Please select a camera model.\n")
            elif len(self.CalibrationQRFile_4.text()) > 0:
                self.qrcoeffs4 = self.findQR(self.CalibrationQRFile_4.text(), [self.CalibrationCameraModel_4.currentIndex(), self.CalibrationFilter_4.currentIndex(), self.CalibrationLens_4.currentIndex()])
                self.qrcoeffs4 = copy.deepcopy(self.multiplication_values["Mono"])
                self.useqr = True
            else:
                self.CalibrationLog.append("Attention! Please select a target image.\n")
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.CalibrationLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
    def on_CalibrationGenButton_5_released(self):
        #Throws error at user if they do not select a camera

        try:
            if self.CalibrationCameraModel_5.currentIndex() == -1:
                self.CalibrationLog.append("Attention! Please select a camera model.\n")
            elif len(self.CalibrationQRFile_5.text()) > 0:
                self.qrcoeffs5 = self.findQR(self.CalibrationQRFile_5.text(), [self.CalibrationCameraModel_5.currentIndex(), self.CalibrationFilter_5.currentIndex(), self.CalibrationLens_5.currentIndex()])
                self.qrcoeffs5 = copy.deepcopy(self.multiplication_values["Mono"])
                self.useqr = True
            else:
                self.CalibrationLog.append("Attention! Please select a target image.\n")
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.CalibrationLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
    def on_CalibrationGenButton_6_released(self):
        #Throws error at user if they do not select a camera 

        try:
            if self.CalibrationCameraModel_6.currentIndex() == -1:
                self.CalibrationLog.append("Attention! Please select a camera model.\n")
            elif len(self.CalibrationQRFile_6.text()) > 0:
                self.qrcoeffs6 = self.findQR(self.CalibrationQRFile_6.text(), [self.CalibrationCameraModel_6.currentIndex(), self.CalibrationFilter_6.currentIndex(), self.CalibrationLens_6.currentIndex()])
                self.qrcoeffs6 = copy.deepcopy(self.multiplication_values["Mono"])
                self.useqr = True
            else:
                self.CalibrationLog.append("Attention! Please select a target image.\n")
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.CalibrationLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))

    def on_CalibrateButton_released(self):

        #Throws errors if a camera model is not selected

        try:
            self.CalibrateButton.setEnabled(False) #button can not be pressed while calibrating
            if self.CalibrationCameraModel.currentIndex() == -1\
                    and self.CalibrationCameraModel_2.currentIndex() == -1 \
                    and self.CalibrationCameraModel_3.currentIndex() == -1 \
                    and self.CalibrationCameraModel_4.currentIndex() == -1 \
                    and self.CalibrationCameraModel_5.currentIndex() == -1 \
                    and self.CalibrationCameraModel_6.currentIndex() == -1:
                self.CalibrationLog.append("Attention! Please select a camera model.\n") #warning
            elif len(self.CalibrationInFolder.text()) <= 0 \
                    and len(self.CalibrationInFolder_2.text()) <= 0 \
                    and len(self.CalibrationInFolder_3.text()) <= 0 \
                    and len(self.CalibrationInFolder_4.text()) <= 0 \
                    and len(self.CalibrationInFolder_5.text()) <= 0 \
                    and len(self.CalibrationInFolder_6.text()) <= 0:
                self.CalibrationLog.append("Attention! Please select a calibration folder.\n") #warning
            else:
                self.firstpass = True
                # self.CalibrationLog.append("CSV Input: \n" + str(self.refvalues))
                # self.CalibrationLog.append("Calibration button pressed.\n")
                calfolder = self.CalibrationInFolder.text()
                calfolder2 = self.CalibrationInFolder_2.text()
                calfolder3 = self.CalibrationInFolder_3.text()
                calfolder4 = self.CalibrationInFolder_4.text()
                calfolder5 = self.CalibrationInFolder_5.text()
                calfolder6 = self.CalibrationInFolder_6.text()
                self.pixel_min_max = {"redmax": 0.0, "redmin": MAPIR_Defaults.UINT16MAX_FLOAT,
                                 "greenmax": 0.0, "greenmin": MAPIR_Defaults.UINT16MAX_FLOAT,
                                 "bluemax": 0.0, "bluemin": MAPIR_Defaults.UINT16MAX_FLOAT}
                # self.CalibrationLog.append("Calibration target folder is: " + calfolder + "\n")
                files_to_calibrate = []
                files_to_calibrate2 = []
                files_to_calibrate3 = []
                files_to_calibrate4 = []
                files_to_calibrate5 = []
                files_to_calibrate6 = []

                # self.CalibrationLog.append("Files to calibrate[0]: " + files_to_calibrate[0])


                #consume the indexes that the calibrate buttons are set to
                indexes = [[self.CalibrationCameraModel.currentIndex(), self.CalibrationFilter.currentIndex(), self.CalibrationLens.currentIndex()],
                           [self.CalibrationCameraModel_2.currentIndex(), self.CalibrationFilter_2.currentIndex(),
                            self.CalibrationLens_2.currentIndex()],
                           [self.CalibrationCameraModel_3.currentIndex(), self.CalibrationFilter_3.currentIndex(),
                            self.CalibrationLens_3.currentIndex()],
                           [self.CalibrationCameraModel_4.currentIndex(), self.CalibrationFilter_4.currentIndex(),
                            self.CalibrationLens_4.currentIndex()],
                           [self.CalibrationCameraModel_5.currentIndex(), self.CalibrationFilter_5.currentIndex(),
                            self.CalibrationLens_5.currentIndex()],
                           [self.CalibrationCameraModel_6.currentIndex(), self.CalibrationFilter_6.currentIndex(),
                            self.CalibrationLens_6.currentIndex()],
                           ]
                #folder index, listing all the folders consumed from UI
                folderind = [calfolder,
                             calfolder2,
                             calfolder3,
                             calfolder4,
                             calfolder5,
                             calfolder6]

                for j, ind in enumerate(indexes):
                    # self.CalibrationLog.append("Checking folder " + str(j + 1))
                    DID_NOT_SELECT_A_CAMERA_MODEL = -1

                    if ind[0] == -DID_NOT_SELECT_A_CAMERA_MODEL: #if they didn't select a camera model during the dropdown skip to next index
                        pass
                    elif ((ind[0] > 2) and not(ind[0] == 3 and ind[1] == 3)):#if this is not a survey3 NIR

                        if os.path.exists(folderind[j]): #if the files to calibrate has images within it
                            # print("Cal1")
                            files_to_calibrate = []
                            """ parsing through the folder, looking for files"""
                            os.chdir(folderind[j])
                            files_to_calibrate.extend(glob.glob("." + os.sep + "*.[tT][iI][fF]"))
                            files_to_calibrate.extend(glob.glob("." + os.sep + "*.[tT][iI][fF][fF]"))
                            files_to_calibrate.extend(glob.glob("." + os.sep + "*.[jJ][pP][gG]"))
                            files_to_calibrate.extend(glob.glob("." + os.sep + "*.[jJ][pP][eE][gG]"))
                            print(str(files_to_calibrate))
                            if "tif" or "TIF" or "jpg" or "JPG" in files_to_calibrate[0]:
                                # self.CalibrationLog.append("Found files to Calibrate.\n")
                                foldercount = 1
                                endloop = False
                                while endloop is False:
                                    outdir = folderind[j] + os.sep + "Calibrated_" + str(foldercount)
                                    if os.path.exists(outdir):
                                        foldercount += 1
                                    else:
                                        os.mkdir(outdir)
                                        endloop = True




                        for calpixel in files_to_calibrate: #for every file in files to calibrate

                            img = cv2.imread(calpixel, -1) #read in the iamge
                            #split the channels
                            blue = img[:, :, 0]
                            green = img[:, :, 1]
                            red = img[:, :, 2]



                            # these are a little confusing, but the check to find the highest and lowest pixel value
                            # in each channel in each image and keep the highest/lowest value found.

                            ''' this giant section of the code equalizes the histogram '''
                            if self.seed_pass == False:


                                self.pixel_min_max["redmax"] = int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(red))], red)[0])


                                self.pixel_min_max["redmin"] = red.min()


                                self.pixel_min_max["greenmax"] = \
                                int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(green))], green)[0])
                                self.pixel_min_max["greenmin"] = green.min()


                                self.pixel_min_max["bluemax"] = \
                                    int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(blue))], blue)[0])
                                self.pixel_min_max["bluemin"] = blue.min()

                                self.seed_pass = True
                            else:

                                self.pixel_min_max["redmax"] = max(int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(red))], red)[0]), self.pixel_min_max["redmax"])
                                self.pixel_min_max["redmin"] = min(red.min(), self.pixel_min_max["redmin"])

                                self.pixel_min_max["greenmax"] = max(
                                    int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(green))], green)[0]), self.pixel_min_max["greenmax"])
                                self.pixel_min_max["greenmin"] = min(green.min(), self.pixel_min_max["greenmin"])

                                self.pixel_min_max["bluemax"] = max(
                                    int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(blue))], blue)[0]), self.pixel_min_max["bluemax"])
                                self.pixel_min_max["bluemin"] = min(blue.min(), self.pixel_min_max["bluemin"])


                            if ind[0] == 5:  # Survey1_NDVI
                                    self.pixel_min_max["redmax"] = (self.pixel_min_max["redmax"] * MAPIR_Defaults.BASE_COEFF_SURVEY1_NDVI_JPG[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_SURVEY1_NDVI_JPG[0]
                                    self.pixel_min_max["redmin"] = (self.pixel_min_max["redmin"] * MAPIR_Defaults.BASE_COEFF_SURVEY1_NDVI_JPG[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_SURVEY1_NDVI_JPG[0]
                                    self.pixel_min_max["bluemin"] = (self.pixel_min_max["bluemin"] * MAPIR_Defaults.BASE_COEFF_SURVEY1_NDVI_JPG[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_SURVEY1_NDVI_JPG[2]
                                    self.pixel_min_max["bluemax"] = (self.pixel_min_max["bluemax"] * MAPIR_Defaults.BASE_COEFF_SURVEY1_NDVI_JPG[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_SURVEY1_NDVI_JPG[2]
                            elif (ind[0] == 4) and ind[1] == 0:
                                if "tif" or "TIF" in calpixel:
                                    self.pixel_min_max["redmax"] = (self.pixel_min_max["redmax"] * MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_TIF[0]
                                    self.pixel_min_max["redmin"] = (self.pixel_min_max["redmin"] * MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_TIF[0]
                                    self.pixel_min_max["bluemin"] = (self.pixel_min_max["bluemin"] * MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_TIF[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_TIF[2]
                                    self.pixel_min_max["bluemax"] = (self.pixel_min_max["bluemax"] * MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_TIF[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_TIF[2]
                                elif "jpg" or "JPG" in calpixel:
                                    self.pixel_min_max["redmax"] = (self.pixel_min_max["redmax"] * MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_JPG[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_JPG[0]
                                    self.pixel_min_max["redmin"] = (self.pixel_min_max["redmin"] * MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_JPG[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_JPG[0]
                                    self.pixel_min_max["bluemin"] = (self.pixel_min_max["bluemin"] * MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_JPG[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_JPG[2]
                                    self.pixel_min_max["bluemax"] = (self.pixel_min_max["bluemax"] * MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_JPG[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_JPG[2]
                            elif ind[0] == 8:
                                if "tif" or "TIF" in calpixel:
                                    self.pixel_min_max["redmax"] = (self.pixel_min_max["redmax"] * MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_TIF[0]
                                    self.pixel_min_max["redmin"] = (self.pixel_min_max["redmin"] * MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_TIF[0]
                                    self.pixel_min_max["bluemin"] = (self.pixel_min_max["bluemin"] * MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_TIF[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_TIF[2]
                                    self.pixel_min_max["bluemax"] = (self.pixel_min_max["bluemax"] * MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_TIF[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_TIF[2]
                                elif "jpg" or "JPG" in calpixel:
                                    self.pixel_min_max["redmax"] = (self.pixel_min_max["redmax"] * MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_JPG[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_JPG[0]
                                    self.pixel_min_max["redmin"] = (self.pixel_min_max["redmin"] * MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_JPG[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_JPG[0]
                                    self.pixel_min_max["bluemin"] = (self.pixel_min_max["bluemin"] * MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_JPG[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_JPG[2]
                                    self.pixel_min_max["bluemax"] = (self.pixel_min_max["bluemax"] * MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_JPG[3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_JPG[2]
                            elif ind[0] == 5:
                                if "tif" or "TIF" in calpixel:
                                    self.pixel_min_max["redmax"] = (
                                                              self.pixel_min_max["redmax"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_TIF[0]
                                    self.pixel_min_max["redmin"] = (
                                                              self.pixel_min_max["redmin"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_TIF[0]
                                    self.pixel_min_max["bluemin"] = (self.pixel_min_max["bluemin"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_TIF[
                                        3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_TIF[2]
                                    self.pixel_min_max["bluemax"] = (self.pixel_min_max["bluemax"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_TIF[
                                        3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_TIF[2]
                                elif "jpg" or "JPG" in calpixel:
                                    self.pixel_min_max["redmax"] = (
                                                              self.pixel_min_max["redmax"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_JPG[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_JPG[0]
                                    self.pixel_min_max["redmin"] = (
                                                              self.pixel_min_max["redmin"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_JPG[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_JPG[0]
                                    self.pixel_min_max["bluemin"] = (self.pixel_min_max["bluemin"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_JPG[
                                        3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_JPG[2]
                                    self.pixel_min_max["bluemax"] = (self.pixel_min_max["bluemax"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_JPG[
                                        3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_JPG[2]
                            elif ind[0] == 6 or ind[0] > 7:
                                if "tif" or "TIF" in calpixel:
                                    self.pixel_min_max["redmax"] = (
                                                              self.pixel_min_max["redmax"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[0]
                                    self.pixel_min_max["redmin"] = (
                                                              self.pixel_min_max["redmin"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[0]
                                    self.pixel_min_max["bluemin"] = (self.pixel_min_max["bluemin"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[
                                        3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[2]
                                    self.pixel_min_max["bluemax"] = (self.pixel_min_max["bluemax"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[
                                        3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[2]
                                elif "jpg" or "JPG" in calpixel:
                                    self.pixel_min_max["redmax"] = (
                                                              self.pixel_min_max["redmax"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[0]
                                    self.pixel_min_max["redmin"] = (
                                                              self.pixel_min_max["redmin"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[1]) \
                                                              + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[0]
                                    self.pixel_min_max["bluemin"] = (self.pixel_min_max["bluemin"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[
                                        3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[2]
                                    self.pixel_min_max["bluemax"] = (self.pixel_min_max["bluemax"] * MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[
                                        3]) \
                                                               + MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF[2]
                        self.seed_pass = False
                        if self.useqr == True:
                            self.pixel_min_max["redmax"] = int(
                                self.multiplication_values["Red"] * self.pixel_min_max["redmax"])
                            self.pixel_min_max["greenmax"] = int(
                                self.multiplication_values["Green"] * self.pixel_min_max["greenmax"])
                            self.pixel_min_max["bluemax"] = int(
                                self.multiplication_values["Blue"] * self.pixel_min_max["bluemax"])
                            self.pixel_min_max["redmin"] = int(
                                self.multiplication_values["Red"] * self.pixel_min_max["redmin"])
                            self.pixel_min_max["greenmin"] = int(
                                self.multiplication_values["Green"] * self.pixel_min_max["greenmin"])
                            self.pixel_min_max["bluemin"] = int(
                                self.multiplication_values["Blue"] * self.pixel_min_max["bluemin"])
                        for i, calfile in enumerate(files_to_calibrate):

                            cameramodel = ind
                            if self.useqr == True:
                                # self.CalibrationLog.append("Using QR")
                                try:
                                    self.CalibrationLog.append("Calibrating image " + str(i + 1) + " of " + str(len(files_to_calibrate)))
                                    QtWidgets.QApplication.processEvents()


                                    self.CalibratePhotos(calfile, self.multiplication_values, self.pixel_min_max, outdir, ind)
                                except Exception as e:
                                    exc_type, exc_obj,exc_tb = sys.exc_info()
                                    self.CalibrationLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
                            else:
                                # calibrating the cameras with corresponding constants
                                if (cameramodel[0] == 4) and (self.CalibrationFilter.currentIndex() == 0):  # Survey2 NDVI
                                    if "TIF" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_TIF, self.pixel_min_max, outdir, ind)
                                    elif "JPG" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_NDVI_JPG, self.pixel_min_max, outdir, ind)
                                elif cameramodel[0] == 4 and self.CalibrationFilter.currentIndex() == 1:  # Survey2 NIR
                                    if "TIF" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_NIR_TIF, self.pixel_min_max, outdir, ind)
                                    elif "JPG" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_NIR_JPG, self.pixel_min_max, outdir, ind)
                                elif cameramodel[0] == 4 and self.CalibrationFilter.currentIndex() == 2:  # Survey2 RED
                                    if "TIF" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_RED_TIF, self.pixel_min_max, outdir, ind)
                                    elif "JPG" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_RED_JPG, self.pixel_min_max, outdir, ind)
                                elif cameramodel[0] == 4 and self.CalibrationFilter.currentIndex() == 3:  # Survey2 GREEN
                                    if "TIF" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_GREEN_TIF, self.pixel_min_max, outdir, ind)
                                    elif "JPG" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_GREEN_JPG, self.pixel_min_max, outdir, ind)
                                elif cameramodel[0] == 4 and self.CalibrationFilter.currentIndex() == 4:  # Survey2 BLUE
                                    if "TIF" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_BLUE_TIF, self.pixel_min_max, outdir, ind)
                                    elif "JPG" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY2_BLUE_JPG, self.pixel_min_max, outdir, ind)
                                elif cameramodel[0] == 5:  # Survey1 NDVI
                                    if "JPG" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY1_NDVI_JPG, self.pixel_min_max, outdir, ind)
                                elif cameramodel[0] == 9:  # DJI X3 NDVI
                                    if "TIF" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_TIF, self.pixel_min_max, outdir, ind)
                                    elif "JPG" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_DJIX3_NDVI_JPG, self.pixel_min_max, outdir, ind)
                                elif cameramodel[0] == 6:  # DJI Phantom4 NDVI
                                    if "TIF" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_TIF, self.pixel_min_max,
                                                             outdir, ind)
                                    elif "JPG" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_DJIPHANTOM4_NDVI_JPG, self.pixel_min_max,
                                                             outdir, ind)
                                elif cameramodel[0] == 7 or cameramodel[0] == 8:  # DJI PHANTOM3 NDVI
                                    if "TIF" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_TIF, self.pixel_min_max,
                                                             outdir, ind)
                                    elif "JPG" in calfile.split('.')[2].upper():
                                        self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_DJIPHANTOM3_NDVI_JPG, self.pixel_min_max,
                                                             outdir, ind)
                                elif self.CalibrationCameraModel.currentIndex() == 3 and self.CalibrationFilter.currentIndex() == 1:  # Survey2 NIR

                                    self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY3_W_RGN_TIF, self.pixel_min_max, outdir, ind)
                                elif self.CalibrationCameraModel.currentIndex() == 3 and self.CalibrationFilter.currentIndex() == 2:  # Survey2 NIR

                                    self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY3_W_NGB_TIF, self.pixel_min_max,
                                                         outdir, ind)
                                elif self.CalibrationCameraModel.currentIndex() == 3 and self.CalibrationFilter.currentIndex() == 3:  # Survey2 NIR

                                    self.CalibratePhotos(calfile, MAPIR_Defaults.BASE_COEFF_SURVEY3_W_NGB_TIF, self.pixel_min_max,
                                                         outdir, ind)
                                else:
                                    self.CalibrationLog.append(
                                        "No default calibration data for selected camera model. Please please supply a MAPIR Reflectance Target to proceed.\n")
                                    break
                    else:
                        files_to_calibrate = []
                        files_to_calibrate2 = []
                        files_to_calibrate3 = []
                        files_to_calibrate4 = []
                        files_to_calibrate5 = []
                        files_to_calibrate6 = []

                        os.chdir(calfolder)
                        files_to_calibrate.extend(glob.glob("." + os.sep + "*.[tT][iI][fF]"))
                        files_to_calibrate.extend(glob.glob("." + os.sep + "*.[tT][iI][fF][fF]"))
                        files_to_calibrate.extend(glob.glob("." + os.sep + "*.[jJ][pP][gG]"))
                        files_to_calibrate.extend(glob.glob("." + os.sep + "*.[jJ][pP][eE][gG]"))
                        print(str(files_to_calibrate))

                        if os.path.exists(calfolder2):

                            os.chdir(calfolder2)
                            files_to_calibrate2.extend(glob.glob("." + os.sep + "*.[tT][iI][fF]"))
                            files_to_calibrate2.extend(glob.glob("." + os.sep + "*.[tT][iI][fF][fF]"))
                            files_to_calibrate2.extend(glob.glob("." + os.sep + "*.[jJ][pP][gG]"))
                            files_to_calibrate2.extend(glob.glob("." + os.sep + "*.[jJ][pP][eE][gG]"))
                            print(str(files_to_calibrate2))
                        if os.path.exists(calfolder3):

                            os.chdir(calfolder3)
                            files_to_calibrate3.extend(glob.glob("." + os.sep + "*.[tT][iI][fF]"))
                            files_to_calibrate3.extend(glob.glob("." + os.sep + "*.[tT][iI][fF][fF]"))
                            files_to_calibrate3.extend(glob.glob("." + os.sep + "*.[jJ][pP][gG]"))
                            files_to_calibrate3.extend(glob.glob("." + os.sep + "*.[jJ][pP][eE][gG]"))
                            print(str(files_to_calibrate3))
                        if os.path.exists(calfolder4):

                            os.chdir(calfolder4)
                            files_to_calibrate4.extend(glob.glob("." + os.sep + "*.[tT][iI][fF]"))
                            files_to_calibrate4.extend(glob.glob("." + os.sep + "*.[tT][iI][fF][fF]"))
                            files_to_calibrate4.extend(glob.glob("." + os.sep + "*.[jJ][pP][gG]"))
                            files_to_calibrate4.extend(glob.glob("." + os.sep + "*.[jJ][pP][eE][gG]"))
                            print(str(files_to_calibrate4))
                        if os.path.exists(calfolder5):

                            os.chdir(calfolder5)
                            files_to_calibrate5.extend(glob.glob("." + os.sep + "*.[tT][iI][fF]"))
                            files_to_calibrate5.extend(glob.glob("." + os.sep + "*.[tT][iI][fF][fF]"))
                            files_to_calibrate5.extend(glob.glob("." + os.sep + "*.[jJ][pP][gG]"))
                            files_to_calibrate5.extend(glob.glob("." + os.sep + "*.[jJ][pP][eE][gG]"))
                            print(str(files_to_calibrate5))

                        if os.path.exists(calfolder6):

                            os.chdir(calfolder6)
                            files_to_calibrate6.extend(glob.glob("." + os.sep + "*.[tT][iI][fF]"))
                            files_to_calibrate6.extend(glob.glob("." + os.sep + "*.[tT][iI][fF][fF]"))
                            files_to_calibrate6.extend(glob.glob("." + os.sep + "*.[jJ][pP][gG]"))
                            files_to_calibrate6.extend(glob.glob("." + os.sep + "*.[jJ][pP][eE][gG]"))
                            print(str(files_to_calibrate6))

                        #calpixel finds the min and max pixel of the data range within a data set
                        for calpixel in files_to_calibrate:
                            # print("MM1")
                            os.chdir(calfolder)
                            temp1 = cv2.imread(calpixel, -1)
                            if len(temp1.shape) > 2:
                                temp1 = temp1[:,:,0]
                            # imgcount = dict((i, list(temp1.flatten()).count(i)) for i in range(0, 65536))
                            # self.imkeys = np.array(list(imgcount.keys()))
                            # imvals = np.array(list(imgcount.values()))
                            self.monominmax["min"] = min(temp1.min(), self.monominmax["min"])
                            self.monominmax["max"] = max(
                                int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(temp1))], temp1)[0]),
                                self.monominmax["max"])
                        #calpixel finds the min and max pixel of the data range within a data set
                        for calpixel2 in files_to_calibrate2:
                            # print("MM2")
                            os.chdir(calfolder2)
                            temp2 = cv2.imread(calpixel2, -1)
                            if len(temp2.shape) > 2:
                                temp2 = temp2[:,:,0]
                            # imgcount = dict((i, list(temp2.flatten()).count(i)) for i in range(0, 65536))
                            # self.imkeys = np.array(list(imgcount.keys()))
                            # imvals = np.array(list(imgcount.values()))
                            self.monominmax["min"] = min(temp2.min(), self.monominmax["min"])
                            self.monominmax["max"] = max(
                                int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(temp2))], temp2)[0]),
                                self.monominmax["max"])
                        #calpixel finds the min and max pixel of the data range within a data set
                        for calpixel3 in files_to_calibrate3:
                            # print("MM3")
                            os.chdir(calfolder3)
                            temp3 = cv2.imread(calpixel3, -1)
                            if len(temp3.shape) > 2:
                                temp3 = temp3[:,:,0]

                            # imgcount = dict((i, list(temp3.flatten()).count(i)) for i in range(0, 65536))
                            # self.imkeys = np.array(list(imgcount.keys()))
                            # imvals = np.array(list(imgcount.values()))
                            self.monominmax["min"] = min(temp3.min(), self.monominmax["min"])
                            self.monominmax["max"] = max(
                                int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(temp3))], temp3)[0]),
                                self.monominmax["max"])
                        #calpixel finds the min and max pixel of the data range within a data set
                        for calpixel4 in files_to_calibrate4:
                            # print("MM4")
                            os.chdir(calfolder4)
                            temp4 = cv2.imread(calpixel4, -1)
                            if len(temp4.shape) > 2:
                                temp4 = temp4[:,:,0]
                            # imgcount = dict((i, list(temp4.flatten()).count(i)) for i in range(0, 65536))
                            # self.imkeys = np.array(list(imgcount.keys()))
                            # imvals = np.array(list(imgcount.values()))
                            self.monominmax["min"] = min(temp4.min(), self.monominmax["min"])
                            self.monominmax["max"] = max(
                                int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(temp4))], temp4)[0]),
                                self.monominmax["max"])
                        #calpixel finds the min and max pixel of the data range within a data set
                        for calpixel5 in files_to_calibrate5:
                            # print("MM5")
                            os.chdir(calfolder5)
                            temp5 = cv2.imread(calpixel5, -1)
                            if len(temp5.shape) > 2:
                                temp5 = temp5[:,:,0]
                            # imgcount = dict((i, list(temp5.flatten()).count(i)) for i in range(0, 65536))
                            # self.imkeys = np.array(list(imgcount.keys()))
                            # imvals = np.array(list(imgcount.values()))
                            self.monominmax["min"] = min(temp5.min(), self.monominmax["min"])
                            self.monominmax["max"] = max(
                                int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(temp5))], temp5)[0]),
                                self.monominmax["max"])
                        #calpixel finds the min and max pixel of the data range within a data set
                        for calpixel6 in files_to_calibrate6:
                            # print("MM6")
                            os.chdir(calfolder6)
                            temp6 = cv2.imread(calpixel6, -1)
                            if len(temp6.shape) > 2:
                                temp6 = temp6[:,:,0]
                            # imgcount = dict((i, list(temp6.flatten()).count(i)) for i in range(0, 65536))
                            # self.imkeys = np.array(list(imgcount.keys()))
                            # imvals = np.array(list(imgcount.values()))
                            self.monominmax["min"] = min(temp6.min(), self.monominmax["min"])
                            self.monominmax["max"] = max(
                                int(np.setdiff1d(self.imkeys[self.imkeys > int(np.median(temp6))], temp6)[0]),
                                self.monominmax["max"])

                        if os.path.exists(calfolder):

                            if "tif" or "TIF" or "jpg" or "JPG" in files_to_calibrate[0]:
                                foldercount = 1
                                endloop = False
                                while endloop is False:
                                    outdir = calfolder + os.sep + "Calibrated_" + str(foldercount)
                                    if os.path.exists(outdir):
                                        foldercount += 1
                                    else:
                                        os.mkdir(outdir)
                                        endloop = True

                                for i, calfile in enumerate(files_to_calibrate):
                                    # print("cb1")
                                    self.CalibrationLog.append("Calibrating image " + str(i + 1) + " of " + str(len(files_to_calibrate)) + " from folder 1")
                                    QtWidgets.QApplication.processEvents()
                                    os.chdir(calfolder)
                                    if self.useqr == True:
                                        # self.CalibrationLog.append("Using QR")
                                        self.CalibrateMono(calfile, self.qrcoeffs, outdir, ind)
                                    else:
                                        if self.CalibrationFilter.currentIndex() == 0:
                                            self.CalibrateMono(calfile, MAPIR_Defaults.BASE_COEFF_KERNEL_F590, outdir, ind)
                                        elif self.CalibrationFilter.currentIndex() == 1:
                                            self.CalibrateMono(calfile, MAPIR_Defaults.BASE_COEFF_KERNEL_F650, outdir, ind)
                                        elif self.CalibrationFilter.currentIndex() == 2:
                                            self.CalibrateMono(calfile, MAPIR_Defaults.BASE_COEFF_KERNEL_F850, outdir, ind)
                        if os.path.exists(calfolder2):

                            if "tif" or "TIF" or "jpg" or "JPG" in files_to_calibrate2[0]:
                                foldercount = 1
                                endloop = False
                                while endloop is False:
                                    outdir2 = calfolder2 + os.sep + "Calibrated_" + str(foldercount)
                                    if os.path.exists(outdir2):
                                        foldercount += 1
                                    else:
                                        os.mkdir(outdir2)
                                        endloop = True

                                for i, calfile2 in enumerate(files_to_calibrate2):
                                    # print("cb2")
                                    self.CalibrationLog.append("Calibrating image " + str(i + 1) + " of " + str(len(files_to_calibrate2)) + " from folder 2")
                                    QtWidgets.QApplication.processEvents()
                                    os.chdir(calfolder2)
                                    if self.useqr == True:
                                        # self.CalibrationLog.append("Using QR")
                                        self.CalibrateMono(calfile2, self.qrcoeffs2, outdir2, ind)
                                    else:
                                        if self.CalibrationFilter.currentIndex() == 0:
                                            self.CalibrateMono(calfile2, MAPIR_Defaults.BASE_COEFF_KERNEL_F590, outdir2)
                                        elif self.CalibrationFilter.currentIndex() == 1:
                                            self.CalibrateMono(calfile2, MAPIR_Defaults.BASE_COEFF_KERNEL_F650, outdir2)
                                        elif self.CalibrationFilter.currentIndex() == 2:
                                            self.CalibrateMono(calfile2, MAPIR_Defaults.BASE_COEFF_KERNEL_F850, outdir2)
                        if os.path.exists(calfolder3):
                            if "tif" or "TIF" or "jpg" or "JPG" in files_to_calibrate3[0]:
                                foldercount = 1
                                endloop = False
                                while endloop is False:
                                    outdir3 = calfolder3 + os.sep + "Calibrated_" + str(foldercount)
                                    if os.path.exists(outdir3):
                                        foldercount += 1
                                    else:
                                        os.mkdir(outdir3)
                                        endloop = True

                                for i, calfile3 in enumerate(files_to_calibrate3):
                                    # print("cb3")
                                    self.CalibrationLog.append("Calibrating image " + str(i + 1) + " of " + str(len(files_to_calibrate3)) +  " from folder 3")
                                    QtWidgets.QApplication.processEvents()
                                    os.chdir(calfolder3)
                                    if self.useqr == True:
                                        # self.CalibrationLog.append("Using QR")
                                        self.CalibrateMono(calfile3, self.qrcoeffs3, outdir3, ind)
                                    else:
                                        if self.CalibrationFilter.currentIndex() == 0:
                                            self.CalibrateMono(calfile3, MAPIR_Defaults.BASE_COEFF_KERNEL_F590, outdir3)
                                        elif self.CalibrationFilter.currentIndex() == 1:
                                            self.CalibrateMono(calfile3, MAPIR_Defaults.BASE_COEFF_KERNEL_F650, outdir3)
                                        elif self.CalibrationFilter.currentIndex() == 2:
                                            self.CalibrateMono(calfile3, MAPIR_Defaults.BASE_COEFF_KERNEL_F850, outdir3)
                        if os.path.exists(calfolder4):
                            if "tif" or "TIF" or "jpg" or "JPG" in files_to_calibrate4[0]:
                                foldercount = 1
                                endloop = False
                                while endloop is False:
                                    outdir4 = calfolder4 + os.sep + "Calibrated_" + str(foldercount)
                                    if os.path.exists(outdir4):
                                        foldercount += 1
                                    else:
                                        os.mkdir(outdir4)
                                        endloop = True

                                for i, calfile4 in enumerate(files_to_calibrate4):
                                    # print("cb2")
                                    self.CalibrationLog.append("Calibrating image " + str(i + 1) + " of " + str(len(files_to_calibrate4)) +  " from folder 4")
                                    QtWidgets.QApplication.processEvents()
                                    os.chdir(calfolder4)
                                    if self.useqr == True:
                                        # self.CalibrationLog.append("Using QR")
                                        self.CalibrateMono(calfile4, self.qrcoeffs4, outdir4, ind)
                                    else:
                                        if self.CalibrationFilter.currentIndex() == 0:
                                            self.CalibrateMono(calfile4, MAPIR_Defaults.BASE_COEFF_KERNEL_F590, outdir4)
                                        elif self.CalibrationFilter.currentIndex() == 1:
                                            self.CalibrateMono(calfile4, MAPIR_Defaults.BASE_COEFF_KERNEL_F650, outdir4)
                                        elif self.CalibrationFilter.currentIndex() == 2:
                                            self.CalibrateMono(calfile4, MAPIR_Defaults.BASE_COEFF_KERNEL_F850, outdir4)
                        if os.path.exists(calfolder5):
                            if "tif" or "TIF" or "jpg" or "JPG" in files_to_calibrate5[0]:
                                foldercount = 1
                                endloop = False
                                while endloop is False:
                                    outdir5 = calfolder5 + os.sep + "Calibrated_" + str(foldercount)
                                    if os.path.exists(outdir5):
                                        foldercount += 1
                                    else:
                                        os.mkdir(outdir5)
                                        endloop = True

                                for i, calfile5 in enumerate(files_to_calibrate5):
                                    # print("cb5")
                                    self.CalibrationLog.append("Calibrating image " + str(i + 1) + " of " + str(len(files_to_calibrate5)) +  " from folder 5")
                                    QtWidgets.QApplication.processEvents()
                                    os.chdir(calfolder5)
                                    if self.useqr == True:
                                        # self.CalibrationLog.append("Using QR")
                                        self.CalibrateMono(calfile5, self.qrcoeffs5, outdir5, ind)
                                    else:
                                        if self.CalibrationFilter.currentIndex() == 0:
                                            self.CalibrateMono(calfile5, MAPIR_Defaults.BASE_COEFF_KERNEL_F590, outdir5)
                                        elif self.CalibrationFilter.currentIndex() == 1:
                                            self.CalibrateMono(calfile5, MAPIR_Defaults.BASE_COEFF_KERNEL_F650, outdir5)
                                        elif self.CalibrationFilter.currentIndex() == 2:
                                            self.CalibrateMono(calfile5, MAPIR_Defaults.BASE_COEFF_KERNEL_F850, outdir5)
                        if os.path.exists(calfolder6):
                            if "tif" or "TIF" or "jpg" or "JPG" in files_to_calibrate6[0]:
                                foldercount = 1
                                endloop = False
                                while endloop is False:
                                    outdir6 = calfolder6 + os.sep + "Calibrated_" + str(foldercount)
                                    if os.path.exists(outdir6):
                                        foldercount += 1
                                    else:
                                        os.mkdir(outdir6)
                                        endloop = True



                                for i, calfile6 in enumerate(files_to_calibrate6):
                                    # print("cb6")
                                    self.CalibrationLog.append("Calibrating image " + str(i + 1) + " of " + str(len(files_to_calibrate6)) +  " from folder 6")
                                    QtWidgets.QApplication.processEvents()
                                    os.chdir(calfolder6)
                                    if self.useqr == True:
                                        # self.CalibrationLog.append("Using QR")
                                        self.CalibrateMono(calfile6, self.qrcoeffs6, outdir6, ind)
                                    else:
                                        if self.CalibrationFilter.currentIndex() == 0:
                                            self.CalibrateMono(calfile6, MAPIR_Defaults.BASE_COEFF_KERNEL_F590, outdir6)
                                        elif self.CalibrationFilter.currentIndex() == 1:
                                            self.CalibrateMono(calfile6, MAPIR_Defaults.BASE_COEFF_KERNEL_F650, outdir6)
                                        elif self.CalibrationFilter.currentIndex() == 2:
                                            self.CalibrateMono(calfile6, MAPIR_Defaults.BASE_COEFF_KERNEL_F850, outdir6)


                self.CalibrationLog.append("Finished Calibrating " + str(len(files_to_calibrate) + len(files_to_calibrate2) + len(files_to_calibrate3) + len(files_to_calibrate4) + len(files_to_calibrate5) + len(files_to_calibrate6)) + " images\n")
                self.CalibrateButton.setEnabled(True)
                self.seed_pass = False
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(repr(e))
            print("Line: " + str(exc_tb.tb_lineno))
            self.CalibrationLog.append(str(repr(e)))

    def CalibrateMono(self, photo, coeffs, output_directory, ind):

        refimg = cv2.imread(photo, -1)
        print(str(refimg))
        if len(refimg.shape) > 2:
            refimg = refimg[:,:,0]
        refimg = refimg.astype("uint16")
        refimg[refimg > self.monominmax["max"]] = self.monominmax["max"]
        pixmin = coeffs * self.monominmax["min"]
        pixmax = coeffs * self.monominmax["max"]
        tempim = coeffs * refimg
        tempim -= pixmin
        tempim /= (pixmax - pixmin)
        if self.Tiff2JpgBox.checkState() > 0:
            tempim *= 255.0
            tempim = tempim.astype("uint8")
        else:
            if self.IndexBox.checkState() == 0:
                tempim *= MAPIR_Defaults.UINT16MAX_FLOAT

                tempim = tempim.astype("uint16")
            else:
                tempim = tempim.astype("float")


        refimg = tempim

        newimg = output_directory + photo.split('.')[1] + "_CALIBRATED." + photo.split('.')[2]
        if self.Tiff2JpgBox.checkState() > 0:
            self.CalibrationLog.append("Making JPG")
            QtWidgets.QApplication.processEvents()
            cv2.imencode(".jpg", refimg)
            cv2.imwrite(output_directory + photo.split('.')[1] + "_CALIBRATED.JPG", refimg,
                        [int(cv2.IMWRITE_JPEG_QUALITY), 100])

            self.copyExif(photo, output_directory + photo.split('.')[1] + "_CALIBRATED.JPG")
        else:
            cv2.imencode(".tif", refimg)
            cv2.imwrite(newimg, refimg)
            srin = gdal.Open(photo)
            inproj = srin.GetProjection()
            transform = srin.GetGeoTransform()
            gcpcount = srin.GetGCPs()
            srout = gdal.Open(newimg, gdal.GA_Update)
            srout.SetProjection(inproj)
            srout.SetGeoTransform(transform)
            srout.SetGCPs(gcpcount, srin.GetGCPProjection())
            self.copyExif(photo, newimg)

    def CalibratePhotos(self, photo, coeffs, minmaxes, output_directory, ind):
        """Calibrates the photos, finds the min and max settings then normalizes the images """
        refimg = cv2.imread(photo, -1)

        if True:
            ### split channels (using cv2.split caused too much overhead and made the host program crash)
            alpha = []
            blue = refimg[:, :, 0]
            green = refimg[:, :, 1]
            red = refimg[:, :, 2]
            if refimg.shape[2] > 3:
                alpha = refimg[:, :, 3]
                refimg = copy.deepcopy(refimg[:, :, :3])
            if self.useqr:
                red = (red * self.multiplication_values["Red"])
                green = (green * self.multiplication_values["Green"])
                blue = (blue * self.multiplication_values["Blue"])

                ### find the maximum and minimum pixel values over the entire directory.
                if ind[0] == 5:  ###Survey1 NDVI
                    maxpixel = minmaxes["redmax"] if minmaxes["redmax"] > minmaxes["bluemax"] else minmaxes["bluemax"]
                    minpixel = minmaxes["redmin"] if minmaxes["redmin"] < minmaxes["bluemin"] else minmaxes["bluemin"]
                    # blue = refimg[:, :, 0] - (refimg[:, :, 2] * 0.80)  # Subtract the NIR bleed over from the blue channel
                elif ((ind[0] == 3) and (ind[1] == 3)) \
                        or ((ind[0] == 4) \
                        and (ind[1] == 1 or ind[1] == 2)):
                    ### red and NIR
                    maxpixel = minmaxes["redmax"]
                    minpixel = minmaxes["redmin"]
                elif (ind[0] == 4) and ind[1] == 3:
                    ### green
                    maxpixel = minmaxes["greenmax"]
                    minpixel = minmaxes["greenmin"]
                elif ((ind[0] == 4)) and ind[1] == 4:
                    ### blue
                    maxpixel = minmaxes["bluemax"]
                    minpixel = minmaxes["bluemin"]

                elif (ind[0] == 3 and ind[1] != 3):

                    maxpixel = minmaxes["redmax"] if minmaxes["redmax"] > minmaxes["bluemax"] else minmaxes["bluemax"]
                    maxpixel = minmaxes["greenmax"] if minmaxes["greenmax"] > maxpixel else maxpixel
                    minpixel = minmaxes["redmin"] if minmaxes["redmin"] < minmaxes["bluemin"] else minmaxes["bluemin"]
                    minpixel = minmaxes["greenmin"] if minmaxes["greenmin"] < minpixel else minpixel

                elif ind[0] == 7:
                    maxpixel = minmaxes["redmax"] if minmaxes["redmax"] > minmaxes["bluemax"] else minmaxes["bluemax"]
                    maxpixel = minmaxes["greenmax"] if minmaxes["greenmax"] > maxpixel else maxpixel
                    minpixel = minmaxes["redmin"] if minmaxes["redmin"] < minmaxes["bluemin"] else minmaxes["bluemin"]
                    minpixel = minmaxes["greenmin"] if minmaxes["greenmin"] < minpixel else minpixel
                else:  ###Survey2 NDVI
                    maxpixel = minmaxes["redmax"] if minmaxes["redmax"] > minmaxes["bluemax"] else minmaxes["bluemax"]
                    minpixel = minmaxes["redmin"] if minmaxes["redmin"] < minmaxes["bluemin"] else minmaxes["bluemin"]

            else:
                if ind[0] == 5:  ###Survey1 NDVI
                    maxpixel = minmaxes["redmax"] if minmaxes["redmax"] > minmaxes["bluemax"] else minmaxes["bluemax"]
                    minpixel = minmaxes["redmin"] if minmaxes["redmin"] < minmaxes["bluemin"] else minmaxes["bluemin"]

                elif (ind[0] == 3 and ind[1] != 3):


                    maxpixel = minmaxes["redmax"] if minmaxes["redmax"] > minmaxes["bluemax"] else minmaxes["bluemax"]
                    maxpixel = minmaxes["greenmax"] if minmaxes["greenmax"] > maxpixel else maxpixel
                    minpixel = minmaxes["redmin"] if minmaxes["redmin"] < minmaxes["bluemin"] else minmaxes["bluemin"]
                    minpixel = minmaxes["greenmin"] if minmaxes["greenmin"] < minpixel else minpixel
                else:
                    maxpixel = minmaxes["redmax"] if minmaxes["redmax"] > minmaxes["bluemax"] else minmaxes["bluemax"]
                    minpixel = minmaxes["redmin"] if minmaxes["redmin"] < minmaxes["bluemin"] else minmaxes["bluemin"]
                    # red = refimg[:, :, 2] - (refimg[:, :, 0] * 0.80)  # Subtract the NIR bleed over from the red channel



            ### Scale calibrated values back down to a useable range (Adding 1 to avaoid 0 value pixels, as they will cause a
            #### devide by zero case when creating an index image.
            red = (((red - minpixel) / (maxpixel - minpixel)))
            green = (((green - minpixel) / (maxpixel - minpixel)))
            blue = (((blue - minpixel) / (maxpixel - minpixel)))
            if self.IndexBox.checkState() == 0:
                if photo.split('.')[2].upper() == "JPG" or photo.split('.')[
                    2].upper() == "JPEG" or self.Tiff2JpgBox.checkState() > 0:

                    red *= 255
                    green *= 255
                    blue *= 255
                    green[green < 0] = 0
                    red[red < 0] = 0
                    blue[blue < 0] = 0
                    red[red > 255] = 255
                    green[green > 255] = 255
                    blue[blue > 255] = 255
                    # index = self.calculateIndex(red, blue)
                    # cv2.imwrite(output_directory + photo.split('.')[1] + "_CALIBRATED_INDEX." + photo.split('.')[2], index)
                    red = red.astype("uint8")
                    green = green.astype("uint8")
                    blue = blue.astype("uint8")
                else:
                    # maxpixel *= 10
                    # minpixel *= 10

                    # tempimg = cv2.merge((blue, green, red)).astype("float32")
                    # cv2.imwrite(output_directory + photo.split('.')[1] + "_Percent." + photo.split('.')[2], tempimg)

                    red *= MAPIR_Defaults.UINT16MAX_INT
                    green *= MAPIR_Defaults.UINT16MAX_INT
                    blue *= MAPIR_Defaults.UINT16MAX_INT

                    green[green > MAPIR_Defaults.UINT16MAX_INT] = MAPIR_Defaults.UINT16MAX_INT
                    red[red > MAPIR_Defaults.UINT16MAX_INT] = MAPIR_Defaults.UINT16MAX_INT
                    blue[blue > MAPIR_Defaults.UINT16MAX_INT] = MAPIR_Defaults.UINT16MAX_INT

                    green[green < 0] = 0
                    red[red < 0] = 0
                    blue[blue < 0] = 0

                    red = red.astype("uint16")
                    green = green.astype("uint16")
                    blue = blue.astype("uint16")
                refimg = cv2.merge((blue, green, red))
            else:
                green[green > 1.0] = 1.0
                red[red > 1.0] = 1.0
                blue[blue > 1.0] = 1.0
                green[green < 0.0] = 0.0
                red[red < 0.0] = 0.0
                blue[blue < 0.0] = 0.0
                red = red.astype("float")
                green = green.astype("float")
                blue = blue.astype("float")

            # if alpha == []:
                refimg = cv2.merge((blue, green, red))
                refimg = cv2.normalize(refimg.astype("float"), None, 0.0, 1.0, cv2.NORM_MINMAX)



            if (((ind[0] == 4)) and ind[1] == 0) or ((ind[0] > 4) and (ind[0] != 7)):
                ### Remove green information if NDVI camera
                refimg[:, :, 1] = 1

            elif (ind[0] == 4 and ind[1] == 1) \
                    or (ind[0] == 3 and ind[1] == 3) or (ind[0] == 4 and self.CalibrationFilter.currentIndex() == 2):
                ### Remove blue and green information if NIR or Red camera
                # refimg[:, :, 0] = 1
                # refimg[:, :, 1] = 1
                refimg = refimg[:, :, 2]
            elif ((ind[0] == 4)) and ind[1] == 3:
                ### Remove blue and red information if GREEN camera
                # refimg[:, :, 0] = 1
                # refimg[:, :, 2] = 1
                refimg = refimg[:, :, 1]
            elif ((ind[0] == 4)) and ind[1] == 4:
                ### Remove red and green information if BLUE camera
                # refimg[:, :, 1] = 1
                # refimg[:, :, 2] = 1
                refimg = refimg[:, :, 0]

        if self.Tiff2JpgBox.checkState() > 0:
            self.CalibrationLog.append("Making JPG")
            QtWidgets.QApplication.processEvents()
            cv2.imencode(".jpg", refimg)
            cv2.imwrite(output_directory + photo.split('.')[1] + "_CALIBRATED.JPG", refimg,
                        [int(cv2.IMWRITE_JPEG_QUALITY), 100])

            self.copyExif(photo, output_directory + photo.split('.')[1] + "_CALIBRATED.JPG")

        else:
            newimg = output_directory + photo.split('.')[1] + "_CALIBRATED." + photo.split('.')[2]
            if 'tif' in photo.split('.')[2].lower():
                cv2.imencode(".tif", refimg)
                cv2.imwrite(newimg, refimg)
                srin = gdal.Open(photo)
                inproj = srin.GetProjection()
                transform = srin.GetGeoTransform()
                gcpcount = srin.GetGCPs()
                srout = gdal.Open(newimg, gdal.GA_Update)
                srout.SetProjection(inproj)
                srout.SetGeoTransform(transform)
                srout.SetGCPs(gcpcount, srin.GetGCPProjection())
                srout = None
                srin = None
            else:
                cv2.imwrite(newimg, refimg, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
            self.copyExif(photo, newimg)


    def calculateIndex(self, visible, nir):
        #calculates the index of visible light
        try:
            nir[nir == 0] = 1
            visible[visible == 0] = 1
            if nir.dtype == "uint8":
                nir = nir / 255.0
                visible = visible / 255.0
            elif nir.dtype == "uint16":
                nir /= MAPIR_Defaults.UINT16MAX_FLOAT
                visible /= MAPIR_Defaults.UINT16MAX_FLOAT

            numer = nir - visible
            denom = nir + visible

            retval = numer/denom
            return retval
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            print(e)
            print("Line: " + str(exc_tb.tb_lineno))
            return False

    ####Function for finding he QR target and calculating the calibration coeficients\
    def findQR(self, image, ind):
        """ finds the MAPIR control ground target and generates normalized calibration value  """
        try:
            self.ref = ""

            subprocess.call([modpath + os.sep + r'FiducialFinder.exe', image], startupinfo=si)


            im_orig = cv2.imread(image, -1)

            list = None
            im = cv2.imread(image, 0)
            listcounter = 2
            if os.path.exists(r'.' + os.sep + r'calib.txt'):
                # cv2.imwrite(image.split('.')[-2] + "_original." + image.split('.')[-1], cv2.imread(image, -1))
                while (list is None or len(list) <= 0) and listcounter < 10:
                    with open(r'.' + os.sep + r'calib.txt', 'r+') as cornerfile:
                        list = cornerfile.read()

                    im = im * listcounter
                    listcounter += 1
                    cv2.imwrite(image, im)
                    subprocess.call([modpath + os.sep + r'FiducialFinder.exe', image], startupinfo=si)


                    try:
                        list = list.split('[')[1].split(']')[0]
                    except Exception as e:
                        exc_type, exc_obj,exc_tb = sys.exc_info()
                        print(e)
                        print("Line: " + str(exc_tb.tb_lineno))
                cv2.imwrite(image, im_orig)
                # os.unlink(image.split('.')[-2] + "_original." + image.split('.')[-1])
                with open(r'.' + os.sep + r'calib.txt', 'r+') as f:
                    f.truncate()

            if list is not None and len(list) > 0:
                self.ref = self.refindex[1]
                # self.CalibrationLog.append(list)
                temp = np.fromstring(str(list), dtype=int, sep=',')
                self.coords = [[temp[0],temp[1]],[temp[2],temp[3]],[temp[6],temp[7]],[temp[4],temp[5]]]
                # self.CalibrationLog.append()
            else:
                self.ref = self.refindex[0]
                if ind[0] > 2:
                    im = cv2.imread(image)
                    grayscale = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    cl1 = clahe.apply(grayscale)
                else:
                    self.CalibrationLog.append("Looking for QR target")
                    QtWidgets.QApplication.processEvents()
                    im = cv2.imread(image, 0)
                    clahe2 = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    cl1 = clahe2.apply(im)
                denoised = cv2.fastNlMeansDenoising(cl1, None, 14, 7, 21)

                threshcounter = 17
                while threshcounter <= 255:
                    ret, thresh = cv2.threshold(denoised, threshcounter, 255, 0)
                    if os.name == "nt":
                        _, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
                    else:
                        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
                    self.coords = []
                    count = 0

                    for i in hierarchy[0]:
                        self.traverseHierarchy(hierarchy, contours, count, im, 0)

                        count += 1
                    if len(self.coords) == 3:
                        break
                    else:
                        threshcounter += 17

                if len(self.coords) is not 3:
                    self.CalibrationLog.append("Could not find MAPIR ground target.")
                    QtWidgets.QApplication.processEvents()
                    return

            line1 = np.sqrt(np.power((self.coords[0][0] - self.coords[1][0]), 2) + np.power((self.coords[0][1] - self.coords[1][1]),
                                                                                  2))  # Getting the distance between each centroid
            line2 = np.sqrt(np.power((self.coords[1][0] - self.coords[2][0]), 2) + np.power((self.coords[1][1] - self.coords[2][1]), 2))
            line3 = np.sqrt(np.power((self.coords[2][0] - self.coords[0][0]), 2) + np.power((self.coords[2][1] - self.coords[0][1]), 2))

            hypotenuse = line1 if line1 > line2 else line2
            hypotenuse = line3 if line3 > hypotenuse else hypotenuse
            if list:
                slope = (self.coords[2][1] - self.coords[1][1]) / (self.coords[2][0] - self.coords[1][0])
                dist = self.coords[0][1] - (slope * self.coords[0][0]) + ((slope * self.coords[2][0]) - self.coords[2][1])
                dist /= np.sqrt(np.power(slope, 2) + 1)
                center = self.coords[0]
                bottom = self.coords[1]
                right = self.coords[2]
            else:
                if hypotenuse == line1:

                    slope = (self.coords[1][1] - self.coords[0][1]) / (self.coords[1][0] - self.coords[0][0])
                    dist = self.coords[2][1] - (slope * self.coords[2][0]) + ((slope * self.coords[1][0]) - self.coords[1][1])
                    dist /= np.sqrt(np.power(slope, 2) + 1)
                    center = self.coords[2]

                    if (slope < 0 and dist < 0) or (slope >= 0 and dist >= 0):

                        bottom = self.coords[0]
                        right = self.coords[1]
                    else:

                        bottom = self.coords[1]
                        right = self.coords[0]
                elif hypotenuse == line2:

                    slope = (self.coords[2][1] - self.coords[1][1]) / (self.coords[2][0] - self.coords[1][0])
                    dist = self.coords[0][1] - (slope * self.coords[0][0]) + ((slope * self.coords[2][0]) - self.coords[2][1])
                    dist /= np.sqrt(np.power(slope, 2) + 1)
                    center = self.coords[0]

                    if (slope < 0 and dist < 0) or (slope >= 0 and dist >= 0):

                        bottom = self.coords[1]
                        right = self.coords[2]
                    else:

                        bottom = self.coords[2]
                        right = self.coords[1]
                else:

                    slope = (self.coords[0][1] - self.coords[2][1]) / (self.coords[0][0] - self.coords[2][0])
                    dist = self.coords[1][1] - (slope * self.coords[1][0]) + ((slope * self.coords[0][0]) - self.coords[0][1])
                    dist /= np.sqrt(np.power(slope, 2) + 1)
                    center = self.coords[1]
                    if (slope < 0 and dist < 0) or (slope >= 0 and dist >= 0):
                        # self.CalibrationLog.append("slope and dist share sign")
                        bottom = self.coords[2]
                        right = self.coords[0]
                    else:

                        bottom = self.coords[0]
                        right = self.coords[2]
            if list is not None and len(list) > 0:
                guidelength = np.sqrt(np.power((center[0] - right[0]), 2) + np.power((center[1] - right[1]), 2))
                pixelinch = guidelength / MAPIR_Defaults.CORNER_TO_CORNER
                rad = (pixelinch * MAPIR_Defaults.CORNER_TO_TARG)
                vx = center[1] - right[1]
                vy = center[0] - right[0]
            else:
                guidelength = np.sqrt(np.power((center[0] - bottom[0]), 2) + np.power((center[1] - bottom[1]), 2))
                pixelinch = guidelength / MAPIR_Defaults.SQ_TO_SQ
                rad = (pixelinch * MAPIR_Defaults.SQ_TO_TARG)
                vx = center[0] - bottom[0]
                vy = center[1] - bottom[1]

            newlen = np.sqrt(vx * vx + vy * vy)

            if list is not None and len(list) > 0:
                #upper left = 0
                #clockwise from upper left, thus lower left is 3
                #doing vector math, moving along the corners
                targ1x = (rad * (vx / newlen)) + self.coords[0][0]
                targ1y = (rad * (vy / newlen)) + self.coords[0][1]
                targ2x = (rad * (vx / newlen)) + self.coords[1][0]
                targ2y = (rad * (vy / newlen)) + self.coords[1][1]
                targ3x = (rad * (vx / newlen)) + self.coords[2][0]
                targ3y = (rad * (vy / newlen)) + self.coords[2][1]
                targ4x = (rad * (vx / newlen)) + self.coords[3][0]
                targ4y = (rad * (vy / newlen)) + self.coords[3][1]

                target1 = (int(targ1x), int(targ1y))
                target2 = (int(targ2x), int(targ2y))
                target3 = (int(targ3x), int(targ3y))
                target4 = (int(targ4x), int(targ4y))
            else:
                targ1x = (rad * (vx / newlen)) + center[0]
                targ1y = (rad * (vy / newlen)) + center[1]
                targ3x = (rad * (vx / newlen)) + right[0]
                targ3y = (rad * (vy / newlen)) + right[1]

                target1 = (int(targ1x), int(targ1y))
                target3 = (int(targ3x), int(targ3y))
                target2 = (int((np.abs(target1[0] + target3[0])) / 2), int(np.abs((target1[1] + target3[1])) / 2))

            im2 = cv2.imread(image, -1)

            # kernel = np.ones((2, 2), np.uint16)
            # im2 = cv2.erode(im2, kernel, iterations=1)
            # im2 = cv2.dilate(im2, kernel, iterations=1)
            if ((ind[0] > 1) and (ind[0] == 3 and ind[1] != 3)) or ((ind[0] < 2) and (ind[1] > 10)):
#
                try:
                    targ1values = im2[(target1[1] - int((pixelinch * 0.75) / 2)):(target1[1] + int((pixelinch * 0.75) / 2)),
                                  (target1[0] - int((pixelinch * 0.75) / 2)):(target1[0] + int((pixelinch * 0.75) / 2))]


                    targ2values = im2[(target2[1] - int((pixelinch * 0.75) / 2)):(target2[1] + int((pixelinch * 0.75) / 2)),
                                  (target2[0] - int((pixelinch * 0.75) / 2)):(target2[0] + int((pixelinch * 0.75) / 2))]
                    targ3values = im2[(target3[1] - int((pixelinch * 0.75) / 2)):(target3[1] + int((pixelinch * 0.75) / 2)),
                                  (target3[0] - int((pixelinch * 0.75) / 2)):(target3[0] + int((pixelinch * 0.75) / 2))]
                except Exception as e:
                    exc_type, exc_obj,exc_tb = sys.exc_info()
                    print(e)
                    print("Line: " + str(exc_tb.tb_lineno))

                #finding the first 3 targets
                t1redmean = np.mean(targ1values[:, :, 2])
                t1greenmean = np.mean(targ1values[:, :, 1])
                t1bluemean = np.mean(targ1values[:, :, 0])
                t2redmean = np.mean(targ2values[:, :, 2])
                t2greenmean = np.mean(targ2values[:, :, 1])
                t2bluemean = np.mean(targ2values[:, :, 0])
                t3redmean = np.mean(targ3values[:, :, 2])
                t3greenmean = np.mean(targ3values[:, :, 1])
                t3bluemean = np.mean(targ3values[:, :, 0])



                yred = []
                yblue = []
                ygreen = []
                if list is not None and len(list) > 0: #find forth target if list is greater than zero
                    targ4values = im2[(target4[1] - int((pixelinch * 0.75) / 2)):(target4[1] + int((pixelinch * 0.75) / 2)),
                                  (target4[0] - int((pixelinch * 0.75) / 2)):(target4[0] + int((pixelinch * 0.75) / 2))]
                    t4redmean = np.mean(targ4values[:, :, 2])
                    t4greenmean = np.mean(targ4values[:, :, 1])
                    t4bluemean = np.mean(targ4values[:, :, 0])
                    yred = [0.87, 0.51, 0.23, 0.0]
                    yblue = [0.87, 0.51, 0.23, 0.0]

                    xred = [t1redmean, t2redmean, t3redmean, t4redmean]
                    xgreen = [t1greenmean, t2greenmean, t3greenmean, t4greenmean]
                    xblue = [t1bluemean, t2bluemean, t3bluemean, t4bluemean]


                else:
                    yred = [0.87, 0.51, 0.23]
                    yblue = [0.87, 0.51, 0.23]
                    ygreen = [0.87, 0.51, 0.23]

                    xred = [t1redmean, t2redmean, t3redmean]
                    xgreen = [t1greenmean, t2greenmean, t3greenmean]
                    xblue = [t1bluemean, t2bluemean, t3bluemean]

                #pick the correct reference values for the appropriate filter
                if ind[1] == 1 and (ind[0] == 4) \
                        or (ind[0] == 3 and ind[1] == 3):
                    yred = self.refvalues[self.ref]["850"][0]
                    ygreen = self.refvalues[self.ref]["850"][1]
                    yblue = self.refvalues[self.ref]["850"][2]
                elif ind[1] == 2 and (ind[0] == 4):
                    yred = self.refvalues[self.ref]["650"][0]
                    ygreen = self.refvalues[self.ref]["650"][1]
                    yblue = self.refvalues[self.ref]["650"][2]
                elif ind[1] == 3 and (ind[0] == 4):
                    yred = self.refvalues[self.ref]["550"][0]
                    ygreen = self.refvalues[self.ref]["550"][1]
                    yblue = self.refvalues[self.ref]["550"][2]
                elif ind[1] == 4 and (ind[0] == 4):
                    yred = self.refvalues[self.ref]["450"][0]
                    ygreen = self.refvalues[self.ref]["450"][1]
                    yblue = self.refvalues[self.ref]["450"][2]
                elif (ind[1] == 1 and ind[0] == 3) or (
                    ind[0] == 7) or (ind[0] == 2 and ind[1] == 0):
                    yred = self.refvalues[self.ref]["550/660/850"][0]
                    ygreen = self.refvalues[self.ref]["550/660/850"][1]
                    yblue = self.refvalues[self.ref]["550/660/850"][2]
                elif (ind[0] == 3 and ind[1] == 2) or (ind[0] == 2 and ind[1] == 1):
                    yred = self.refvalues[self.ref]["475/550/850"][0]
                    ygreen = self.refvalues[self.ref]["475/550/850"][1]
                    yblue = self.refvalues[self.ref]["475/550/850"][2]
                elif (ind[0] == 3 and ind[1] == 4):

                    yred = self.refvalues[self.ref]["490/615/808"][0]
                    ygreen = self.refvalues[self.ref]["490/615/808"][1]
                    yblue = self.refvalues[self.ref]["490/615/808"][2]
                else:
                    yred = self.refvalues[self.ref]["660/850"][0]
                    ygreen = self.refvalues[self.ref]["660/850"][1]
                    yblue = self.refvalues[self.ref]["660/850"][2]


                xred = np.array(xred)
                xgreen = np.array(xgreen)
                xblue = np.array(xblue)

                xred /= MAPIR_Defaults.UINT16MAX_INT
                xgreen /= MAPIR_Defaults.UINT16MAX_INT
                xblue /= MAPIR_Defaults.UINT16MAX_INT

                yred = np.array(yred)
                ygreen = np.array(ygreen)
                yblue = np.array(yblue)

                cofr = yred[0]/xred[0]
                cofg = ygreen[0]/xgreen[0]
                cofb = yblue[0]/xblue[0]


                self.multiplication_values["Red"] = cofr
                self.multiplication_values["Green"] = cofg
                self.multiplication_values["Blue"] = cofb


                if list is not None and len(list) > 0:
                    self.CalibrationLog.append("Found QR Target Model 2, please proceed with calibration.")
                else:
                    self.CalibrationLog.append("Found QR Target Model 1, please proceed with calibration.")
                # return [ared, agreen, ablue]
            else:
                if list is not None and len(list) > 0:
                    targ1values = im2[(target1[1] - int((pixelinch * 0.75) / 2)):(target1[1] + int((pixelinch * 0.75) / 2)),
                                  (target1[0] - int((pixelinch * 0.75) / 2)):(target1[0] + int((pixelinch * 0.75) / 2))]
                    targ2values = im2[(target2[1] - int((pixelinch * 0.75) / 2)):(target2[1] + int((pixelinch * 0.75) / 2)),
                                  (target2[0] - int((pixelinch * 0.75) / 2)):(target2[0] + int((pixelinch * 0.75) / 2))]
                    targ3values = im2[(target3[1] - int((pixelinch * 0.75) / 2)):(target3[1] + int((pixelinch * 0.75) / 2)),
                                  (target3[0] - int((pixelinch * 0.75) / 2)):(target3[0] + int((pixelinch * 0.75) / 2))]
                    targ4values = im2[(target4[1] - int((pixelinch * 0.75) / 2)):(target4[1] + int((pixelinch * 0.75) / 2)),
                                  (target4[0] - int((pixelinch * 0.75) / 2)):(target4[0] + int((pixelinch * 0.75) / 2))]
                    if len(im2.shape) > 2:
                        t1mean = np.mean(targ1values[:,:,0])
                        t2mean = np.mean(targ2values[:,:,0])
                        t3mean = np.mean(targ3values[:,:,0])
                        t4mean = np.mean(targ4values[:,:,0])
                    else:
                        t1mean = np.mean(targ1values)
                        t2mean = np.mean(targ2values)
                        t3mean = np.mean(targ3values)
                        t4mean = np.mean(targ4values)
                    y = [0.87, 0.51, 0.23, 0.0]

                    #check the first value in ind, find the corresponding filter
                    if ind[1] == 0:
                        y = self.refvalues[self.ref]["Mono405"]
                    elif ind[1] == 1:
                        y = self.refvalues[self.ref]["Mono450"]
                    elif ind[1] == 2:
                        y = self.refvalues[self.ref]["Mono490"]
                    elif ind[1] == 3:
                        y = self.refvalues[self.ref]["Mono518"]
                    elif ind[1] == 4:
                        y = self.refvalues[self.ref]["Mono550"]
                    elif ind[1] == 5:
                        y = self.refvalues[self.ref]["Mono590"]
                    elif ind[1] == 6:
                        y = self.refvalues[self.ref]["Mono615"]
                    elif ind[1] == 7:
                        y = self.refvalues[self.ref]["Mono632"]
                    elif ind[1] == 8:
                        y = self.refvalues[self.ref]["Mono650"]
                    elif ind[1] == 9:
                        y = self.refvalues[self.ref]["Mono685"]
                    elif ind[1] == 10:
                        y = self.refvalues[self.ref]["Mono725"]
                    elif ind[1] == 11:
                        y = self.refvalues[self.ref]["Mono808"]
                    elif ind[1] == 12:
                        y = self.refvalues[self.ref]["Mono850"]

                    x = [t1mean, t2mean, t3mean, t4mean]
                else:
                    targ1values = im2[int(target1[1] - ((pixelinch * 0.75) / 2)):(target1[1] + ((pixelinch * 0.75) / 2)),
                                  int(target1[0] - ((pixelinch * 0.75) / 2)):(target1[0] + ((pixelinch * 0.75) / 2))]
                    targ2values = im2[int(target2[1] - ((pixelinch * 0.75) / 2)):(target2[1] + ((pixelinch * 0.75) / 2)),
                                  int(target2[0] - ((pixelinch * 0.75) / 2)):(target2[0] + ((pixelinch * 0.75) / 2))]
                    targ3values = im2[int(target3[1] - ((pixelinch * 0.75) / 2)):(target3[1] + ((pixelinch * 0.75) / 2)),
                                  int(target3[0] - ((pixelinch * 0.75) / 2)):(target3[0] + ((pixelinch * 0.75) / 2))]
                    if len(im2.shape) > 2:
                        t1mean = np.mean(targ1values[:,:,0])
                        t2mean = np.mean(targ2values[:,:,0])
                        t3mean = np.mean(targ3values[:,:,0])
                    else:
                        t1mean = np.mean(targ1values)
                        t2mean = np.mean(targ2values)
                        t3mean = np.mean(targ3values)
                    y = [0.87, 0.51, 0.23]
                    if ind[1] == 0:
                        y = self.refvalues[self.ref]["Mono405"]
                    elif ind[1] == 1:
                        y = self.refvalues[self.ref]["Mono450"]

                    elif ind[1] == 2:
                        y = self.refvalues[self.ref]["Mono518"]
                    elif ind[1] == 3:
                        y = self.refvalues[self.ref]["Mono550"]
                    elif ind[1] == 4:
                        y = self.refvalues[self.ref]["Mono590"]
                    elif ind[1] == 5:
                        y = self.refvalues[self.ref]["Mono632"]
                    elif ind[1] == 6:
                        y = self.refvalues[self.ref]["Mono650"]
                    elif ind[1] == 7:
                        y = self.refvalues[self.ref]["Mono615"]
                    elif ind[1] == 8:
                        y = self.refvalues[self.ref]["Mono725"]
                    elif ind[1] == 9:
                        y = self.refvalues[self.ref]["Mono780"]
                    elif ind[1] == 10:
                        y = self.refvalues[self.ref]["Mono808"]
                    elif ind[1] == 11:
                        y = self.refvalues[self.ref]["Mono850"]
                    elif ind[1] == 12:
                        y = self.refvalues[self.ref]["Mono880"]


                    x = [t1mean, t2mean, t3mean]
                x = np.array(x)


                y = np.array(y)


                self.multiplication_values["Mono"] = x.dot(y) / x.dot(x)

                if list is not None and len(list) > 0:
                    self.CalibrationLog.append("Found QR Target Model 2, please proceed with calibration.")
                else:
                    self.CalibrationLog.append("Found QR Target Model 1, please proceed with calibration.")
                QtWidgets.QApplication.processEvents()
                # return a
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.CalibrationLog.append("Error: " + str(e) + ' Line: ' + str(exc_tb.tb_lineno))
            return
            # slope, intcpt, r_value, p_value, std_err = stats.linregress(x, y)
            # self.CalibrationLog.append("Found QR Target, please proceed with calibration.")
            #
            # return [intcpt, slope]
    # Calibration Steps: End


    # Helper functions
    def debayer(self, m):
        b = m[0:: 2, 1:: 2]
        g = np.clip(m[0::2, 0::2] // 2 + m[1::2, 1::2] // 2, 0, 2**14 - 1)
        r = m[1:: 2, 0:: 2]
        # b = (((b - b.min()) / (b.max() - b.min())) * 65536.0).astype("uint16")
        # r = (((r - r.min()) / (r.max() - r.min())) * 65536.0).astype("uint16")
        # g = (((g - g.min()) / (g.max() - g.min())) * 65536.0).astype("uint16")
        return np.dstack([b, g, r])

    def preProcessHelper(self, infolder, outfolder, customerdata=True):

        if 5 < self.PreProcessCameraModel.currentIndex() <= 10:
            os.chdir(infolder)
            infiles = []
            infiles.extend(glob.glob("." + os.sep + "*.DNG"))
            infiles.sort()
            counter = 0
            for input in infiles:
                self.PreProcessLog.append(
                    "processing image: " + str((counter) + 1) + " of " + str(len(infiles)) +
                    " " + input.split(os.sep)[1])
                QtWidgets.QApplication.processEvents()
                self.openDNG(infolder + input.split('.')[1] + "." + input.split('.')[2], outfolder, customerdata)


                counter += 1
        elif 0 <= self.PreProcessCameraModel.currentIndex() <= 2:
            os.chdir(infolder)
            infiles = []
            infiles.extend(glob.glob("." + os.sep + "*.[mM][aA][pP][iI][rR]"))
            infiles.extend(glob.glob("." + os.sep + "*.[tT][iI][fF]"))
            infiles.extend(glob.glob("." + os.sep + "*.[tT][iI][fF][fF]"))
            counter = 0
            for input in infiles:
                self.PreProcessLog.append(
                    "processing image: " + str((counter) + 1) + " of " + str(len(infiles)) +
                    " " + input.split(os.sep)[1])
                QtWidgets.QApplication.processEvents()
                filename = input.split('.')
                outputfilename = outfolder + filename[1] + '.tif'
                # print(infolder + input.split('.')[1] + "." + input.split('.')[2])
                # print(outfolder + outputfilename)
                self.openMapir(infolder + input.split('.')[1] + "." + input.split('.')[2],  outputfilename)


                counter += 1
        else:
            os.chdir(infolder)
            infiles = []
            infiles.extend(glob.glob("." + os.sep + "*.[rR][aA][wW]"))
            infiles.extend(glob.glob("." + os.sep + "*.[jJ][pP][gG]"))
            infiles.extend(glob.glob("." + os.sep + "*.[jJ][pP][eE][gG]"))
            infiles.sort()
            if len(infiles) > 1:
                if ("RAW" in infiles[0].upper()) and ("JPG" in infiles[1].upper()):
                    counter = 0
                    oldfirmware = False
                    for input in infiles[::2]:
                        if customerdata == True:
                            self.PreProcessLog.append(
                                "processing image: " + str((counter / 2) + 1) + " of " + str(len(infiles) / 2) +
                                " " + input.split(os.sep)[1])
                            QtWidgets.QApplication.processEvents()
                        if self.PreProcessCameraModel.currentIndex() == 3:
                            try:
                                data = np.fromfile(input, dtype=np.uint8)
                                # temp1 = data[::2]
                                # temp2 = data[1::2]
                                # # temp3 = data[2::4]
                                # # temp4 = data[3::4]
                                # data2 = np.zeros(len(data), dtype=np.uint8)
                                # data2[::2] = temp2
                                # data2[1::2] = temp1
                                # # data2[2::4] = temp2
                                # # data2[3::4] = temp1
                                # data[:len(data) - 1:2], data[1::2] = data[1::2], data[:len(data) - 1:2]
                                data = np.unpackbits(data)
                                data = data.reshape((int(data.shape[0] / 12), 12))

                                images = np.zeros((4000 * 3000),dtype=np.uint16)
                                for i in range(0, 12):
                                    images += 2 ** (11 - i) * data[:,  i]
                                # red = (MAPIR_Defaults.UINT16MAX_FLOAT/31.0 * np.bitwise_and(np.right_shift(data, 11), 0x1f)).astype("uint16")
                                # green = (MAPIR_Defaults.UINT16MAX_FLOAT/63.0 * np.bitwise_and(np.right_shift(data, 5), 0x3f)).astype("uint16")
                                # blue = (MAPIR_Defaults.UINT16MAX_FLOAT/31.0 * np.bitwise_and(data, 0x1f)).astype("uint16")
                                #
                                # img = cv2.merge((blue,green,red)).astype("uint16")
                                #
                                #
                                #
                                img = np.reshape(images, (3000, 4000))
                                tim = self.debayer(img)
                                color = copy.deepcopy(tim)
                                # color[tim[:, :, 0] >= MAPIR_Defaults.UINT16MAX_INT] = MAPIR_Defaults.UINT16MAX_INT
                                # color[tim[:, :, 1] >= MAPIR_Defaults.UINT16MAX_INT] = MAPIR_Defaults.UINT16MAX_INT
                                # color[tim[:, :, 2] >= MAPIR_Defaults.UINT16MAX_INT] = MAPIR_Defaults.UINT16MAX_INT
                                # cv2.imwrite(outfolder + "test.tif", img)
                                # cv2.imwrite(outfolder + "testDB.tif", tim)
                            except Exception as e:
                                print(e)
                                oldfirmware = True
                        else:
                            img = np.fromfile(rawimage, np.dtype('u2'), self.imsize).reshape(
                                (self.imrows, self.imcols))
                            color = cv2.cvtColor(img, cv2.COLOR_BAYER_RG2RGB).astype("uint16")
                        if oldfirmware == True:
                            with open(input, "rb") as rawimage:

                                    img = np.fromfile(rawimage, np.dtype('u2'), (4000 * 3000)).reshape((3000, 4000))
                        color = cv2.cvtColor(img, cv2.COLOR_BAYER_RG2RGB).astype("float32")
                                    # rawimage.seek(0)
                                    #
                                    # data = struct.unpack("=18000000B", rawimage.read())
                                    # k = np.zeros(int(2*len(data)/3))
                                    # kcount = 0
                                    # #TODO fix this
                                    # for oo in range(0, len(data) - 2, 3):
                                    #     k[kcount], k[kcount + 1] = bitstring.Bits(bytes=data[oo:oo + 3], length=24).unpack('uint:12,uint:12')
                                    #     kcount = kcount + 2
                                    #
                                    # # for i in range(0, int(len(data)/3)):
                                    # #     # j = struct.pack("=H", data[i])
                                    # #     # p = struct.pack("=H", data[i + 1])
                                    # #     # q = struct.pack("=H", data[i + 2])
                                    # #     k.append(data[i] | data[i + 1] | data[i + 2])
                                    # #     # k.append((p[1] << 12) | data[i + 2] | 0)
                                    # k = np.array(k)
                                    # h = int(np.sqrt(k.shape[0] / (4 / 3)))
                                    # w = int(h * (4 / 3))
                                    # img = np.reshape(k, (3000, 4000)).astype("uint16")
                        if self.PreProcessFilter.currentIndex() == 0 and self.PreProcessCameraModel.currentIndex() == 3:


                            # redmax = np.setdiff1d(self.imkeys[self.imkeys > int(np.median(color[:,:,0]))], color[:,:,0])[0]
                            # redmin = color[:,:,0].min()
                            redmax = np.percentile(color[:,:,0], 98)


                            redmin = np.percentile(color[:, :, 0], 2)

                            # greenmax = \
                            #     np.setdiff1d(self.imkeys[self.imkeys > int(np.median(color[:,:,2]))], color[:,:,2])[0]
                            # greenmin = color[:,:,2].min()
                            greenmax = np.percentile(color[:, :, 1], 98)

                            greenmin = np.percentile(color[:, :, 1], 2)

                            # bluemax = \
                            #     np.setdiff1d(self.imkeys[self.imkeys > int(np.median(color[:,:,1]))], color[:,:,1])[0]
                            # bluemin = color[:,:,1].min()
                            bluemax = np.percentile(color[:, :, 2], 98)

                            bluemin = np.percentile(color[:, :, 2], 2)

                            # maxpixel = redmax if redmax > bluemax else bluemax
                            # maxpixel = greenmax if greenmax > maxpixel else maxpixel
                            # minpixel = redmin if redmin < bluemin else bluemin
                            # minpixel = greenmin if greenmin < minpixel else minpixel

                            # color = cv2.merge((color[:,:,0],color[:,:,2],color[:,:,1])).astype(np.dtype('u2'))
                            color[:,:,0] = (((color[:,:,0] - redmin) / (redmax - redmin)))
                            color[:,:,2] = (((color[:,:,2] - bluemin) / (bluemax - bluemin)))
                            color[:,:,1] = (((color[:,:,1] - greenmin) / (greenmax - greenmin)))
                            color[color > 1.0] = 1.0
                            color[color < 0.0] = 0.0

                        if self.PreProcessCameraModel.currentIndex() == 3 and self.PreProcessFilter.currentIndex() == 3:
                            color = color[:,:,0]
                        # maxcol = color.max()
                        # mincol = color.min()
                        if self.PreProcessJPGBox.isChecked():
                            # color = (color - mincol) / (maxcol  - mincol)
                            # color = color * 255.0
                            color = color.astype("uint8")
                            filename = input.split('.')
                            outputfilename = filename[1] + '.jpg'
                            cv2.imencode(".jpg", color)
                        else:
                            # color = (color - mincol) / (maxcol  - mincol)
                            # color = color * MAPIR_Defaults.UINT16MAX_FLOAT
                            color = color.astype("uint16")
                            filename = input.split('.')
                            outputfilename = filename[1] + '.tif'
                            cv2.imencode(".tif", color)
                        # cv2.imencode(".tif", color2)
                        cv2.imwrite(outfolder + outputfilename, color)
                        # outputfilename = filename[1] + '_EQ.tif'
                        # cv2.imwrite(outfolder + outputfilename, color2)
                        if customerdata == True:
                            self.copyExif(infolder + infiles[counter + 1], outfolder + outputfilename)
                        counter += 2

                else:
                    self.PreProcessLog.append(
                        "Incorrect file structure. Please arrange files in a RAW, JPG, RAW, JPG... format.")


    def traverseHierarchy(self, tier, cont, index, image, depth):

        if tier[0][index][2] != -1:
            self.traverseHierarchy(tier, cont, tier[0][index][2], image, depth + 1)
            return
        elif depth >= 2:
            c = cont[index]
            moment = cv2.moments(c)
            if int(moment['m00']) != 0:
                x = int(moment['m10'] / moment['m00'])
                y = int(moment['m01'] / moment['m00'])
                self.coords.append([x, y])
            return

    def openDNG(self, inphoto, outfolder, customerdata=True):
        """ """
        inphoto = str(inphoto)
        newfile = inphoto.split(".")[0] + ".tif"
        if not os.path.exists(outfolder + os.sep + newfile.rsplit(os.sep, 1)[1]):
            if sys.platform == "win32":
                subprocess.call([modpath + os.sep + 'dcraw.exe', '-6', '-T', inphoto], startupinfo=si)
            else:
                subprocess.call([r'/usr/local/bin/dcraw', '-6', '-T', inphoto])
            if customerdata == True:
                self.copyExif(os.path.abspath(inphoto), newfile)
            shutil.move(newfile, outfolder)
        else:
            self.PreProcessLog.append("Attention!: " + str(newfile) + " already exists.")

    def openMapir(self, inphoto, outphoto):
        """ openMapir is a wrapper function for MAPIR Converter, it has two calls with the darkscale parameter
        if darkscale = False bits are padded on the least signficant pits are padded
            e.g. 1111 1111 1111 -> 1111 1111 1111 0000
        if darks scale = True the most significant bits are padded
            e.g. 1111 1111 1111 -> 0000 1111 1111 1111
        """
        # self.PreProcessLog.append(str(inphoto) + " " + str(outphoto))
        try:
            if "mapir" in inphoto.split('.')[1]:
                self.conv = Converter()
                if self.PreProcessDarkBox.isChecked():
                    # subprocess.call(
                    #     [modpath + os.sep + r'Mapir_Converter.exe', '-d', os.path.abspath(inphoto),
                    #      os.path.abspath(outphoto)], startupinfo=si)
                    _, _, _, self.lensvals = self.conv.openRaw(inphoto, outphoto, darkscale=True)
                else:
                    # subprocess.call(
                    #     [modpath + os.sep + r'Mapir_Converter.exe', os.path.abspath(inphoto),
                    #      os.path.abspath(outphoto)], startupinfo=si)
                    _, _, _, self.lensvals = self.conv.openRaw(inphoto, outphoto, darkscale=False)
                img = cv2.imread(outphoto, -1)
                try:


                    if self.PreProcessFilter.currentIndex() > 16 or self.PreProcessCameraModel.currentIndex() == 2:
                        self.PreProcessLog.append("Debayering")
                        QtWidgets.QApplication.processEvents()
                        cv2.imwrite(outphoto.split('.')[0] + r"_TEMP." + outphoto.split('.')[1], img)
                        self.copySimple(outphoto, outphoto.split('.')[0] + r"_TEMP." + outphoto.split('.')[1])
                        color = cv2.cvtColor(img, cv2.COLOR_BAYER_GB2RGB).astype("uint16")
                        color2 = cv2.cvtColor(img, cv2.COLOR_BAYER_BG2BGR).astype("uint16")
                        # gr = ((color2[:,:,2] + color2[:,:,0])/2).astype("uint16")
                        #
                        # color[:,:,1] = gr
                        #
                        # color[color > MAPIR_Defaults.UINT16MAX_INT] = MAPIR_Defaults.UINT16MAX_INT
                        # color[color < 0] = 0
                        # color[:, :, 1] = color2[:, :, 2]
                        color[:, :, 1] = color2[:, :, 0]
                        # temp1 = color[:,:,0]
                        # color[:,:,0] = color[:,:,2]
                        # color[:,:2] = temp1
                        # color = self.debayer(img)
                        # color = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype("uint16")
                        roff = 0
                        goff = 0
                        boff = 0
                        color -= 2690
                        color = color / MAPIR_Defaults.UINT16MAX_INT
                        if self.PreProcessColorBox.isChecked():
                            red = color[:, :, 0] = (1.510522 * color[:, :, 0]) + (0.0 * color[:, :, 1]) + (0.0 * color[:, :, 2]) + roff
                            green = color[:, :, 1] = (0.0 * color[:, :, 0]) + (1 * color[:, :, 1]) + (0.0 * color[:, :, 2]) + goff
                            blue = color[:, :, 2] = (0.0 * color[:, :, 0]) + (0.0 * color[:, :, 1]) + (1.5467111 * color[:, :, 2]) + boff

                            color[red > 1.0] = 1.0
                            color[green > 1.0] = 1.0
                            color[blue > 1.0] = 1.0
                            color[red < 0.0] = 0.0
                            color[green < 0.0] = 0.0
                            color[blue < 0.0] = 0.0

                        color = (color * MAPIR_Defaults.UINT16MAX_FLOAT).astype("uint16")



                        cv2.imencode(".tif", color)

                        cv2.imwrite(outphoto, color)
                        self.copyMAPIR(outphoto.split('.')[0] + r"_TEMP." + outphoto.split('.')[1], outphoto)
                        os.unlink(outphoto.split('.')[0] + r"_TEMP." + outphoto.split('.')[1])

                        self.PreProcessLog.append("Done Debayering")
                        QtWidgets.QApplication.processEvents()
                    else:
                        h, w = img.shape[:2]
                        try:
                            if self.PreProcessVignette.isChecked():
                                with open(modpath + os.sep + r"vig_" + str(
                                        self.PreProcessFilter.currentText()) + r".txt", "rb") as vigfile:
                                    # with open(self.VignetteFileSelect.text(), "rb") as vigfile:
                                    v_array = np.ndarray((h, w), np.dtype("float32"),
                                                         np.fromfile(vigfile, np.dtype("float32")))
                                    img = img / v_array
                                    img[img > MAPIR_Defaults.UINT16MAX_FLOAT] = MAPIR_Defaults.UINT16MAX_FLOAT
                                    img[img < 0.0] = 0.0
                                    img = img.astype("uint16")
                                cv2.imwrite(outphoto, img)
                        except Exception as e:
                            print(e)
                            self.PreProcessLog.append("No vignette correction data found")
                            QtWidgets.QApplication.processEvents()
                        self.copyMAPIR(outphoto, outphoto)
                        # self.PreProcessLog.append("Skipped Debayering")
                        QtWidgets.QApplication.processEvents()
                except Exception as e:
                    exc_type, exc_obj,exc_tb = sys.exc_info()
                    print(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
            else:
                try:

                    if self.PreProcessFilter.currentIndex() > 16 or self.PreProcessCameraModel.currentIndex() == 2:
                        img = cv2.imread(inphoto, 0)

                        #TODO Take the Matrix from Opencv and try to dot product

                        color = cv2.cvtColor(img, cv2.COLOR_BAYER_GR2RGB)
                        # color = self.debayer(img)

                        self.PreProcessLog.append("Debayering")
                        QtWidgets.QApplication.processEvents()
                        cv2.imencode(".tif", color)
                        cv2.imwrite(outphoto, color)
                        self.copyExif(inphoto, outphoto)
                        self.PreProcessLog.append("Done Debayering")
                        QtWidgets.QApplication.processEvents()

                    else:

                        if "mapir" not in inphoto.split('.')[1]:
                            img = cv2.imread(inphoto, -1)
                            h, w = img.shape[:2]
                            try:
                                if self.PreProcessVignette.isChecked():
                                    with open(modpath + os.sep + r"vig_" + str(
                                            self.PreProcessFilter.currentText()) + r".txt", "rb") as vigfile:
                                        # with open(self.VignetteFileSelect.text(), "rb") as vigfile:
                                        v_array = np.ndarray((h, w), np.dtype("float32"),
                                                             np.fromfile(vigfile, np.dtype("float32")))
                                        img = img / v_array
                                        img[img > MAPIR_Defaults.UINT16MAX_FLOAT] = MAPIR_Defaults.UINT16MAX_FLOAT
                                        img[img < 0.0] = 0.0
                                        img = img.astype("uint16")
                                    cv2.imwrite(outphoto, img)
                                else:
                                    shutil.copyfile(inphoto, outphoto)

                            except Exception as e:
                                print(e)
                                self.PreProcessLog.append("No vignette correction data found")
                                QtWidgets.QApplication.processEvents()

                            self.copyExif(inphoto, outphoto)
                        else:

                            self.copyExif(outphoto, outphoto)
                        # self.PreP.shaperocessLog.append("Skipped Debayering")
                        QtWidgets.QApplication.processEvents()
                except Exception as e:
                    exc_type, exc_obj,exc_tb = sys.exc_info()
                    print(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.PreProcessLog.append("Error in function openMapir(): " + str(e) + ' Line: ' + str(exc_tb.tb_lineno))
        QtWidgets.QApplication.processEvents()
    def findCameraModel(self, resolution):
        if resolution < 10000000:
            return 'Kernel 3.2MP'
        else:
            return 'Kernel 14.4MP'

    def copyExif(self, inphoto, outphoto):

        """ def copyExif reads in the metadata and adds a large amount of additional meta data to the tif files"""
        subprocess._cleanup()
        # if self.PreProcessCameraModel.currentIndex() < 3:
        try:
            data = subprocess.run(
                args=[modpath + os.sep + r'exiftool.exe', '-m', r'-UserComment', r'-ifd0:imagewidth', r'-ifd0:imageheight',
                      os.path.abspath(inphoto)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.PIPE, startupinfo=si).stdout.decode("utf-8")
            data = [line.strip().split(':') for line in data.split('\r\n') if line.strip()]
            ypr = data[0][1].split()
            # ypr = [0.0] * 3
            # ypr[0] = abs(float(ypr[0]))
            # ypr[1] = -float(ypr[1])
            # ypr[2] = ((float(ypr[2]) + 180.0) % 360.0)
            w = int(data[1][1])
            h = int(data[2][1])
            model = self.findCameraModel(w * h)
            centralwavelength = self.lensvals[3:6][1]
            bandname = self.lensvals[3:6][0]

            fnumber = self.lensvals[0][1]
            focallength = self.lensvals[0][0]
            lensmodel = self.lensvals[0][0] + "mm"

            # centralwavelength = inphoto.split(os.sep)[-1][1:4]
            if '' not in bandname:
                exifout = subprocess.run(
                    [modpath + os.sep + r'exiftool.exe', r'-config', modpath + os.sep + r'mapir.config', '-m',
                     r'-overwrite_original', r'-tagsFromFile',
                     os.path.abspath(inphoto),
                     r'-all:all<all:all',
                     r'-ifd0:make=MAPIR',
                     r'-Model=' + model,
                     r'-ifd0:blacklevelrepeatdim=' + str(1) + " " + str(1),
                     r'-ifd0:blacklevel=0',
                     r'-bandname=' + str(bandname[0] + ', ' + bandname[1] + ', ' + bandname[2]),
                     # r'-bandname2=' + str( r'F' + str(self.BandNames.get(bandname, [0, 0, 0])[1])),
                     # r'-bandname3=' + str( r'F' + str(self.BandNames.get(bandname, [0, 0, 0])[2])),
                     r'-WavelengthFWHM=' + str( self.lensvals[3:6][0][2] + ', ' + self.lensvals[3:6][1][2] + ', ' + self.lensvals[3:6][2][2]) ,
                     r'-ModelType=perspective',
                     r'-Yaw=' + str(ypr[0]),
                     r'-Pitch=' + str(ypr[1]),
                     r'-Roll=' + str(ypr[2]),
                     r'-CentralWavelength=' + str(float(centralwavelength[0])) + ', ' + str(float(centralwavelength[1])) + ', ' + str(float(centralwavelength[2])),
                     r'-Lens=' + lensmodel,
                     r'-FocalLength=' + focallength,
                     r'-fnumber=' + fnumber,
                     r'-FocalPlaneXResolution=' + str(6.14),
                     r'-FocalPlaneYResolution=' + str(4.60),
                     os.path.abspath(outphoto)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                    startupinfo=si).stderr.decode("utf-8")
            else:
                if bandname[0].isdigit():
                    bandname[0] = r'F' + bandname[0]
                if bandname[1].isdigit():
                    bandname[1] = r'F' + bandname[1]
                if bandname[2].isdigit():
                    bandname[2] = r'F' + bandname[2]
                exifout = subprocess.run(
                    [modpath + os.sep + r'exiftool.exe', r'-config', modpath + os.sep + r'mapir.config', '-m',
                     r'-overwrite_original', r'-tagsFromFile',
                     os.path.abspath(inphoto),
                     r'-all:all<all:all',
                     r'-ifd0:make=MAPIR',
                     r'-Model=' + model,
                     r'-ifd0:blacklevelrepeatdim=' + str(1) + " " + str(1),
                     r'-ifd0:blacklevel=0',
                     r'-bandname=' + str( bandname[0]),
                     r'-ModelType=perspective',
                     r'-WavelengthFWHM=' + str(self.lensvals[3:6][0][2]),
                     r'-Yaw=' + str(ypr[0]),
                     r'-Pitch=' + str(ypr[1]),
                     r'-Roll=' + str(ypr[2]),
                     r'-CentralWavelength=' + str(float(centralwavelength[0])),
                     r'-Lens=' + lensmodel,
                     r'-FocalLength=' + focallength,
                     r'-fnumber=' + fnumber,
                     r'-FocalPlaneXResolution=' + str(6.14),
                     r'-FocalPlaneYResolution=' + str(4.60),
                     os.path.abspath(outphoto)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                    startupinfo=si).stderr.decode("utf-8")
        except:
            exifout = subprocess.run(
                [modpath + os.sep + r'exiftool.exe', #r'-config', modpath + os.sep + r'mapir.config',
                 r'-overwrite_original_in_place', r'-tagsFromFile',
                 os.path.abspath(inphoto),
                 r'-all:all<all:all',
                 os.path.abspath(outphoto)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                startupinfo=si).stderr.decode("utf-8")
            print(exifout)
    def copySimple(self, inphoto, outphoto):
        exifout = subprocess.run(
            [modpath + os.sep + r'exiftool.exe',  # r'-config', modpath + os.sep + r'mapir.config',
             r'-overwrite_original_in_place', r'-tagsFromFile',
             os.path.abspath(inphoto),
             r'-all:all<all:all',
             os.path.abspath(outphoto)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
            startupinfo=si).stderr.decode("utf-8")
        print(exifout)
    def copyMAPIR(self, inphoto, outphoto):
        if sys.platform == "win32":
            # with exiftool.ExifTool() as et:
            #     et.execute(r' -overwrite_original -tagsFromFile ' + os.path.abspath(inphoto) + ' ' + os.path.abspath(outphoto))

            try:
                subprocess._cleanup()
                data = subprocess.run(
                    args=[modpath + os.sep + r'exiftool.exe', '-m', r'-ifd0:imagewidth', r'-ifd0:imageheight', os.path.abspath(inphoto)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE, startupinfo=si).stdout.decode("utf-8")
                data = [line.strip().split(':') for line in data.split('\r\n') if line.strip()]
                # ypr = data[0][1].split()
                #
                ypr = [0.0] * 3
                # ypr[0] = abs(float(self.conv.META_PAYLOAD["ATT_Q0"][1]))
                # ypr[1] = -float(self.conv.META_PAYLOAD["ATT_Q1"][1])
                # ypr[2] = ((float(self.conv.META_PAYLOAD["ATT_Q2"][1]) + 180.0) % 360.0)
                ypr[0] = abs(float(self.conv.META_PAYLOAD["ATT_Q0"][1]))
                ypr[1] = float(self.conv.META_PAYLOAD["ATT_Q1"][1])
                ypr[2] = ((float(self.conv.META_PAYLOAD["ATT_Q2"][1])))
                w = int(data[0][1])
                h = int(data[1][1])
                model = self.findCameraModel(w * h)
                centralwavelength = [self.lensvals[3:6][0][1], self.lensvals[3:6][1][1], self.lensvals[3:6][2][1]]
                bandname = [self.lensvals[3:6][0][0], self.lensvals[3:6][1][0], self.lensvals[3:6][2][0]]

                fnumber = self.lensvals[0][1]
                focallength = self.lensvals[0][0]
                lensmodel = self.lensvals[0][0] + "mm"

            except Exception as e:
                exc_type, exc_obj,exc_tb = sys.exc_info()
                ypr = None
                print(e)
                print("Line: " + str(exc_tb.tb_lineno))
                print("Warning: No userdefined tags detected")


            finally:
                if ypr is not None:
                    try:
                        dto = datetime.datetime.fromtimestamp(self.conv.META_PAYLOAD["TIME_SECS"][1])
                        m, s = divmod(self.conv.META_PAYLOAD["GNSS_TIME_SECS"][1], 60)
                        h, m = divmod(m, 60)
                        # dd, h = divmod(h, 24)


                        altref = 0 if self.conv.META_PAYLOAD["GNSS_HEIGHT_SEA_LEVEL"][1] >= 0 else 1
                        if '' not in bandname:
                            ###using exifout to write a bunch of metadata information to the kernel
                            exifout = subprocess.run(
                                [modpath + os.sep + r'exiftool.exe',  r'-config', modpath + os.sep + r'mapir.config', '-m', r'-overwrite_original', r'-tagsFromFile',
                                 os.path.abspath(inphoto),
                                 r'-all:all<all:all',
                                 r'-ifd0:make=MAPIR',
                                 r'-Model=' + model,
                                 r'-ifd0:blacklevelrepeatdim=' + str(1) + " " + str(1),
                                 r'-ifd0:blacklevel=0',
                                 r'-ModelType=perspective',
                                 r'-Yaw=' + str(ypr[0]),
                                 r'-Pitch=' + str(ypr[1]),
                                 r'-Roll=' + str(ypr[2]),
                                 r'-CentralWavelength=' + str(float(centralwavelength[0])) + ', ' + str(float(centralwavelength[1])) + ', ' + str(float(centralwavelength[2])),
                                 # r'-BandName="{band1=' + str(self.BandNames[bandname][0]) + r'band2=' + str(self.BandNames[bandname][1]) + r'band3=' + str(self.BandNames[bandname][2]) + r'}"',
                                 r'-bandname=' + str(bandname[0] + ', ' + bandname[1] + ', ' + bandname[2]),
                                 # r'-bandname2=' + str( r'F' + self.BandNames.get(bandname, [0,0,0])[1]),
                                 # r'-bandname3=' + str( r'F' + self.BandNames.get(bandname, [0,0,0])[2]),

                                 r'-WavelengthFWHM=' +str( self.lensvals[3:6][0][2] + ', ' + self.lensvals[3:6][1][2] + ', ' + self.lensvals[3:6][2][2]),
                                 r'-GPSLatitude="' + str(self.conv.META_PAYLOAD["GNSS_LAT_HI"][1]) + r'"',

                                 r'-GPSLongitude="' + str(self.conv.META_PAYLOAD["GNSS_LON_HI"][1]) + r'"',
                                 r'-GPSTimeStamp="{hour=' + str(h) + r',minute=' + str(m) + r',second=' + str(s) + r'}"',
                                 r'-GPSAltitude=' + str(self.conv.META_PAYLOAD["GNSS_HEIGHT_SEA_LEVEL"][1]),
                                 # r'-GPSAltitudeE=' + str(self.conv.META_PAYLOAD["GNSS_HEIGHT_ELIPSOID"][1]),
                                 r'-GPSAltitudeRef#=' + str(altref),
                                 r'-GPSTimeStampS=' + str(self.conv.META_PAYLOAD["GNSS_TIME_NSECS"][1]),
                                 r'-GPSLatitudeRef=' + self.conv.META_PAYLOAD["GNSS_VELOCITY_N"][1],
                                 r'-GPSLongitudeRef=' + self.conv.META_PAYLOAD["GNSS_VELOCITY_E"][1],
                                 r'-GPSLeapSeconds=' + str(self.conv.META_PAYLOAD["GNSS_LEAP_SECONDS"][1]),
                                 r'-GPSTimeFormat=' + str(self.conv.META_PAYLOAD["GNSS_TIME_FORMAT"][1]),
                                 r'-GPSFixStatus=' + str(self.conv.META_PAYLOAD["GNSS_FIX_STATUS"][1]),
                                 r'-DateTimeOriginal=' + dto.strftime("%Y:%m:%d %H:%M:%S"),
                                 r'-SubSecTimeOriginal=' + str(self.conv.META_PAYLOAD["TIME_NSECS"][1]),
                                 r'-ExposureTime=' + str(self.conv.META_PAYLOAD["EXP_TIME"][1]),
                                 r'-ExposureMode#=' + str(self.conv.META_PAYLOAD["EXP_MODE"][1]),
                                 r'-ISO=' + str(self.conv.META_PAYLOAD["ISO_SPEED"][1]),
                                 r'-Lens=' + lensmodel,
                                 r'-FocalLength=' + focallength,
                                 r'-fnumber=' + fnumber,
                                 r'-FocalPlaneXResolution=' + str(6.14),
                                 r'-FocalPlaneYResolution=' + str(4.60),
                                 os.path.abspath(outphoto)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, startupinfo=si).stderr.decode("utf-8")
                        else:

                            exifout = subprocess.run(
                                [modpath + os.sep + r'exiftool.exe', r'-config', modpath + os.sep + r'mapir.config',
                                 '-m', r'-overwrite_original', r'-tagsFromFile',
                                 os.path.abspath(inphoto),
                                 r'-all:all<all:all',
                                 r'-ifd0:make=MAPIR',
                                 r'-Model=' + model,
                                 r'-ModelType=perspective',
                                 r'-Yaw=' + str(ypr[0]),
                                 r'-Pitch=' + str(ypr[1]),
                                 r'-Roll=' + str(ypr[2]),
                                 r'-CentralWavelength=' + str(float(centralwavelength[0])),
                                 r'-ifd0:blacklevelrepeatdim=' + str(1) + " " +  str(1),
                                 r'-ifd0:blacklevel=0',
                                 # r'-BandName="{band1=' + str(self.BandNames[bandname][0]) + r'band2=' + str(self.BandNames[bandname][1]) + r'band3=' + str(self.BandNames[bandname][2]) + r'}"',
                                 r'-bandname=' + bandname[0],
                                 r'-WavelengthFWHM=' + str(self.lensvals[3:6][0][2]),
                                 r'-GPSLatitude="' + str(self.conv.META_PAYLOAD["GNSS_LAT_HI"][1]) + r'"',

                                 r'-GPSLongitude="' + str(self.conv.META_PAYLOAD["GNSS_LON_HI"][1]) + r'"',
                                 r'-GPSTimeStamp="{hour=' + str(h) + r',minute=' + str(m) + r',second=' + str(
                                     s) + r'}"',
                                 r'-GPSAltitude=' + str(self.conv.META_PAYLOAD["GNSS_HEIGHT_SEA_LEVEL"][1]),
                                 # r'-GPSAltitudeE=' + str(self.conv.META_PAYLOAD["GNSS_HEIGHT_ELIPSOID"][1]),
                                 r'-GPSAltitudeRef#=' + str(altref),
                                 r'-GPSTimeStampS=' + str(self.conv.META_PAYLOAD["GNSS_TIME_NSECS"][1]),
                                 r'-GPSLatitudeRef=' + self.conv.META_PAYLOAD["GNSS_VELOCITY_N"][1],
                                 r'-GPSLongitudeRef=' + self.conv.META_PAYLOAD["GNSS_VELOCITY_E"][1],
                                 r'-GPSLeapSeconds=' + str(self.conv.META_PAYLOAD["GNSS_LEAP_SECONDS"][1]),
                                 r'-GPSTimeFormat=' + str(self.conv.META_PAYLOAD["GNSS_TIME_FORMAT"][1]),
                                 r'-GPSFixStatus=' + str(self.conv.META_PAYLOAD["GNSS_FIX_STATUS"][1]),
                                 r'-DateTimeOriginal=' + dto.strftime("%Y:%m:%d %H:%M:%S"),
                                 r'-SubSecTimeOriginal=' + str(self.conv.META_PAYLOAD["TIME_NSECS"][1]),
                                 r'-ExposureTime=' + str(self.conv.META_PAYLOAD["EXP_TIME"][1]),
                                 r'-ExposureMode#=' + str(self.conv.META_PAYLOAD["EXP_MODE"][1]),
                                 r'-ISO=' + str(self.conv.META_PAYLOAD["ISO_SPEED"][1]),
                                 r'-Lens=' + lensmodel,
                                 r'-FocalLength=' + focallength,
                                 r'-fnumber=' + fnumber,
                                 r'-FocalPlaneXResolution=' + str(6.14),
                                 r'-FocalPlaneYResolution=' + str(4.60),
                                 os.path.abspath(outphoto)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.PIPE, startupinfo=si).stderr.decode("utf-8")
                        print(exifout)

                    except Exception as e:
                        exc_type, exc_obj,exc_tb = sys.exc_info()
                        if self.MapirTab.currentIndex() == 0:
                            self.PreProcessLog.append("Error: " + str(e) + ' Line: ' + str(exc_tb.tb_lineno))
                        elif self.MapirTab.currentIndex() == 1:
                            self.CalibrationLog.append("Error: " + str(e) + ' Line: ' + str(exc_tb.tb_lineno))
                else:
                    # self.PreProcessLog.append("No IMU data detected.")
                    subprocess.call(
                        [modpath + os.sep + r'exiftool.exe', '-m', r'-overwrite_original', r'-tagsFromFile',
                         os.path.abspath(inphoto),
                         # r'-all:all<all:all',
                         os.path.abspath(outphoto)], startupinfo=si)
        else:
            subprocess.call(
                [r'exiftool', r'-overwrite_original', r'-addTagsFromFile', os.path.abspath(inphoto),
                 # r'-all:all<all:all',
                 os.path.abspath(outphoto)])

    def on_AnalyzeInButton_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            folder = QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read())
            self.AnalyzeInput.setText(folder)
            self.AnalyzeOutput.setText(folder)
            try:
                folders = glob.glob(self.AnalyzeInput.text() + os.sep + r'*' + os.sep)
                filecount = len(glob.glob(folders[0] + os.sep + r'*'))
                for fold in folders:
                    if filecount == len(glob.glob(fold + os.sep + r'*')):
                        pass
                    else:
                        raise ValueError("Sub-Directories must contain the same number of files.")
            except ValueError as ve:
                print("Error: " + ve)
                return 256
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.AnalyzeInput.text())

    def on_AnalyzeOutButton_released(self):
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.AnalyzeOutput.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.AnalyzeOutput.text())

    def on_AnalyzeButton_released(self):
        self.kcr = KernelConfig.KernelConfig(self.AnalyzeInput.text())
        for file in self.kcr.getItems():
            self.analyze_bands.append(file.split(os.sep)[-2])
        self.BandOrderButton.setEnabled(True)
        self.AlignButton.setEnabled(True)

    """The following definitions check if various bittons are toggled and
    anable the appropriate settings depending on if the buttons are toggled
    or not"""
    def on_PrefixBox_toggled(self):
        if self.PrefixBox.isChecked():
            self.Prefix.setEnabled(True)
        else:
            self.Prefix.setEnabled(False)
    def on_SuffixBox_toggled(self):
        if self.SuffixBox.isChecked():
            self.Suffix.setEnabled(True)
        else:
            self.Suffix.setEnabled(False)

    def on_LightRefBox_toggled(self):
        if self.LightRefBox.isChecked():
            self.LightRef.setEnabled(True)
        else:
            self.LightRef.setEnabled(False)

    def on_AlignmentPercentageBox_toggled(self):
        if self.AlignmentPercentageBox.isChecked():
            self.AlignmentPercentage.setEnabled(True)
        else:
            self.AlignmentPercentage.setEnabled(False)

    def on_BandOrderButton_released(self):
        if self.Bandwindow == None:
            self.Bandwindow = BandOrder(self, self.kcr.getItems())
        self.Bandwindow.resize(385, 205) #resize the window
        self.Bandwindow.exec_()
        self.kcr.orderRigs(order=self.rdr)
        self.kcr.createCameraRig() #create a new camera rig

    def on_AlignButton_released(self):
        """ on_AlignButton_released(Self) is a function definition that
        truncates strings with the appropriate ending depending on which
        buttons are checked
        """
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            cmralign = [QtWidgets.QFileDialog.getOpenFileName(directory=instring.read())[0],]
            instring.truncate(0)
            instring.seek(0)
            instring.write(cmralign[0])
        if self.PrefixBox.isChecked():
            cmralign.append(r'-prefix')
            cmralign.append(self.Prefix.text())
        if self.SuffixBox.isChecked():
            cmralign.append(r'-suffix')
            cmralign.append(self.Suffix.text())
        if self.NoVignettingBox.isChecked():
            cmralign.append(r'-novignetting')
        if self.NoExposureBalanceBox.isChecked():
            cmralign.append(r'-noexposurebalance')
        if self.NoExposureBalanceBox.isChecked():
            cmralign.append(r'-noexposurebalance')
        if self.ForceAlignmentBox.isChecked():
            cmralign.append(r'-realign')
        if self.SeperateFilesBox.isChecked():
            cmralign.append(r'-separatefiles')
        if self.SeperateFoldersBox.isChecked():
            cmralign.append(r'-separatefolders')
        if self.SeperatePagesBox.isChecked():
            cmralign.append(r'-separatepages')
        if self.LightRefBox.isChecked():
            cmralign.append(r'-variablelightref')
            cmralign.append(self.LightRef.text())
        if self.AlignmentPercentageBox.isChecked():
            cmralign.append(r'-alignframepct')
            cmralign.append(self.AlignmentPercentage.text())
        cmralign.append(r'-i')
        cmralign.append(self.AnalyzeInput.text())
        cmralign.append(r'-o')
        cmralign.append(self.AnalyzeOutput.text())
        cmralign.append(r'-c')
        cmralign.append(self.AnalyzeInput.text() + os.sep + "mapir_kernel.camerarig")
        subprocess.call(cmralign)

    """
    DarkCurrents subtract the pxiel noise that exist in a black frame images, still investigating
    if this is necessary, probably not
    """
    # def on_DarkCurrentInputButton_released(self):
    #     with open(modpath + os.sep + "instring.txt", "r+") as instring:
    #         self.DarkCurrentInput.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
    #         instring.truncate(0)
    #         instring.seek(0)
    #         instring.write(self.DarkCurrentInput.text())
    # def on_DarkCurrentOutputButton_released(self):
    #     with open(modpath + os.sep + "instring.txt", "r+") as instring:
    #         self.DarkCurrentOutput.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
    #         instring.truncate(0)
    #         instring.seek(0)
    #         instring.write(self.DarkCurrentOutput.text())
    # def on_DarkCurrentGoButton_released(self):
    #     folder1 = []
    #     folder1.extend(glob.glob(self.DarkCurrentInput.text() + os.sep + "*.tif?"))
    #     for img in folder1:
    #         QtWidgets.QApplication.processEvents()
    #         self.KernelLog.append("Updating " + str(img))
    #         subprocess.call(
    #             [modpath + os.sep + r'exiftool.exe', '-m', r'-overwrite_original', r'-ifd0:blacklevelrepeatdim=2 2',  img], startupinfo=si)
    #
    #     self.KernelLog.append("Finished updating")

    def closeEvent(self, event):
        """ closeEvent defines the actions taken when closing the widget"""
        self.closingPlugin.emit()
        event.accept()
