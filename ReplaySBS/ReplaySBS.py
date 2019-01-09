from osrparse import parse_replay_file
import os
from os import listdir
from os.path import isfile, join
import difflib
import math
import json

#Paths
pathToUserReplay = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\userReplay\\"
pathToOtherReplays = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\otherReplays\\"

userOsrList = [f for f in listdir(pathToUserReplay) if isfile(join(pathToUserReplay, f))]
osrList = [f for f in listdir(pathToOtherReplays) if isfile(join(pathToOtherReplays, f))]
averageDistances = []

class ReplayInstance:
    def __init__(self,userReplay, otherReplay):
        self.userReplay = userReplay
        self.otherReplay = otherReplay
        self.userReplayEvent = userReplay.play_data
        self.otherReplayEvent = otherReplay.play_data
        

    def computeSimilarity(self):
        userCoords = []
        otherCoords = []
        distances = []
        flippedDistances = []
        totalDistance = 0
        totalFlippedDistance = 0
        hardRockFlag = 0
        averageDistance = 0


        players = self.userReplay.player_name + " vs " +self.otherReplay.player_name
        
        userReplayData = self.userReplay.play_data
        otherReplayData = self.otherReplay.play_data

        for data in otherReplayData:
            otherCoords.append((data.x, data.y))
        for data in userReplayData:
            userCoords.append((data.x, data.y))
        
        
        allCoords = list(zip(userCoords, otherCoords))
        #print(allCoords)

        length = int(len(allCoords) * 0.10)
        #print("The length of all coords is" +str(length))

        for i in range(length):
            x2 = allCoords[i][0][0]
            x1 = allCoords[i][1][0]
            y2 = allCoords[i][0][1]
            y1 = allCoords[i][1][1]

            

            flippedY = (192-y2) +192
            distance = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            #print("Distance is " +str(distance))
            flippedDistance = math.sqrt((x2-x1)**2 + (flippedY - y1)**2)
            distances.append(distance)
            flippedDistances.append(flippedDistance)
            
            
            #calculates and returns the average distance of the points

        for i in range(len(distances)):
            totalDistance = totalDistance + distances[i]
            totalFlippedDistance = totalFlippedDistance + flippedDistances[i]
            
        #print("Total" +str(totalDistance))    
        averageDistance = (totalDistance/len(distances))
        #print(averageDistance)
        #print(len(distances))
        averageFlippedDistance = (totalFlippedDistance/len(distances))

        #Checks the normal play and a flipped version to compare against HR plays

        if averageDistance < averageFlippedDistance:
            averageDistances.append(str(averageDistance) + " " + players)
        else:
            averageDistances.append(str(averageFlippedDistance) + " " + players)
            hardRockFlag = 1

        return averageDistance
 
    def getSummary(self):
        print("SUMMARY OF FINDINGS")
        print("")
        for i in range(len(averageDistances)):
            print(averageDistances[i])
            print("")


def main():
    
    for userOsr in userOsrList:
        userOsr = pathToUserReplay + userOsr
        userReplay = parse_replay_file(userOsr)
    
    for osr in osrList:
        osr = pathToOtherReplays + osr
        otherReplay = parse_replay_file(osr)
   
        replayInstance = ReplayInstance(userReplay,otherReplay)
        replayInstance.computeSimilarity()
        replayInstance.getSummary()

if __name__ == '__main__':
    main()
