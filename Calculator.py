"""
/***************************************************************************
 Calculator.py

 Class function for calculating Normalized Difference Vegetation Index (NDVI)

 calculator.py is passed a new Q object and class RASTER_CLASS which it then
 modifies and sends back with the calculated NDVI
 ***************************************************************************/


"""

import os
from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic as uic
import cv2
import copy
import numpy as np
RASTER_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'MAPIR_Processing_dockwidget_raster.ui'))


class Calculator(QtWidgets.QDialog, RASTER_CLASS):
    ndvi = None #Normalized Difference Vegetation Index
    def __init__(self, parent=None):
        """Constructor."""
        super(Calculator, self).__init__(parent=parent)
        self.parent = parent

        self.setupUi(self)
        img = cv2.imread(os.path.dirname(__file__) + "/ndvi_400px.jpg") #read in image containing NDVI formula
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)                      #change from BGR to RGB
        h, w = img.shape[:2]                                            #find the height and width
        img2 = QtGui.QImage(img, w, h, w * 3, QtGui.QImage.Format_RGB888) #img2 is for the QtGui
        self.IndexFormula.setPixmap(QtGui.QPixmap.fromImage(img2))
        self.RasterX.addItem(self.parent.KernelBrowserFile.text().split(r'/')[-1] + " @Band1(Red Channel)")
        self.RasterX.addItem(self.parent.KernelBrowserFile.text().split(r'/')[-1] + " @Band2(Green Channel)")
        self.RasterX.addItem(self.parent.KernelBrowserFile.text().split(r'/')[-1] + " @Band3(Blue Channel)")
        self.RasterY.addItem(self.parent.KernelBrowserFile.text().split(r'/')[-1] + " @Band1(Red Channel)")
        self.RasterY.addItem(self.parent.KernelBrowserFile.text().split(r'/')[-1] + " @Band2(Green Channel)")
        self.RasterY.addItem(self.parent.KernelBrowserFile.text().split(r'/')[-1] + " @Band3(Blue Channel)")
        self.RasterZ.hide()
        self.ZLabel.hide()
        # self.RasterZ.addItem(self.parent.KernelBrowserFile.text().split(os.sep)[-1] + " @Band1")
        # self.RasterZ.addItem(self.parent.KernelBrowserFile.text().split(os.sep)[-1] + " @Band2")
        # self.RasterZ.addItem(self.parent.KernelBrowserFile.text().split(os.sep)[-1] + " @Band3")
        self.parent.ViewerCalcButton.setEnabled(False)

    def on_RasterApplyButton_released(self):
        try:
            self.processIndex()
            self.parent.ViewerIndexBox.setEnabled(True)
            if self.parent.LUTwindow == None or not self.parent.LUTwindow.isVisible():
                self.parent.LUTButton.setEnabled(True)
            if self.parent.ViewerIndexBox.isChecked():
                self.parent.applyRaster()
            else:
                self.parent.ViewerIndexBox.setChecked(True)
        except Exception as e:
            print(e)

    def on_RasterOkButton_released(self):
        try:
            self.processIndex()
            self.parent.ViewerIndexBox.setEnabled(True)
            if self.parent.LUTwindow == None or not self.parent.LUTwindow.isVisible():
                self.parent.LUTButton.setEnabled(True)
            if self.parent.ViewerIndexBox.isChecked():
                self.parent.applyRaster()
            else:
                self.parent.ViewerIndexBox.setChecked(True)
            self.parent.ViewerCalcButton.setEnabled(True)

            self.close()
        except Exception as e:
            print(e)

    def on_RasterCloseButton_released(self):
        self.parent.ViewerCalcButton.setEnabled(True)
        self.close()

    def processIndex(self):
        try:
            h, w = self.parent.display_image_original.shape[:2] #get image height and width
            bands = [self.parent.display_image_original[:, :, 0], self.parent.display_image_original[:, :, 1], self.parent.display_image_original[:, :, 2]]
            self.ndvi = self.parent.calculateIndex(bands[self.RasterX.currentIndex()], bands[self.RasterY.currentIndex()])
            self.parent.LUT_Min = copy.deepcopy(np.percentile(self.ndvi, 2)) #LUT_min = 2nd percentile
            self.parent.LUT_Max = copy.deepcopy(np.percentile(self.ndvi, 98)) #LUT_max = 98th percentile
            midpoint = (self.parent.LUT_Max - self.parent.LUT_Min) / 2 #midpoint = (min + max)/2

            steps = midpoint * 1 / 3 #each step is a third of the midpoint

            # legend max is a string representing LUT_Max
            self.parent.legend_max.setText(str(round(self.parent.LUT_Max, 2)))

            #two thirds point occurs at the max minus 1 step
            self.parent.legend_2thirds.setText(str(round(self.parent.LUT_Max - (steps), 2)))

            #one third point occurs at the max minus 2 steps
            self.parent.legend_1third.setText(str(round(self.parent.LUT_Max - (steps * 2), 2)))

            #zero point occurs at 3 steps minus the max
            self.parent.legend_zero.setText(str(round(self.parent.LUT_Max - (steps * 3), 2)))

            #legend min is a string representing LUT_min
            self.parent.legend_min.setText(str(round(self.parent.LUT_Min, 2)))

            #negative two thirds occurs at the max minus 5 steps
            self.parent.legend_neg2thirds.setText(str(round(self.parent.LUT_Max - (steps * 5), 2)))

            #negative one third point occurs at the max minus 4 steps
            self.parent.legend_neg1third.setText(str(round(self.parent.LUT_Max - (steps * 4), 2)))

            #process the events in the widget
            QtWidgets.QApplication.processEvents()

            self.ndvi -= self.ndvi.min() # ndvi = ndvi - min
            self.ndvi /= (self.ndvi.max())# ndvi = ndvi/max

            #at this point our ndvi value is called between 0 and 1, we are going to store it in a uint8 though thus
            #it must be formatted appropriately

            self.ndvi *= 255.0 #scaling ndvi for max value in a uint8 bit variable
            # self.ndvi += 128.0
            self.ndvi = np.around(self.ndvi) #round to zero decimals
            self.ndvi = self.ndvi.astype("uint8") #typecast into uint8
            self.ndvi = cv2.equalizeHist(self.ndvi)  #stretch histogram to improve constrast of image

            #at this point ndvi is now finished being calculated and the Q object has been modified accordingly
            
            # self.ndvi = cv2.cvtColor(self.ndvi, cv2.COLOR_GRAY2RGB)
        except Exception as e:
            print(e)

