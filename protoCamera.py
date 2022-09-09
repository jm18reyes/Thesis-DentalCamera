import RPi.GPIO as GPIO
from picamera import PiCamera
from time import sleep
from datetime import datetime
from gpiozero import Button
from threading import Thread
from subprocess import call
import os
import fnmatch
import zipfile
import shutil
import re
import glob
from gpiozero import LED

#Edit Values Here -------------------------
cameraButton = 22 #22
optionButton = 26 #26
sourceDirectoryPath = '/home/pi/Desktop/' #directory of the folder
destinationDirectory = '/home/pi/Pictures/Storage/'#path of the file
maxNumberJpg = 3 #edit value here. Example maxNumberJpg =3 (1. front, 2. upper portion, 3. lower portion)
#------------------------------------------

sequenceOfImage = 0
imgLabel = ['_front','_upper','_lower']
Button.was_held = False
sendFlag = 0

DATA = LED(25)
CLOCK = LED(7)
LATCH = LED(8)

JPEG = '.jpg'
ZIP = '.zip'
TXT = '.txt'

OFF_LED = 10
binarySevenSeg = ((0,0,1,1,1,1,1,1),(0,0,0,0,0,1,1,0),(0,1,0,1,1,0,1,1),(0,1,0,0,1,1,1,1),(0,1,1,0,0,1,1,0),(0,1,1,0,1,1,0,1),(0,1,1,1,1,1,0,1),(0,0,0,0,0,1,1,1),(0,1,1,1,1,1,1,1),(0,1,1,0,0,1,1,1),(0,0,0,0,0,0,0,0))
animation = ((0,0,0,0,0,0,0,1),(0,0,0,0,0,0,1,0),(0,0,0,0,0,1,0,0),(0,0,0,0,1,0,0,0),(0,0,0,1,0,0,0,0),(0,0,1,0,0,0,0,0),(0,0,0,0,0,0,0,1))
sendSuccessBinary = [1,1,1,0,1,1,1,0]
sendingFailedBinary = [1,1,1,1,0,0,0,1]
startBinary = [1,0,0,0,0,0,0,0]

def main():
    print("Program starting...")
    startNotice()
    camera = Button(cameraButton,pull_up=False)
    option = Button(optionButton,pull_up=False)

    while True:
        camera.when_pressed = singleCapture
        option.when_pressed = optionReleased
        
def optionReleased():
    print("Option was pressed")
    deleteLastImage()
    

    
def deleteLastImage():
    print("Delete button was pressed")
    listOfImages = getFileNames(JPEG)
    totalImages = countJPGFiles()
    if(totalImages > 0):
        latestImage = max(listOfImages, key=os.path.getmtime)
        print(latestImage)
        os.remove(latestImage)
        updateSevenSegCount()
    else:
        print("No image Existing")

def getLatestZip(): 
    latestZipFile = ''
    listOfZipFiles = getFileNames(ZIP)
    totalZipFiles = countZipFiles()
    if(totalZipFiles > 0):
        latestZipFile = max(listOfZipFiles, key=os.path.getmtime)
        print(latestZipFile)
        return latestZipFile
    else:
        print("No Zipfile Existing")

    

def singleCapture():
    print("Camera was pressed")
    if((countJPGFiles()+1)==4):
        checkBatchContent()
        sendingAnimation()
        sendZipFiles()
        print("send flag: "+str(sendFlag))
        checkIfNotSent()
    else:
        digiCam = PiCamera()
        digiCam.start_preview()
        sleep(3)
        digiCam.capture(saveInThisDirectory(JPEG))
        digiCam.stop_preview()
        digiCam.close()
    
        updateSevenSegCount()
        printFileLists(JPEG)
    
def saveInThisDirectory(fileFormat):
    fileDirectory = sourceDirectoryPath + createNewFileName() + fileFormat
    print("saving: "+fileDirectory)
    return fileDirectory

def createNewFileName():
    global sequenceOfImage
    sequenceOfImage = countJPGFiles()
    if(sequenceOfImage <= maxNumberJpg):
        fileName = datetime.now().strftime("%Y_%m_%d-%H_%M_%S_%p")
        fileName = fileName+imgLabel[sequenceOfImage]
    else:
        fileName = datetime.now().strftime("%Y_%m_%d-%H_%M_%S_%p")
    return fileName

def updateSevenSegCount():
    numPhoto = countJPGFiles()
    if(numPhoto <= maxNumberJpg and numPhoto >= 0):
        print(numPhoto)
        loadBinaryValues(numPhoto)
    else:
        print("Out of range")

