



from osrparse import parse_replay_file
import os
from os import listdir
from os.path import isfile, join
import difflib
import math
import json

#This program compares a user's replay with others in order to see how close the cursor movement is to eachother
#The test replays here are Cookiezi's Timefreeze  FC, _Ryuk's FC, and a replay botted copy of Cookiezi's FC
#The distances of the x and y coordinates of each play are compared against each-other
#The average distance of the cursor between the legit and copied Cookiezi play is about 13 pixels
#The average distance of the cursor between the legit _Ryuk play and Cookiezi play is about 156 pixels

pathToUserReplay = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\userReplay\\"

pathToOtherReplays = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\otherReplays\\"


averageDistances = [] #Stores the average distances between the user's replay and the all the ones it was checked against
flippedDistances = [] #used to store the distances of flipped coordinates of user's replays

with open("apikeys.json") as apikeys:
    keys = json.load(apikeys)

key = keys['osu_apikey']
mainApi = 'https://osu.ppy.sh/api/'

    
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
        
    
def parseOtherReplays(usersCoords): # Parse other replays
    osrList = [f for f in listdir(pathToOtherReplays) if isfile(join(pathToOtherReplays, f))]
    #print(osrList)
    for osr in osrList:
        
        otherCoords = []
        
        print("Replay Osr: " + osr)
        print("")
        osr = pathToOtherReplays + osr
        
        replay = parse_replay_file(osr)
        playData = replay.play_data
        
        for play in playData:
            otherCoords.append((play.x, play.y))
    
        averageDistance = (computeSimilarity(usersCoords, otherCoords))
        
        averageDistances.append((averageDistance, osr)) #appends the osr filename and the average distance 
        
    
        print("Average distance is " +str(averageDistance))
        print("")
    
    return 0
            
            
def computeSimilarity(userCoords, otherCoords ): # Calculates distance between the cursor between the users replay and the other replay
   
    distances = []
    totalDistance = 0
    totalFlippedDistance = 0
    
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
        
        flippedY = (190-y2 ) + 190 #converts the replay's y value to the HR y value
        
        #print("")
        #print("userFlipped " + str(x2), str(flippedY))
        #print("userNormal " +str(x2), str(y2))
      
        #print("other " + str(x1), str(y1))
        
        distance= math.sqrt((x2 - x1)**2 + (y2- y1)**2) #uses distance formula to compute difference in the cursor values between the replays. May use different algorithm later
        
        flippedDistance = math.sqrt((x2 - x1)**2 + (flippedY- y1)**2) #flips the user's coordinates to check to see if they stole someone's hr play and made it no-mod or vice versa
        
        #print("NoMod Distance: " +str(distance))
        #print("HR Distance: " +str(flippedDistance))


        distances.append(distance)
        flippedDistances.append(flippedDistance)

       



    # calculates and returns the average distance of the points
    for i in range(len(distances)):
        totalDistance = totalDistance + distances[i]
        totalFlippedDistance = totalFlippedDistance + flippedDistances[i] #checks the flipped distances
    
    averageDistance = (totalDistance/len(distances))
    averageFlippedDistance = (totalFlippedDistance/len(distances))
    
    print("user replay vs other replay " +str(averageDistance))
   
    print("flipped user replay vs other replay " +str(averageFlippedDistance))

    if averageDistance < averageFlippedDistance:
        return averageDistance
    else:
        return averageFlippedDistance
    

 
        
    


def getReplay():
    getReplay = 'get_replay?' +key
    
    





checkDiffInReplays()


#Summary of findings, needs to be cleaned up
print("")
print("SUMMARY OF FINDINGS")
for i in range(len(averageDistances)):
    print(averageDistances[i]) #prints all the average distances






















from osrparse import parse_replay_file
import os
from os import listdir
from os.path import isfile, join
import difflib
import math
import json


pathToUserReplay = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\userReplay\\"

