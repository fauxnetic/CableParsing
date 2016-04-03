#! python

# csvToXML.py
# 
# PROJECT 2 SPECIFICATION:
# With the source file content (attached), parse the Line 1 of all the cable messages to extract its constituent components. 
# For every column value you have extracted create an output xml structure and encloses this value into appropriate xml tags.
#
#
# USAGE:
# File defines a class to parse a cable in CSV format and produce an xml file representing it
# >>> cableDoc = XMLCablesDocument()
# >>> cableDoc.parseCSVFile(<inputCSVFile>)
# >>> cableDoc.writeToFile(<outputXMLFile>)
#
# Executing this script as follows:
# 	> python ./csvToXML.py
# will run a demonstration taking the "./cables_tiny.csv" file and producing "./cables_tiny.xml". 
# Therefor "cables_tiny.csv" file should be placed in the current working directory. The XML file will be written to the same location 
# (see end of file for exact code).
#
#
# ASSUMPTIONS, BUGS & OTHER NOTES:
# Uses Python 3.4 on Windows. Other versions untested.
#
# Unsure of meaning of "parse the Line 1" in specification. All CSV entries were a single line. (Escaped) newlines exist within quoted text but were left
# alone. Anything within free text after the first newline could be easily ignored if intended, but that did not seem a likely desire.
#
# Assumes that CSV is sanity checked before being processed here (i.e. by something like the first project).
# Any lines that do not contain 8 values are ignored and the rest of the file is skipped.
#
# Assumes cables follow the CSV format shown in the example file and that the only variations within cable CSV data format are shown within the example.
# When format for a mandatory field is not as expected, a warning is emited. XML is still produced for remaining valid data.
# 
# Will not explicitly handle filesystem errors such as running out of space or other storage failures.
#
# If a file already exists at the location specified for XML output, that file will be overwritten.
# 
# Not protected against deliberately malicious XML. See https://docs.python.org/3.4/library/xml.html#xml-vulnerabilities
#


import csv
import datetime
import re
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom


