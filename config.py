import json

with open('config.json') as f:
    config = json.load(f)

page_id = config['page_id']
page_access_token = config['page_access_token']
