__author__ = 'mdavid'

import base64
import json
import requests

class NamecoinException(Exception):
    def __init__(self, message=None, code=0):
        self.message =  message
        self.code = code

    def __str__(self):
        return 'NamecoinException [Code: %d | Message: %s]' % (self.code, self.message)

class NamecoinClient:

    def __init__(self, host='127.0.0.1', port=8336, user=None, password=None, timeout=60):

        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout

    def send(self, method='getinfo', params=[]):

        headers = {
            'User-Agent': 'bitcoin-json-rpc/0.3.50',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if self.user and self.password:
            headers['Authorization'] = 'Basic %s' %  base64.b64encode(self.user + ':' + self.password)

        req_data = {
            'method': method,
            'params': params,
            'id': 1}

        try:
            response = requests.post('http://%s:%d/' % (self.host, self.port), data=json.dumps(req_data), headers=headers, timeout=self.timeout)
        except:
            raise NamecoinException('Unable to connect to Namecoin node', 500)

        try:
            result = json.loads(response.text)
        except Exception as e:
            raise NamecoinException('Unable to parse namecoind rpc response', 500)

        if result.get('result'):
            return result.get('result')
        elif result.get('error'):
            raise NamecoinException(result.get('error').get('message', ''), int(result.get('error').get('code', 0)))

    ############################################
    # Domain Information and Registration
    ############################################
    def get_domain(self, name):
        try:
            response = self.send('name_show', ['d/%s' % name])
        except NamecoinException as e:
            if e.code == -4:
                return None
            raise
        return response