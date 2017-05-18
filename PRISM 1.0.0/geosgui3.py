# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '.\geossma.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
import sys,inspect
import os, time, datetime as dt
import shutil
import pandas as pd
import threading
import psutil

# Globals
fpath = os.path.dirname(os.path.realpath(__file__))
csvpath = os.path.join(fpath,'UBC97.csv')
rootPath = os.path.dirname(fpath)
rawDataPath = os.path.join(rootPath,'rawData')
print rootPath
out = r"\computed_parms\out"


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class MyPopup(QtGui.QMessageBox):
    def __init__(self, parent=None):
        super(MyPopup, self).__init__(parent)
        QtGui.QMessageBox.__init__(self,parent)

class MonitorThread(QtCore.QThread):
    data_downloaded = QtCore.pyqtSignal(object)
    def __init__(self,threshold,inp,opt):
        QtCore.QThread.__init__(self)
        self.threshold = threshold
        self.inp = inp
        self.opt = opt

    def run(self):
        # Monitor changes in rawData folder
        self.demo = 'DEMO3'
        self.path_to_watch = rawDataPath
        self.before = dict ([(self.f, None) for self.f in os.listdir(self.path_to_watch) if self.demo in self.f])
        print self.before
        state = True
        while state:
            time.sleep (3)
            self.after = dict ([(self.f, None) for self.f in os.listdir(self.path_to_watch) if self.demo in self.f])
            self.added = [self.f for self.f in self.after if not self.f in self.before]
            self.removed = [self.f for self.f in self.before if not self.f in self.after]
            if self.added:
                print "Added: ", ", ".join(self.added)
                self.timeNow = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print "A new event has been recorded at {}. Converting to cosmos format...".format(self.timeNow)

                # Convert new files using k2cosmos
                self.k2cosmos(self.added[0])

                # Run prism for new files
                self.m0,self.m1,self.m2 = self.runPrism(self.threshold,self.inp,self.opt)
                self.data_downloaded.emit((self.m0,self.m1,self.m2))
                time.sleep(0.1)
            if self.removed:
                print "Removed: ", ", ".join(self.removed)
            self.before = self.after


    def k2cosmos(self,file):
        # Convert the new file to cosmos file format
        self.file = file
        self.k2c = os.path.join(rootPath,'K2C')
        os.chdir(self.k2c)
        os.system('start /b K2COSMOS.exe "{}" -n1'.format(os.path.join(rawDataPath,self.file)))

        # Clear input/output prism path
        self.clearInOutDir()

        # Sleep for 5 seconds for conversion
        time.sleep(5)
        self.inPath = os.path.join(fpath,'computed_parms\in')
        for item in os.listdir(self.k2c):
            if item.endswith('.v0'):
                shutil.move(os.path.join(self.k2c,item),os.path.join(self.inPath,item))

        print "Done converting to cosmos format..."

    def clearInOutDir(self):
        self.inPath = os.path.join(fpath,'computed_parms\in')
        self.outPath = os.path.join(fpath,'computed_parms\out')

        try:
            shutil.rmtree(self.inPath)
            shutil.rmtree(self.outPath)
        except Exception as e:
            print e
            pass
        time.sleep(1)
        try:
            os.mkdir(self.inPath)
            os.mkdir(self.outPath)
        except:
            pass

    def computePrism(self):
        print "Computing seismograph parameters..."
        # Change directory to PRISM path and execute java file
        os.chdir(fpath)
        os.system("java -jar prism.jar ./computed_parms/in ./computed_parms/out ./config_files/prism_config.xml")
        print "Done."

    def readResults(self):
        # Read result
        self.outPath = fpath + out
        for i,j,k in os.walk(self.outPath):
            if '\V2' in i:
                self.v2folder = i
                # print self.v2folder

        # Axis mapping
        self.axes = {'C1':'X','C2':'Y','C3':'Z'}

        # Get v2 distance files
        self.vals = []
        for fname in os.listdir(self.v2folder):
            if ".dis.V2" in fname:
                self.v2file = os.path.join(self.v2folder,fname)
                with open(self.v2file,'r') as f:
                    for i,line in enumerate(f):
                        if i == 10:
                            self.l = line.split(',')[2]
                            self.val = abs(float(self.l.split('at')[0].split()[2]))
                            self.unit = self.l.split('at')[0].split()[3]
                            self.axis = self.axes[fname.split('.')[-3]]
                            self.vals.append((self.val,self.axis))
        return self.vals

    def replaceAlarm(self,opt):
        # Replace sound file depending on the choice
        with open("sound.vbs",'r') as f:
            for i,line in enumerate(f):
                if i == 1:
                    splitline = line.split('=')
                    splitline[1] = '"{}"'.format(opt)+'\n'
                    newline = ' = '.join(splitline)
        with open("sound.vbs",'r') as ff:
            allLines = ff.readlines()
            allLines[1] = newline
            # print allLines
        with open("sounds.vbs",'wb') as file:
            file.writelines(allLines)

    def runPrism(self,threshold,inp,opt):
        self.threshold = threshold
        self.inp = inp
        self.opt = opt
        self.computePrism()
    
        while True:
            try:
                self.vals = self.readResults()
                break
            except Exception as e:
                print e
                pass
            else:
                break
        self.replaceAlarm(self.opt)
        self.m1,self.m2,self.m3=self.checkThreshold(self.inp,self.vals,self.threshold)
        return self.m1,self.m2,self.m3

    def checkThreshold(self,inp,values,threshold):
        self.inp = inp
        self.values = values
        self.threshold = threshold
        # print self.values
        # print self.threshold

        # Get individual thresholds
        self.threshX = self.threshold[0]
        self.threshY = self.threshold[1]
        self.threshZ = self.threshold[2]

        # Message
        self.messages = []

        # Check if any of the value is greater than the threshold
        self.hit = None
        for i in range(len(self.values)):
            self.m = "Calculated {} cm at {}-axis or {}% allowable drift.<br>".format(self.values[i][0],self.values[i][1],(self.values[i][0]/self.threshold[i])*100)
            self.messages.append(self.m)
            if self.values[i][0] >= self.threshold[i]:
                self.hit = True
        print self.messages
        if self.hit is True:
            if self.inp.lower() == 'a':
                os.system("start sound.vbs")
            else:
                os.system("start sound.vbs")
                os.system("start alarm.vbs")

            self.message0 = "Event recorded.<br>"
            self.message1 = ' '.join(self.messages)
            self.message2 = "Threshold met. Evacuation recommended."
            # QtGui.QMessageBox.critical(self,"a","a",QtGui.QMessageBox.Ok)
            # QtGui.QMessageBox.about(self,"WARNING!!!","<font size = 40 color = red > {}{}</font><b><font size = 40 color = red > {} </font></b>".format(self.message0,self.message1,self.message2))
            # self.showAlarm(self.message0,self.message1,self.message2)
        else:
            self.message0 = "Event recorded.<br>"
            self.message1 = ' '.join(self.messages)
            self.message2 = "Threshold not met. Evacuation not necessary."
            # self.showNonAlarm(self.message0,self.message1,self.message2)
        return self.message0,self.message1,self.message2



