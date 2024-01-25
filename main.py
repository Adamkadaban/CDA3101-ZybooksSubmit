#!/usr/bin/env python3

import pandas as pd
import requests
import json
import yaml
#from pprint import pprint


CONFIG_FILE = './config.yaml'
with open(CONFIG_FILE) as fin:
	config = yaml.safe_load(fin)
	zybooks_grades_path = config['zybooks_path']
	student_mapping_path = config['student_sid_path']
	access_token = config['api_token']
	course_id = str(config['course_id'])
	assignment_id = str(config['assignment_id'])

if None in [zybooks_grades_path, student_mapping_path, access_token, course_id, assignment_id]:
	print('[!] Item missing from config.yaml. Please check config.yaml.example')
	exit()


df = pd.read_excel(zybooks_grades_path)
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
	except Exception as err:
		print(str(err))

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
#print(assignments)



asst_entry = list(filter(lambda x: 'quiz_id' in x and str(x['quiz_id']) == assignment_map[course_id], assignments))

if not asst_entry:
	asst_entry = list(filter(lambda x: 'id' in x and str(x['id']) == assignment_map[course_id], assignments))

assignment_name = asst_entry[0]['name']
print(f'Grading for assignment {assignment_name}. Countinue?')
user_selection = input('Y/n')
if user_selection not in ['Y', 'y', '\n']:
	print('[+] Exiting')
	exit()

#print(asst_entry)
assignment_id_map[course_id] = asst_entry[0]["id"]


#print(assignment_id_map)
exercise_name = asst_entry[0]['name']

#this_submission_uri = f'{assignments_uri}/{assignment_id_map[course_id]/submissions/{this_sid}'


fail_count = 0
fail_students = []
for sid,name in sids.items():
	print(f'Working on {name}')
	submission_uri = f'{assignments_uri}/{assignment_id_map[course_id]}/submissions/{sid}'
	try:
		submission_response = requests.get(url=submission_uri, headers=headers)
	except:
		print(f'[!] Failed to request this student')
		continue

	assignment_entry = json.loads(submission_response.text)
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
	total_points = asst_entry[0]['points_possible']
	score = total_points * float(percent_score.values[0])/100.0
	# set grade for student
	#print(percent_score)
	print(f'\tScore: {score}')
	'''
	submission_uri = f'{assignments_uri}/{assignment_id_map[course_id]}/submissions/{sid}'
	params = {'submission[posted_grade]', str(score)}
	try:
		response = requests.put(url=submission_uri, headers=headers, params=params)
	except:
		print('[!] Failed to submit score')

	'''
