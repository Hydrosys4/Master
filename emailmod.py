from __future__ import print_function
from builtins import str
from builtins import range
import logging
import datetime
import hardwaremod
import os
import subprocess
import emaildbmod
import networkmod
import sensordbmod
import actuatordbmod
import messageboxmod

# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

logger = logging.getLogger("hydrosys4."+__name__)

# GET path ---------------------------------------------
global MYPATH
print("path ",hardwaremod.get_path())
MYPATH=hardwaremod.get_path()

global IPEXTERNALSENT
IPEXTERNALSENT=""

def send_email(user, pwd, recipient, subject, body):

    gmail_user = user
    gmail_pwd = pwd
    FROM = user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP(emaildbmod.getserver(), emaildbmod.getport())
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        server.quit()
        print('successfully sent the mail')
    except:
        print("failed to send mail")

def create_htmlopen():

	html = """\
	<html>
	  <head>

	  </head>
	  <body>
	"""
	return html

def create_htmlclose():

	html = """\
	  </body>
	</html>
	"""
	return html

def create_htmlintro(intromessage):
	html = """\
		<h3> """ + intromessage + """</h3>

	"""
	return html

def create_htmlbody(bodytextlist):
	# the input should be a list
	html = """\
	<p></p>
		"""
	for textrow in bodytextlist:
		html = html + """\
			<p> """ + textrow + """</p>

		"""
	return html

def create_htmladdresses(descriptionlist, addresslist, port):
	html = """\

	<h3>Below the links for System connection:</h3>
	<p></p>

	"""

	for inde in range(len(addresslist)):
		addressport=addresslist[inde]+":"+port

		html = html + """\

			<a href="http://""" + addressport + """"> """ + descriptionlist[inde] + """ </a>
			<p></p>
			<p></p>
		"""
	return html

def create_htmlmatrix(matrixinfo):
	htmlopen = """<table style="width:100%!important" cellpadding="2" cellspacing="1">"""


	htmlheader="""<tr>"""
	for header in matrixinfo[0]:
		htmlheader = htmlheader+ """<th align="center" style="background: #81BEF7; border:0px !important;">"""+  header  +"""</th> """
	htmlheader = htmlheader+ """</tr> """


	htmltable=""
	for row in matrixinfo[1:]:
		htmltable=htmltable + """<tr> """
		for element in row:
			htmltable = htmltable+ """<td align="center" style="background: #2E64FE; border:0px !important;">"""+  element  +"""</td> """
		htmltable = htmltable+ """</tr> """

	htmlclose = """	</table>"""
	html=htmlopen+htmlheader+htmltable+htmlclose

	return html

def send_email_html(user, pwd, recipient, subject, html, showpicture):
	# me == my email address
	# you == recipient's email address
	gmail_user = user
	gmail_pwd = pwd
	me = user
	you=[]
	for address in recipient.split(";"):
		you.append(address.strip())
	print(" Sending mail to : ", recipient)

	# Create message container - the correct MIME type is multipart/alternative.
	msg = MIMEMultipart()
	msg['Subject'] = subject
	msg['From'] = me
	msg['To'] =", ".join(you)
	#msg.preamble = 'Our family reunion'

	# Create the body of the message HTML version

	# Record the MIME t
	part1 = MIMEText(html, 'html')
	msg.attach(part1)

	if showpicture:
		#retrieve last picture ------------------------------------
		global MYPATH

		photolist=hardwaremod.photolist(MYPATH,3)
		imgfiles=[]
		if photolist:
			referencestr=photolist[0][0].split(",")[0]
			for items in photolist:
				if referencestr in items[0]:
					folderpath=os.path.join(MYPATH, "static")
					folderpath=os.path.join(folderpath, items[0])
					imgfiles.append(folderpath)

		for filename in imgfiles:
			# Open the files in binary mode.  Let the MIMEImage class automatically
			# guess the specific image type.
			print("filename " , filename)
			fp = open(filename, 'rb')
			img = MIMEImage(fp.read())
			fp.close()
			picturename=os.path.basename(filename)
			img.add_header('Content-Disposition','attachment; filename="%s"' % picturename)
			msg.attach(img)

	try:
		server = smtplib.SMTP("smtp.gmail.com", 587)
		server.ehlo()
		server.starttls()
		server.login(gmail_user, gmail_pwd)
		server.sendmail(me, you, msg.as_string())
		server.quit()
		print('successfully sent the mail')
		logger.info('mail sent succesfully ')
		return True
	except:
		logger.error('failed to send mail')
		print("failed to send mail")
		return False

