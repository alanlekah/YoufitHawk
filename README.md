# YoufitHawk
A project to take the Youfit Gym membership system and integrate events into Google Calendar automatically

# Usage
To use, you can transform (which might happen eventually) the main method into a Lambda to run weekly on AWS.

# Config
You need to set the environmental variables as follows:
* USERNAME - The username for the youfit login system
* PASSWORD - Password for the login system
* OFFSET - The offset of the week you wish to pull and create events for 
    * For example, -5 would pull from 5 weeks ago or 1 would pull for next week. You can also just set it 0 to pull from the current week
    * A current week is defined (from the event system) as Sunday - Saturday of the current week
    
# Setup
In order to add events to Google Calendar:
* You need to download the credentials.json file from GCP
* Run the GoogleCalToken.py file to create the authorization token.json file that will be used for auth