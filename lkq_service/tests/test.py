import requests
import os

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

data = {}
files = {'file': open(os.path.join(__location__, 'mm.txt.zip'), 'rb')}
req = requests.post('http://localhost:8069/lkq/invoices', data=data, files=files)
