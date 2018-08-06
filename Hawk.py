from __future__ import print_function
from requests import session
from requests.utils import quote
import json
from datetime import timedelta, date
import calendar
import os
from datetime import datetime
import pytz

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# Youfit login
USERNAME = os.environ['USERNAME']
PASSWORD = os.environ['PASSWORD']

# Offset of the current week (can be used to run for next week or 3 weeks back - if needed)
OFFSET = int(os.environ['OFFSET']) if 'OFFSET' in os.environ else 0


def get_last_or_next_day(cal_day, backwards, week_offset=0):
    """
    Method to find the next calendar.(MONDAY/TUESDAY/WEDNESDAY...etc) in the week
    :param cal_day:
    :param backwards: Will search forwards/backwards in the week
    :param week_offset: The offset of the current week we want to search (default is today / this week)
    :return:
    """
    # Iterator of the current day we're holding (plus/minus the week offset)
    last_day = date.today() + timedelta(weeks=week_offset)
    # Static one-day variable datetime
    one_day = timedelta(days=1)

    # While iterator isn't the day we're looking for..
    while last_day.weekday() != cal_day:
        # Search back through time
        if backwards:
            last_day -= one_day
        # Search forward through time
        else:
            last_day += one_day
    # Return the iterator
    return last_day


def build_calendar_service():
    # Setup the Calendar API
    SCOPES = 'https://www.googleapis.com/auth/calendar'
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('calendar', 'v3', http=creds.authorize(Http()))  # service


def get_json_schedule():
    """
    Get the Youfit schedule JSON payload for the week
    :return:
    """

    # Create a new session
    session_requests = session()

    # Request the signin page for Youfit
    signin_page_result = session_requests.get('https://mico.myiclubonline.com/iclub/members/signin.htm')

    # Try to sign in
    member_page = session_requests.post('https://mico.myiclubonline.com/iclub/j_spring_security_check',
                                        data={'j_username': USERNAME, 'j_password': PASSWORD})
    # Go-to the member activity page
    member_page_2 = session_requests.get('https://mico.myiclubonline.com/iclub/members')

    # Calculate the last saturday and next sunday of the week
    last_sun = get_last_or_next_day(calendar.SUNDAY, backwards=True, week_offset=OFFSET)
    next_sat = get_last_or_next_day(calendar.SATURDAY, backwards=False, week_offset=OFFSET)

    # Get the json data from the current/next week
    json_result = session_requests.get(
        'https://mico.myiclubonline.com/iclub/scheduling/memberSchedule.htm?lowDate={}&highDate={}&_=1532035883769'.format(
            quote(last_sun.strftime('%m/%d/%Y'), safe=''),
            quote(next_sat.strftime('%m/%d/%Y'), safe='')
        )
    )

    # Load in the JSON response
    try:
        member_schedule_json = json.loads(json_result.text)
    except json.JSONDecodeError:
        print("Unable to decode JSON output!")
        exit(1)

    if len(member_schedule_json) == 0:
        print("Nothing found for the week of {} to {}, try again later!".format(last_sun, next_sat))
        exit(1)

    # Print out the information found about each event, date, and time
    for apt in member_schedule_json:
        print("You have an appointment with {} on {} at {} - {}".format(apt['employeeName'],
                                                                        apt['eventDate'],
                                                                        apt['eventStartTime'],
                                                                        apt['eventEndTime']))

    return member_schedule_json


def add_schedule_to_calendar(service, payload):
    """
    Given a JSON payload from Youfit, and the Google Calendar service, add each event to the calendar
    :param service:
    :param payload:
    :return:
    """

    for apt in payload:
        timezone = 'America/New_York'
        py_timezone = pytz.timezone(timezone)
        start_time_dt = datetime.strptime("{} {}".format(apt['eventDate'], apt['eventStartTime']), '%m/%d/%Y %I:%M %p')
        end_time_dt = datetime.strptime("{} {}".format(apt['eventDate'], apt['eventEndTime']), '%m/%d/%Y %I:%M %p')
        start_time = py_timezone.localize(start_time_dt).isoformat()
        end_time = py_timezone.localize(end_time_dt).isoformat()

        event = {
            'summary': 'Trainer Session',
            'description': 'Autogenerated Youfit event',
            'start': {
                'dateTime': start_time,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': timezone,
            },
            "reminders": {
                "useDefault": True
            }
        }

        event_check = {
            'timeMin': start_time,
            'timeMax': end_time,
            'timeZone': timezone,
            'items': [
                {
                    "id": 'primary'
                }
            ]
        }
        # Check if event is already in calendar
        freebusy_query_result = service.freebusy().query(body=event_check).execute()
        if len(freebusy_query_result['calendars']['primary']['busy']) > 0:
            # Skip if event already in calendar
            print("Event skipped {} - {}!".format(start_time, end_time))
            continue

        # Create an event
        event_created_result = service.events().insert(calendarId='primary', body=event).execute()
        print('Event created: %s' % (event_created_result.get('htmlLink')))


def hawk():
    """
    Main method
    :return:
    """
    payload = get_json_schedule()
    service = build_calendar_service()
    add_schedule_to_calendar(service, payload)


if __name__ == '__main__':
    hawk()
