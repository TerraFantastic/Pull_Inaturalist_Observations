#Import Required Modules
import requests, pandas, math, arcpy
from arcgis.features import GeoAccessor, GeoSeriesAccessor

#Set Environmental Variables
arcpy.env.overwriteOutput = True

#Get User Input for Species Selection by iNaturalist Taxon Number
userInput = arcpy.GetParameterAsText(0)

#Set API Parameters for Quality Grade by User Input
if arcpy.GetParameter(1):
    grading = "&quality_grade=research"
else:
    grading = ""  
#Set API Parameters for Captive Observations by User Input    
if arcpy.GetParameter(2):  
    captive = "captive=false"
else: 
    captive = ""
arcpy.AddMessage("API Parameters Set: Research Grade = " + grading + " Captive Exclusion = " + captive)        

#Determine number of pages of observations needed to be pulled
arcpy.AddMessage("API URL for determining number of pages: https://api.inaturalist.org/v1/observations?" + captive + grading + "&indentified=true&taxon_id=" + str(userInput) + "&geo=true&per_page=200") 
obsResults = requests.get("https://api.inaturalist.org/v1/observations?" + captive + grading + "&indentified=true&taxon_id=" + str(userInput) + "&geo=true&per_page=200").json()["total_results"] 
obsNumber = math.ceil(obsResults / 200)
arcpy.AddMessage("Number of pages of observations found: " + str(obsNumber))

#Create Empty Dataframe with X, Y Columns
obsdf = pandas.DataFrame(columns=['x', 'y'])

lastid = 999999999

arcpy.SetProgressor("Step", "Pulling Observations from iNaturalist", 0, obsNumber, 1)

#For each page of results, get observation location results and concat to empty dataframe to create one dataframe with all location results. 
for i in range(1, obsNumber+1):
    results = requests.get("https://api.inaturalist.org/v1/observations?" + captive + grading + "&id_below=" + str(lastid) + "&indentified=true&taxon_id=" + str(userInput) + "&geo=true&per_page=200").json()['results']
    arcpy.AddMessage("API URL Page: https://api.inaturalist.org/v1/observations?" + captive + grading + "&id_below=" + str(lastid) + "&indentified=true&taxon_id=" + str(userInput) + "&geo=true&per_page=200")
    normalised = pandas.json_normalize(results)['location']
    newObs = pandas.DataFrame(normalised)['location'].str.split(',',  expand=True)
    newObs.rename(columns={0:'x', 1:'y'}, inplace=True)
    obsdf = pandas.concat([obsdf, newObs])
    idlist = pandas.json_normalize(results)['id']
    lastid = idlist[len(idlist) - 1]
    arcpy.SetProgressorPosition()
   
#Convert Dataframe to Spatial Dataframe
obsdf = pandas.DataFrame.spatial.from_xy(df=obsdf,x_column='y',y_column='x', sr=4326)

#Create Path for Output Layer in the Default Geodatabase
outPath = arcpy.mp.ArcGISProject("CURRENT").defaultGeodatabase + "/iNaturalist_Taxon_" + str(userInput)

#Convert Spatial Dataframe to Shapefile/Feature 
obsdf.spatial.to_featureclass(outPath, overwrite=True)

arcpy.AddMessage("Feature Class Created at " + outPath)

#Add Point Layer to Current Map
arcpy.mp.ArcGISProject('CURRENT').activeMap.addDataFromPath(outPath)