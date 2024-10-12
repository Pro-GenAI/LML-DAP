# Copyright (c) 2024 Praneeth Vadlapati

import os
import time

from dotenv import load_dotenv
import openai

def load_env():
	load_dotenv(override=True)  # bypass the cache and reload the variables
load_env()

random_state = 1
data_folder = 'data_files'
if not os.path.exists(data_folder):
	os.makedirs(data_folder)

def print_progress(chr='.'):
	if chr == 0 and type(chr) == int:
		return
	if type(chr) == bool:
		chr = '.' if chr else ','
	print(chr, end='', flush=True)

def print_error(err=None):
	# print(err)
	print_progress('!')

def extract_data(response, tag):
	if not tag:  # if tags are provided, extract data from tags
		raise Exception('No data format or tag provided to extract data from the response')
	response = str(response).strip()  # create a copy

	open_tag = f'<{tag}>'
	if open_tag not in response:
		raise Exception(f'Tag "{tag}" not found in the response')
	start = response.rfind(open_tag) + len(open_tag)
	
	close_tag = f'</{tag}>'
	if close_tag in response[start:]:
		end = response.find(close_tag, start)
	else:
		end = len(response)
	response = response[start:end].strip()

	if '```csv' in response:
		response = response.replace('```csv', '```').strip()
	if '```' in response:
		response = response.split('```')[1].strip()
	return response


model = os.getenv('LM_MODEL')
if model:
	model = model.strip()
else:
	raise Exception('LM_MODEL is not set in the environment variables')

client = None

def load_client():
	global client
	if client:  # if already loaded, and reloading now
		print('Reloading client...')
	load_dotenv(override=True)
	base_url = os.getenv('LM_PROVIDER_BASE_URL').strip() or None

	api_key = os.getenv('LM_API_KEY').strip() or None
	client = openai.OpenAI(base_url=base_url, api_key=api_key)


load_client()  # Load client for the first time



def get_lm_response(messages, max_retries=4):
	if isinstance(messages, str):
		messages = [{'role': 'user', 'content': messages}]

	for _ in range(max_retries):
		response = None
		try:
			response = client.chat.completions.create(messages=messages, model=model)
			response = response.choices[0].message.content.strip()
			if not response:
				raise Exception('Empty response from the bot')
			return response
		except Exception as e:
			e = str(e)
			if '429' in e or 'Resource has been exhausted' in e:  # Rate limit
				total_wait_time = None
				if 'Please retry after' in e:  # Please retry after X sec
					total_wait_time = e.split('Please retry after')[1].split('sec')[0].strip()
					# print(f'Rate Limit reached. Waiting for {total_wait_time} seconds. ', end='')
					total_wait_time = int(total_wait_time) + 1
				elif 'Please try again in' in e:  # 'Please try again in 23m3s. ...'
					rate_limit_time = e.split('Please try again in')[1].split('.')[0].strip()
					# print(f'Rate Limit reached for {rate_limit_time}. ', end='', flush=True)
	 				# rate_limit_time = '1m20s'
					rate_limit_time_min = 0
					rate_limit_time_sec = 0
					if 'm' in rate_limit_time:
						rate_limit_time_min = rate_limit_time.split('m')[0]
						rate_limit_time = rate_limit_time.split('m')[1]  # get text after 'm'
					if 's' in rate_limit_time:
						rate_limit_time_sec = rate_limit_time.split('s')[0]
					total_wait_time = (int(rate_limit_time_min) * 60) + int(rate_limit_time_sec) + 1
				else:
					total_wait_time = 20
				print_progress(f' RL Wait{total_wait_time}s ')
				time.sleep(int(total_wait_time))
			elif '503' in e:  # Service Unavailable
				print_progress('Unavailable Wait ')
				time.sleep(15)
			elif e == 'Connection error.':
				print_progress('Server not online ')
			else:
				print_progress(f'Error Retrying ')
	raise Exception(f'No response from the bot after {max_retries} retries')
