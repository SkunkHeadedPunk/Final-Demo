#!/usr/bin/env python
"""Computer Vision module for Final-Demo. SEED Lab: Group 007.

REQUIREMENTS AND COMPATIBILITY:
Requires install of numpy, picamera, time, math, and opencv. 
Built for Raspberry Pi Camera Module v2, but works with other picameras.
This file uses essential camera calibration data from the
'CV_CameraCalibrationData.npz' file created by 'CV_CameraCalibration.py',
and an optional value from the file 'CV_ZeroAngle.npz', created by
'CV_ZeroAngleCalibration.py' for calibrating the zero angle. The camera
calibration matrices need to be updated using the respective file for any new
camera, and the zero angle value needs to be updated any time you reposition
the camera.

PURPOSE AND METHODS:
This program uses computer vision techniques and opencv to capture a stream of
images and detect Aruco markers. In stage0, the program captures continuous
images at high speed using the 'sports' exposure mode to reduce blur while the
robot rotates in place. Once an Aruco marker is detected, a signal is sent to
stop the robot from rotating, and Opencv tequniques are used to get the
translation vector to the Aruco marker. X and Z values from the translation
vector are used to calculate distance to the marker, and also calculate the
angle from the camera to the marker using trigonometry and math functions. The
timing module is used to measure the FPS in state0 for testing.

INSTRUCTIONS:
Set 'DISP_STREAM_UNDETECTED' to 'True' in order to view the stream of images as
they are captured in state0. Set 'DISP_STREAM_DETECTED' to 'True' in order to
view the final capture in state0 where the marker is first detected. This image
remains open when it is viewed, whereas the undetected stream automatically
closes upon detection. Set 'DISP_PRECISE_IMG' to 'True' in order to view the
image captured in state1 once the robot has stopped spinning. This is the image
which distance and angle calculations are performed on. The waitkey for each set
of displays can be adjusted as needed just below their T/F selection lines.

Set the global variable 'USE_CALIB_ANGLE' to 'True' in order to use the zero
angle calibration. The zero angle calibration should be performed every time
you move the camera module. The calibration angle can be updated using the file
'CV_ZeroAngle.py'. Set 'USE_CALIB_ANGLE' to 'False' if the value has not been
updated.

OUTPUTS:
The detected angle from the camera to the Aruco marker is given in degrees
in the 'main' function as 'angle_deg', and the detected distance is given in
inches in the 'main' function as 'distance'. These values are also sent in
'main' to the Arduino.
"""

__author__ = "Jack Woolery and Jeffrey Hostetter"
__email__ = "lwoolery@mines.edu, "

from picamera.array import PiRGBArray
from picamera import PiCamera
import picamera
import time
from time import time
import cv2 as cv
import numpy as np
import math
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd
import smbus
import busio
import board

# I2C INITIALIZATION
bus = smbus.SMBus(1)
i2c = busio.I2C(board.SCL, board.SDA)

# INITIALIZATION OF ARRAY TO SEND TO ARDUINO
dataToArduino = [0, 180, 0]

# LCD INITIALIZATION
##lcd_columns = 16
##lcd_rows = 2
##lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
##lcd.clear()
##lcd.color = [100, 0, 100]
##lcd.message("DiNgUS")

address = 0x04

# FOR ZERO ANGLE CALIBRATION
USE_CALIB_ANGLE = False

##CALIB_ANGLE_FILE = np.load('CV_ZeroAngle.npz')
##CALIB_ANGLE = - CALIB_ANGLE_FILE['zero_angle']

# DISTANCE TO THE RIGHT OF MARKER
R_DIST = 8

# TO DISPLAY STREAM IMAGES (state0)
DISP_STREAM_UNDETECTED = False
STREAM_UNDETECTED_WAITKEY = 1
DISP_STREAM_DETECTED = True
STREAM_DETECTED_WAITKEY = 1
# TO DISPLAY PRECISE IMAGE (state1)
DISP_PRECISE_IMG = True
PRECISE_IMG_WAITKEY = 100

# Measured Aruco marker length in inches
##MARKER_LENGTH_IN = 50 / 25.4    # Tiny test marker
##MARKER_LENGTH_IN = 3.8125       # Small marker
##MARKER_LENGTH_IN = 7.75         # Large marker
##MARKER_LENGTH_IN = 185 / 25.4   # Demo-2 Markers
MARKER_LENGTH_IN = 90 / 25.4    # "100mm Marker"

