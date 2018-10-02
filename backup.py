#!/usr/bin/python

###
# Author: parnell
# Version: 2.3.2
# Disclaimer: I use these scripts for my own use,
#	so caveat progtor. (let the programmer beware)
###

import os
import sys
import shutil
import datetime
import getopt
from subprocess import *

## For an example, see end of script

def usage(out):
	print >> out , "Usage: backup src dest name [opts]"
	print >> out , "Destination directory will be created if it does not already exist"
	print >> out , "Options are"
	print >> out , " -n= Number of backups"
	print >> out , "		Default: 4"
	print >> out , " --link-dest= Specify a link destination directory for rsync"
	print >> out , "		Default: name.1"
	print >> out , " --log-dir= Directory for logging"
	print >> out , "		Default: /Library/Logs/Backups"
	print >> out , " --exclude-from: Pass exclude from argument to rsync"

# the Main body
if (len(sys.argv) < 3):
	usage(sys.stderr)
	sys.exit(1)
try:
	os.path.exists(sys.argv[1])
except IOError:
	print "No Src Path Exists: "

################# DEFAULT VALUES ################
#where the data to be backed up is located
src_dir = sys.argv[1]

#where the backup folder is located
dest_dir = sys.argv[2]

#name
name = sys.argv[3]

#where to back up the data
backup_dir = "%s/%s.0" %(dest_dir, name)
temp_dest = "%s/tmp.bk" %(dest_dir)

#how many backups
num_backups = 4

#Link Destination
link_dest = "%s.1" %name

#Log Directory
log_dir = "/Library/Logs/Backups"  #for Mac
#log_dir = "/var/log/Backups" #for Unix

#Name of the log file
LOG_FILE = "%s/rsync_log.txt" %log_dir
LAST_LOG_FILE = "%s/rsync_last_%s.txt" % (log_dir, name)
logging = False
try:
	f = open(LOG_FILE, 'a')
	f.close()
	logging = True
except IOError, (errno, strerror):
	logging = False
	print "Logs will not be written due to I/O error(%d): %s" %(errno, strerror)


# Excludes
excludes = ""
try:
	opts, args = getopt.gnu_getopt(sys.argv[1:], "hn:", ("link-dest=", "log-dir=", "help"))
except getopt.GetoptError:
	usage(sys.stderr)
	sys.exit(1)

for o, a in opts:
	if o == "-n":
		num_backups = int(a)
	elif o in ("-h", "--help"):
		usage(sys.stdout)
		sys.exit()
	elif o == "--link-dest":
		link_dest = a
	elif o == "--log-dir":
		log_dir = a
	elif o == "--exclude-from":
		excludes = "--exclude-from=%s" %a

#Rsync Option (brief) Explanation
#a : archive mode, same as -rlptgoD (essentially preserve all permissions owners, times etc)
#link-dest: compare to this file and hard link if files are the same.
#			*CAUTION* link-dest is relative to the destination
#verbose: wordy output 								#debugging
#stats: statistics on bytes sent, matched, etc		#debugging
#progress: print how far through the backup 		#debugging
OPTS = "-a -z --super --link-dest=%s/%s --verbose --stats --progress %s" %(dest_dir, link_dest, excludes)

###############################################################################
############################ Main Program #####################################
###############################################################################

#Create Dirs
if not os.path.exists(dest_dir) :
	os.makedirs(dest_dir)

if not os.path.exists(log_dir) :
	os.makedirs(log_dir)

class RsyncException(Exception):
	def __init__(self, value): self.parm = value
	def __str__(self): return repr(self.parm)

def incrementDirs(n, srcpath):
	# iterate from back to front moving backups
	for i in range(n -1,-1,-1) :
		src = "%s.%s" %(srcpath, str(i))
		dest = "%s.%s" %(srcpath, str(i + 1))
		if os.path.exists(src) :
			os.rename(src, dest)

def decrementDirs(n, srcpath):
	# iterate from back to front moving backups
	for i in range(0,n+1) :
		src = "%s.%s" %(srcpath, str(i+1))
		dest = "%s.%s" %(srcpath, str(i))
		if os.path.exists(src) :
			os.rename(src, dest)

### run rsync
cmd = ""
if logging :cmd = "rsync %s %s %s >> %s" %(OPTS , src_dir, temp_dest, LAST_LOG_FILE )
else: cmd = "rsync %s %s %s " %(OPTS , src_dir, temp_dest)
try:
	src_path ="%s/%s" %(dest_dir,name)
	incrementDirs(num_backups,src_path)
	ll = None
	rcode = 0
	# cin, couterr = os.popen4(cmd) ## Python 2.4
	### if we are logging, log to last file
	if logging:
		ll = open(LAST_LOG_FILE,'w')
		rcode = call(cmd, shell=True,stdout=ll,stderr=ll) ## Python 2.4+
	else :
		rcode = call(cmd, shell=True) ## Python 2.4+

	if not rcode == 0:
		decrementDirs(num_backups,src_path)
		raise RsyncException(rcode)

	## rename our tmp named backup to the real one
	dest = "%s/%s.0" %(dest_dir,name)
	os.rename(temp_dest,dest)


	#delete oldest backup
	file = "%s/%s.%s" %(dest_dir, name, str(num_backups))
	if os.path.exists(file) :
		shutil.rmtree(file)
except RsyncException, e:
	print "An error occurred while running rsync with error code=%s" %e

except OSError, e:
	print >>sys.stderr, "Execution failed:", e

### Log time
if logging:
	try:
		f = open(LOG_FILE, 'a')
		f.write("%s %s: Command: '%s'\n" %(name, datetime.datetime.today(),cmd))
		f.close()

		#Create the lastLog file
		f = open(LAST_LOG_FILE, 'a')
		f.write("\n%s\n" %datetime.datetime.today())
		f.write("Command: '%s'\n" %cmd ) # write command to last log file
		f.close()
	except IOError, (errno, strerror):
		print "Logs not written due to I/O error(%d): %s" %(errno, strerror)


"""
	Example of Backup
	#Time 1
Data		0			1			2
A			A
B			B
C			C

	#Time 2, 	A & B modified
Data		0			1			2
A1			A1			A
B1			B1			B
C			C			C

	#Time 3, 	A & C Modified
Data		0			1			2
A2			A2			A1			A
B1			B1			B1			B
C1			C1			C			C

	#Time 4, 	B Modified
Data		0			1			2
A2			A2			A2			A1
B2			B2			B1			B1
C1			C1			C1			C

Example Cron
backs up 3 times a day
backs up the last 5 days
backs up the last 3 weeks
log_dir = "/backupfiles/saves/log" #for Unix
# minute	hour	mday	month	wday	who	command
	0		6,12,18	*		*		*		root	/var/spool/cron/backup.py /Users /backup snapshot
	45		23		*		*		*		root 	/var/spool/cron/backup.py /Users /backup daily --link-dest=snapshot.0 -n 5
	15		1		*		*		0		root 	/var/spool/cron/backup.py /Users /backup weekly --link-dest=daily.0

	0 6,12,18 * * *  backup.py /Users /backup snapshot
	0 0 * * 1-6      backup.py /Users /backup snapshot; backup.py /Users /backup daily --link-dest=snapshot.0
	0 0 * * 0        backup.py /Users /backup snapshot; backup.py /Users /backup daily --link-dest=snapshot.0; backup.py /Users /backup weekly --link-dest=daily.0
"""
