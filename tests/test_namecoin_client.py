__author__ = 'mdavid'

import json
from mock import *
from unittest import TestCase
from bcresolver.namecoin import NamecoinClient, NamecoinException

class TestNamecoinException(TestCase):

    def test_go_right(self):

        ex = NamecoinException(message='test_message', code=42)
        msg = str(ex)
        self.assertEqual('NamecoinException [Code: 42 | Message: test_message]', msg)

class TestNamecoinInit(TestCase):

    def test_empty_params(self):

        nc = NamecoinClient()
        self.assertEqual('127.0.0.1', nc.host)
        self.assertEqual(8336, nc.port)
        self.assertIsNone(nc.user)
        self.assertIsNone(nc.password)
        self.assertEqual(60, nc.timeout)

    def test_with_params(self):

        nc = NamecoinClient('namecoin.local', 4242, 'billybob', '1234567890', 42)
        self.assertEqual('namecoin.local', nc.host)
        self.assertEqual(4242, nc.port)
        self.assertEqual('billybob', nc.user)
        self.assertEqual('1234567890', nc.password)
        self.assertEqual(42, nc.timeout)

class TestNamecoinSend(TestCase):

    def setUp(self):

        self.patcher1 = patch('bcresolver.namecoin.requests')
        self.mockRequests = self.patcher1.start()
        self.mockRequests.post.return_value.text = json.dumps({
            'result': {
                'name': 'd/mattdavid',
                'value': "{'ns': ['pdns83.ultradns.com', 'pdns83.ultradns.net', 'pdns83.ultradns.biz', 'pdns83.ultradns.org'], 'ds': [[40039, 8, 1, '0A939E5C82BFFC65A87BB27FFB2C04D6CED01E24'], [40039, 8, 2, '3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734']]}",
                'txid': '09ff56a2eb53598f0fe2933a2cec881ee3443468f42cd4998dc6524d88d6f2ab',
                'address': 'NDujvTbg2BU1CbeejURo5rbZJEs44Rtm2N',
                'expires_in': 35478
            }
        })

        self.nc_client = NamecoinClient('namecoin.local', 4242, 'billybob', '1234567890', 42)

    def tearDown(self):

        self.patcher1.stop()

    def test_go_right(self):

        try:
            result = self.nc_client.send('name_show', ['d/mattdavid'])
        except:
            self.assertTrue(False)

        self.assertTrue(self.mockRequests.post.called)
        self.assertEqual('http://namecoin.local:4242/',self.mockRequests.post.call_args[0][0])
        self.assertEqual('{"params": ["d/mattdavid"], "method": "name_show", "id": 1}', self.mockRequests.post.call_args[1]['data'])
        self.assertEqual({'Content-Type': 'application/json', 'Authorization': 'Basic YmlsbHlib2I6MTIzNDU2Nzg5MA==', 'Accept': 'application/json', 'User-Agent': 'bitcoin-json-rpc/0.3.50'}, self.mockRequests.post.call_args[1]['headers'])
        self.assertEqual(42, self.mockRequests.post.call_args[1]['timeout'])
        self.assertEqual('d/mattdavid', result.get('name'))
        self.assertEqual('09ff56a2eb53598f0fe2933a2cec881ee3443468f42cd4998dc6524d88d6f2ab', result.get('txid'))
        self.assertEqual('NDujvTbg2BU1CbeejURo5rbZJEs44Rtm2N', result.get('address'))
        self.assertEqual(35478, result.get('expires_in'))
        self.assertEqual("{'ns': ['pdns83.ultradns.com', 'pdns83.ultradns.net', 'pdns83.ultradns.biz', 'pdns83.ultradns.org'], 'ds': [[40039, 8, 1, '0A939E5C82BFFC65A87BB27FFB2C04D6CED01E24'], [40039, 8, 2, '3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734']]}", result.get('value'))

    def test_requests_exception(self):

        self.mockRequests.post.side_effect = Exception()

        try:
            result = self.nc_client.send('name_show', ['d/mattdavid'])
            self.assertTrue(False)
        except NamecoinException:
            pass
        except Exception:
            raise

        self.assertTrue(self.mockRequests.post.called)
        self.assertEqual('http://namecoin.local:4242/',self.mockRequests.post.call_args[0][0])
        self.assertEqual('{"params": ["d/mattdavid"], "method": "name_show", "id": 1}', self.mockRequests.post.call_args[1]['data'])
        self.assertEqual({'Content-Type': 'application/json', 'Authorization': 'Basic YmlsbHlib2I6MTIzNDU2Nzg5MA==', 'Accept': 'application/json', 'User-Agent': 'bitcoin-json-rpc/0.3.50'}, self.mockRequests.post.call_args[1]['headers'])
        self.assertEqual(42, self.mockRequests.post.call_args[1]['timeout'])

    def test_json_exception(self):

        self.mockRequests.post.return_value.text = None

        try:
            self.nc_client.send('name_show', ['d/mattdavid'])
            self.assertTrue(False)
        except NamecoinException as e:
            self.assertEqual('Unable to parse namecoind rpc response', e.message)
            self.assertEqual(500, e.code)

        self.assertTrue(self.mockRequests.post.called)
        self.assertEqual('http://namecoin.local:4242/',self.mockRequests.post.call_args[0][0])
        self.assertEqual('{"params": ["d/mattdavid"], "method": "name_show", "id": 1}', self.mockRequests.post.call_args[1]['data'])
        self.assertEqual({'Content-Type': 'application/json', 'Authorization': 'Basic YmlsbHlib2I6MTIzNDU2Nzg5MA==', 'Accept': 'application/json', 'User-Agent': 'bitcoin-json-rpc/0.3.50'}, self.mockRequests.post.call_args[1]['headers'])
        self.assertEqual(42, self.mockRequests.post.call_args[1]['timeout'])

    def test_error(self):

        self.mockRequests.post.return_value.text = json.dumps({
            'error': {
                'message': 'test_message',
                'code': 42
            }
        })

        try:
            self.nc_client.send('name_show', ['d/mattdavid'])
            self.assertTrue(False)
        except NamecoinException as e:
            self.assertEqual('test_message', e.message)
            self.assertEqual(42, e.code)

        self.assertTrue(self.mockRequests.post.called)
        self.assertEqual('http://namecoin.local:4242/',self.mockRequests.post.call_args[0][0])
        self.assertEqual('{"params": ["d/mattdavid"], "method": "name_show", "id": 1}', self.mockRequests.post.call_args[1]['data'])
        self.assertEqual({'Content-Type': 'application/json', 'Authorization': 'Basic YmlsbHlib2I6MTIzNDU2Nzg5MA==', 'Accept': 'application/json', 'User-Agent': 'bitcoin-json-rpc/0.3.50'}, self.mockRequests.post.call_args[1]['headers'])
        self.assertEqual(42, self.mockRequests.post.call_args[1]['timeout'])

class TestGetDomain(TestCase):

    def setUp(self):

        self.patcher1 = patch('bcresolver.namecoin.NamecoinClient.send')
        self.mockSend = self.patcher1.start()
        self.mockSend.return_value = 'response'

        self.nc_client = NamecoinClient('namecoin.local', 4242, 'billybob', '1234567890', 42)

    def tearDown(self):

        self.patcher1.stop()

    def test_go_right(self):

        ret_val = self.nc_client.get_domain('d/mattdavid')
        self.assertEqual('response', ret_val)

    def test_no_such_name(self):

        self.mockSend.side_effect = NamecoinException('no_such_name', -4)
        ret_val = self.nc_client.get_domain('d/mattdavid')
        self.assertIsNone(ret_val)

    def test_general_error(self):

        self.mockSend.side_effect = NamecoinException('invalid_error', 1024)
        try:
            self.nc_client.get_domain('d/mattdavid')
            self.assertTrue(False)
        except NamecoinException as e:
            self.assertEqual('invalid_error', e.message)
            self.assertEqual(1024, e.code)