# Image capture dimensions
# Max res: 3280 x 2464
# MAX WORKING DIMENSIONS
WIDTH, HEIGHT = 640, 480
width, height = str(WIDTH), str(HEIGHT)

# Get the Aruco dictionary
arucoDict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_7X7_100)

# Load camera properties matrices from file
# This file is generated from the camera calibration
KD = np.load('CV_CameraCalibrationData.npz')
K = KD['k']
DIST_COEFFS = KD['dist']

# Text settings
FONT = cv.FONT_HERSHEY_SIMPLEX
FONTSCALE = 1
THICKNESS = 2
LINETYPE = cv.LINE_AA


####### FUNCTION FOR WRITING ARRAY TO ARDUINO #######
def writeBlock(block):
    try:
        bus.write_i2c_block_data(address, 1, block)
        #lcd.message = "Sent: " + userString + "\
    except:
        print("%%%%%%%%%%I2C Error%%%%%%%%%%%")
        print("%%%%%%%%%%I2C Error%%%%%%%%%%%")
        print("%%%%%%%%%%I2C Error%%%%%%%%%%%")
        print("%%%%%%%%%%I2C Error%%%%%%%%%%%")
        print("%%%%%%%%%%I2C Error%%%%%%%%%%%")
        print("%%%%%%%%%%I2C Error%%%%%%%%%%%")
        print("%%%%%%%%%%I2C Error%%%%%%%%%%%")


####### FUNCTION FOR WRITING A NUMBER TO THE ARDUINO #######
def writeNumber(num):
    try:
        bus.write_byte_data(address, 0, num)
    except:
        print("I2C Error")
    return -1


####### FUNCTION FOR READING A NUMBER FROM THE ARDUINO #######
def readNumber():
    try:
        number = bus.read_byte(address)
        return number
    except:
        print("I2C Error")
        return 0



# Gets runtime / FPS data
def get_timing(start_time):
    runtime = time() - start_time
    fps = 1 / runtime
    fps = round(fps, 3)
    print("FPS: ", fps)
    print("\n")
    return fps


# Gets distance and angle to Aruco marker
def get_vals(corners, newCamMtx, mult_marks_det, ids, img):
    # Get rotation and translation vectors with respect to marker
    rvecs, tvecs, _ = cv.aruco.estimatePoseSingleMarkers(
        corners,
        markerLength = MARKER_LENGTH_IN,
        cameraMatrix = newCamMtx,
        distCoeffs = 0
        )

    d_array = []
    # Unpack translation vector
    # This vector contains x, y, z distances of tag from camera
    inc = 0
    print("tvecs: ", tvecs)
    for tag in ids:
        tvec = tvecs[inc][0]
        print("tvec: ", tvec)
        # Calculate distance using the root of the sum of the squares
        distance = math.sqrt(tvec[0] ** 2 + tvec[2] ** 2)
        print("distance: ", round(distance, 2), "inches")
        d_array.append(distance)
        inc = inc + 1

    mark_inc = d_array.index(min(d_array))
    next_id = ids[mark_inc]
    print("Next ID: ", next_id)

    # Calculate angle using trigonometry with distance values
    angle_rad = np.arctan(tvec[0] / tvec[2])
    angle_rad = - angle_rad
    # if USE_CALIB_ANGLE is True:
    #     angle_rad = angle_rad + CALIB_ANGLE
    angle_deg = angle_rad * 180 / math.pi
    print("angle: ", round(angle_deg, 2), "degrees;     ",
          round(angle_rad, 2), "radians")

    # distance, angle_rad, angle_deg = get_adj_vals(rvecs, tvecs)
    adj_dist, adj_angle_rad, adj_angle_deg, img = get_adj_vals(rvecs, tvecs, mark_inc, mult_marks_det, img)
    
    return adj_dist, adj_angle_rad, adj_angle_deg, img


