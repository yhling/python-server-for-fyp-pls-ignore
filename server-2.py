import SimpleHTTPServer
from SocketServer import ThreadingMixIn
import thread
import threading
import time
import subprocess
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import glob
import base64
import re
import json
import urllib
import urlparse
from operator import itemgetter
from ua_parser import user_agent_parser

class http_handler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        print self.path
        if self.path.find("/list.json") >= 0:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            data = self.headers.getheader('User-Agent')
            data = user_agent_parser.ParseUserAgent(data)
            self.wfile.write(data['family'])
        elif self.path.find("/incident_list") >= 0:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            data = 'halp'
            self.wfile.write(data)
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

