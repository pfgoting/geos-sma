# -*- coding: utf-8 -*-
"""
Created on Sat Mar 18 18:54:56 2017

@author: Cloud
"""

import os, time, datetime as dt
import shutil
from threading import Thread
#fpath = r"C:\Users\Cloud\Desktop\testing\PRISM 1.0.0"
#fpath = raw_input("Enter your PRISM folder path: ")
fpath = os.path.dirname(os.path.realpath(__file__))
rootPath = os.path.dirname(fpath)
rawDataPath = os.path.join(rootPath,'rawData')
print rootPath
out = r"\computed_parms\out"

def getUserInputs():
    # Enter displacement threshold
    threshold = raw_input("Enter displacement threshold to be used (in centimeters): ")

    # Choose audio
    print "Choose audio alert: "
    print "a. Siren  b. Tagalog  c. Dr. Lagmay  d. GEOS"
    inp = raw_input(">> ")
    if inp.lower() == 'a':
        opt = "MandatoryEvacuationSounds.mp3"
    elif inp.lower() == 'b':
        opt = "audio1.mp3"
    elif inp.lower() == 'c':
        opt = "audio2.mp3"
    elif inp.lower() == 'd':
        opt = "audio3.mp3"
    return threshold,inp,opt

def clearInOutDir():
    inPath = os.path.join(fpath,'computed_parms\in')
    outPath = os.path.join(fpath,'computed_parms\out')

    try:
        shutil.rmtree(inPath)
        shutil.rmtree(outPath)
    except Exception as e:
        print e
        pass
    time.sleep(1)
    try:
        os.mkdir(inPath)
        os.mkdir(outPath)
    except:
        pass

def computePrism():
    print "Computing seismograph parameters..."
    # Change directory to PRISM path and execute java file
    os.chdir(fpath)
    os.system("java -jar prism.jar ./computed_parms/in ./computed_parms/out ./config_files/prism_config.xml")

def readResults():
    # Read result
    outPath = fpath + out
    for i,j,k in os.walk(outPath):
        print i
        if '\V2' in i:
            v2folder = i
            print v2folder

    # Axis mapping
    axes = {'C1':'X','C2':'Y','C3':'Z'}

    # Get v2 distance files
    vals = []
    for fname in os.listdir(v2folder):
        if ".dis.V2" in fname:
            v2file = os.path.join(v2folder,fname)
            with open(v2file,'r') as f:
                for i,line in enumerate(f):
                    if i == 10:
                        l = line.split(',')[2]
                        val = abs(float(l.split('at')[0].split()[2]))
                        unit = l.split('at')[0].split()[3]
                        axis = axes[fname.split('.')[-3]]
                        vals.append((val,axis))
    return vals

def replaceAlarm(opt):
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

def checkThreshold(inp,values,threshold):
    # Check if any of the value is greater than the threshold
    hit = None
    threshold = float(threshold)
    for value in values:
        print "The displacement is {} cm at {}-axis. It is {}% of the maximum recommended drift of this floor.".format(value[0],value[1],(value[0]/threshold)*100)
        if value[0] >= threshold:
            hit = True

    if hit is True:
        if inp.lower() == 'a':
            os.system("start sound.vbs")
        else:
            os.system("start sound.vbs")
            os.system("start alarm.vbs")
        print "A seismograph has recorded a value greater than the threshold. Please evacuate immediately!\n"
    else:
        print "Event recorded but no threshold has been met. \n"

def runPrism(threshold,inp,opt):
    computePrism()
#    time.sleep(1)
    
    while True:
        try:
            vals = readResults()
            break
        except Exception as e:
            print e
            pass
        else:
            break
    replaceAlarm(opt)
    checkThreshold(inp,vals,threshold)

def syncFiles():
    # Start syncing data files
    os.chdir(os.path.join(rootPath,'Syncme.v1.0'))
    syncPath = os.path.join(rootPath,r'Syncme.v1.0\syncme.bat')
#    print syncPath
    os.system('start syncme.bat')

def monitorNewFiles(threshold,inp,opt):
    # Monitor changes in rawData folder
    path_to_watch = rawDataPath
    before = dict ([(f, None) for f in os.listdir(path_to_watch) if '.evt' in f])
    print before
    while 1:
        time.sleep (3)
        after = dict ([(f, None) for f in os.listdir(path_to_watch) if '.evt' in f])
        added = [f for f in after if not f in before]
        removed = [f for f in before if not f in after]
        if added:
            print "Added: ", ", ".join(added)
            timeNow = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print "A new event has been recorded at {}. Converting to cosmos format...".format(timeNow)

            # Convert new files using k2cosmos
            k2cosmos(added[0])

            # Run prism for new files
            runPrism(threshold,inp,opt)
        if removed:
            print "Removed: ", ", ".join(removed)
        before = after

def k2cosmos(file):
    # Convert the new file to cosmos file format
    k2c = os.path.join(rootPath,'K2C')
    os.chdir(k2c)
    os.system('start K2COSMOS.exe "{}" -n1'.format(os.path.join(rawDataPath,file)))

    # Clear input/output prism path
    clearInOutDir()

    # Sleep for 5 seconds for conversion
    time.sleep(5)
    inPath = os.path.join(fpath,'computed_parms\in')
    for item in os.listdir(k2c):
        if item.endswith('.v0'):
            shutil.move(os.path.join(k2c,item),os.path.join(inPath,item))

    print "Done converting to cosmos format..."


def main():
    syncFiles()
    threshold,inp,opt = getUserInputs()
    monitorNewFiles(threshold,inp,opt)
    
    # For debugging
    # runPrism(threshold,inp,opt)


# def main():
    # sync = Thread(target=syncFiles)
    # monit = monitorNewFiles()
    # runPrism = Thread(target=prism)

    # Start threads
    # runPrism.start()
    # sync.start()
    # monit.start()



if __name__ == "__main__":
    main()