# Gets distance and angle for trajectory to the right of marker
def get_adj_vals(rvecs, tvecs, mark_inc, mult_marks_det, img):
    # Matrix for destination point with respect to marker
    p_m = np.array([[R_DIST], [0], [0], [1]])
    # Reorganize tvecs for block function
    tvecs = np.array([tvecs]).T

    # If multiple markers are detected...
    if mult_marks_det == True:
        # Save rvec and tvec of single correct marker
        rvec = rvecs[mark_inc]
        tvec = np.zeros((3, 1))
        for t in range(3):
            tvec[t] = tvecs[t][0][mark_inc]
        
    # If single correct marker is detected...
    if mult_marks_det == False:
        tvec = tvecs
        rvec = rvecs
        
    # Get rotation matrix
    R = cv.Rodrigues(rvec)[0]
    
    # Create homography matrix
##    H = np.block([[R, tvec], [0, 0, 0, 1]]) # Does not work with version
    H = np.zeros((4, 4))
    for i in range(3):
        for j in range(3):
            H[i][j] = R[i][j]
            if i == 3:
                H[i][j] = 0
    H[3][3] = 1
    for k in range(3):
        H[k][3] = tvec[k]

    # Get destination point with respect to camera
    p_c = np.array(H @ p_m)
    print("p_c: ", p_c)

    Mext = H[0:3, :]
    p_v = K @ Mext @ p_c
    print("p_v: ", p_v)
    print("p_v[0]: ", p_v[0])
    cv.drawMarker(img, (int(p_v[1][0]), int(p_v[0][0])), (0, 0, 255), cv.MARKER_CROSS, 20, 1, 8)


    
    # Calculate distance to destination point
    distance = math.sqrt(p_c[0] ** 2 + p_c[2] ** 2)
    dist_send = int(round(distance))
    print("transform dist: ", dist_send, "inches")
    # Calculate angle to destination point
    angle_rad = np.arctan(p_c[0] / p_c[2])
    angle_rad = - angle_rad
    angle_deg = angle_rad * 180 / math.pi
    angle_send = int(np.round(angle_deg)[0])
    print("transform angle: ", angle_send, "degrees")

    return dist_send, angle_rad, angle_send, img


def state0(state, img):
    print("Running State 0")
                
    # Detect if Aruco marker is present
    corners, ids, _ = cv.aruco.detectMarkers(image=img,
                                             dictionary=arucoDict,
                                             cameraMatrix=K,
                                             distCoeff=DIST_COEFFS
                                            )
    # If marker not detected...
    if ids is None:
        print("Beacon not detected")
        
        # Optional stream display
        if DISP_STREAM_UNDETECTED is True:
            cv.imshow("Stream - undetected", img)
            cv.waitKey(STREAM_UNDETECTED_WAITKEY)

    # If marker detected...
    if ids is not None:
        for tag in ids:
            print("----------BEACON DETECTED STATE 0----------")
            # Change to next state
            state = 1

        # Optional stream detected display
        if DISP_STREAM_DETECTED is True:
            for tag in ids:
                cv.aruco.drawDetectedMarkers(image=img,
                                             corners=corners,
                                             ids=ids,
                                             borderColor=(0, 0, 255)
                                            )
                # Display image from time of initial state0 detection
                cv.imshow("Stream - DETECTED", img)
                cv.waitKey(STREAM_DETECTED_WAITKEY)
                
            try:
                cv.destroyWindow("Stream - undetected")
            except:
                print("")

    return state