pathToOtherReplays = "C:\\Users\\Travis\\source\\repos\\ReplaySBS\\ReplaySBS\\replays\\otherReplays\\"


averageDistances = [] #Stores the average distances between the user's replay and the all the ones it was checked against
flippedDistances = [] #used to store the distances of flipped coordinates of user's replays

userCorrds = [] # Where the coordinates of the user's replay will be stored



def parseUserReplay():
    # Parse user replay
    
    userOsrList = [f for f in listdir(pathToUserReplay) if isfile(join(pathToUserReplay, f))]
    
    for userOsr in userOsrList: #For every user replay (should only be one for now)
        userOsr = pathToUserReplay + userOsr
       
        userReplay = parse_replay_file(userOsr)
        playData = userReplay.play_data
        userPlayerName = userReplay.player_name
        print("User's Name: " + userPlayerName)
        #print("")
        
        for play in playData:
             userCorrds.append((play.x, play.y))

    return userPlayerName


def parseOtherReplays(userPlayerName):
    #parse other replays
    
    osrList = [f for f in listdir(pathToOtherReplays) if isfile(join(pathToOtherReplays, f))]
    
    for osr in osrList:
        
        otherCoords = []
        
        osr = pathToOtherReplays + osr
        
        replay = parse_replay_file(osr)
        playData = replay.play_data
        otherPlayerName = replay.player_name
        
        #print("")
        #print("Other Player: " + otherPlayerName)
        
        
        for play in playData:
            otherCoords.append((play.x, play.y))

        #averageDistances.append(userPlayerName + "" +otherPlayerName)
        averageDistance = (computeSimilarity(userCorrds, otherCoords, userPlayerName, otherPlayerName))
        

    return otherPlayerName



def computeSimilarity(userCoords, otherCoords, userPlayerName, otherPlayerName): # Calculates distance between the cursor between the users replay and the other replay
   
    distances = []
    totalDistance = 0
    totalFlippedDistance = 0
    players= userPlayerName + " vs " +otherPlayerName
    
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
        
        flippedY = (192-y2 ) + 192 #converts the replay's y value to the HR y value
        
        #print("")
        #print("userFlipped " + str(x2), str(flippedY))
        #print("userNormal " +str(x2), str(y2))
      
        #print("other " + str(x1), str(y1))
        
        distance= math.sqrt((x2 - x1)**2 + (y2- y1)**2) #uses distance formula to compute difference in the cursor values between the replays. May use different algorithm later
        
        flippedDistance = math.sqrt((x2 - x1)**2 + (flippedY- y1)**2) #flips the user's coordinates to check to see if they stole someone's hr play and made it no-mod or vice versa
        
        #print("NoMod Distance: " +str(distance))
        #print("HR Distance: " +str(flippedDistance))


        distances.append(distance)
        flippedDistances.append(flippedDistance)

       



    # calculates and returns the average distance of the points
    for i in range(len(distances)):
        totalDistance = totalDistance + distances[i]
        totalFlippedDistance = totalFlippedDistance + flippedDistances[i] #checks the flipped distances
    
    averageDistance = (totalDistance/len(distances))
    averageFlippedDistance = (totalFlippedDistance/len(distances))
    
    #print("user replay vs other replay " +str(averageDistance))
   
    #print("flipped user replay vs other replay " +str(averageFlippedDistance))

    if averageDistance < averageFlippedDistance:
        averageDistances.append(str(averageDistance) + " " + players)
        
    else:
        averageDistances.append(str(averageFlippedDistance) + " " + players)


    
        
    print("")
    print("Similarity of " +userPlayerName + " and " +otherPlayerName + " is " +str(averageDistance))


def checkDiffInReplays():
    userPlayerName = parseUserReplay()
    parseOtherReplays(userPlayerName)
   
    
 
checkDiffInReplays()



#Summary of findings, needs to be cleaned up
print("")
print("SUMMARY OF FINDINGS")
for i in range(len(averageDistances)):
    print(averageDistances[i]) #prints all the average distances