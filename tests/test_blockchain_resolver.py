__author__ = 'mdavid'

from mock import *
from unittest import TestCase
from bcresolver import *

class TestBuildTempUnboundConfig(TestCase):

    def setUp(self):

        self.mockOpen = mock_open()

        self.patcher1 = patch('bcresolver.tempfile')
        self.patcher2 = patch('bcresolver.open', self.mockOpen, create=True)
        self.mockTempfile = self.patcher1.start()
        self.mockOpenPatch = self.patcher2.start()

        self.nc_resolver = NamecoinResolver() 

    def tearDown(self):

        self.patcher1.stop()
        self.patcher2.stop()

    def test_go_right(self):

        # Setup Mock
        self.mockTempfile.mktemp.return_value='temp_file_path'

        ret_val = self.nc_resolver._build_temp_unbound_config('somedomain.bit', '127.0.0.1')
        self.assertEqual('temp_file_path', ret_val)
        self.assertEqual(1, self.mockOpen.call_count)
        self.assertEqual('temp_file_path', self.mockOpen.call_args[0][0])
        self.assertEqual(1, self.mockOpen.return_value.write.call_count)
        self.assertEqual(1, self.mockOpen.return_value.flush.call_count)
        self.assertEqual(1, self.mockOpen.return_value.close.call_count)
        self.assertEqual('\nforward-zone:\n    name: "somedomain.bit"\n    forward-addr: 127.0.0.1\n    forward-first: yes\n        ', self.mockOpen.return_value.write.call_args[0][0])

    def test_no_zone(self):

        self.assertRaises(AttributeError, self.nc_resolver._build_temp_unbound_config, None, '127.0.0.1')

        self.assertEqual(0, self.mockOpen.call_count)
        self.assertEqual(0, self.mockOpen.return_value.write.call_count)
        self.assertEqual(0, self.mockOpen.return_value.flush.call_count)
        self.assertEqual(0, self.mockOpen.return_value.close.call_count)

    def test_no_nameserver(self):

        self.assertRaises(AttributeError, self.nc_resolver._build_temp_unbound_config, 'somedomain.bit', None)

        self.assertEqual(0, self.mockOpen.call_count)
        self.assertEqual(0, self.mockOpen.return_value.write.call_count)
        self.assertEqual(0, self.mockOpen.return_value.flush.call_count)
        self.assertEqual(0, self.mockOpen.return_value.close.call_count)

    def test_tempfile_exception(self):

        # Setup Mock
        self.mockTempfile.mktemp.side_effect = Exception('Cannot create a tempfile here bro')

        self.assertRaises(Exception, self.nc_resolver._build_temp_unbound_config, 'somedomain.bit', '127.0.0.1')
        self.assertEqual(0, self.mockOpen.call_count)
        self.assertEqual(0, self.mockOpen.return_value.write.call_count)
        self.assertEqual(0, self.mockOpen.return_value.flush.call_count)
        self.assertEqual(0, self.mockOpen.return_value.close.call_count)

class TestDeleteTempUnboundConfig(TestCase):

    def setUp(self):

        self.patcher1 = patch('bcresolver.os')
        self.mockOS = self.patcher1.start()

        self.nc_resolver = NamecoinResolver()

    def tearDown(self):

        self.patcher1.stop()

    def test_go_right(self):

        ret_val = self.nc_resolver._delete_temp_unbound_config('temp_file_name')

        self.assertEqual(1, self.mockOS.unlink.call_count)
        self.assertEqual('temp_file_name', self.mockOS.unlink.call_args[0][0])
        self.assertTrue(ret_val)

    def test_unlink_exception(self):

        self.mockOS.unlink.side_effect = Exception('Unable to Unlink File')

        ret_val = self.nc_resolver._delete_temp_unbound_config('temp_file_name')

        self.assertEqual(1, self.mockOS.unlink.call_count)
        self.assertEqual('temp_file_name', self.mockOS.unlink.call_args[0][0])
        self.assertFalse(ret_val)

