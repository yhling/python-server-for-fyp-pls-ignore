import SimpleHTTPServer
from SocketServer import ThreadingMixIn
import thread
import threading
import time
import subprocess
from BaseHTTPServer import HTTPServer
import glob
import base64
import re
import json
import urllib
import urlparse
from operator import itemgetter

class http_handler(SimpleHTTPServer.SimpleHTTPRequestHandler):
	
	def do_GET(self):
		print self.path
		if self.path.find("/list.json") >= 0:
			self.send_response(200)
			self.send_header('Content-Type', 'application/json')
			self.end_headers()
			host_incidents = {}
			for f in glob.glob("video_sink/*.mp4"):
				file_full_name = re.search('/(\S*\.mp4)', f).group(1)
				json_object = json.loads(base64.b32decode(file_full_name.strip(".mp4")))
				if json_object['hn'] in host_incidents:
					host_incidents[json_object['hn']] += 1
				else:
					host_incidents[json_object['hn']] = 1
			try:
				k = json.loads(subprocess.check_output('alfred-json -r 64 &', shell=True))
				g = []
				for u in k:
					x={}
					x['mac']=u
					for c in k[u]:
						x[c]=k[u][c]
					if x['hostname'] in host_incidents:
						x['incidents']=host_incidents[x['hostname']]
					x['hostname']="<a href='/incidents.html?s=" + x['hostname'] + "'>" + x['hostname'] + "</a>"
					g.append(x)
				data = json.dumps(g, separators=(',',':'))
				print "Wrote Alfred data"
			except:
				data = "Failed to get alfred data: " + data
			self.wfile.write(data)
		elif self.path.find("/incident_list") >= 0:
			self.send_response(200)
			self.send_header('Content-Type', 'application/json')
			self.end_headers()
			json_list = "["
			g = []
			if 'search' in urlparse.parse_qs(urlparse.urlparse(self.path).query):
				search_string = urlparse.parse_qs(urlparse.urlparse(self.path).query)['search'][0]
				search_enabled = True
			else:
				search_enabled = False
			for f in glob.glob("video_sink/*.mp4"):
				file_full_name = re.search('/(\S*\.mp4)', f).group(1)
				json_object = json.loads(base64.b32decode(file_full_name.strip(".mp4")))
				json_object['hn']="<a href='video_sink/" + file_full_name + "'>" + json_object['hn'] + "</a>"
				json_object['thumb']='<img src="video_sink/' + file_full_name.strip(".mp4") + '.jpg" alt="thumnail">' 
				if search_enabled:
					try:
						if json_object['hn'].find(search_string) >= 0:
							g.append(json_object)
					except Exception, e:
						print e
				else:
					g.append(json_object)
			k={}
			k['total']=len(g)
			if 'sort' in urlparse.parse_qs(urlparse.urlparse(self.path).query):
				if 'order' in urlparse.parse_qs(urlparse.urlparse(self.path).query):
					if urlparse.parse_qs(urlparse.urlparse(self.path).query)['order'][0] == 'desc':
						try:
							g.sort(key=itemgetter(urlparse.parse_qs(urlparse.urlparse(self.path).query)['sort'][0]), reverse=True)
						except Exception, e:
							print e
					else:
						try:
							g.sort(key=itemgetter(urlparse.parse_qs(urlparse.urlparse(self.path).query)['sort'][0]))
						except Exception, e:
							print e
				else:
					try:
						g.sort(key=itemgetter(urlparse.parse_qs(urlparse.urlparse(self.path).query)['sort'][0]))
					except Exception, e:
						print e
			if 'offset' in urlparse.parse_qs(urlparse.urlparse(self.path).query):
				g = g[int(urlparse.parse_qs(urlparse.urlparse(self.path).query)['offset'][0]):int(urlparse.parse_qs(urlparse.urlparse(self.path).query)['offset'][0])+10]
			k['rows']=g
			json_output = json.dumps(k, separators=(',',':'))
			self.wfile.write(json_output)
		else:
			return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

PORT = 8035

Handler = http_handler
httpd = ThreadedHTTPServer(("", PORT), Handler)

print "serving at port", PORT
try:
	httpd.serve_forever()
except KeyboardInterrupt:
	print '^C received, shutting down server'

