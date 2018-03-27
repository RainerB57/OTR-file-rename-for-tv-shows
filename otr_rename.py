#/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OTR file rename for tv-shows
Extract all information from the (decoded) otrkey file name (onlinetvrecorder.com)
and use the website fernsehserien.de to rename the file with the episode and season info

@author: Jens
"""

import re
import os
from datetime import datetime
import time
from shutil import move
from time import localtime
import codecs
from types import *
import logging
import sys
import conf

from Fernsehserien_de_Scraper import Fernsehserien_de_Scraper
# nicht   import Fernsehserien_de_Scraper wegen import datetime in Fernsehserien_de_Scraper

# create logger
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

global IsSerie  # global, weil verschiedene Funktionen von OTR_Rename es aufrufen und ggf. verändern 


class OTR_RenameBack(object):
	def __init__(self, filename):
		self.filename0 = filename
		path,file = os.path.split(filename)
		self.file = file
		self.path = path
#		self.LineNrVonOldFile = 0

	def getOriginalFilename(self, filename):
		with open('log.txt') as f:
			self.lines = f.read().splitlines()
		Zeile1 = self.lines[0]
		i = 1
		OrigFileName = ''
		while len(self.lines) > i-1:
			Zeile2 = self.lines[i]
			if ('output ') in Zeile2 and (self.file in Zeile2):
				OrigFileName = Zeile1[26:len(Zeile1)]
				conf.LineNrVonOldFile= i
				break
			else:
				Zeile1 = Zeile2
			i += 1

		return OrigFileName

	def RenameToOld(self,a):
		move (a, self.filename0)
		self.lines = []
		with open('log.txt') as f:
			self.lines = f.read().splitlines()
		f.close()
		f = open('log.txt', 'w')
		i = 0
		while i < conf.LineNrVonOldFile-1:
			f.write(self.lines[i] + '\n')
			i+= 1
		i = conf.LineNrVonOldFile+2
		while i < len(self.lines):
			f.write(self.lines[i] + '\n')
			i += 1
		f.close()


class OTR_Rename(object):
	def __init__(self, filename):
		path,file = os.path.split(filename)
		self.file = file
		self.path = path
		self.parseFileInfo()

    
	def parseFileInfo(self):
		# Get Title, date and so on from filename
		self.extension = os.path.splitext(self.file)[1]
		m = re.search("(.*)_([0-9]{2}\.[0-9]{2}\.[0-9]{2})_([0-9]{2}\-[0-9]{2})_([A-Za-z0-9]+)", self.file)
		title = m.group(1)
		# Check for SxxExx in filename:
		m2=re.search("(S[0-9]{2}E[0-9]{2})",title)
		if type(m2) is not NoneType:
			title = title.split('_'+m2.group(1))[0]
		title = title.split('__')[0] # for US series SeriesName__EpisodeTitle (problems with shows like CSI__NY)

		self.show = title.replace("_",' ').strip()
		self.epdate = m.group(2)
		self.eptime = m.group(3)
		self.SendeZeit = self.epdate + self.eptime
		self.sender = m.group(4)
		if 'HQ' in self.file:
			self.Format = 'HQ'
		else:
			self.Format = 'DivX'
		if self.sender[:2] != 'us':
			self.lang='de'
		else:
			self.lang='us'
		logging.info(self.show + ' (' + self.lang + ') : ' + self.epdate + ' ' + self.eptime)

	def queryEpisodeInfo(self):
		global IsSerie
		self.scraper = Fernsehserien_de_Scraper(self.show, self.SendeZeit)

		if self.lang == 'us':
			(d,s,e,t) = self.scraper.getEpisodeGuide(lang='us')
		conf.SZaehler = 1;
		while conf.SZaehler > 0:
			if self.lang == 'de':
				(d,s,e,t,time_list) = self.scraper.getTimeTable(self.sender)

			# Find match in Date
			if not(d[:]):
				idx = False
				IsSerie = False
				conf.SZaehler = -2  # Suche erfolglos
			else:
				IsSerie = True
				idx = self.searchDate(self.epdate, d)
			if str(idx).isdigit():  # Found match:
				conf.SZaehler = -1
				if self.lang == 'de':
					idx = self.checkFollowingDateEntry(self.epdate, self.eptime, d, time_list, idx-1 if idx>0 else idx) #Search for closest eptime on the date
				date, season, episode, title = d[idx], s[idx], e[idx], t[idx]
				if len(season) == 1:
					season = "0" + season  #rb Season 2-stellig
			else: # No match
				date, season, episode, title = None, None, None, None
				#SZaehler += 1
				if conf.LetzteSeite:
					conf.SZaehler = -1
				else:
					if  IsSerie: 
						self._d= d[len(d)-1]
						self._t = time_list[len(time_list)-1]
						self.test = self._d[8:10] + self._d[2:6] + self._d[0:2] + self._t[0:2] + '-' + self._t[3:5]
						if (self.SendeZeit > self.test):     #unnötig, in älteren Webseiteneinträgen zu suchen
							conf.SZaehler = -1
						else:
							conf.SZaehler += 1
		return date, season, episode, title

	def buildNewFilename(self):
		# Get filename from the scraped webpage
		date, season, episode, title = self.queryEpisodeInfo()
		if None in (date, season, episode, title):
			if  IsSerie:
				newfilename = ''  #rb 
				logging.info('Falsche Angaben im Dateinamen?')
			else:
				 newfilename = self.show \
				 +' [20' + self.epdate.replace('.','-') \
				 +' ' + self.eptime.replace(':','-') + '] ' + self.sender + ' ' + self.Format +self.extension  #rb
		else:
			newfilename = self.show + ' '  + season + 'x' + episode + ' ' \
			+ title +' [20' + self.epdate.replace('.','-') \
			+' ' + self.eptime.replace(':','-') + '] ' + self.sender + ' ' + self.Format +self.extension  #rb
			#newfilename = self.show + '.' + 'S' + season + 'E' + episode + '.' + title + self.extension
		return newfilename

	def copy_and_sort(self):
		global IsSerie
		log = open('log.txt','a')
		lt = localtime()
		jahr, monat, tag, stunde, minute = lt[0:5]
		log.write(str(jahr)+'-'+ str(monat).zfill(2) +'-'+ str(tag).zfill(2) +' '+ str(stunde).zfill(2) +':'+ str(minute).zfill(2) +' : ')
		log.write("input  " + self.file + "\n")

		newfilename = self.buildNewFilename()
		if not(os.path.isdir(os.path.join(self.path,self.show))):
			if IsSerie: 
				os.mkdir(os.path.join(self.path,self.show))
		chars = {'ö':'oe','ä':'ae','ü':'ue','ß':'ss', '`':"'", '´':"'", \
		'Ö':'OE','Ä':'AE','Ü':'UE',	'à':'a', 'ê':'e', 'é':'e', 'è':'e', \
		'À':'A', 'Ê':'E', 'É':'E', 'È':'E'} # rb Umlaute und Vokale mit Akzenten konvertieren
		if newfilename != False:
			#newfilename = "´`*~'#,;-" rb test
			for char in chars:  #rb
				newfilename = newfilename.replace(char,chars[char])
#			newfilename = "".join(i for i in newfilename if i not in r'\/:*?"<>|´`')
			newfilename = "".join(i for i in newfilename if (ord(i) < 128) and (i not in r'\/:*?"<>|´`'))
			if IsSerie: 
				newpath = os.path.join(self.path,self.show + '/' + newfilename)
			else:
				newpath = 'NichtSerien/' + newfilename
			logging.debug('Encoding ist %s' %  sys.stdin.encoding)
			logging.debug("newpath: " + newpath)  #rb zum testen
			newpath = u''.join(newpath).encode('utf-8').strip()

			if not(os.path.isfile(newpath)):
				if not(len(newfilename)==0):
					move(os.path.join(self.path,self.file), newpath)
					log.write(str(jahr)+'-'+ str(monat).zfill(2) +'-'+ str(tag).zfill(2) +' '+ str(stunde).zfill(2) +':'+ str(minute).zfill(2) +' : ')
					log.write("output " + newpath + "\n\n")
					logging.info(self.file + ' moved to: \n' + newpath +'\n')
				else:
					logging.info('Filename hat 0 Bytes	==> Skip file')
			else:
				logging.info('File exists already in the target directory \n	==> Skip file')
		else:
			logging.info('No match found \n   ==> skip file')
			newpath = os.path.join(self.path,self.file)

		log.close()


	@staticmethod
	def searchDate(date, date_list):
		date=datetime.strptime(date.strip(),"%y.%m.%d")
		for index, item in enumerate(date_list):
			item = item.strip() #remove potential white spaces
			if item != u'\xa0' and item != '':
				actualdate = datetime.strptime(item,"%d.%m.%Y")
			if actualdate.date() == date.date():
				return index

	@staticmethod
	def checkFollowingDateEntry(date,stime,date_list,time_list,idx):
		tc = time.strptime(date+' '+stime,"%y.%m.%d %H-%M")  #Time from filename

		actual=time.strptime(date_list[idx]+' '+time_list[idx],"%d.%m.%Y %H:%M")

		if idx <= len(date_list)-2:
			after=time.strptime(date_list[idx+1]+' '+time_list[idx+1],"%d.%m.%Y %H:%M")
		else:
			return idx

		trynext = True
		while trynext:

			diffactual= abs(time.mktime(actual)-time.mktime(tc))
			diffnext= abs(time.mktime(after)-time.mktime(tc))

			if diffactual > diffnext and idx < len(date_list)-2:
				idx=idx+1
				actual = time.strptime(date_list[idx]+' '+time_list[idx],"%d.%m.%Y %H:%M")
				after = time.strptime(date_list[idx+1]+' '+time_list[idx+1],"%d.%m.%Y %H:%M")
			elif diffactual > diffnext and idx == len(date_list)-2:
				idx=idx+1
				trynext = False
			else:
				trynext = False

		return idx

if __name__ == '__main__':
	import sys
	if len(sys.argv) == 2:
		filename = sys.argv[1]
		otrfile = OTR_Rename(filename)
		filename_new = otrfile.buildNewFilename()
		if filename_new != False:
			print filename_new
		else:
			print 'No episode data found.'
	else:
		print 'Usage: ' + sys.argv[0] + ' filename'
