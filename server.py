import socketio
import time
import gevent
from flask import Flask, Response
from flask_socketio import SocketIO
#from picamera import PiCamera
from io import BytesIO
from camera_output import CameraOutput
from drivers.servo import Servo
from drivers.lps2X import Barometer, BAROMETER_TYPE
from drivers.lps22 import LPS22

allow_launch = False

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='gevent')
servo = Servo(18)
barometer = LPS22()

def send_status(parachute_armed, parachute_deployed, is_launched = False):
    socketio.emit('status', { 'parachuteArmed': parachute_armed, 'parachuteDeployed': parachute_deployed, 'isLaunched': is_launched})

def send_rocket_data(altitude):
    socketio.emit('rocket-data', { 'timestamp': time.time(), 'altitude': altitude})
    
# Event handler for new connections
@socketio.event
def connect():
    print('Client connected')

# Event handler for messages
@socketio.event
def message(sid, data):
    print('message ', data)
    socketio.send(sid, f"Reply: {data}")

# Event handler for disconnections
@socketio.event
def disconnect():
    print('client disconnected')

@socketio.on('arm-parachute')
def arm_parachute():
    print('arm-parachute')

    send_status(True, False)

@socketio.on('disarm-parachute')
def arm_parachute():
    print('disarm-parachute')

    send_status(False, False)

@socketio.on('reset-parachute')
def arm_parachute():
    print('reset-parachute')

    send_status(False, False)

@socketio.on('deploy-parachute')
def arm_parachute():
    print('deploy-parachute')

    send_status(True, True)

@socketio.on('launch')
def launch():
    print('launch')
    send_status(True, True, True)
    
    global allow_launch 

    allow_launch = True
    gevent.sleep(5)
    
    if allow_launch:
        servo.right()
        gevent.sleep(2)
        servo.stop()
        allow_launch = False

@socketio.on('abort-launch')
def cancel_launch():
    print('abort launch')
    global allow_launch 
    allow_launch = False

# def record_video():
#     camera = PiCamera()
#     camera.resolution = (640, 480)
#     camera.start_recording(f'video{time.time()}.h264')
#     camera.wait_recording(60)
#     camera.stop_recording()

# def generate_camera_stream(output):
#     while True:
#         with output.condition:h264
#             output.condition.wait()
#             frame = output.frame
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# @app.route('/stream')
# def video_feed():
#     return Response(generate_camera_stream(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

def read_and_send_data():
    while True:
        print(barometer.altitude())
        send_rocket_data(1)
        gevent.sleep(1) # Send data every 1 second, change this

if __name__ == '__main__':
    output = CameraOutput(f'video-{time.time()}.h264', 'mjpeg')

    gevent.spawn(read_and_send_data)
    #gevent.spawn(record_video)

    socketio.run(app, port=5000, host='0.0.0.0', debug=False)