def getFileNames(fileExtension):
    if(fileExtension == JPEG):
        fileList = [ f for f in os.listdir( os.curdir ) if re.match(r'.*\.jpg',f)]
    elif(fileExtension == ZIP):
        fileList = [ f for f in os.listdir( os.curdir ) if re.match(r'.*\.zip',f)]
    elif(fileExtension == TXT):
        fileList = [ f for f in os.listdir( os.curdir ) if re.match(r'.*\.txt',f)]

    else:
        print("File extension not known")
    return fileList

def countJPGFiles():
    numOfJPG = len(fnmatch.filter(os.listdir(os.curdir), '*.jpg'))
    return numOfJPG

def countZipFiles():
    numOfZip = len(fnmatch.filter(os.listdir(os.curdir), '*.zip'))
    return numOfZip

def countTXTFiles():
    numOfTxt = len(fnmatch.filter(os.listdir(os.curdir), '*.txt'))
    return numOfTxt

def printFileLists(fileExtension):
    if(fileExtension == JPEG):
        imgList = getFileNames(JPEG)
        for i in imgList:
            print(i)
    elif(fileExtension == ZIP):
        zipList = getFileNames(ZIP)
        for j in zipList:
            print(j)
    else:
        print("File extension not known")

def checkBatchContent():
    numberOfJpg = len(fnmatch.filter(os.listdir(os.curdir), '*.jpg'))
    print("Number of JPG: "+str(numberOfJpg))
    if(numberOfJpg >= maxNumberJpg):
        compressBatch(getFileNames(JPEG))
        moveFiles(JPEG)
        updateSevenSegCount()
        
def compressBatch(fList):
    number = str(1+countZipFiles())
    compressedFileName = str('zippy'+number+ZIP)
    with zipfile.ZipFile(compressedFileName, 'w') as zipF:
        for file in fList:
            zipF.write(file, compress_type=zipfile.ZIP_DEFLATED)
    print("Zipped: "+compressedFileName)
    
    


def sendZipFiles():
    print("Entered here in sending function")
    
    global sendFlag
    fileName = getLatestZip()
    print("Sending...")
    sleep(5)
    call('/usr/bin/sshpass -p "memorablepass98" /usr/bin/scp -o ConnectTimeout=5 -o StrictHostKeyChecking=no '+sourceDirectoryPath+fileName+ ' cloney@192.168.1.49:C:/Users/cloney/Desktop/THESIS/DesktopApp/Images && touch /home/pi/Desktop/sentIndicator.txt',shell=True)

    if(countTXTFiles() > 0):
        
        sendSuccessNotice()
        sendFlag = 1
        print("flag: "+str(sendFlag))
        sleep(1)
        moveFiles(ZIP)
    else:
        print("Not sent error")
        
    moveFiles(TXT)
def checkIfNotSent():
    global sendFlag
    if(sendFlag == 0):
        sendFailedNotice()
    else:
        sendFlag = 0

def moveFiles(fileExtension):
    if(fileExtension == JPEG):
        usedPictures = getFileNames(JPEG)
        for i in usedPictures:
            shutil.move(sourceDirectoryPath+i,destinationDirectory+i)
    elif(fileExtension == ZIP):
        usedZipFiles = getFileNames(ZIP)
        for j in usedZipFiles:
            shutil.move(sourceDirectoryPath+j,destinationDirectory+j)
    elif(fileExtension == TXT):
        usedTXTFiles = getFileNames(TXT)
        for k in usedTXTFiles:
            shutil.move(sourceDirectoryPath+k,destinationDirectory+k)


def loadBinaryValues(value):
    for i in binarySevenSeg[value]:
        
        if(i == 0):
            DATA.off()
        elif(i == 1):
            DATA.on()
        CLOCK.off()
        sleep(0.001)
        CLOCK.on()
    displayCount()

def displayCount():
    LATCH.on()
    sleep(0.001)
    LATCH.off()

def sendingAnimation():
    for x in range(0,3):
        for i in range(0,len(animation)):
            for j in animation[i]:
                if(j == 0):
                    DATA.off()
                elif(j == 1):
                    DATA.on()
                CLOCK.off()
                sleep(0.01)
                CLOCK.on()
            displayCount()
    
    loadBinaryValues(10)

def sendSuccessNotice():
    print("Sent!")
    for i in sendSuccessBinary:
        if(i == 0):
            DATA.off()
        elif(i == 1):
            DATA.on()
        CLOCK.off()
        sleep(0.001)
        CLOCK.on()
    displayCount()

def sendFailedNotice():
    print("Sending Failed. Will try again later")
    for i in sendingFailedBinary:
        if(i == 0):
            DATA.off()
        elif(i == 1):
            DATA.on()
        CLOCK.off()
        sleep(0.001)
        CLOCK.on()
    displayCount()

def startNotice():
    print("Device is activated")
    for i in startBinary:
        if(i == 0):
            DATA.off()
        elif(i == 1):
            DATA.on()
        CLOCK.off()
        sleep(0.001)
        CLOCK.on()
    displayCount()
    


main()




