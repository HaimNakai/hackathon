import socketio
import time
import gevent
from flask import Flask, Response
from flask_socketio import SocketIO
# from picamera import PiCamera
from io import BytesIO
from camera_output import CameraOutput
from drivers import servo
from drivers import lps25h
from drivers.lps2x_full import LPS25 
import board
import math

def pressure_to_altitude(pressure,temperature):
    # if pressure & (1 << 23) != 0:
    #     pressure = pressure - (1 << 24)
    # else:
    #     pressure = pressure / 4096.0
    
    return (((1013.25 / pressure)**(1/5.257)) - 1.0) * (temperature + 273.15) / 0.0065

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='gevent')

def send_status(parachute_armed, parachute_deployed):
    socketio.emit('status', { 'parachuteArmed': parachute_armed, 'parachuteDeployed': parachute_deployed})

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
def arm_parachute():
    print('launch')

# def record_video():
#     camera = PiCamera()
#     camera.resolution = (640, 480)
#     camera.start_recording(f'video{time.time()}.h264')
#     camera.wait_recording(60)
#     camera.stop_recording()

def generate_camera_stream(output):
    while True:
        with output.condition:
            output.condition.wait()
            frame = output.frame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/stream')
def video_feed():
    return Response(generate_camera_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

class Rocket:
    def __init__(self):
        print("started...")
        self.altlog = open("rocketLog.txt", "w")   # init log
        L = [" rocket logger \n"]
        self.altlog.writelines(L)   
        self.srv = servo.Servo(17)                 # init servo
        self.barometer = LPS25(board.I2C())        # init barometer

        pressure = int(self.barometer.pressure)
        temperature = self.barometer.temperature
        self.max_alt = int(pressure_to_altitude(pressure,temperature))
        self.ground_alt = self.max_alt
        # params
        self.altDiff_to_start = 2
        self.diff_to_update_counter = 1
        self.rate = 0.5
        self.max_count_to_deploy = 4
        self.counter = 0                        

        print("ground alt: ", self.ground_alt)
        print("")

    def update_alt(self):
        pressure = int(self.arometer.pressure)
        temperature = self.barometer.temperature
        self.cur_alt = int(pressure_to_altitude(pressure,temperature))
        
        self.altlog.writelines(str(self.cur_alt))
        print("cur_alt: ",str(self.cur_alt), "pressure: ",pressure )

    def deploy(self):
        self.altlog.writelines("deploying parachute")
        print("deploying parachute, max:", self.max_alt)
        self.srv.right()
        gevent.sleep(2)
        self.srv.stop()
        self.altlog.close()

    def read_and_send_data(self):
        while True:
            self.update_alt
            if (self.ground_alt + self.altDiff_to_start) < self.cur_alt:
                self.altlog("\nrocket launched...\n")
                break

        try:
            while True:
                self.update_alt()

                if self.cur_alt > self.max_alt:
                    self.max_alt = self.cur_alt
                    self.counter = 0
                    print("max_alt: ",str(self.max_alt),"counter: ", self.counter)

                if self.cur_alt < (self.max_alt + self.diff_to_update_counter):
                    self.counter += 1

                if self.counter > self.max_count_to_deploy:
                    self.deploy()            
                    break
                
                send_rocket_data(1)
                gevent.sleep(self.rate) # Send data every 1 second, change this

        except KeyboardInterrupt:
                print("closed file")
                self.altlog.close()

if __name__ == '__main__':
    output = CameraOutput(f'video-{time.time()}.h264', 'mjpeg')

    rocket = Rocket()

    gevent.spawn(rocket.read_and_send_data())
    #gevent.spawn(record_video)

    socketio.run(app, port=5000, host='0.0.0.0', debug=False)