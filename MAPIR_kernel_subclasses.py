"""
/***************************************************************************
 MAPIR_kernel_subclasses.py

contains subclasses for processing dockwidget
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
import string
from PyQt5 import QtCore, QtGui, QtWidgets

import PyQt5.uic as uic

import time
import glob


modpath = os.path.dirname(os.path.realpath(__file__))

# print(str(modpath))
if not os.path.exists(modpath + os.sep + "instring.txt"):
    istr = open(modpath + os.sep + "instring.txt", "w")
    istr.close()



"""
The following code is meant to define various constants to be used in kernel classes:

FORM_CLASS represents the main UI class
MODAL_CLASS is the window that forces you to save changes before closing
CAN_CLASS is for the can settings modal window
TIME_CLASS represents the time settings modal window
TRANSFER_CLASS is a modal window for the transfer
ADVANCED_CLASS is a modal window for advanced settings on the camera
MATRIX_CLASS is a modal window for the CT (Color Transform) Matrix

Each of these constants points to the location of the QT ui corresponding to the class
"""
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'MAPIR_Processing_dockwidget_base.ui'))
MODAL_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'MAPIR_Processing_dockwidget_modal.ui'))
CAN_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'MAPIR_Processing_dockwidget_CAN.ui'))
TIME_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'MAPIR_Processing_dockwidget_time.ui'))
# DEL_CLASS, _ = uic.loadUiType(os.path.join(
#     os.path.dirname(__file__), 'MAPIR_Processing_dockwidget_delete.ui'))
TRANSFER_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'MAPIR_Processing_dockwidget_transfer.ui'))
ADVANCED_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'MAPIR_Processing_dockwidget_Advanced.ui'))
MATRIX_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'MAPIR_Processing_dockwidget_matrix.ui'))

class DebayerMatrix(QtWidgets.QDialog, MATRIX_CLASS):
    """DebayerMatrix (Debayer ~ De )

    ***Note: This class has yet to be implemented, it is in the works

        No such thing as Red Blue Green Channels, need to take the image and interpolate through it to get separate RBG channel
        1/4 Red data is actually there, other 75% must be interpolated
        1/4 Blue data is actually there, other 75% must be interpolated
        1/2 Green is actually there, other 50% must be interpolated

    """
    parent = None

    #GAMMA_LIST is a dictionary containing constant values for the Gamma list
    GAMMA_LIST = [{"CCM": [1,0,0,0,1,0,0,0,1], "RGB_OFFSET": [0,0,0], "GAMMA": [1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0]},
                  {"CCM": [1,0,1.402,1,-0.34414,-0.71414,1,1.772,0], "RGB_OFFSET": [0, 0, 0],
                   "GAMMA": [2.3,1.3,2.3,0.3,0.3,0.3,2.3,2.3,1,2,1,2,2,2,1,2,1,2,2,0,2,0,2,0]},
                  {"CCM": [3.2406,-1.5372,-0.498,-0.9689,1.8756,0.0415,0.0557,-0.2040,1.0570 ], "RGB_OFFSET": [0, 0, 0],
                   "GAMMA": [7.0,0.0,6.5,3.0,6.0,8.0,5.5,13.0,5.0,22.0,4.5,38.0,3.5,102.0,2.5,230.0,1.75,422.0,1.25,679.0,0.875,1062.0,0.625,1575.0]},]

    def __init__(self, parent=None):
        """Constructor."""
        super(DebayerMatrix, self).__init__(parent=parent)
        self.parent = parent
        self.setupUi(self)

    def on_ModalSaveButton_released(self):
    """ on_ModalSaveButton_released closes self when the save button is released (clicked)
    """
        self.close()

    def on_ModalCancelButton_released(self):
        """ on_ModalCancelButton_released closes self when the cancel button is released (clicked)
        """
        self.close()


class AdvancedOptions(QtWidgets.QDialog, ADVANCED_CLASS):
    """class AdvancedOptions(QtWidgets.QDialog, ADVANCED_CLASS)
        takes in inputs QtWidgets.QDialog and ADVANCED_CLASS

        sets up the advanced options in the kernel tab
    """
    parent = None

    def __init__(self, parent=None):
        """Constructor."""
        super(AdvancedOptions, self).__init__(parent=parent)
        self.parent = parent

        self.setupUi(self)
        try:
            buf = [0] * 512
            buf[0] = self.parent.SET_REGISTER_READ_REPORT
            buf[1] = eRegister.RG_UNMOUNT_SD_CARD_S.value
            # if self.SDCTUM.text():
            #     buf[2] = int(self.SDCTUM.text()) if 0 <= int(self.SDCTUM.text()) < 255 else 255

            res = self.parent.writeToKernel(buf)[2]
            self.SDCTUM.setText(str(res))

            buf = [0] * 512
            buf[0] = self.parent.SET_REGISTER_READ_REPORT
            buf[1] = eRegister.RG_VIDEO_ON_DELAY.value
            # buf[2] = int(self.VCRD.text()) if 0 <= int(self.VCRD.text()) < 255 else 255

            res = self.parent.writeToKernel(buf)[2]
            self.VCRD.setText(str(res))

            buf = [0] * 512
            buf[0] = self.parent.SET_REGISTER_READ_REPORT
            buf[1] = eRegister.RG_PHOTO_FORMAT.value


            res = self.parent.writeToKernel(buf)[2]
            self.KernelPhotoFormat.setCurrentIndex(int(res))

            buf = [0] * 512
            buf[0] = self.parent.SET_REGISTER_BLOCK_READ_REPORT
            buf[1] = eRegister.RG_MEDIA_FILE_NAME_A.value
            buf[2] = 3
            # buf[3] = ord(self.CustomFilter.text()[0])
            # buf[4] = ord(self.CustomFilter.text()[1])
            # buf[5] = ord(self.CustomFilter.text()[2])
            res = self.parent.writeToKernel(buf)
            filt = chr(res[2]) + chr(res[3]) + chr(res[4])

            self.CustomFilter.setText(str(filt))
            QtWidgets.QApplication.processEvents()
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.parent.KernelLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
            # QtWidgets.QApplication.processEvents()
        finally:
            QtWidgets.QApplication.processEvents()
            self.close()
        # for i in range(1, 256):
        #     self.SDCTUM.addItem(str(i))
        #
        # for j in range(1, 256):
        #     self.VCRD.addItem(str(j))
    # def on_ModalBrowseButton_released(self):
    #     with open(modpath + os.sep + "instring.txt", "r+") as instring:
    #         self.ModalOutputFolder.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
    #         instring.truncate(0)
    #         instring.seek(0)
    #         instring.write(self.ModalOutputFolder.text())
    #         self.ModalSaveButton.setEnabled(True)
    def on_SaveButton_released(self):
        """

        """
        # self.parent.transferoutfolder  = self.ModalOutputFolder.text()
        # self.parent.yestransfer = self.TransferBox.isChecked()
        # self.parent.yesdelete = self.DeleteBox.isChecked()
        # self.parent.selection_made = True
        try:
            # if self.parent.KernelCameraSelect.currentIndex() == 0:
            #     for cam in self.parent.paths:
            #         self.parent.camera = cam
            #         buf = [0] * 512
            #         buf[0] = self.parent.SET_REGISTER_WRITE_REPORT
            #         buf[1] = eRegister.RG_UNMOUNT_SD_CARD_S.value
            #         buf[2] = int(self.SDCTUM.text()) if 0 < int(self.SDCTUM.text()) < 255 else 255
            #
            #         self.parent.writeToKernel(buf)
            #
            #         buf = [0] * 512
            #         buf[0] = self.parent.SET_REGISTER_WRITE_REPORT
            #         buf[1] = eRegister.RG_VIDEO_ON_DELAY.value
            #         buf[2] = int(self.VCRD.text()) if 0 < int(self.VCRD.text()) < 255 else 255
            #
            #         self.parent.writeToKernel(buf)
            #
            #         buf = [0] * 512
            #         buf[0] = self.parent.SET_REGISTER_WRITE_REPORT
            #         buf[1] = eRegister.RG_PHOTO_FORMAT.value
            #         buf[2] = int(self.KernelPhotoFormat.currentIndex())
            #
            #         self.parent.writeToKernel(buf)
            #         buf = [0] * 512
            #         buf[0] = self.SET_REGISTER_BLOCK_WRITE_REPORT
            #         buf[1] = eRegister.RG_MEDIA_FILE_NAME_A.value
            #         buf[2] = 3
            #         buf[3] = ord(self.CustomFilter.text()[0])
            #         buf[4] = ord(self.CustomFilter.text()[1])
            #         buf[5] = ord(self.CustomFilter.text()[2])
            #         res = self.parent.writeToKernel(buf)
            #     self.parent.camera = self.parent.paths[0]
            # else:
            buf = [0] * 512
            buf[0] = self.parent.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_UNMOUNT_SD_CARD_S.value
            val = int(self.SDCTUM.text()) if 0 < int(self.SDCTUM.text()) < 255 else 255
            buf[2] = val

            self.parent.writeToKernel(buf)

            buf = [0] * 512
            buf[0] = self.parent.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_VIDEO_ON_DELAY.value
            val = int(self.VCRD.text()) if 0 < int(self.VCRD.text()) < 255 else 255
            buf[2] = val
            self.parent.writeToKernel(buf)

            buf = [0] * 512
            buf[0] = self.parent.SET_REGISTER_WRITE_REPORT
            buf[1] = eRegister.RG_PHOTO_FORMAT.value
            buf[2] = int(self.KernelPhotoFormat.currentIndex())


            self.parent.writeToKernel(buf)
            buf = [0] * 512
            buf[0] = self.parent.SET_REGISTER_BLOCK_WRITE_REPORT
            buf[1] = eRegister.RG_MEDIA_FILE_NAME_A.value
            buf[2] = 3
            buf[3] = ord(self.CustomFilter.text()[0])
            buf[4] = ord(self.CustomFilter.text()[1])
            buf[5] = ord(self.CustomFilter.text()[2])
            res = self.parent.writeToKernel(buf)
        except Exception as e:
            exc_type, exc_obj,exc_tb = sys.exc_info()
            self.parent.KernelLog.append(str(e) + ' Line: ' + str(exc_tb.tb_lineno))
        finally:

            QtWidgets.QApplication.processEvents()
            self.close()

    def on_CancelButton_released(self):
        # self.parent.yestransfer = False
        # self.parent.yesdelete = False
        # self.parent.selection_made = True
        self.close()

class KernelTransfer(QtWidgets.QDialog, TRANSFER_CLASS):
        """
        class KernelTransfer(QtWidgets.QDialog, TRANSFER_CLASS)

        is the class called to instantiate the kernel transfer tab object
        """
    parent = None

    def __init__(self, parent=None):
        """Constructor."""
        super(KernelTransfer, self).__init__(parent=parent)
        self.parent = parent

        self.setupUi(self)

    def on_ModalBrowseButton_released(self):
        """ on_ModalBrowseButton_released defines the actions taken when the browse button is clicked""""
        with open(modpath + os.sep + "instring.txt", "r+") as instring:
            self.ModalOutputFolder.setText(QtWidgets.QFileDialog.getExistingDirectory(directory=instring.read()))
            instring.truncate(0)
            instring.seek(0)
            instring.write(self.ModalOutputFolder.text())
            self.ModalSaveButton.setEnabled(True)

    def on_DeleteBox_toggled(self):
        """ on_ModalDeleteButton_released defines the actions taken when the delete button is clicked""""
        if self.DeleteBox.isChecked():
            self.ModalSaveButton.setEnabled(True)
        else:
            self.ModalSaveButton.setEnabled(False)
    def on_ModalSaveButton_released(self):
        """ on_ModalSaveButton_released defines the actions taken when the save button is clicked""""

        self.parent.transferoutfolder  = self.ModalOutputFolder.text()
        self.parent.yestransfer = self.TransferBox.isChecked()
        self.parent.yesdelete = self.DeleteBox.isChecked()
        self.parent.selection_made = True
        QtWidgets.QApplication.processEvents()
        self.close()

    def on_ModalCancelButton_released(self):
        self.parent.yestransfer = False
        self.parent.yesdelete = False
        self.parent.selection_made = True
        QtWidgets.QApplication.processEvents()
        self.close()

# class KernelDelete(QtWidgets.QDialog, DEL_CLASS):
#     parent = None
#
#     def __init__(self, parent=None):
#         """Constructor."""
#         super(KernelDelete, self).__init__(parent=parent)
#         self.parent = parent
#
#         self.setupUi(self)
#
#     def on_ModalSaveButton_released(self):
#         for drv in self.parent.driveletters:
#             if os.path.isdir(drv + r":" + os.sep + r"dcim"):
#                 # try:
#                 files = glob.glob(drv + r":" + os.sep + r"dcim/*/*")
#                 for file in files:
#                     os.unlink(file)
#         self.close()
#
#     def on_ModalCancelButton_released(self):
#         self.close()

class KernelModal(QtWidgets.QDialog, MODAL_CLASS):
    """
    class KernalModal(QtWidgets.QDialog, MODAL_CLASS)

    first the submethod calls setupUI to pop up the widgets

    next when the save button is released it records the inputs given by the user for the seconds, minutes, hours, days, and
    weeks

    Finally seconds are converted to minutes, minutes to hours, hours to days, and days to weeks in order to generate a
    string that may be passed to writeToIntervalLine()

    this string represents the time interval that the MAPIR camera will take between taking images as specified by the user
    """
    parent = None

    def __init__(self, parent=None):
        """Constructor."""
        super(KernelModal, self).__init__(parent=parent)
        self.parent = parent

        self.setupUi(self)

    def on_ModalSaveButton_released(self):
        seconds = int(self.SecondsLine.text())
        minutes = int(self.MinutesLine.text())
        hours = int(self.HoursLine.text())
        days = int(self.DaysLine.text())
        weeks = int(self.WeeksLine.text())
        if (seconds / 60) > 1:
            minutes += int(seconds / 60)
            seconds = seconds % 60
        if (minutes / 60) > 1:
            hours += int(minutes / 60)
            minutes = minutes % 60
        if (hours / 24) > 1:
            days += int(hours / 24)
            hours = hours % 24
        if (days / 7) > 1:
            weeks += int(days / 7)
            days = days % 7
        self.parent.seconds = seconds
        self.parent.minutes = minutes
        self.parent.hours = hours
        self.parent.days = days
        self.parent.weeks = weeks
        self.parent.writeToIntervalLine()

        # weeks /= 604800
        # days /= 86400
        # hours /= 3600
        # minutes /= 60
        # seconds += minutes + hours + days + weeks
        #
        # MAPIR_ProcessingDockWidget.interval = int(seconds)
        self.close()

    def on_ModalCancelButton_released(self):
        self.close()

class KernelCAN(QtWidgets.QDialog, CAN_CLASS):
    """
    class KernalCan

    sets the CAN bus for kernel time, it is a data bus used in vehicles

    """
    parent = None

    def __init__(self, parent=None):
        """Constructor."""
        super(KernelCAN, self).__init__(parent=parent)
        self.parent = parent

        self.setupUi(self)
        buf = [0] * 512
        buf[0] = self.parent.SET_REGIST ER_READ_REPORT
        buf[1] = eRegister.RG_CAN_NODE_ID.value
        nodeid = self.parent.writeToKernel(buf)[2]
        # buf[2] = nodeid
        self.KernelNodeID.setText(str(nodeid))
        # self.parent.writeToKernel(buf)
        buf = [0] * 512
        buf[0] = self.parent.SET_REGISTER_BLOCK_READ_REPORT
        buf[1] = eRegister.RG_CAN_BIT_RATE_1.value
        buf[2] = 2
        bitrate = self.parent.writeToKernel(buf)[2:4]
        bitval = ((bitrate[0] << 8) & 0xff00) | bitrate[1]
        self.KernelBitRate.setCurrentIndex(self.KernelBitRate.findText(str(bitval)))
        # bit1 = (bitrate >> 8) & 0xff
        # bit2 = bitrate & 0xff
        # buf[3] = bit1
        # buf[4] = bit2

        buf = [0] * 512
        buf[0] = self.parent.SET_REGISTER_BLOCK_READ_REPORT
        buf[1] = eRegister.RG_CAN_SAMPLE_POINT_1.value
        buf[2] = 2
        samplepoint = self.parent.writeToKernel(buf)[2:4]


        sample = ((samplepoint[0] << 8) & 0xff00) | samplepoint[1]
        self.KernelSamplePoint.setText(str(sample))
    def on_ModalSaveButton_released(self):
        buf = [0] * 512
        buf[0] = self.parent.SET_REGISTER_WRITE_REPORT
        buf[1] = eRegister.RG_CAN_NODE_ID.value
        nodeid = int(self.KernelNodeID.text())
        buf[2] = nodeid

        self.parent.writeToKernel(buf)
        buf = [0] * 512
        buf[0] = self.parent.SET_REGISTER_BLOCK_WRITE_REPORT
        buf[1] = eRegister.RG_CAN_BIT_RATE_1.value
        buf[2] = 2
        bitrate = int(self.KernelBitRate.currentText())
        bit1 = (bitrate >> 8) & 0xff
        bit2 = bitrate & 0xff
        buf[3] = bit1
        buf[4] = bit2

        self.parent.writeToKernel(buf)
        buf = [0] * 512
        buf[0] = self.parent.SET_REGISTER_BLOCK_WRITE_REPORT
        buf[1] = eRegister.RG_CAN_SAMPLE_POINT_1.value
        buf[2] = 2
        samplepoint = int(self.KernelSamplePoint.text())
        sample1 = (samplepoint >> 8) & 0xff
        sample2 = samplepoint & 0xff
        buf[3] = sample1
        buf[4] = sample2

        self.parent.writeToKernel(buf)
        self.close()

    def on_ModalCancelButton_released(self):
        self.close()

class KernelTime(QtWidgets.QDialog, TIME_CLASS):
    """
    class KernelTime(QtWidgets.QDialog, TIME_CLASS)

    takes in actual UTC (Coordinated Universal Time), GPS, or Computer Time
    reads the time from the kernal's internal clock

    Syncs the internal clock to whichever of the three times was selected

    """
    parent = None
    timer = QtCore.QTimer()
    BUFF_LEN = 512 #length of the buffer


    '''

       The following SET commands represent odd integers that correspond to the buffer values which tell the kernel
       camera which operation to take

       e.g. SET_EVENT_REPORT tells the kernel camera to conduct operation 1

       the reason that these integers are odd is because they are flipping the next bit on
    '''

    SET_EVENT_REPORT = 1
    SET_COMMAND_REPORT = 3
    SET_REGISTER_WRITE_REPORT = 5
    SET_REGISTER_BLOCK_WRITE_REPORT = 7
    SET_REGISTER_READ_REPORT = 9
    SET_REGISTER_BLOCK_READ_REPORT = 11
    SET_CAMERA = 13
    def __init__(self, parent=None):
        """Constructor."""
        super(KernelTime, self).__init__(parent=parent)
        self.parent = parent

        self.setupUi(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1)
    def on_ModalSaveButton_released(self):
        self.timer.stop()

        # if self.parent.KernelCameraSelect.currentIndex() == 0:
        #     for p in self.parent.paths:
        #         self.parent.camera = p
        #
        #         self.adjustRTC()
        #     self.parent.camera = self.parent.paths[0]
        # else:
        self.adjustRTC()


    #to create the time string you have to follow boolean logic take the first 8 bits, then the next 8 bits, etc

    def adjustRTC(self):
        buf = [0] * 512

        buf[0] = self.SET_REGISTER_BLOCK_WRITE_REPORT
        buf[1] = eRegister.RG_REALTIME_CLOCK.value
        buf[2] = 8
        t = QtCore.QDateTime.toMSecsSinceEpoch(self.KernelReferenceTime.dateTime())
        buf[3] = t & 0xff
        buf[4] = (t >> 8) & 0xff
        buf[5] = (t >> 16) & 0xff
        buf[6] = (t >> 24) & 0xff
        buf[7] = (t >> 32) & 0xff
        buf[8] = (t >> 40) & 0xff
        buf[9] = (t >> 48) & 0xff
        buf[10] = (t >> 54) & 0xff
        self.parent.writeToKernel(buf)
        buf = [0] * 512

        buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
        buf[1] = eRegister.RG_REALTIME_CLOCK.value
        buf[2] = 8
        r = self.parent.writeToKernel(buf)[2:11]
        val = r[0] | (r[1] << 8) | (r[2] << 16) | (r[3] << 24) | (r[4] << 32) | (r[5] << 40) | (r[6] << 48) | (
        r[7] << 56)

        offset = QtCore.QDateTime.currentMSecsSinceEpoch() - val

        while offset > 0.01:
            if self.KernelTimeSelect.currentIndex() == 0:
                buf[0] = self.SET_REGISTER_BLOCK_WRITE_REPORT
                buf[1] = eRegister.RG_REALTIME_CLOCK.value
                buf[2] = 8
                t = QtCore.QDateTime.toMSecsSinceEpoch(QtCore.QDateTime.currentDateTimeUtc().addSecs(18).addMSecs(offset))
                buf[3] = t & 0xff
                buf[4] = (t >> 8) & 0xff
                buf[5] = (t >> 16) & 0xff
                buf[6] = (t >> 24) & 0xff
                buf[7] = (t >> 32) & 0xff
                buf[8] = (t >> 40) & 0xff
                buf[9] = (t >> 48) & 0xff
                buf[10] = (t >> 54) & 0xff
                self.parent.writeToKernel(buf)
                buf = [0] * 512

                buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
                buf[1] = eRegister.RG_REALTIME_CLOCK.value
                buf[2] = 8
                r = self.parent.writeToKernel(buf)[2:11]
                val = r[0] | (r[1] << 8) | (r[2] << 16) | (r[3] << 24) | (r[4] << 32) | (r[5] << 40) | (r[6] << 48) | (
                    r[7] << 56)

                offset = QtCore.QDateTime.currentMSecsSinceEpoch() - val
            elif self.KernelTimeSelect.currentIndex() == 1:
                buf[0] = self.SET_REGISTER_BLOCK_WRITE_REPORT
                buf[1] = eRegister.RG_REALTIME_CLOCK.value
                buf[2] = 8
                t = QtCore.QDateTime.toMSecsSinceEpoch(QtCore.QDateTime.currentDateTimeUtc().addMSecs(offset))
                buf[3] = t & 0xff
                buf[4] = (t >> 8) & 0xff
                buf[5] = (t >> 16) & 0xff
                buf[6] = (t >> 24) & 0xff
                buf[7] = (t >> 32) & 0xff
                buf[8] = (t >> 40) & 0xff
                buf[9] = (t >> 48) & 0xff
                buf[10] = (t >> 54) & 0xff
                self.parent.writeToKernel(buf)
                buf = [0] * 512

                buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
                buf[1] = eRegister.RG_REALTIME_CLOCK.value
                buf[2] = 8
                r = self.parent.writeToKernel(buf)[2:11]
                val = r[0] | (r[1] << 8) | (r[2] << 16) | (r[3] << 24) | (r[4] << 32) | (r[5] << 40) | (r[6] << 48) | (
                    r[7] << 56)

                offset = QtCore.QDateTime.currentMSecsSinceEpoch() - val
            else:

                buf[0] = self.SET_REGISTER_BLOCK_WRITE_REPORT
                buf[1] = eRegister.RG_REALTIME_CLOCK.value
                buf[2] = 8
                t = QtCore.QDateTime.toMSecsSinceEpoch(QtCore.QDateTime.currentDateTime().addMSecs(offset))
                buf[3] = t & 0xff
                buf[4] = (t >> 8) & 0xff
                buf[5] = (t >> 16) & 0xff
                buf[6] = (t >> 24) & 0xff
                buf[7] = (t >> 32) & 0xff
                buf[8] = (t >> 40) & 0xff
                buf[9] = (t >> 48) & 0xff
                buf[10] = (t >> 54) & 0xff
                self.parent.writeToKernel(buf)
                buf = [0] * 512

                buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
                buf[1] = eRegister.RG_REALTIME_CLOCK.value
                buf[2] = 8
                r = self.parent.writeToKernel(buf)[2:11]
                val = r[0] | (r[1] << 8) | (r[2] << 16) | (r[3] << 24) | (r[4] << 32) | (r[5] << 40) | (r[6] << 48) | (
                    r[7] << 56)

                offset = QtCore.QDateTime.currentMSecsSinceEpoch() - val

        self.close()

    def on_ModalCancelButton_released(self):
        self.timer.stop()
        self.close()

    def tick(self):
        buf = [0] * 512

        buf[0] = self.SET_REGISTER_BLOCK_READ_REPORT
        buf[1] = eRegister.RG_REALTIME_CLOCK.value
        buf[2] = 8
        r = self.parent.writeToKernel(buf)[2:11]
        val = r[0] | (r[1] << 8) | (r[2] << 16) | (r[3] << 24) | (r[4] << 32) | (r[5] << 40) | (r[6] << 48) | (r[7] << 56)
        self.KernelCameraTime.setDateTime(QtCore.QDateTime.fromMSecsSinceEpoch(val))
        if self.KernelTimeSelect.currentIndex() == 0:
            self.KernelReferenceTime.setDateTime(QtCore.QDateTime.currentDateTimeUtc().addSecs(18))
        elif self.KernelTimeSelect.currentIndex() == 1:
            self.KernelReferenceTime.setDateTime(QtCore.QDateTime.currentDateTimeUtc())
        else:
            self.KernelReferenceTime.setDateTime(QtCore.QDateTime.currentDateTime())

class tPoll:
    """ class tPoll sets variables request, code, len equal to zero, it sets values equal to an empty list

    it is setting up a timer for the KernelTime class
    """
    def __init__(self):
        request = 0
        code = 0
        len = 0 #Len can also store the value depending on the code given
        values = []
