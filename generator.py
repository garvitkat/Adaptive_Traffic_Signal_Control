from __future__ import print_function
from sumolib import checkBinary

import os
import sys
import optparse
import subprocess
import random
import traci
import random
import numpy as np
import keras
import h5py
from collections import deque
from keras.layers import Input, Conv2D, Flatten, Dense
from keras.models import Model

class SumoIntersection:
    def __init__(self):
        # we need to import python modules from the $SUMO_HOME/tools directory
        try:
            sys.path.append(os.path.join(os.path.dirname(
                __file__), '..', '..', '..', '..', "tools"))  # tutorial in tests
            sys.path.append(os.path.join(os.environ.get("SUMO_HOME", os.path.join(
                os.path.dirname(__file__), "..", "..", "..")), "tools"))  # tutorial in docs
            from sumolib import checkBinary  # noqa
        except ImportError:
            sys.exit(
                "please declare environment variable 'SUMO_HOME' as the root directory of your sumo installation (it should contain folders 'bin', 'tools' and 'docs')")

    def routeFileGenerator(self):
        random.seed(42)  # make tests reproducible
        N = 3600  # number of time steps
        # demand per second from different directions
        pH = 1. / 7
        pV = 1. / 11
        pAR = 1. / 30
        pAL = 1. / 25
        with open("input_routes.rou.xml", "w") as routes:
            print('''<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    <vType id="SUMO_DEFAULT_TYPE" accel="0.8" decel="4.5" sigma="0" length="5" minGap="2" maxSpeed="70"/>
    <route id="always_right" edges="1fi 1si 4o 4fi 4si 2o 2fi 2si 3o 3fi 3si 1o 1fi"/>
    <route id="always_left" edges="3fi 3si 2o 2fi 2si 4o 4fi 4si 1o 1fi 1si 3o 3fi"/>
    <route id="horizontal" edges="2fi 2si 1o 1fi 1si 2o 2fi"/>
    <route id="vertical" edges="3fi 3si 4o 4fi 4si 3o 3fi"/>

    ''', file=routes)
            lastVehicle = 0
            vehicleNumber = 0
            for i in range(N):
                if random.uniform(0, 1) < pH:
                    print('    <vehicle id="right_%i" type="SUMO_DEFAULT_TYPE" route="horizontal" depart="%i" />' % (
                        vehicleNumber, i), file=routes)
                    vehicleNumber += 1
                    lastVehicle = i
                if random.uniform(0, 1) < pV:
                    print('    <vehicle id="left_%i" type="SUMO_DEFAULT_TYPE" route="vertical" depart="%i" />' % (
                        vehicleNumber, i), file=routes)
                    vehicleNumber += 1
                    lastVehicle = i
                if random.uniform(0, 1) < pAL:
                    print('    <vehicle id="down_%i" type="SUMO_DEFAULT_TYPE" route="always_left" depart="%i" color="1,0,0"/>' % (
                        vehicleNumber, i), file=routes)
                    vehicleNumber += 1
                    lastVehicle = i
                if random.uniform(0, 1) < pAR:
                    print('    <vehicle id="down_%i" type="SUMO_DEFAULT_TYPE" route="always_right" depart="%i" color="1,0,0"/>' % (
                        vehicleNumber, i), file=routes)
                    vehicleNumber += 1
                    lastVehicle = i
            print("</routes>", file=routes)

    def getOptions(self):
        optParser = optparse.OptionParser()
        optParser.add_option("--nogui", action="store_true",
                             default=False, help="run the commandline version of sumo")
        options, args = optParser.parse_args()
        return options

    def getState(self):
        positionMatrix = []
        velocityMatrix = []

        cellLength = 7
        offset = 11
        speedLimit = 14

        junctionPosition = traci.junction.getPosition('0')[0]
        vehiclesAtRoad1 = traci.edge.getLastStepVehicleIDs('1si')
        vehiclesAtRoad2 = traci.edge.getLastStepVehicleIDs('2si')
        vehiclesAtRoad3 = traci.edge.getLastStepVehicleIDs('3si')
        vehiclesAtRoad4 = traci.edge.getLastStepVehicleIDs('4si')
        for i in range(12):
            positionMatrix.append([])
            velocityMatrix.append([])
            for j in range(12):
                positionMatrix[i].append(0)
                velocityMatrix[i].append(0)

        for v in vehiclesAtRoad1:
            ind = int(
                abs((junctionPosition - traci.vehicle.getPosition(v)[0] - offset)) / cellLength)
            if(ind < 12):
                positionMatrix[2 - traci.vehicle.getLaneIndex(v)][11 - ind] = 1
                velocityMatrix[2 - traci.vehicle.getLaneIndex(
                    v)][11 - ind] = traci.vehicle.getSpeed(v) / speedLimit

        for v in vehiclesAtRoad2:
            ind = int(
                abs((junctionPosition - traci.vehicle.getPosition(v)[0] + offset)) / cellLength)
            if(ind < 12):
                positionMatrix[3 + traci.vehicle.getLaneIndex(v)][ind] = 1
                velocityMatrix[3 + traci.vehicle.getLaneIndex(
                    v)][ind] = traci.vehicle.getSpeed(v) / speedLimit

        junctionPosition = traci.junction.getPosition('0')[1]
        for v in vehiclesAtRoad3:
            ind = int(
                abs((junctionPosition - traci.vehicle.getPosition(v)[1] - offset)) / cellLength)
            if(ind < 12):
                positionMatrix[6 + 2 -
                               traci.vehicle.getLaneIndex(v)][11 - ind] = 1
                velocityMatrix[6 + 2 - traci.vehicle.getLaneIndex(
                    v)][11 - ind] = traci.vehicle.getSpeed(v) / speedLimit

        for v in vehiclesAtRoad4:
            ind = int(
                abs((junctionPosition - traci.vehicle.getPosition(v)[1] + offset)) / cellLength)
            if(ind < 12):
                positionMatrix[9 + traci.vehicle.getLaneIndex(v)][ind] = 1
                velocityMatrix[9 + traci.vehicle.getLaneIndex(
                    v)][ind] = traci.vehicle.getSpeed(v) / speedLimit

        signalLight = []
        if(traci.trafficlight.getPhase('0') == 4):
            signalLight = [1, 0]
        else:
            signalLight = [0, 1]

        position = np.array(positionMatrix)
        position = position.reshape(1, 12, 12, 1)

        velocity = np.array(velocityMatrix)
        velocity = velocity.reshape(1, 12, 12, 1)

        lgts = np.array(signalLight)
        lgts = lgts.reshape(1, 2, 1)

        return [position, velocity, lgts]