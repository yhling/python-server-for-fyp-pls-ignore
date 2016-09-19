import SimpleHTTPServer
from SocketServer import ThreadingMixIn
import thread
import threading
import time
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import glob
import json
import urlparse
from ua_parser import user_agent_parser
from autobahn.twisted.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory
from autobahn.websocket.types import ConnectionDeny

PORT = 8035

device_table = {}

class dict_differ(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.current_keys, self.past_keys = [
            set(d.keys()) for d in (current_dict, past_dict)
        ]
        self.intersect = self.current_keys.intersection(self.past_keys)

    def added(self):
        return self.current_keys - self.intersect

    def removed(self):
        return self.past_keys - self.intersect

    def changed(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect
            if self.past_dict[o] == self.current_dict[o])
        
class device_table_handler():

    def add(self, dict_list):
            self.device_table[dict_list['uid']]={'hostname': dict_list['hostname'], 'data_type': dict_list['data_type'], 'content': dict_list['content'], 'location': dict_list['location'], 'last_seen': time.time(), 'ws_object': self.device_table[dict_list['uid']]['ws_object']}
            print self.device_table
            
    def bind_to(self, callback):
        self._device_table_change_subscribers.append(callback)
     
    def get(self):
        for callback in self._device_table_change_subscribers:
            print 'anouncing change internally'
            callback(self._device_table)
        return self._device_table
        
    device_table = property(get, add)
        
    def __init__(self):
        self._device_table = device_table
        self._device_table_change_subscribers = []
        
class MyServerProtocol(WebSocketServerProtocol):
    
    def onConnect(self, request):
        global device_table_object
        if 'uid' in request.headers:
            if request.headers['uid'] in device_table_object.device_table:
                raise ConnectionDeny(400, unicode('Duplicate UID used'))
            else:
                self.uid = request.headers['uid']
                device_table_object.device_table[self.uid] = {'ws_object': self}
                if 'type' in request.headers:
                    device_table_object.device_table[self.uid] = {'type': request.headers['type']}  
        else:
            raise ConnectionDeny(400, unicode('You must provide a UID in your header'))

    def onOpen(self):
        global device_table_object
        print("WebSocket connection open.")
        print device_table_object.device_table

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            recv_data = payload.decode('utf8')
            print("Text message received: {0}".format(recv_data))
            recv_data = json.loads(recv_data)
            if recv_data['intent'] == 'service':
                device_table_object.add(recv_data)
                self.sendMessage('service ok', isBinary)
            elif recv_data['intent'] == 'update':
                notif.add('%s (UID %s): %s' % (recv_data['hostname'], recv_data['uid'], recv_data['message']))
                self.sendMessage('update ok', isBinary)

    def onClose(self, wasClean, code, reason):
        global device_table_object
        print("WebSocket connection closed: {0}".format(reason))
        if hasattr(self, 'uid'):
            del device_table_object.device_table[self.uid]
        print device_table_object.device_table
        
    @classmethod
    def send_to_device(cls, uid, payload):
        global device_table_object
        payload['uid'] = uid
        payload = json.dumps(payload, ensure_ascii = False).encode('utf8')
        if uid in device_table_object.device_table:
            device_table_object.device_table[uid]['ws_object'].sendMessage(payload, 0)
        else:
            print 'UID websocket dest not exist.'

        
class table_diff_notifier(object):
    
    def __init__(self, data):
        self.data = data
        self.initial_table = dict(data.device_table)
        self.data.bind_to(self.diff_notifier)
        
    def diff_notifier(self, new_table):
        k = dict_differ(new_table, self.initial_table)
        for a in k.added():
            notif.add('%s has come online' % (a))
        for a in k.removed():
            notif.add('%s has gone offline' % (a))
        #for a in k.changed():
        #    notif.add('Parameters for UID \'%s\' (%s) has changed' % (a, new_table[a]['hostname']))
        self.initial_table = dict(new_table)
        
class notification():
    def __init__(self):
        self.queue = []
        
    def add(self, data):
        self.queue.append({'time': time.time(), 'message': data})

class http_handler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        print self.path
        if self.path.find("/list.json") >= 0:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            user_agent_browser = user_agent_parser.ParseUserAgent(self.headers.getheader('User-Agent'))
            browser_type_string = user_agent_browser['family']
            data = []
            for uid in device_table_object.device_table.keys():
                temp = dict(device_table_object.device_table[uid])
                if 'type' in temp:
                    if temp['type'] == 'INTERNAL_SERVICE':
                        continue
                if 'last_seen' in temp:
                    temp['last_seen'] = time.time() - temp['last_seen']
                else:
                    temp['last_seen'] = ''
                if not 'location' in temp:
                    temp['location'] = ''
                if not 'hostname' in temp:
                    temp['hostname'] = ''
                if not 'hostname' in temp:
                    temp['hostname'] = ''
                if not 'content' in temp:
                    temp['content'] = ''
                if 'ws_object' in temp:
                    del temp['ws_object']
                data.append(temp)
            self.wfile.write(json.dumps(data))
        elif self.path.find("/history.json") >= 0:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            data = []
            for a in notif.queue:
                data.append({'time': time.time() - a['time'], 'message': a['message']})
            self.wfile.write(json.dumps(data))
        elif self.path.find("/history_count.json") >= 0:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'count': str(len(notif.queue))}))
        else:
            return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            
    def do_POST(self):
        print self.path
        if self.path.find('/command') >= 0:
            content_len = int(self.headers.getheader('content-length', 0))
            post_body = self.rfile.read(content_len)
            k = urlparse.parse_qs(post_body) # {'device': ['D0'], 'command': ['ON'], 'uid': ['%s']}
            received_data = {}
            for keys in k.keys():
                received_data[keys] = k[keys][0]
            try:
                MyServerProtocol.send_to_device(received_data['uid'], {'command': received_data['command'], 'device': received_data['device']})
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write('ok')
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write('not ok', )
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write('Nope')
            

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

    
if __name__ == '__main__':
    import sys

    from twisted.python import log
    from twisted.internet import reactor
    
    log.startLogging(sys.stdout)
    
    #-->
    # setup internals variables
    
    device_table_object = device_table_handler()
    diff_notifier = table_diff_notifier(device_table_object)
    notif = notification()
    
    factory = WebSocketServerFactory(u"ws://0.0.0.0:9000")
    factory.protocol = MyServerProtocol
    factory.setProtocolOptions(autoPingInterval=5,
                           autoPingTimeout=5)
    
    #--->
    # setup websocket server
    
    reactor.listenTCP(9000, factory)
    this_thread = threading.Thread(target=reactor.run, kwargs={'installSignalHandlers':0})
    this_thread.daemon = True
    this_thread.start()
    
    #--->
    # setup http server
    
    Handler = http_handler
    httpd = ThreadedHTTPServer(("", PORT), Handler)
    
    #--->
    
    print "HTTP serving at port", PORT
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'

