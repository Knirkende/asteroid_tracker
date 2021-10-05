#Google API imports
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from urllib import error
from email.mime.text import MIMEText
import base64

#core functionality imports
import requests
import json
import datetime
from math import inf
from ole_secrets import *

class dangerAsteroid:
    """
    A twitterbot helper class.

    Queries the NASA NeoWs API and instantiates an object representing the
    closest known near earth object one day ahead of the current system date.

    Attributes:
    date (datetime.date): current date + 1
    cloud_cover (int): forecast percentage cloud cover over Bergen on self.date
    distance (int): closest pass distance of NEO in km
    summary (str): short summary of danger level in Norwegian
    velocity (int): relative velocity to earth of NEO in kmph
    danger (bool): NASA's binary "danger" rating
    tweet (str): twitter-friendly message in Norwegian
    """
    def __init__(self):
        self.date = str((datetime.datetime.now()
            + datetime.timedelta(days=1)).date())
        self.cloud_cover = self._get_weather_data()
        self.distance = inf
        self._asteroid_setter()
        self.summary = self._danger_message()
        self.tweet = self._generate_tweet()

    def _crybaby(self, action, err_msg):
        """
        HTTP error reporter.
        Sends an email via gmail to the administrator if a request returned a
        bad status code. Email contains the request (action) and status
        code (err_msg).
        DEV_MAIL imported from secrets file.
        """
        SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
        creds = None
        # --- google API snippet ---
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        service = build('gmail', 'v1', credentials=creds)
        # --- end google API snippet ---
        message_text = f"""
Asteroid tracker script has engaged the crybaby.\n
Request:\n{action}
Response:\n{err_msg}
        """
        #encode email string
        message = MIMEText(message_text)
        message['to'] = DEV_MAIL
        message['from'] = DEV_MAIL
        message['subject'] = '<crybaby> Asteroid tracker'
        raw_message = {'raw': base64.urlsafe_b64encode(
            message.as_string().encode()).decode()}
        #send email
        try:
            service.users().messages().send(
                userId=DEV_MAIL, body=raw_message).execute()
        except:
            print('Error reporter is broken. Now what.')
        
    def _get_data(self):
        """
        Queries NASA's "Near Earth Object Web Service" API with the instance's
        date attribute.
        NASA_API_KEY imported from secrets file.
        Returns: the data in json format.
        """
        query = ('https://api.nasa.gov/neo/rest/v1/feed?start_date='
            + self.date + '&end_date=' + self.date + '&api_key=' + NASA_API_KEY)
        try:
            response = requests.get(query)
        except:
            self._crybaby(query, 'query received no response')
            return None
        if response.status_code != 200:
            self._crybaby(query, response.status_code)
            return None
        return response.json()

    def _get_weather_data(self):
        """
        Queries openweathermap.org API and extracts current cloud coverage over
        the city of Bergen, Norway, in percent.
        WEATHER_API_KEY imported from secrets file.
        """
        CITY = 'Bergen'
        COUNTRY = 'nor'

        query = ('https://api.openweathermap.org/data/2.5/weather?q='
            + CITY + ',' + COUNTRY + '&appid=' + WEATHER_API_KEY)

        response = requests.get(query)

        if response.status_code != 200:
            self._crybaby(query, response.status_code)
            return None 
        return response.json()['clouds']['all']

    def _asteroid_setter(self):
        """
        Sets attributes representing selected data for the asteroid that will
        come closest to earth on a given date. Sets all to None if there is no
        data.
        TO DO: Add weather data.
        """
        nasa_data = self._get_data()
        if not nasa_data:
            self.name = None
            self.velocity = None
            self.danger = False
        else:
            start_date = self.date
            for idx in range(len(nasa_data['near_earth_objects'][start_date])):
                asteroid_name = (nasa_data['near_earth_objects']
                    [start_date][idx]
                    ['name'])
                dist_km = float((nasa_data['near_earth_objects']
                    [start_date][idx]
                    ['close_approach_data'][0]
                    ['miss_distance']
                    ['kilometers']))
                pass_v = float((nasa_data['near_earth_objects']
                    [start_date][idx]
                    ['close_approach_data'][0]
                    ['relative_velocity']
                    ['kilometers_per_second']))
                danger = (nasa_data['near_earth_objects']
                    [start_date][idx]
                    ['is_potentially_hazardous_asteroid'])
                if dist_km < self.distance:
                    self.name = asteroid_name.replace('(', '"').replace(')', '"')
                    self.distance = dist_km
                    self.velocity = pass_v
                    self.danger = danger

    def _danger_message(self):
        """
        Returns a string containing a short summary of the danger
        level of the near earth object pass distance.
        """
        disaster_threshold = 5000
        risky_threshold = 6000
        moon_distance = 384399
        summaries = [
        'Huffda',
        'På håret',
        'God margin',
        'Null stress',
        ]
        if self.distance <= 5000:
            return summaries[0]
        elif self.distance <= 6000:
            return summaries[1]
        elif self.distance <= 384399:
            return summaries[2]
        else:
            return summaries[3]

    def _readable_distance(self, distance):
        """
        Returns a string representation of distance.
        Accurate to the nearest billion, million, 100k or thousand.
        """
        milliarder, dist = divmod(distance, 10000000)
        millioner, dist = divmod(dist, 1000000)
        hundre_tusen, dist = divmod(dist, 100000)
        tusen, dist = divmod(dist, 1000)

        tall = ['null', 'ett', 'to', 'tre', 'fire',
        'fem', 'seks', 'syv', 'åtte', 'ni']
        tall_han = ['null', 'en', 'to', 'tre', 'fire',
        'fem', 'seks', 'syv', 'åtte', 'ni']

        if milliarder:
            return tall_han[int(milliarder)] + ' milliard' + 'er' * (milliarder > 1)
        elif millioner:
            return tall_han[int(millioner)] + ' million' + 'er' * (milliarder > 1)
        elif hundre_tusen:
            return tall[int(hundre_tusen)] + ' hundre tusen'
        elif tusen:
            return tall[int(tusen)] + ' tusen'
        else:
            return dist        

    def _generate_tweet(self):
        weather_string = ('Vi ville ikke sett noe uansett sånn været er nå.'
            * (self.cloud_cover > 50))

        if not self.name:
            return None
        return(
            f'{self.summary}. '
            f'I morgen passerer asteroiden {self.name} '
            f'Fisketorget med en avstand på mer enn '
            f'{self._readable_distance(self.distance)} km. '
            f'{weather_string}'
            )

if __name__ == '__main__':
    asteroid = dangerAsteroid()
    print(asteroid.tweet)
#   asteroid._crybaby('Action', 'Error message')
#   print(asteroid.distance)