def state1(img):
    print("Running State 1")
    # Return zeros
    angle_deg = 180
    angle_rad = math.pi
    distance = 0
    
    # Get new camera matrix
    newCamMtx, roi = cv.getOptimalNewCameraMatrix(cameraMatrix=K,
                                                  distCoeffs=DIST_COEFFS,
                                                  imageSize=(WIDTH, HEIGHT),
                                                  alpha=1,
                                                  newImgSize=(WIDTH, HEIGHT)
                                                  )
    # Create undistorted, corrected image
    corr_img = cv.undistort(img, K, DIST_COEFFS, None, newCamMtx)

    # Detect Aruco marker corners and IDs
    corners, ids, _ = cv.aruco.detectMarkers(image=corr_img,
                                             dictionary=arucoDict,
                                             cameraMatrix=newCamMtx,
                                             distCoeff=0
                                             )

    # If marker detected...
    if ids is not None:
        print("Detected IDs: ", ids)
        # Initialize variables
        mult_marks_det = False
        count = 0

        for tag in ids:
            # Perform subpixel corner detection
            gray_img = cv.cvtColor(corr_img, cv.COLOR_BGR2GRAY)

            criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER,
                        100,
                        0.0001
                        )
            for corner in corners:
                cv.cornerSubPix(image=gray_img,
                                corners=corner,
                                winSize=(2, 2),
                                zeroZone=(-1, -1),
                                criteria=criteria
                                )
            if count > 0:
                mult_marks_det = True
            count = count + 1
            
            
        # Frame detected markers
        img = cv.aruco.drawDetectedMarkers(corr_img, corners, ids)
            

        # Get distance and angle to marker
        distance, angle_rad, angle_deg, img = get_vals(corners,
                                                       newCamMtx,
                                                       mult_marks_det,
                                                       ids,
                                                       img
                                                       )
        str_dist = str(distance)
        str_ang = str(angle_deg)
        cv.putText(img, "Dist: "+str_dist, (5, 25), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv.LINE_AA)
        cv.putText(img, "Angle: "+str_ang, (5, 50), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv.LINE_AA)

    # If marker not detected...
    if ids is None:
        print("Marker not detected - State 1")

    # Optional display stream images
    if DISP_PRECISE_IMG is True:
        # Display image
        cv.imshow("Precise Img", img)
        cv.waitKey(PRECISE_IMG_WAITKEY)
        
    return distance, angle_deg, angle_rad
  
            
if __name__ == '__main__':
    # Initialize variables
    state = 0
    start = time()
    fps_arr = []
    mark_num = 0

    # Initialize camera
    camera = PiCamera()
    camera.resolution = (WIDTH, HEIGHT)
    camera.exposure_mode = 'sports'
    rawCapture = PiRGBArray(camera, size=(WIDTH, HEIGHT))

    # For each frame captured...
    for frame in camera.capture_continuous(rawCapture,
                                           format="bgr",
                                           use_video_port=True
                                           ):
        # Start frame timer
        start_time = time()
        # Get state from Arduino
        state = readNumber()
        # Get and display stream images
        img = frame.array
        str_state = str(state)
        str_mark = str(mark_num)
        cv.putText(img, "Marker Stage: "+str_state, (5, 475), FONT, FONTSCALE, (0, 0, 0), THICKNESS, LINETYPE)        
        cv.putText(img, "State: "+str_mark, (500, 475), FONT, FONTSCALE, (0, 0, 0), THICKNESS, LINETYPE)
        cv.imshow("Main Stream", img)
        cv.waitKey(1)
        rawCapture.truncate(0)

        # State0: Rotate robot and search continuously for marker
        if state == 0 or state == 5:
            # Default distance and angle
            distance = 0
            angle_deg = 180
            # Run State 0 continuous detection on img
            state_send = state0(state, img)

            ###### SEND STATE 1 TO ARDUINO ######
            if state_send == 1:
                print("SENDING STATE 1 TO ARDUINO")
                dataToArduino[0] = state_send
                writeBlock(dataToArduino)
                state_send = 0
                
    

        # State 1: Robot has stopped; capture still photo, send dist & angle
        if state == 1:
            # Run State 1 precise detection and get distance & angle values
            dist_send, angle_send, angle_rad = state1(img)

            # If correct beacon is detected...
            if dist_send != 0:
                # Increment marker ID
                mark_num = mark_num + 1
                # Proceed to next state
                state = 2

                ###### SEND DISTANCE AND ANGLE TO ARDUINO ######
                print("Sending angle and distance")
##                try:
##                    print("int(np.round(angle_deg + 31)[0]: ", int(np.round(angle_deg + 31)[0]))
##                    angle_send = int(np.round(angle_deg + 31)[0])
##                except:
##                    print("int(np.round(angle_deg + 31)): ", int(np.round(angle_deg + 31)))
##                    angle_send = int(np.round(angle_deg + 31))
            
                dataToArduino[1] = angle_send + 31
##                dist_send = int(round(distance))
                dataToArduino[2] = dist_send
##                writeBlock(dataToArduino)
                ###### SEND STATE 2 TO ARDUINO ######
                dataToArduino[0] = state
                writeBlock(dataToArduino)

        else:
            print("State ", state)

        # Final state
        if state == 6:
            cv.destroyAllWindows()
            break

