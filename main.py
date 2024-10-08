#!/usr/bin/env python3

import pandas as pd
import requests
import json
import yaml
from pprint import pprint


CONFIG_FILE = './config.yaml'
with open(CONFIG_FILE) as fin:
	config = yaml.safe_load(fin)
	zybooks_grades_path = config['zybooks_path']
	student_mapping_path = config['student_sid_path']
	access_token = config['api_token']
	course_id = str(config['course_id'])
	assignment_id = str(config['assignment_id'])
	autorun = False if None else config['autorun']
	verbose = False if None else config['verbose']
	dry_run = False if None else config['dry_run']

if None in [zybooks_grades_path, student_mapping_path, access_token, course_id, assignment_id]:
	print('[!] Item missing from config.yaml. Please check example_config.yaml')
	exit()

try:
	df = pd.read_excel(zybooks_grades_path)
except ValueError:
	df = pd.read_csv(zybooks_grades_path)
df['Full name'] = df['First name'] + ' ' + df['Last name']

sid_email_mapping = pd.read_csv(student_mapping_path)
sid_email_mapping['email'] = sid_email_mapping['SIS Login ID']


# print(df['Last name'])

assignment_map = {course_id:assignment_id}
assignment_id_map = {}

assignment_uri_base = 'https://ufl.instructure.com/api/v1/courses/'
uri_base = f'https://ufl.instructure.com/api/v1/'

def paginated_get(url, headers, params):
	data_set = []

	while True:
		response = requests.get(url=url, headers=headers, params=params)
		result = json.loads(response.text)
		if verbose:
			print('[*] paginated_get response')
			pprint(result)
		data_set.extend(result)
		# stop when no more responses exit
		if response.links['current']['url'] == response.links['last']['url']:
			break
		url = response.links['next']['url']

	return response, data_set


# get submissions


print('[+] Getting Student IDs')
sids = {}
headers = {'Authorization': f'Bearer {access_token}'}
csv_headers = {'Content-Type': 'text/csv',
			   'Authorization': f'Bearer {access_token}'}


for course_id in assignment_map.keys():
	try:
		assignment_submissions_rq_params = {'include': ['user']}
		assignment_submissions_uri = f'{uri_base}courses/{course_id}/assignments/{assignment_map[course_id]}/submissions'
		assignment_submissions_response, data_set = paginated_get(url=assignment_submissions_uri,
																		headers=headers,
																		params=assignment_submissions_rq_params)
	except KeyboardInterrupt:
		print('[!] Exiting')
		exit()
	except Exception as err:
		print(str(err))
		print('[!] Error. Perhaps the course doesn\'t exist?')
		exit()

	for entry_dict in data_set:
		'''
		if entry_dict['user']['name'] != entry_dict['user']['short_name']:
			pprint(entry_dict)
		'''
		name = entry_dict['user']['name']
		#name = name.replace(' ','')
		test_student_name = 'Student-Test'
		'''
		if name[:len(test_student_name)] == test_student_name:
			name = f'Zz-{name}'
		'''
		sids[entry_dict["user"]["id"]] = name
print(f'[+] Got {len(sids)} students!')

print('[+] Getting exercise info')


headers = {'Content-Type': 'application/json',
			   'Authorization': 'Bearer ' + access_token}


assignments_uri = f'{assignment_uri_base}{course_id}/assignments/'
assignments_response = requests.get(url=assignments_uri,
											headers=headers,
											params={'per_page': '500'})
assignments = json.loads(assignments_response.text)
if verbose:
	print('[*] assignment response')
	pprint(assignments)
#print(assignments)



asst_entry = list(filter(lambda x: 'quiz_id' in x and str(x['quiz_id']) == assignment_map[course_id], assignments))

if not asst_entry:
	asst_entry = list(filter(lambda x: 'id' in x and str(x['id']) == assignment_map[course_id], assignments))

assignment_name = asst_entry[0]['name']
if dry_run:
	print(f'Doing dry run. Will not submit grades to canvas')
print(f'Grading for assignment {assignment_name}.', end='')
if not autorun:
	print(' Countinue? (Y/n)')
	user_selection = input()
	if user_selection not in ['Y', 'y', '\n', '']:
		print('[-] Exiting')
		exit()
else:
	print()

#print(asst_entry)
assignment_id_map[course_id] = asst_entry[0]["id"]


#print(assignment_id_map)
exercise_name = asst_entry[0]['name']

#this_submission_uri = f'{assignments_uri}/{assignment_id_map[course_id]/submissions/{this_sid}'


fail_count = 0
fail_students = []
email_checked = []
name_checked = []
for sid,name in sids.items():
	if name == 'Test Student':
		print(f'Skipping Test Student')
		break
	print(f'Working on {name}')
	submission_uri = f'{assignments_uri}/{assignment_id_map[course_id]}/submissions/{sid}'
	try:
		submission_response = requests.get(url=submission_uri, headers=headers)
	except KeyboardInterrupt:
		print('[!] Exiting')
		exit()
	except Exception as err:
		print(f'[!] Failed to request this student')
		print(err)
		continue

	assignment_entry = json.loads(submission_response.text)
	if verbose:
		print('[*] assignment entry')
		pprint(assignment_entry)
	#print(assignment_entry)

	submission_id = assignment_entry['id']
	attempt = assignment_entry['attempt']

	'''
	if attempt is None:
		print(f'No attempts made by this student')
		continue
	'''
	# get score from xlsx
	# first, we try to get sid/score based on email
	email = sid_email_mapping.loc[sid_email_mapping.ID == sid, 'email'].values[0]
	percent_score = df.loc[df['Primary email'] == email, 'Percent grade']
	# next, we try to get score based on full name
	if percent_score.empty:
		percent_score = df.loc[df['Full name'] == name, 'Percent grade']
		if percent_score.empty:
			print(f"\t[!] Can't find score for student")
			fail_count += 1
			fail_students.append(name)
			continue
		else:
			name_checked.append(name)
	else:
		email_checked.append(name)
	total_points = asst_entry[0]['points_possible']
	score = total_points * float(percent_score.values[0])/100.0
	# set grade for student
	#print(percent_score)
	print(f'\tScore: {score}')

	submission_uri = f'{assignments_uri}/{assignment_id_map[course_id]}/submissions/{sid}'
	params = {'submission[posted_grade]': str(score)}
	try:
		#print(submission_uri)
		#pprint(headers)
		#pprint(params)
		if not dry_run:
			response = requests.put(url=submission_uri, headers=headers, params=params)
		else:
			print('Skipping')
	except KeyboardInterrupt:
		print('[!] Exiting')
		exit()
	except Exception as err:
		print(err)
		print('[!] Failed to submit score')