class Ui_MainWindow(QtGui.QMainWindow):
    # For radio
    radio = None

    def __init__(self, parent = None):
        super(Ui_MainWindow, self).__init__(parent)
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)

    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(366, 206)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_2 = QtGui.QLabel(self.centralwidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_2.addWidget(self.label_2)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label = QtGui.QLabel(self.centralwidget)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_3.addWidget(self.label)
        self.spinBox = QtGui.QSpinBox(self.centralwidget)
        self.spinBox.setObjectName(_fromUtf8("spinBox"))
        self.horizontalLayout_3.addWidget(self.spinBox)
        self.horizontalLayout_2.addLayout(self.horizontalLayout_3)
        self.gridLayout.addLayout(self.horizontalLayout_2, 0, 0, 1, 2)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.radioButton_3 = QtGui.QRadioButton(self.centralwidget)
        self.radioButton_3.setObjectName(_fromUtf8("radioButton_3"))
        self.verticalLayout.addWidget(self.radioButton_3)
        self.radioButton = QtGui.QRadioButton(self.centralwidget)
        self.radioButton.setObjectName(_fromUtf8("radioButton"))
        self.verticalLayout.addWidget(self.radioButton)
        self.radioButton_2 = QtGui.QRadioButton(self.centralwidget)
        self.radioButton_2.setObjectName(_fromUtf8("radioButton_2"))
        self.verticalLayout.addWidget(self.radioButton_2)
        self.radioButton_4 = QtGui.QRadioButton(self.centralwidget)
        self.radioButton_4.setObjectName(_fromUtf8("radioButton_4"))
        self.verticalLayout.addWidget(self.radioButton_4)
        self.gridLayout.addLayout(self.verticalLayout, 1, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(self.centralwidget)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 2, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 366, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuAbout = QtGui.QMenu(self.menubar)
        self.menuAbout.setObjectName(_fromUtf8("menuAbout"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.actionHow_To_Use = QtGui.QAction(MainWindow)
        self.actionHow_To_Use.setObjectName(_fromUtf8("actionHow_To_Use"))
        self.actionVersion = QtGui.QAction(MainWindow)
        self.actionVersion.setObjectName(_fromUtf8("actionVersion"))
        self.actionLicense = QtGui.QAction(MainWindow)
        self.actionLicense.setObjectName(_fromUtf8("actionLicense"))
        self.menuAbout.addAction(self.actionHow_To_Use)
        self.menuAbout.addAction(self.actionVersion)
        self.menuAbout.addAction(self.actionLicense)
        self.menubar.addAction(self.menuAbout.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "GEOS SMA", None))
        self.label_2.setText(_translate("MainWindow", "Select audio alert to use:", None))
        self.label.setText(_translate("MainWindow", "Select floor:", None))
        self.radioButton_3.setText(_translate("MainWindow", "Default", None))
        self.radioButton.setText(_translate("MainWindow", "Filipino Advisory", None))
        self.radioButton_2.setText(_translate("MainWindow", "Dr. Lagmay Advisory", None))
        self.radioButton_4.setText(_translate("MainWindow", "GEOS Advisory", None))
        self.menuAbout.setTitle(_translate("MainWindow", "About", None))
        self.actionHow_To_Use.setText(_translate("MainWindow", "How To Use", None))
        self.actionVersion.setText(_translate("MainWindow", "Version", None))
        self.actionLicense.setText(_translate("MainWindow", "License", None))

        # Button attributes
        self.buttonBox.button(QtGui.QDialogButtonBox.Cancel).clicked.connect(self.close)
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).clicked.connect(self.prism)

        # Radio buttons
        QtCore.QObject.connect(self.radioButton_3,QtCore.SIGNAL("toggled(bool)"),self.radioDefault)
        QtCore.QObject.connect(self.radioButton,QtCore.SIGNAL("toggled(bool)"),self.radioFil)
        QtCore.QObject.connect(self.radioButton_2,QtCore.SIGNAL("toggled(bool)"),self.radioMahar)
        QtCore.QObject.connect(self.radioButton_4,QtCore.SIGNAL("toggled(bool)"),self.radioGEOS)


    # App Functions
    def getFloorThreshold(self):
        self.thresholdDf = pd.read_csv(csvpath)
        self.ordinal = ordinal = lambda n: "%d%s" % (n,"tsnrhtdd".upper()[(n/10%10!=1)*(n%10<4)*n%10::4])
        self.floor = ordinal(self.spinBox.value())
        print "{} floor selected...".format(self.floor)
        # Get threshold on floor
        self.floorDf = self.thresholdDf.loc[self.thresholdDf['STORY LEVEL'].str.match("{}".format(self.floor))==True]
        # self.floorDf = self.thresholdDf.loc[self.thresholdDf['STORY LEVEL'].str.contains("{}".format(self.floor))==True]
        self.xThreshold = float(self.floorDf['DISPLACEMENT EQX (mm)'])*.02
        self.yThreshold = float(self.floorDf['DISPLACEMENT EQY (mm)'])*.02
        self.zThreshold = float(self.floorDf['DISPLACEMENT EQX (mm)'])*0.666*.02
        self.threshold = (self.xThreshold,self.yThreshold,self.zThreshold)
        return self.threshold

    # Radios
    def radioDefault(self):
        Ui_MainWindow.radio = 'a'

    def radioFil(self):
        Ui_MainWindow.radio = 'b'

    def radioMahar(self):
        Ui_MainWindow.radio = 'c'

    def radioGEOS(self):
        Ui_MainWindow.radio = 'd'

    def readRadioButton(self):
        self.opt = None
        if Ui_MainWindow.radio == None:
            print "Please choose audio alert to use"
        elif Ui_MainWindow.radio == 'a':
            self.opt = "MandatoryEvacuationSounds.mp3"
        elif Ui_MainWindow.radio == 'b':
            self.opt = "audio1.mp3"
        elif Ui_MainWindow.radio == 'c':
            self.opt = "audio2.mp3"
        elif Ui_MainWindow.radio == 'd':
            self.opt = "audio3.mp3"

        return Ui_MainWindow.radio,self.opt

    def syncFiles(self):
        # Start syncing data files
        os.chdir(os.path.join(rootPath,'Syncme.v1.0'))
        syncPath = os.path.join(rootPath,r'Syncme.v1.0\syncme.bat')
        os.system('start syncme.bat')

    def close(self):
        def kill_proc_tree(pid, including_parent=True):    
            parent = psutil.Process(pid)
            if including_parent:
                parent.kill()
        me = os.getpid()
        kill_proc_tree(me)
        QtGui.qApp.closeAllWindows()

    def test(self):
        self.message1 = "Event recorded. Calculated displacement at {} or {}% allowable drift. Thresholds not met."
        self.message2 = "Evacuation not necessary."
        self.showAlarm(self.message1,self.message2)

    def prism(self):
        self.syncFiles()
        self.inp,self.opt = self.readRadioButton()
        self.threshold = self.getFloorThreshold()
        self.monitorer = MonitorThread(self.threshold,self.inp,self.opt)
        self.monitorer.data_downloaded.connect(self.on_data_ready)
        self.monitorer.start()
        # self.stop_event = threading.Event()
        # self.c_thread = threading.Thread(target=self.monitorNewFiles,args=(self.stop_event,self.threshold,self.inp,self.opt,))
        # self.c_thread.start()
        # self.test()
        # QtGui.qApp.closeAllWindows()

    def on_data_ready(self, data):
        print "dat: ".format(data)
        print data[0]
        print data[1]
        print data[2]
        if 'Threshold met' in data[2]:
            QtGui.QMessageBox.warning(self,"Alert!","<font size = 40 color = red > {}{}</font><b><font size = 40 color = red > {} </font></b>".format(data[0],data[1],data[2]))
        else:
            QtGui.QMessageBox.about(self,"Event","<font size=20 color=green>{}{}</font><b><font size = 20 color = green > {} </font></b>".format(data[0],data[1],data[2]))


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    MainWindow = QtGui.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

