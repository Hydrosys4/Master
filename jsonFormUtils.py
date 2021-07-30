#!/usr/bin/env python3
 
import json
import logging
import os
from datetime import datetime,date,timedelta



 
class utils():

    def __init__(self,itemname):
        self.logger = logging.getLogger("hydrosys4."+__name__+"."+itemname)
        self.templatepath="templates"
        self.databasepath="database"
        self.databasedefaultpath=os.path.join(self.databasepath, "default")
        self.itemname=itemname
        self.fileNameList=self.listtemplatefiles()



    def listtemplatefiles(self):
        fileNameList=[]
        for file in os.listdir(self.templatepath):
            if file.endswith(".json"):
                fileNameList.append(file)
        return fileNameList

    def readJsonFormFilePlusValues(self):
        jsonschema, itemslist = self.readJsonFormFile()
        datadict=self.readDataFile()
        jsonschema["value"]=datadict
        return jsonschema, itemslist



    def readJsonFormFile(self):

        jsonschema={}
        itemlist=[]
        # create the path
        filename=self.itemname + ".json"
        # check if file exist
        if filename not in self.fileNameList:
            print("template file not found, abort")
            self.logger.error("template file not found, abort")
            return jsonschema, itemlist

        fullpath=os.path.join(self.templatepath, filename)

        # this form uses the template from JSONform
        
        try:
            # Opening JSON file
            f = open(fullpath)
            print("file open" , f)
            
            # returns JSON object as 
            # a dictionary
            jsonschema = json.load(f)
            
            # Closing file
            f.close()
        except:
            print("problem opening the form schema file")
            self.logger.error("problem opening the form schema file")

        if ("schema" in jsonschema):
            for item in jsonschema["schema"]:
                #print (item)
                itemlist.append(item)


        return jsonschema, itemlist


    def readDataFile(self):
        datadict={}
        # create the path
        filename=self.itemname + ".txt"

        fullpath=os.path.join(self.databasepath, filename)

        #if os.path.isfile(fullpath):

        try:
            with open(fullpath) as json_file:
                datadict = json.load(json_file)
            #print (datadict , "aaa")
        except:
            print("problem opening the Data file, try with the default setting")
            self.logger.error("problem opening the Data file, try with the default setting")
            # default path
            fullpath=os.path.join(self.databasedefaultpath, "def"+filename)
            try:
                with open(fullpath) as json_file:
                    datadict = json.load(json_file)
                # Save the file
                #print (datadict , "bbb")
                self.saveDataFile(datadict)
                
            except:
                print("problem opening the default Data file")
                self.logger.error("problem opening the Default Data file")

        #print(datadict , "*************************************************************************+")
        return datadict

    def saveDataFile(self,datadict):
        # create the path
        isok=False
        if datadict:

            filename=self.itemname + ".txt"

            fullpath=os.path.join(self.databasepath, filename)

            try:
                with open(fullpath,'w') as outfile: 
                    json.dump(datadict, outfile)
                isok=True              
            except:
                print("problem saving the data file")
                self.logger.error("problem saving the Data file")   

        return isok



    
if __name__ == '__main__':
    
    mycalss=utils('HC12form')
    datadict=mycalss.readDataFile()
    print (datadict)
    #datadict=mycalss.saveDataFile(datadict)


    """
    AT+Cxxx: Change wireless communication channel, selectable from 001 to 127 (for wireless channels exceeding 100, the communication distance cannot be guaranteed). The default value for the wireless channel is 001, with a working frequency of 433.4MHz. The channel stepping is 400KHz, and the working frequency of channel 

    AT+FUx:  Change the serial port transparent transmission mode of the module. Four modes are available, namely FU1, FU2, FU3, and FU4. Only when the serial port speed, channel, and transparent transmission mode of two modules is set to be the same,can normal wireless communications occur. For more details, please see the abovesection “Wireless Serial Port Transparent Transmission”.
    FU4 mode is useful for maximum range, up to 1.8km. Only a single baud rate of 1200bps is supported, with the in the air baud rate reduced to 500bps for improved communication distance. This mode can only be used for small amounts ofdata (each packet should be 60 bytes or less), and the time interval between sending packets must not be too short (preferably no less than 2 seconds) in order to prevent loss of data.

    AT+Px:   Set the transmitting power of the module, with x selectable from 1 to 8, default 8.
    
    """ 


