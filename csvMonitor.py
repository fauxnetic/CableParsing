#! python

# csvMonitor.py
# 
# PROJECT 1 SPECIFICATION:
# Monitors a folder for files that are dropped throughout the day.
# When a file is dropped in the folder the program should scan the file...
# o IF all the records in the file have the same length 
# o THEN the file should be moved to a "success" folder and a text file written indicating the total number of records processed 
#
# o IF the file is empty OR the records are not all of the same length 
# o THEN the file should be moved to a "failure" folder and a text file written indicating the cause for failure 
#   for example: Empty file or line 100 was not the same length as the rest) 
#
#
# USAGE:
# Execution of the script will begin monitoring the current working directory. 
# > python ./csvMonitor
# Alternatively, a target directory can be specified as a command-line argument 
# > python ./csvMonitor.py <target>			
# e.g.:
# > python ./csvMonitor.py ./dropped
#
# Requires import of the supporting class defined in "watchdog.py" (place in working directory). 
# Log file written to "monitor.log" in target directory.
#
#
# ASSUMPTIONS, BUGS & OTHER NOTES:
# This is intended for use on Windows systems. Uses Python 3.4 and requires Python for Windows Extensions. Other versions untested.
# 
# Relies on the Windows behaviour for local filesystems where files are locked while being written:
# Assumes that if a file cannot be opened for writing, then it is locked by another process that will cause a subsequent
# write notification when completed allowing the file to be processed at a later date. If this is not the case then a file can sit unprocessed until
# a notification is forced (e.g. by rename). Will cause enexpected beahviour when this is not the case (network filesystems?).
#
# Will not explicitly handle filesystem errors (e.g. running out of space).
#
# Does not automatically trim the log file. It will therefore grow indefinitely with long term use.
#
# No graceful shutdown process currently implemented. (CTRL+C will not be processed until the  
#
# We assume folders are not deleted while this process is running.
# Similarly, unavoidable race condition if folder is created/deleted just after we check it exists
#
# Can fail to process all files if many small files are dropped simultaneously. Tested OK for 10K files with current buffer size. 
# Increase the buffer in "watchdog.py" if required.
#
# Potential race conditions exist between checking for file/folder existence and the following move or creation. 
# This could cause errors but is incredibly unlikely under normal use.

import csv
import datetime
import os
import shutil
import signal
import sys
import time

from watchdog import FolderWatchDog


class CSVMonitor:

	watchdog = FolderWatchDog()

	def initialise(self, folderToWatch):
		
		self.folderToWatch = folderToWatch
		self.successFolder = os.path.join(folderToWatch, "success")
		self.failureFolder = os.path.join(folderToWatch, "failure")

		self.logFilePath = os.path.join(folderToWatch, "monitor.log")
		
		try:
			if not os.path.exists(self.successFolder):
				os.makedirs(self.successFolder)
				
			if not os.path.exists(self.failureFolder):
				os.makedirs(self.failureFolder)
		
		except IOError:
			sys.exit("Error while creating success and failure folders.")

			
	def monitorLoop(self):
	
		self.watchdog.open(self.folderToWatch)
		self.writeToLog("STATUS: Folder monitor launched successfully. Observing \"%s\"" % self.folderToWatch)
		
		# Loop indefinitely
		while True:
			# Store each file we attempt to proccess so it is only processed once in the case of multiple notifications		
			processedFiles = set()						
			
			# BLOCKING;
			# will wait until changes are detected
			watchdogReport = self.watchdog.getFolderWriteActions()		

			for action, filename in watchdogReport:
			
				# Process only files which are updated (written in some form) or renamed
				if(action == FolderWatchDog.ACTIONS.UPDATED or action == FolderWatchDog.ACTIONS.RENAME_TO):
					
					# Only attempt to process files with .csv suffix
					if(filename.endswith(".csv") and filename not in processedFiles):
						
						processedSuccessfully = self.processFile(filename)
						if(processedSuccessfully):
							processedFiles.add(filename)

						
	def writeToLog(self, text):

		timestampedMessage = time.strftime("%a, %d %b %Y %H:%M:%S") + ", " + text + '\n'

		try:
			with open(self.logFilePath, 'a') as logFile:
				logFile.write(timestampedMessage)
		except:
			print("ERROR: Unable to write to log file at \"%s\"" % self.logFilePath)
		
		print(timestampedMessage)
	

	def parseCSV(self, fullFilename):
		
		with open(fullFilename, newline='') as csvfile:
			
			csvreader = csv.reader(csvfile, delimiter=',', quotechar='"', escapechar='\\')
			
			# Test for empty file
			try:
				firstLine = next(csvreader)
				firstLineLength = len(firstLine)
			except StopIteration:
				self.writeToLog("ERROR: File \"%s\" is empty." % fullFilename)
				return False
			
			# Parse subsequent lines, check they are of the same length
			for currentLine in csvreader:
				
				currentLineLength = len(currentLine)
				
				if(currentLineLength != firstLineLength):
					self.writeToLog("ERROR: Record at line %d of \"%s\" was of length %d. Expected previous lines' length of %d items." % (csvreader.line_num, fullFilename, currentLineLength, firstLineLength))
					return False
				
		return True


	def processFile(self, filename):
		fullFilename = os.path.join(self.folderToWatch, filename)
		
		try:
			successful = self.parseCSV(fullFilename)
			
			if(successful):
				targetLocation = os.path.join(self.successFolder, filename)
				logText = "SUCCESS: \"%s\" successfully processed. Moved to \"%s\"" % (filename, targetLocation)
			else:
				targetLocation = os.path.join(self.failureFolder, filename)
				logText = "FAILURE: \"%s\" processing failed. Moved to \"%s\"" % (filename, targetLocation)
			
			
			if(self.safeMove(fullFilename, targetLocation) == True):
				self.writeToLog(logText)
			else:
				self.writeToLog("ERROR: Unable to move file \"%s\"." % filename)
		
		except IOError:
			# Suppress file opening errors. These routinely occur due to multiple signals during the write process.
			# Files will only be readable when writing is complete.
			
			successful = False
			#writeToLog("ERROR: Unable to open file \"%s\"." % fullFilename)

		return successful;
		

	def safeMove(self,fromPath, toPath):
		
		if(os.path.exists(toPath)):
			self.writeToLog("ERROR: Unable to move file to \"%s\" because a file already exists with that name." % toPath)
			return False
			
		shutil.move(fromPath, toPath)
		return True
	

	
	
	
	
if __name__ == "__main__":

	# Argument can override folder to monitor, otherwise defaults to current working dir
	monitor = CSVMonitor()
	folderToMonitor = "."
	
	if(len(sys.argv)) > 1:
		if(os.path.isdir(sys.argv[1])):
			folderToMonitor = sys.argv[1]
		else:
			monitor.writeToLog("ERROR: Invalid folder to monitor passed as argument: \"%s\"" % sys.argv[1])
			sys.exit()

	
	monitor.initialise(folderToMonitor)
	monitor.monitorLoop()