#!/usr/bin/env python3

import pandas as pd
import requests
import json
#from pprint import pprint

path = './thing.xlsx'
df = pd.read_excel(path)
df['Full name'] = df['First name'] + ' ' + df['Last name']


# print(df['Last name'])


with open('API_TOKEN') as fin:
	access_token = fin.read().rstrip()

course_id = "498331"
assignment_map = {"498331":"5921392"}
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

#print(asst_entry)
assignment_id_map[course_id] = asst_entry[0]["id"]


#print(assignment_id_map)
exercise_name = asst_entry[0]['name']

#this_submission_uri = f'{assignments_uri}/{assignment_id_map[course_id]/submissions/{this_sid}'

for sid,name in sids.items():
	print(f'Working on {name}')
	submission_uri = f'{assignments_uri}/{assignment_id_map[course_id]}/submissions/{sid}'
	submission_response = requests.get(url=submission_uri, headers=headers)

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
	percent_score = df.loc[df['Full name'] == name, 'Percent grade']
	if percent_score.empty:
		print(f"[!] Can't find score for student")
	else:
		score = float(percent_score.values[0])/100.0
	# set grade for student
	print(percent_score)
	'''
	submission_uri = f'{assignments_uri}/{assignment_id_map[course_id]}/submissions/{sid}'
	params = {'submission[posted_grade]', str(score)}
	try:
		response = requests.put(url=submission_uri, headers=headers, params=params)
	except:
		print('[!] Failed to submit score')

	'''
