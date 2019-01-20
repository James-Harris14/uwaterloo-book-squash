#!/usr/bin/env python3

# Inspiration: https://warrior.uwaterloo.ca/CourtReservation/GetReservationSlotsForFacility?courtId=45084514-6fb2-4068-ac72-7df3786e84a7&facilityId=00000000-0000-0000-0000-000000000000&date=12/23/2018
import os
import requests
import re
from bs4 import BeautifulSoup
import datetime

# Some strings.. I don't know how accurate these will be in the future
LOGIN_URL = 'https://warrior.uwaterloo.ca/Account/Login'
AVAIL_URL = 'https://warrior.uwaterloo.ca/CourtReservation/GetReservation'\
	'SlotsForFacility?courtId=45084514-6fb2-4068-ac72-7df3786e84a7&facility'\
	'Id=00000000-0000-0000-0000-000000000000&date={}/{}/{}'
RES_CONF = 'https://warrior.uwaterloo.ca/CourtReservation/GetReservationConfirmation'
BOOK_URL = 'https://warrior.uwaterloo.ca/CourtReservation/ReserveCourt'
TIMES = []
COURTS = ['North American 1 (Court 07)','International 1 (Court 08)',
	'International 2 (Court 09)', 'North American 2 (Court 10)']
FACILITY_IDS = ['5e568875-dadf-47bb-9080-ad4c4df145c1',
	'58b4988f-fb79-42f9-bd19-f7dbb6c8eab7',
	'b2eacfee-0fad-4fa1-a4bd-609bfe3ca532',
	'f8162fb1-c828-431b-a6f8-c1bab9927b61']
NUM_COURTS = 4

def get_available_courts_url_for_day(day):
	today = datetime.date.today()
	if day >= today.day:
		return AVAIL_URL.format(today.month, day, today.year)
	
	return '' # fail

''' get verification token for hitting specific endpoint '''
def get_verification_token(content):
	soup = BeautifulSoup(content, 'html.parser')
	token = soup.find('input', {'name': '__RequestVerificationToken'}).get('value')
	return token

''' ask user for booking date '''
def request_booking_date(session):
	avail = [] # court availability
	date = input('What day number (in this month) would you like to book squash? ')
	r = s.get(get_available_courts_url_for_day(int(date)))
	soup = BeautifulSoup(r.content, 'html.parser')
	time_rows = soup.findAll('table')[0].findAll('tr')
	for tr in time_rows[1:]: #get all time slots
		TIMES.append(tr.find('div').text.split('-')[0].strip())

	avail_rows = soup.findAll('table')[1].findAll('tr') # get second table in html; get all rows in the table
	for i, row in enumerate(avail_rows[1:]): # ignore first row (header)
		avail_for_time = [] # True = avail, False = taken
		for td in row.findAll('td'):
			avail_for_time.append(td.text.strip() == 'Reserve')
		avail.append(avail_for_time)

	today = datetime.date.today()
	date_str = '{}/{}/{}'.format(today.month, date, today.year) # booking date
	return avail, date_str

def book_court(session, date, court_availability):
	times_avail = [] # time slots with at least 1 available court
	for i in range(len(court_availability)):
		for j in range(NUM_COURTS):
			if court_availability[i][j] == True:
				times_avail.append(TIMES[i])
				break
	print('The following times are available:')
	print(', '.join(times_avail))
	time_requested = input('What time would you like to book? ')
	courts_for_time = []
	for i, court in enumerate(court_availability[TIMES.index(time_requested)]):
		if court == True:
			courts_for_time.append(COURTS[i])
	print('The following courts are available for {}:'.format(time_requested))
	print(', '.join(courts_for_time))
	court_requested = input('Which court # would you like to book (eg. 9)? (write back or b to select a new time) ')
	if court_requested.lower() == 'back' or court_requested.lower() == 'b':
		return book_court(session, date, court_availability)
	query_params = {
		'courtId': '45084514-6fb2-4068-ac72-7df3786e84a7',
		'facilityId': FACILITY_IDS[{'7':0,'8':1,'9':2,'10':3}[court_requested]],
		'slotNumber': str(TIMES.index(time_requested)),
		'reservationDate': '{} {}'.format(date, time_requested)
	}
	r = s.get(RES_CONF, params=query_params) # need this to get verification token to book court
	token = get_verification_token(r.content)
	book_payload = {
		'__RequestVerificationToken': token,
		'CourtId': '45084514-6fb2-4068-ac72-7df3786e84a7',
		'FacilityId': FACILITY_IDS[{'7':0,'8':1,'9':2,'10':3}[court_requested]],
		'ActivityTypeCode': '00000000-0000-0000-0000-000000003466',
		'BookingStarts': '{} {}'.format(date, time_requested),
		'SlotNumber': str(TIMES.index(time_requested)),
		'Participants[0].ParticipantId': '',
		'Participants[0].PartyId': '00000000-0000-0000-0000-000000000000',
		'Participants[0].ParticipantIdType': 'Email',
		'ParticipantsType': '0'
	}
	r = s.post(BOOK_URL, data=book_payload)

if __name__ == '__main__':
	quest_user = os.environ.get('QUEST_USER')
	quest_pass = os.environ.get('QUEST_PASS')
	if quest_user is None or quest_pass is None:
		quest_user = input('Enter your quest username: ')
		quest_pass = input('Enter your quest Password: ')
	with requests.Session() as s:
		r = s.get(LOGIN_URL) # get login page for verification token
		token = get_verification_token(r.content)
		request_data = {
			'__RequestVerificationToken': token,
			'UserName': quest_user,
			'Password': quest_pass
		}
		r = s.post(LOGIN_URL, data=request_data) # login
		court_availability, date_str = request_booking_date(s)
		book_court(s, date_str, court_availability)