class TestResolve(TestCase):

    def setUp(self):

        self.patcher1 = patch('bcresolver.NamecoinClient')
        self.patcher2 = patch('bcresolver.ub_ctx')
        self.patcher3 = patch('bcresolver.NamecoinResolver._build_temp_unbound_config')
        self.patcher4 = patch('bcresolver.NamecoinResolver._delete_temp_unbound_config')

        self.mockNamecoinClient = self.patcher1.start()
        self.mockUnboundContext = self.patcher2.start()
        self.mockBuildUnboundConfig = self.patcher3.start()
        self.mockDeleteUnboundConfig = self.patcher4.start()

        self.mockNamecoinClient.return_value.get_domain.return_value = {
            'value': json.dumps({
                'ds': [[40039, 8, 2, 'NZbut7iqVxCP0IGCX7J1DA/DrbrkFJzEML1PetAxVzQ=']],
                'ns': ['pdns83.ultradns.org', 'pdns83.ultradns.com', 'pdns83.ultradns.net', 'pdns83.ultradns.biz']
            })
        }

        # Setup Multiple Unbound Contexts
        self.ns_ctx = Mock()
        self.wallet_ctx = Mock()

        self.result_obj = Mock()
        self.result_obj.secure = 1
        self.result_obj.bogus = 0
        self.result_obj.havedata = 1
        self.result_obj.data.as_address_list.return_value = ['127.0.0.1']
        self.ns_ctx.resolve.return_value = (0, self.result_obj)

        self.result_obj2 = Mock()
        self.result_obj2.secure = 1
        self.result_obj2.bogus = 0
        self.result_obj2.havedata = 1
        self.result_obj2.data.as_domain_list.return_value = ['btc']
        self.wallet_ctx.resolve.return_value = (0, self.result_obj2)

        self.mockUnboundContext.side_effect = (self.ns_ctx, self.wallet_ctx)

        self.mockBuildUnboundConfig.return_value = 'temp_config_file'

        self.nc_resolver = NamecoinResolver()

    def tearDown(self):

        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()
        self.patcher4.stop()

    def test_go_right_txt_rr(self):

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual('btc', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(2, self.mockUnboundContext.call_count)
        self.assertEqual(1, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(1, self.mockDeleteUnboundConfig.call_count)
        self.assertEqual(1, self.result_obj.data.as_address_list.call_count)
        self.assertEqual(1, self.result_obj2.data.as_domain_list.call_count)

        self.assertEqual(1, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(1, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(1, self.wallet_ctx.config.call_count)
        self.assertEqual(1, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_go_right_cname_rr(self):

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'CNAME')

        self.assertEqual('btc', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(2, self.mockUnboundContext.call_count)
        self.assertEqual(1, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(1, self.mockDeleteUnboundConfig.call_count)
        self.assertEqual(1, self.result_obj.data.as_address_list.call_count)
        self.assertEqual(1, self.result_obj2.data.as_domain_list.call_count)

        self.assertEqual(1, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(1, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(1, self.wallet_ctx.config.call_count)
        self.assertEqual(1, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_go_right_a_rr(self):

        self.result_obj2.data.as_address_list.return_value = ['127.0.0.1']

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'A')

        self.assertEqual('127.0.0.1', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(2, self.mockUnboundContext.call_count)
        self.assertEqual(1, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(1, self.mockDeleteUnboundConfig.call_count)
        self.assertEqual(1, self.result_obj.data.as_address_list.call_count)
        self.assertEqual(1, self.result_obj2.data.as_address_list.call_count)

        self.assertEqual(1, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(1, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(1, self.wallet_ctx.config.call_count)
        self.assertEqual(1, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_go_right_aaaa_rr(self):

        self.result_obj2.data.as_address_list.return_value = ['0000:0000:0000:0000:0000:0000:0000:0000']

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'AAAA')

        self.assertEqual('0000:0000:0000:0000:0000:0000:0000:0000', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(2, self.mockUnboundContext.call_count)
        self.assertEqual(1, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(1, self.mockDeleteUnboundConfig.call_count)
        self.assertEqual(1, self.result_obj.data.as_address_list.call_count)
        self.assertEqual(1, self.result_obj2.data.as_address_list.call_count)

        self.assertEqual(1, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(1, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(1, self.wallet_ctx.config.call_count)
        self.assertEqual(1, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_go_right_mx_rr(self):

        self.result_obj2.data.as_mx_list.return_value = [(10, 'mx.mattdavid.bit')]

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'MX')

        self.assertEqual((10, 'mx.mattdavid.bit'), ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(2, self.mockUnboundContext.call_count)
        self.assertEqual(1, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(1, self.mockDeleteUnboundConfig.call_count)
        self.assertEqual(1, self.result_obj.data.as_address_list.call_count)
        self.assertEqual(1, self.result_obj2.data.as_mx_list.call_count)

        self.assertEqual(1, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(1, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(1, self.wallet_ctx.config.call_count)
        self.assertEqual(1, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_no_domain_data(self):

        self.mockNamecoinClient.return_value.get_domain.return_value = None

        try:
            ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'TXT')
            self.assertTrue(False)
        except NamecoinValueException as e:
            self.assertEqual('No Name Value Data Found for: d/testdomain', e.message)
        except:
            raise

        self.assertEqual(0, self.ns_ctx.resolve.call_count)
        self.assertEqual(0, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(0, self.ns_ctx.add_ta_file.call_count)

    def test_unsupported_rr_type(self):

        try:
            ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'SRV')
            self.assertTrue(False, 'SRV is an unsupported RRSet query type')

        except NotImplementedError as e:
            self.assertEqual('Unsupported DNS Query Type: SRV', e.message)

        except Exception as e:
            raise

        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(2, self.mockUnboundContext.call_count)
        self.assertEqual(1, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(1, self.mockDeleteUnboundConfig.call_count)
        self.assertEqual(1, self.result_obj.data.as_address_list.call_count)
        self.assertEqual(0, self.result_obj2.data.as_mx_list.call_count)

        self.assertEqual(1, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(1, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(1, self.wallet_ctx.config.call_count)
        self.assertEqual(1, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_go_right_hex_ds(self):

        self.mockNamecoinClient.return_value.get_domain.return_value = {
            'value': json.dumps({
                'ds': [[40039, 8, 2, '3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734']],
                'ns': ['pdns83.ultradns.org', 'pdns83.ultradns.com', 'pdns83.ultradns.net', 'pdns83.ultradns.biz']
            })
        }

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual('btc', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(2, self.mockUnboundContext.call_count)
        self.assertEqual(1, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(1, self.mockDeleteUnboundConfig.call_count)

        self.assertEqual(1, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(1, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(1, self.wallet_ctx.config.call_count)
        self.assertEqual(1, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])


    def test_non_bit_tld(self):

        self.assertRaises(ValueError, self.nc_resolver.resolve, '_wallet.wallet.testdomain.com', 'TXT')
        self.assertEqual(0, self.mockNamecoinClient.call_count)

    def test_tld_only(self):

        self.assertRaises(ValueError, self.nc_resolver.resolve, 'bit', 'TXT')
        self.assertEqual(0, self.mockNamecoinClient.call_count)

    def test_missing_ds_records(self):

        self.mockNamecoinClient.return_value.get_domain.return_value['value'] = json.dumps({'ns':['127.0.0.1']})

        self.assertRaises(NoDSRecordException, self.nc_resolver.resolve, '_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(0, self.mockUnboundContext.call_count)
        self.assertEqual(0, self.mockBuildUnboundConfig.call_count)

    def test_missing_ns_records(self):

        self.mockNamecoinClient.return_value.get_domain.return_value['value'] = json.dumps({'ds':['bob']})

        self.assertRaises(NoNameserverException, self.nc_resolver.resolve, '_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(0, self.mockUnboundContext.call_count)
        self.assertEqual(0, self.mockBuildUnboundConfig.call_count)

    def test_no_trust_anchor_file(self):

        self.mockOSPatcher = patch('bcresolver.os.path.isfile')
        self.mockOS = self.mockOSPatcher.start()

        self.mockOS.return_value = False

        self.assertRaises(Exception, self.nc_resolver.resolve, '_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(1, self.mockUnboundContext.call_count)
        self.assertEqual(0, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(0, self.mockDeleteUnboundConfig.call_count)
        self.assertEqual(0, self.ns_ctx.resolve.call_count)

        self.mockOSPatcher.stop()

    def test_empty_nameservers(self):

        data = json.loads(self.mockNamecoinClient.return_value.get_domain.return_value['value'])
        data['ns'] = []
        self.mockNamecoinClient.return_value.get_domain.return_value['value'] = json.dumps(data)

        self.assertRaises(NoNameserverException, self.nc_resolver.resolve, '_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(0, self.mockUnboundContext.call_count)
        self.assertEqual(0, self.mockBuildUnboundConfig.call_count)

    def test_fail_ns_lookup_all(self):

        self.ns_ctx.resolve.return_value = (-1, 'Resolution Failed')

        self.assertRaises(InvalidNameserverException, self.nc_resolver.resolve, '_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(1, self.mockUnboundContext.call_count)
        self.assertEqual(0, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(0, self.mockDeleteUnboundConfig.call_count)

        self.assertEqual(4, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual(0, self.wallet_ctx.resolve.call_count)

    def test_fail_ns_lookup_one_status(self):

        result_obj = Mock()
        result_obj.secure = 1
        result_obj.bogus = 0
        result_obj.havedata = 1
        result_obj.data.as_address_list.return_value = ['127.0.0.1']

        self.ns_ctx.resolve.side_effect = (
            (-1, 'Resolution Failed'),
            (0, result_obj)
        )

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual('btc', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(2, self.mockUnboundContext.call_count)
        self.assertEqual(1, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(1, self.mockDeleteUnboundConfig.call_count)

        self.assertEqual(2, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(1, self.wallet_ctx.resolve.call_count)
        self.assertFalse(0, self.wallet_ctx.resolvconf.called)
        self.assertEqual(1, self.wallet_ctx.config.call_count)
        self.assertEqual(1, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_fail_ns_lookup_one_bogus(self):

        bogus_result_obj = Mock()
        bogus_result_obj.secure = 1
        bogus_result_obj.bogus = 1
        bogus_result_obj.havedata = 1
        bogus_result_obj.data.as_address_list.return_value = ['127.0.0.1']

        result_obj = Mock()
        result_obj.secure = 1
        result_obj.bogus = 0
        result_obj.havedata = 1
        result_obj.data.as_address_list.return_value = ['127.0.0.1']

        self.ns_ctx.resolve.side_effect = (
            (0, bogus_result_obj),
            (0, result_obj)
        )

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual('btc', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(2, self.mockUnboundContext.call_count)
        self.assertEqual(1, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(1, self.mockDeleteUnboundConfig.call_count)

        self.assertEqual(2, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(1, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(1, self.wallet_ctx.config.call_count)
        self.assertEqual(1, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_fail_wallet_name_lookup_status_fail_once(self):

        bogus_result_obj = Mock()
        bogus_result_obj.secure = 1
        bogus_result_obj.bogus = 0
        bogus_result_obj.havedata = 1
        bogus_result_obj.data.as_domain_list.return_value = ['btc']

        result_obj = Mock()
        result_obj.secure = 1
        result_obj.bogus = 0
        result_obj.havedata = 1
        result_obj.data.as_domain_list.return_value = ['btc']

        self.wallet_ctx.resolve.side_effect = (
            (-1, bogus_result_obj),
            (0, result_obj)
        )

        self.mockUnboundContext.side_effect = (self.ns_ctx, self.wallet_ctx, self.wallet_ctx)

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual('btc', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(3, self.mockUnboundContext.call_count)
        self.assertEqual(2, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(2, self.mockDeleteUnboundConfig.call_count)

        self.assertEqual(2, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(2, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(2, self.wallet_ctx.config.call_count)
        self.assertEqual(2, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_fail_wallet_name_lookup_secure_once(self):

        bogus_result_obj = Mock()
        bogus_result_obj.secure = 0
        bogus_result_obj.bogus = 0
        bogus_result_obj.havedata = 1
        bogus_result_obj.data.as_domain_list.return_value = ['btc']

        result_obj = Mock()
        result_obj.secure = 1
        result_obj.bogus = 0
        result_obj.havedata = 1
        result_obj.data.as_domain_list.return_value = ['btc']

        self.wallet_ctx.resolve.side_effect = (
            (0, bogus_result_obj),
            (0, result_obj)
        )

        self.mockUnboundContext.side_effect = (self.ns_ctx, self.wallet_ctx, self.wallet_ctx)

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual('btc', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(3, self.mockUnboundContext.call_count)
        self.assertEqual(2, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(2, self.mockDeleteUnboundConfig.call_count)

        self.assertEqual(2, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(2, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(2, self.wallet_ctx.config.call_count)
        self.assertEqual(2, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_fail_wallet_name_lookup_bogus_once(self):

        bogus_result_obj = Mock()
        bogus_result_obj.secure = 1
        bogus_result_obj.bogus = 1
        bogus_result_obj.havedata = 1
        bogus_result_obj.data.as_domain_list.return_value = ['btc']

        result_obj = Mock()
        result_obj.secure = 1
        result_obj.bogus = 0
        result_obj.havedata = 1
        result_obj.data.as_domain_list.return_value = ['btc']

        self.wallet_ctx.resolve.side_effect = (
            (0, bogus_result_obj),
            (0, result_obj)
        )

        self.mockUnboundContext.side_effect = (self.ns_ctx, self.wallet_ctx, self.wallet_ctx)

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual('btc', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(3, self.mockUnboundContext.call_count)
        self.assertEqual(2, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(2, self.mockDeleteUnboundConfig.call_count)

        self.assertEqual(2, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(2, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(2, self.wallet_ctx.config.call_count)
        self.assertEqual(2, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

    def test_fail_wallet_name_lookup_havedata_once(self):

        bogus_result_obj = Mock()
        bogus_result_obj.secure = 1
        bogus_result_obj.bogus = 0
        bogus_result_obj.havedata = 0
        bogus_result_obj.data.as_domain_list.return_value = ['btc']

        result_obj = Mock()
        result_obj.secure = 1
        result_obj.bogus = 0
        result_obj.havedata = 1
        result_obj.data.as_domain_list.return_value = ['btc']

        self.wallet_ctx.resolve.side_effect = (
            (0, bogus_result_obj),
            (0, result_obj)
        )

        self.mockUnboundContext.side_effect = (self.ns_ctx, self.wallet_ctx, self.wallet_ctx)

        ret_val = self.nc_resolver.resolve('_wallet.wallet.testdomain.bit', 'TXT')

        self.assertEqual('btc', ret_val)
        self.assertEqual(1, self.mockNamecoinClient.call_count)
        self.assertEqual(1, self.mockNamecoinClient.return_value.get_domain.call_count)
        self.assertEqual('127.0.0.1', self.mockNamecoinClient.call_args[1]['host'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['password'])
        self.assertEqual(8336, self.mockNamecoinClient.call_args[1]['port'])
        self.assertEqual(60, self.mockNamecoinClient.call_args[1]['timeout'])
        self.assertEqual('', self.mockNamecoinClient.call_args[1]['user'])
        self.assertEqual(3, self.mockUnboundContext.call_count)
        self.assertEqual(2, self.mockBuildUnboundConfig.call_count)
        self.assertEqual(2, self.mockDeleteUnboundConfig.call_count)

        self.assertEqual(2, self.ns_ctx.resolve.call_count)
        self.assertEqual(1, self.ns_ctx.resolvconf.call_count)
        self.assertEqual(1, self.ns_ctx.add_ta_file.call_count)
        self.assertFalse(self.ns_ctx.add_ta.called)

        self.assertEqual('testdomain.bit. IN DS 40039 8 2 3596EEB7B8AA57108FD081825FB2750C0FC3ADBAE4149CC430BD4F7AD0315734', self.wallet_ctx.add_ta.call_args[0][0])

        self.assertEqual('testdomain.bit.', self.mockBuildUnboundConfig.call_args[0][0])
        self.assertEqual('127.0.0.1', self.mockBuildUnboundConfig.call_args[0][1])

        self.assertEqual(2, self.wallet_ctx.resolve.call_count)
        self.assertFalse(self.wallet_ctx.resolvconf.called)
        self.assertEqual(2, self.wallet_ctx.config.call_count)
        self.assertEqual(2, self.wallet_ctx.add_ta.call_count)
        self.assertFalse(self.wallet_ctx.add_ta_file.called)

        self.assertEqual('temp_config_file', self.wallet_ctx.config.call_args[0][0])
        self.assertEqual('temp_config_file', self.mockDeleteUnboundConfig.call_args[0][0])

