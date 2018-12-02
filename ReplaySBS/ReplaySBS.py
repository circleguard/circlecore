from osrparse import parse_replay_file
import os
from os import listdir
from os.path import isfile, join
import difflib
import math

#Paths to replays
pathToUserReplay = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\userReplay\\"

pathToOtherReplays = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\otherReplays\\"


averageDistances = [] #Stores the average distances between the user's replay and the all the ones it was checked against
flaggedReplays = [] #if the average distance is really low, store it here
cheatedReplays = [] #if the average distance is so low, there is no chance its legit
    
def checkDiffInReplays():
    
    
    userOsrList = [f for f in listdir(pathToUserReplay) if isfile(join(pathToUserReplay, f))]
    
    userCorrds = [] # Where the coordinates of the user's replay will be stored
    otherCoords = [] # Where the coordinates of the other replays will be stored

    
    # Parse user replay
    for userOsr in userOsrList: #For every user replay (should only be one for now)
        userOsr = pathToUserReplay + userOsr
        print("User Osr: " + userOsr)
        userReplay = parse_replay_file(userOsr)
        playData = userReplay.play_data
        
        for play in playData:
             userCorrds.append((play.x, play.y))
            
        parseOtherReplays(userCorrds) #parses the other replay, then checks for similarity
        
    
def parseOtherReplays(userCoords): # Parse other replays
    osrList = [f for f in listdir(pathToOtherReplays) if isfile(join(pathToOtherReplays, f))]
    for osr in osrList:
        
        otherCoords = []
        
        print("Replay Osr: " + osr)
        osr = pathToOtherReplays + osr
        
        replay = parse_replay_file(osr)
        playData = replay.play_data
        
        for play in playData:
            otherCoords.append((play.x, play.y))
    
        averageDistance = (computeSimilarity(userCoords, otherCoords))
        
        averageDistances.append((averageDistance, osr)) #appends the osr filename and the average distance 

        if averageDistance < 60: 
            flaggedReplays.append((averageDistance, osr))

        if averageDistance < 30:
            cheatedReplays.append((averageDistance, osr))
        
        print("Average distance is " +str(averageDistance))
    
    return otherCoords
            
            
def computeSimilarity(userCoords, otherCoords ): # Calculates distance between the cursor between the users replay and the other replay
   
    distances = []
    totalDistance = 0
    
    allCoords = list(zip(userCoords, otherCoords)) # Combines the replay coordinates from both replays into one list so we can iterate through it at the same time

    length = int(len(allCoords) *0.10) # Use this to set the length of the replays you want to compare. I found bugs if the entire replay is used due to outliers at the very end skewing the average
    
    for i in range(length):
        
        #print("Both")
        #print(allCoords[i]) # prints the list of both replays coordinates at that frame
        #print("User Coords")
        #print(allCoords[i][0]) # [i][0] use to access user coords | [i][1]  to access other replay's coords
        
        #print(allCoords[i][0][1]) # user coords x value
        #print(allCoords[i][0][1]) # user coords y value
        #print("Other Coords") 
        #print(allCoords[i][1]) # used to access other replay's coords
        #print(allCoords[i][1][0]) # other coords x
        #print(allCoords[i][1][1]) # other coords y
        
        x2 = allCoords[i][0][0] # user coords x
        x1 = allCoords[i][1][0] # other coords x
        
        y2 = allCoords[i][0][1] # user coords y
        y1 = allCoords[i][1][1] # other coords y
        
        distance = math.sqrt((x2 - x1)**2 + (y2- y1)**2) #uses distance formula to compute difference in the cursor values between the replays. May use different algorithm later
        
        print(distance)

        distances.append(distance)

    # calculates and returns the average distance of the points
    for i in range(len(distances)):
        totalDistance = totalDistance + distances[i]
    
    averageDistance = (totalDistance/len(distances))
     
    return averageDistance
    


checkDiffInReplays()

#Summary of findings, needs to be cleaned up
print("")
print("SUMMARY OF FINDINGS")
print("Here are the certainly stolen replays")
for i in range(len(cheatedReplays)):
    print(cheatedReplays[i])

print("Here are the sketchy replays, need manual verification")

for i in range(len(flaggedReplays)):
    print(flaggedReplays[i])

#All replays 
#for i in range(len(averageDistances)):
    #print(averageDistances[i]) #prints all the average distances