class XMLCablesDocument:

	def __init__(self):
		self.root = ET.Element("root")
	
	
	def parseCableMessageText(self, cableNode, contentText):
		
		contentNode = ET.SubElement(cableNode, "content")
		cableLines = contentText.split('\n');
		
		# Assumes E.O., Tags, Subject and Ref lines always appear in that order.
		# Allows for single pass of data when this is the case (as in example file).
		
		lineIterator = iter(cableLines)
		
		# E.O. Line
		foundItem = False
		for currentLine in lineIterator:
			m = re.match("^(?P<eoline>E\.\s?O\. (?:.+))", currentLine)					# Begins "E.O." or "E. O."
			
			if(m != None):
				ET.SubElement(contentNode, "eoline").text = m.group('eoline').strip()
				foundItem = True
				break
		
		
		if(not foundItem):
			# Missing item. Reset iterator to beginning for next item.
			lineIterator = iter(cableLines)
			print("WARNING: E.O. line not found within cable content.")
		else:
			foundItem = False
		
		
		# TAGS in message
		for currentLine in lineIterator:												# Begins "TAGS: "
			m = re.match("^TAGS: (?P<tagslist>.+)", currentLine)							
			
			if(m != None):
				tagsList = re.findall("(\w+)(?:,\s|$)", m.group('tagslist').strip())	# Tags then separated by ", " or " "
				foundItem = True
				
				tagsNode = ET.SubElement(contentNode, "tags", count = str(len(tagsList)))
				for currentTag in tagsList:
					ET.SubElement(tagsNode, "tag").text = currentTag
					
				break
		
		if(not foundItem):
			# Missing item. Reset iterator to beginning for next item.
			lineIterator = iter(cableLines)
			print("WARNING: TAGS not found within cable content.")
		else:
			foundItem = False
		
		
		# SUBJECT in message
		for currentLine in lineIterator:
			m = re.match("^(?:SUBJECT:|SUBJ:) (?P<subject>.+)", currentLine)				# Begins "SUBJECT: "
			
			if(m != None):
				ET.SubElement(contentNode, "subject").text = m.group('subject').strip()
				foundItem = True
				break
		
		if(not foundItem):
			# Missing item. Reset iterator to beginning for next item.
			lineIterator = iter(cableLines)
			print("WARNING: SUBJECT not found within cable content.")
		else:
			foundItem = False
		
		
		# REF in message. Optional.
		for currentLine in lineIterator:
			m = re.match("^(?:REF:) (?P<ref>.+)", currentLine)								# Begins "REF: ". 
																							# Note this is different from header REF
			if(m != None):
				ET.SubElement(contentNode, "ref").text = m.group('ref').strip()
				break
		
		
		# Also retain full free text
		ET.SubElement(contentNode, "fullText").text = repr(contentText.strip())
				

	
	
	def parseCSVLine(self, csvLine):
		
		# ID
		thisCable = ET.SubElement(self.root, "cable", idInSource = csvLine[0])	# "1"
		
		# Date & Time
		try:
			cableDateTime = time.strptime(csvLine[1], "%m/%d/%Y %H:%M") 		# "12/28/1966 18:48"
			
			ET.SubElement(thisCable, "year").text = str(cableDateTime.tm_year)
			ET.SubElement(thisCable, "month").text = str(cableDateTime.tm_mon)
			ET.SubElement(thisCable, "day").text = str(cableDateTime.tm_mday)
			ET.SubElement(thisCable, "hour").text = str(cableDateTime.tm_hour)
			ET.SubElement(thisCable, "minute").text = str(cableDateTime.tm_min)
		
		except ValueError:
			print("WARNING: Time/Date field provided in invalid format.")
		
		
		# Reference, origin, classification
		
		ET.SubElement(thisCable, "reference").text = csvLine[2]					# "66BUENOSAIRES2481"
		ET.SubElement(thisCable, "origin").text = csvLine[3]					# "Embassy Buenos Aires"
		ET.SubElement(thisCable, "classification").text = csvLine[4]			# "UNCLASSIFIED"
		
		# Source(s)
		
		if(csvLine[5] == ""):													# "66STATE106206" or "" or "72MOSCOW1603|72TEHRAN1091|72TEHRAN263"
			sourcesCount = 0
		else:
			sourcesText = csvLine[5].split("|")									
			sourcesCount = len(sourcesText)
		
		sources = ET.SubElement(thisCable, "sources", count = str(sourcesCount))
		
		if(sourcesCount > 0):
			for currentSource in sourcesText:
				ET.SubElement(sources, "source").text = currentSource
		
		
		header = ET.SubElement(thisCable, "header")
		
		m = re.match("^(?P<ref>(?:.+) (?P<month>\D{3}) (?P<year>\d{2})(?: .+)?)" + 		# "R 220927Z AUG 72 XYZ1" Final section optional. "R" also seen as multiple chars.
			"[\r\n]+FM (?P<fromlist>[\w\s]+)" +											# "FM AMEMBASSY TEHRAN ..." multiple sources separated by new lines
			"[\r\n]+TO (?P<tolist>[\w\s]+?)" +											# "TO SECSTATE WASHDC 9461" multiple recipients separated by new lines. 
			"(?:(?:[\r\n]+INFO) (?P<infolist>[\w\s]+))?$", csvLine[6])					# "INFO ... " multiple BCC recipients separated by new lines. (Optional section)
		
		
		if(m != None):
			# Header REF / MONTH / YEAR
			
			ET.SubElement(header, "ref").text = m.group('ref').strip()
			ET.SubElement(header, "month").text = m.group('month')
			ET.SubElement(header, "year").text = m.group('year')

			# Header FROM
			
			if(m.group('fromlist') == None):
				fromCount = 0
			else:
				fromText = m.group(4).strip().split("\n")									
				fromCount = len(fromText)
			
			headerFrom = ET.SubElement(header, "from", count = str(fromCount))
			
			if(fromCount > 0):
				for currentFrom in fromText:
					ET.SubElement(headerFrom, "institution").text = currentFrom.strip()
			
			# Header TO
			
			if(m.group('tolist') == None):	
				toCount = 0
			else:
				toText = m.group(5).strip().split("\n")									
				toCount = len(toText)
			
			headerTo = ET.SubElement(header, "to", count = str(toCount))
			
			if(toCount > 0):
				for currentTo in toText:
					ET.SubElement(headerTo, "institution").text = currentTo.strip()
			
			# Header INFO
			
			if(m.group('infolist') == None):	
				infoCount = 0
			else:
				infoText = m.group(6).strip().split("\n")									
				infoCount = len(infoText)
			
			headerInfo = ET.SubElement(header, "info", count = str(infoCount))
			
			if(infoCount > 0):
				for currentInfo in infoText:
					ET.SubElement(headerInfo, "institution").text = currentInfo.strip()
		
		else:
			print("WARNING: Header provided in invalid format.")
		
		
		# Message Text
		self.parseCableMessageText(thisCable, csvLine[7])
		
		
		# Save
		self.xmlString = ET.tostring(self.root, method="xml")
		
		
	
	def parseCSVFile(self, filePath):
		
		with open(filePath, newline='') as csvfile:
		
			csvreader = csv.reader(csvfile, delimiter=',', quotechar='"', escapechar='\\')
			
			try:
				next(csvreader)
			except StopIteration:
				print("ERROR: File \"%s\" is empty." % filePath)
				return False
			
			for currentLine in csvreader:
				
				if(len(currentLine) != 8):
					print("ERROR: Line %d of CSV file does not contain 8 values in the appropriate format. Skipping remaining lines." % csvreader.line_num)
					return
				
				self.parseCSVLine(currentLine)
	

	
	def writeToFile(self, xmlFilePath):
		
		# Fast version
		#with open(xmlFilePath, 'wb') as xmlFile:
			#xmlFile.write(self.xmlString)
		
		
		# Pretty, easy-to-read version
		try:
			with open(xmlFilePath, 'w') as xmlFile:
				xmlFile.write(minidom.parseString(self.xmlString).toprettyxml())
		except AttributeError:
			print("ERROR: XML generated not valid. No file genereated. Did you parse a valid CSV file?")
		except IOError:
			print("ERROR: Unable to write xml file.")
	
	
	def clear():
		self.root = ET.Element("root")
		

if __name__ == "__main__":
	cableDoc = XMLCablesDocument()
	
	cableDoc.parseCSVFile("./cables_tiny.csv")
	#cableDoc.parseCSVFile("./cables_tiny_fail.csv")
	#cableDoc.parseCSVFile("./cables_tiny_partialA.csv")
	#cableDoc.parseCSVFile("./cables_tiny_partialB.csv")
	#cableDoc.parseCSVFile("./cables_tiny_partialC.csv")
	#cableDoc.parseCSVFile("./empty.csv")
	
	cableDoc.writeToFile("./cables_tiny.xml")
	