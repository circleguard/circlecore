from osrparse import parse_replay_file
import os
from os import listdir
from os.path import isfile, join
import difflib
import math

#This program compares a user's replay with others in order to see how close the cursor movement is to eachother
#The test replays here are Cookiezi's Timefreeze  FC, _Ryuk's FC, and a replay botted copy of Cookiezi's FC
#The distances of the x and y coordinates of each play are compared against eachother
#The average distance of the cursor between the legit and copied Cookiezi play is about 13 pixels
#The average distance of the cursor between the legit _Ryuk play and Cookiezi play is about 156 pixels



def checkDiffInReplays():
    
    replays = []
    userOsrList = [f for f in listdir("E:\\testing") if isfile(join("E:\\testing", f))]
    
    userCorrds = [] # Where the coordinates of the user's replay will be stored
    otherCoords = [] # Where the coordinates of the other replays will be stored

    # Parse user replay
    for userOsr in userOsrList:
        userOsr = "E:\\testing\\" + userOsr
        print("User Osr: " + userOsr)
        userReplay = parse_replay_file(userOsr)
        playData = userReplay.play_data
        
        for play in playData:
             userCorrds.append((play.x, play.y))
            
           
        #for i in range(len(userCorrds)):
            #print(userCorrds[i])

        otherCoords = parseOtherReplays()

        #for i in range(len(otherCoords)):
            #print(otherCoords[i])


    averageDistance = computeSimilarity(userCorrds, otherCoords)

    print("Average Distance " +str(averageDistance))
    print(len(userCorrds))
    print(len(otherCoords))


def parseOtherReplays(): # Parse other replays
    osrList = [f for f in listdir("E:\\testing\\compareReplays") if isfile(join("E:\\testing\\compareReplays", f))]
    for osr in osrList:
        replayXs = []
        replayYs = []

        otherCoords = []
        
        print("Replay Osr: " + osr)
        osr = "E:\\testing\\compareReplays\\" + osr
        replay = parse_replay_file(osr)
        playData = replay.play_data
        for play in playData:
            replayXs = replayXs + [play.x]
            replayYs = replayYs + [play.y]

            otherCoords.append((play.x, play.y))
    
    return otherCoords
            
            
def computeSimilarity(userCoords, otherCoords ): #Calculates distance between the cursor between the users replay and the other replay
   
    distances = []
    totalDistance = 0
    
    allCoords = list(zip(userCoords, otherCoords))

    length = int(len(allCoords) *0.10)
    for i in range(length):
        
        #print("Both")
        #print(allCoords[i])
        #print("User Coords")
        #print(allCoords[i][0]) #[i][0] user coords [i][1] other coords
        
        #print(allCoords[i][0][1]) #user coords x value, y value would be [i][0][1]
        
        #print("Other Coords")
        #print(allCoords[i][1])
        #print(allCoords[i][1][0]) #other coords x
        #print(allCoords[i][1][1]) #other coords y
        
        x2 = allCoords[i][0][0] #user coords x
        x1 = allCoords[i][1][0] #other coords x
        
        y2 = allCoords[i][0][1] #user coords y
        y1 = allCoords[i][1][1] #other coords y
        
        distance = math.sqrt((x2 - x1)**2 + (y2- y1)**2)
        print(distance)

        distances.append(distance)

    for i in range(len(distances)):
        totalDistance = totalDistance + distances[i]
    
    averageDistance = (totalDistance/len(distances))



    return averageDistance
    

    




checkDiffInReplays()