# -*- coding: utf-8 -*-

from __future__ import print_function
import shutil
import logging
import re
import os
import os.path
import sys
import string
from datetime import datetime,date,timedelta
import filestoragemod
import copy


# ///////////////// -- GLOBAL VARIABLES AND INIZIALIZATION --- //////////////////////////////////////////

DATABASEPATH=filestoragemod.DATABASEPATH  # by default this variable is "database"
CONFIGDOWNLOADPATH="download/configdownload"
ZIPCONFIGDOWNLOADPATH="download/zipconfig"
logger = logging.getLogger("hydrosys4."+__name__)




def folderfilelist(basefolder, folder , filetype):

	folderpath=os.path.join(basefolder, folder) #database path

	# control if the folder exist otherwise create it
	if not os.path.exists(folderpath):
		os.makedirs(folderpath)
		print(" folder has been created")
	
	filelist=[]
	sortedlist=sorted([f for f in os.listdir(folderpath) if os.path.isfile(os.path.join(folderpath, f))])
	sortedlist.reverse()
	
	# select file with given extension"
	for files in sortedlist:
		if (files.endswith(filetype)):
			tempdict={}
			tempdict["filename"]=files
			tempdict["relativepath"]=folder
			filelist.append(tempdict)

	return filelist

def copyfiles(basefolder, filelist, relativedstfolder):
	for filedata in filelist:
		fullsrcfolder=os.path.join(basefolder, filedata["relativepath"])		
		src=os.path.join(fullsrcfolder, filedata["filename"])		
		dstfilename=filedata["filename"]
		fulldstfolder=os.path.join(basefolder, relativedstfolder)
		dst=os.path.join(fulldstfolder,  dstfilename)
		print("COPY, source = " , src, "destination =" , dst)
		try:
			shutil.copyfile(src, dst)
			answer="ready"
		except:
			answer="problem copying file"


def deletefilesinfolder(basefolder, relativefolder):
	fullfolderpath=os.path.join(basefolder, relativefolder)
	# control if the folder exist otherwise create it
	if not os.path.exists(fullfolderpath):
		os.makedirs(fullfolderpath)
		print(" folder has been created")
		return 0
	
	sortedlist=os.listdir(fullfolderpath)
	i=0
	for files in sortedlist:
		filenamepath=os.path.join(fullfolderpath, files)
		if os.path.isfile(filenamepath):
			os.remove(filenamepath)
			i=i+1
	return i




def zipfolder(basefolder, relativefolder, zipfilename , relativezipfolder):
	fullfolderpath=os.path.join(basefolder, relativefolder)
	zipfullpath=os.path.join(basefolder, relativezipfolder)
	zipfilenamepath=os.path.join(zipfullpath, zipfilename)
	if os.path.exists(fullfolderpath):
		shutil.make_archive(zipfilenamepath, 'zip', fullfolderpath)			
	return zipfilenamepath+".zip"


def unzipfolder(basefolder, relativefolder, zipfilename , absolutezipfolder):
	fullfolderpath=os.path.join(basefolder, relativefolder)
	zipfullpath=absolutezipfolder
	zipfilenamepath=os.path.join(zipfullpath, zipfilename)
	
	# control if the folder exist otherwise create it
	if not os.path.exists(fullfolderpath):
		os.makedirs(fullfolderpath)
		print(" folder has been created")
	print("unzip file="	, 	zipfilenamepath)
	if os.path.isfile(zipfilenamepath):
		# unzipping

		#shutil.unpack_archive(zipfilenamepath, fullfolderpath , "zip") available in python 2.7.6, but default stretch has the 2.7.13
		import zipfile
		zip_ref = zipfile.ZipFile(zipfilenamepath, 'r')
		zip_ref.extractall(fullfolderpath)
		zip_ref.close()

	return 



def configfilezip():
	basefolder=get_path()
	relativedstfolder=os.path.join("static", CONFIGDOWNLOADPATH)
	relativezipfolder=os.path.join("static", ZIPCONFIGDOWNLOADPATH)	
	#delete files in download folder, or create it if not existing
	deletefilesinfolder(basefolder, relativedstfolder)
	#get config files list
	relativeconfigfolder=DATABASEPATH
	filedatalist=folderfilelist(basefolder, relativeconfigfolder , ".txt")
	#copy config files in the folder
	copyfiles(basefolder, filedatalist, relativedstfolder)

	# remove credentials from downloadfolder
	logincredpath = os.path.join(basefolder, relativedstfolder, "logincred.txt")
	if os.path.isfile(logincredpath):
		os.unlink(logincredpath)
	emailcredpath = os.path.join(basefolder, relativedstfolder, "emailcred.txt")
	if os.path.isfile(emailcredpath):
		os.unlink(emailcredpath)

	# make zip file and get link
	zipfilename="allconfigfiles"
	zipfilenamepath=zipfolder(basefolder, relativedstfolder, zipfilename , relativezipfolder)

	#cleanup
	deletefilesinfolder(basefolder, relativedstfolder)

	# check file exist
	if os.path.isfile(zipfilenamepath):
		filelink=ZIPCONFIGDOWNLOADPATH+"/"+zipfilename+".zip" # relative path vithout static
	else:
		filelink=""

	print(filelink)

	return filelink

def configfileunzip():
	basefolder=get_path()
	relativedstfolder=os.path.join("static", CONFIGDOWNLOADPATH)
	relativezipfolder=os.path.join("static", ZIPCONFIGDOWNLOADPATH)	
	#delete files in download folder, or create it if not existing
	deletefilesinfolder(basefolder, relativedstfolder)
	# make unzip zip file and get link
	zipfilename="allconfigfiles.zip"
	unzipfolder(basefolder, relativedstfolder, zipfilename , relativezipfolder)
	filelink=ZIPCONFIGDOWNLOADPATH+"/"+zipfilename # relative path vithout static
	print(filelink)
	return filelink

def restoreconfigfilefromzip(absolutezipfolder, zipfilename): #zipfilename is only the filename without path, zipfilename should have .zip extension
	basefolder=get_path()
	relativedstfolder=os.path.join("static", CONFIGDOWNLOADPATH)	
	#delete files in download folder, or create it if not existing
	deletefilesinfolder(basefolder, relativedstfolder)
	# make unzip zip file and get link
	unzipfolder(basefolder, relativedstfolder, zipfilename , absolutezipfolder)
	#get config files list
	relativeconfigfolder=relativedstfolder
	filedatalist=folderfilelist(basefolder, relativeconfigfolder , ".txt")
	#copy config files in the folder
	relativedstfolder=DATABASEPATH
	copyfiles(basefolder, filedatalist, relativedstfolder)




def get_path():
    '''Get the path to this script no matter how it's run.'''
    #Determine if the application is a py/pyw or a frozen exe.
    if hasattr(sys, 'frozen'):
        # If run from exe
        dir_path = os.path.dirname(sys.executable)
    elif '__file__' in locals():
        # If run from py
        dir_path = os.path.dirname(__file__)
    else:
        # If run from command line
        dir_path = sys.path[0]
    return dir_path
	


	
if __name__ == '__main__':
	# comment
	print("test copy and zip")
	configfileunzip()
	#restoreconfigfilefromzip()
	