def send_email_main(address,title,cmd,mailtype,intromessage,bodytextlist=[]):
	# mailtype option
	# "report"
	# "alert"
	if mailtype=="report":
		starttitle="Report:"
		showtable=True
		showpicture=True
		showlink=True

	elif mailtype=="alert":
		starttitle="Alert:"
		showtable=False
		showpicture=False
		showlink=True

	elif mailtype=="info":
		starttitle="Info:"
		showtable=False
		showpicture=False
		showlink=True

	currentdate=datetime.datetime.now().strftime("%y-%m-%d,%H:%M")
	# got credentials here !
	user=emaildbmod.getaddress()
	pwd=emaildbmod.getpassword()
	recipient=address

	# check IP address
	iplocal=networkmod.get_local_ip()
	ipext=networkmod.EXTERNALIPADDR
	if ipext=="":
		logger.info('Stored external IP address is empty, try to get it from network')
		ipext=networkmod.get_external_ip()

	print("Try to send mail")
	# subject of the mail
	subject=starttitle +" " + title + "  " + currentdate
	htmlbody=create_htmlopen()
	htmlbody=htmlbody+create_htmlintro(intromessage)+create_htmlbody(bodytextlist)

	if showlink:
		if ipext=="":
			print("No external IP address available")
			logger.error('Unable to get external IP address')
		else:
			port=str(networkmod.PUBLICPORT)
			if cmd=="mail+info+link":
				addresslist=[]
				descriptionlist=[]
				addresslist.append(iplocal)
				descriptionlist.append("Link for local Access")
				addresslist.append(ipext)
				descriptionlist.append("Link for Remote Access")
				customURL=networkmod.getCUSTOMURL()
				if not customURL=="":
					addresslist.append(customURL)
					descriptionlist.append("your Link")
				print("Mail url list ",addresslist)
				htmlbody=htmlbody+create_htmladdresses(descriptionlist,addresslist, port)

	if showtable:
		# table with information
		matrixinfo=sensordbmod.sensorsysinfomatrix()
		htmlbody=htmlbody+create_htmlmatrix(matrixinfo)
		matrixinfo=actuatordbmod.sensorsysinfomatrix()
		htmlbody=htmlbody+create_htmlmatrix(matrixinfo)
	htmlbody=htmlbody+create_htmlclose()
	issent=send_email_html(user, pwd, recipient, subject, htmlbody, showpicture)
	if (issent) and (showlink) and (ipext!=""):
		global IPEXTERNALSENT
		IPEXTERNALSENT=ipext
	return issent

def sendallmail(mailtype,intromessage,bodytextlist=[],localmessage=True):
	# archive the message in messagebox
	if mailtype=="alert":
		if localmessage:
			dictitem={'title': "System Message (Alert)", 'content': intromessage, 'color': "olive" }
			messageboxmod.SaveMessage(dictitem)
	usedfor="mailcontrol"
	hwnamelist=hardwaremod.searchdatalist(hardwaremod.HW_FUNC_USEDFOR,usedfor,hardwaremod.HW_INFO_NAME)
	for hwname in hwnamelist:
		sendmail(hwname,mailtype,intromessage,bodytextlist)

def sendmail(hwname, mailtype, intromessage, bodytextlist=[]):
	address=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, hwname, hardwaremod.HW_CTRL_ADDR)

	if not address == "":
		print("mail recipient ", address)
		title=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, hwname, hardwaremod.HW_CTRL_TITLE)
		print("mail title ", title)
		cmd=hardwaremod.searchdata(hardwaremod.HW_INFO_NAME, hwname, hardwaremod.HW_CTRL_CMD)
		print("mail type ", cmd)
		issent=send_email_main(address, title, cmd, mailtype, intromessage, bodytextlist)
		return issent
	else:
		print("No address specified for ", str(hwname))
		logger.warning('No address specified for %s', str(hwname))
		return False

if __name__ == '__main__':
	"""
	prova email
	"""

