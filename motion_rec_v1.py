import imutils
import time
import cv2
import sys
import threading
import socket
import json
from ws4py.client.threadedclient import WebSocketClient

delta_thresh = 5
min_area = 5000
min_motion_frame = 8
image_output_path = '/root/python-server-for-fyp-pls-ignore/images/'
server = 'http://localhost/'

stream = sys.argv[1]
uid = 'motion detection service ' + str(time.time())
motion_counter = 0
avg = None
socket_class = None
websocket_ready = False

class DummyClient(WebSocketClient):
    
    def opened(self):
        print 'Connected to websocket of localhost/api'
        global socket_class
        global websocket_ready
        websocket_ready = True
        socket_class = self

    def closed(self, code, reason=None):
        global websocket_ready
        websocket_ready = False
        print "Closed down", code, reason

    def received_message(self, m):
        if m.is_text:
            m = m.data.decode("utf-8")
            print 'Websocket got:', m  

class service():

    def send(self, intent, to_send_dict):
        if websocket_ready:
            try:
                to_send_dict['uid'] = uid
                to_send_dict['hostname'] = socket.gethostname()
                to_send_dict['intent'] = intent
                socket_class.send(json.dumps(to_send_dict))
            except Exception as e:
                print 'Failed to send data to server with intent %s, error %s' % (intent, e)
        else:
            print 'Websocket not ready, not sending'
            
    def socket_init(self):
        while True:
            try:
                ws = DummyClient('ws://localhost/api', protocols=['http-only', 'chat'], headers=[('uid',uid),('type', 'INTERNAL_SERVICE')])
                ws.connect()
                s_thread = threading.Thread(target=ws.run_forever)
                s_thread.start()
                while s_thread.is_alive(): time.sleep(2)
            except Exception as e:
                print 'Oops, ws restarted ', e
                time.sleep(5)
  
    def __init__(self):
        self.server = server
        s_thread = threading.Thread(target=self.socket_init)
        s_thread.start()
        
api = service()


cap = cv2.VideoCapture()
cap.open(stream)

firstFrame = None
while True:
    
    ret, frame = cap.read()
    found = False
    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    if avg is None:
        print "[INFO] starting background model..."
        avg = gray.copy().astype("float")
        continue
        
    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
    
    thresh = cv2.threshold(frameDelta, delta_thresh, 255,
        cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
        
    for c in cnts:
        # if the contour is too small, ignore it
        if cv2.contourArea(c) < min_area:
            continue

        # compute the bounding box for the contour, draw it on the frame
        found = True
        
    if found:
        motion_counter += 1
        if motion_counter > min_motion_frame:
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            filename = str(time.time()) + '.jpg'
            print 'Write'
            cv2.imwrite(image_output_path + filename, frame)
            api.send('update', {'message': 'Movement detected  <img src="images/%s" class="movement">' % (filename)})
            motion_counter = 0
            
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
