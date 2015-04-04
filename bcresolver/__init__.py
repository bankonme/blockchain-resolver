__author__ = 'mdavid'

import base64
import json
import logging
import os
import re
import tempfile
from dns import rdatatype, rdataclass
from unbound import ub_ctx

# Local Import(s)
from namecoin import NamecoinClient

# Setup Logging
log = logging.getLogger()

class NamecoinValueException(BaseException):
    pass

class NoNameserverException(BaseException):
    pass

class InvalidNameserverException(BaseException):
    pass

class NoDSRecordException(BaseException):
    pass

class InsecureResultException(BaseException):
    pass

class BogusResultException(BaseException):
    pass

class EmptyResultException(BaseException):
    pass

class NamecoinResolver:
    def __init__(self, resolv_conf='/etc/resolv.conf', dnssec_root_key='/usr/local/etc/unbound/root.key', host=None, user=None, password=None, port=8336, temp_dir=None):
        '''

        Initialize a NamecoinResolver object

        :param host: Namecoin Node Hostname (DNS Name or IP Address)
        :param user: Namecoin Node Username
        :param password: Namecoin Node Password
        :param port: Namecoin Node Port (Default is 8336)
        :param temp_dir: Directory for temporary Unbound config files. We suggest a ramdisk-backed volume
        :return: NamecoinResolver object
        '''

        self.resolv_conf = resolv_conf
        self.dnssec_root_key = dnssec_root_key
        self.host = host if host else '127.0.0.1'
        self.user = user if user else ''
        self.password = password if password else ''
        self.port = port if port else 8336
        self.temp_dir = temp_dir

    def _build_temp_unbound_config(self, zone, nameserver):
        '''

        Build a temporary forward-first config file for use with Unbound

        :param zone: Namecoin-based Second Level Domain to be Resolved
        :param nameserver: IP Address of Nameserver to be used for resolution (retrieved from Namecoin name value)
        :return: Path to newly created temporary config file for use with Unbound
        '''

        if not zone:
            raise AttributeError('_build_temp_unbound_config requires a zone')

        if not nameserver:
            raise AttributeError('_build_temp_unbound_config requires a nameserver')

        # Create Temporary Config File
        try:
            tmp_config_file = tempfile.mktemp(prefix='unbound-config', dir=self.temp_dir)
        except Exception as e:
            log.error('ERROR: Unable to create temporary config file: %s' % str(e))
            raise e

        config_contents = """
forward-zone:
    name: "%s"
    forward-addr: %s
    forward-first: yes
        """ % (zone, nameserver)

        log.debug('Creating Temp Unbound Config File: %s' % tmp_config_file)
        cf = open(tmp_config_file, 'w')
        cf.write(config_contents)
        cf.flush()
        cf.close()

        return tmp_config_file

    def _delete_temp_unbound_config(self, filename):
        '''

        Deletes given filename (if it exists)

        :param filename: Path to delete
        :return: Boolean based on file deletion success
        '''

        log.debug('Removing Temp Unbound Config File: %s' % filename)
        try:
            os.unlink(filename)
            return True
        except Exception as e:
            log.error('Unable to Remove Temp Unbound Config File: %s' % str(e))
            return False

    def resolve(self, name, qtype):
        '''

        Resolves a Blockchain-based (Namecoin) DNS Name via 2 step process using DNSSEC

        Step 1:
        -------
        Get NS and DS records for the Namecoin name (for example: www.mattdavid.bit) from the Namecoin Client

        Step 2:
        -------
        For each listed nameserver:

            - Create a temporary config file for use with unbound
            - Set Unbound's Trust Anchor to be the given DS records for the Namecoin-based domain name
            - Do DNSSEC-enabled DNS resolution for the given name / qtype


        :param name: DNS Record Name Query (for example: www.mattdavid.bit)
        :param qtype: String representation of query type (for example: A, AAAA, TXT, NS, SOA, etc...)
        :return: Resolved value if successful, None if un-successful
        '''

        name = name.rstrip('.')
        if not name.endswith('.bit'):
            raise ValueError('This is not a valid .bit domain')

        domains = name.split('.')
        domains.reverse()
        if len(domains) < 2:
            raise ValueError('At least SLD Required')

        client = NamecoinClient(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            timeout=60
        )

        # Get Namecoin-based Domain Info from Namecoin Blockchain
        nc_domain = client.get_domain(domains[1])
        if not nc_domain or not nc_domain.get('value'):
            log.error('No Name Value Data Found for Namecoin-based Domain Name: d/%s' % domains[1])
            raise NamecoinValueException('No Name Value Data Found for: d/%s' % domains[1])

        nc_value = json.loads(nc_domain.get('value', '{}').replace('\'','"'))
        if not nc_value.get('ds'):
            log.error('No DS Records Present for Namecoin-based Domain Name: %s' % name)
            raise NoDSRecordException()

        if not nc_value.get('ns'):
            log.error('No NS Records Present for Namecoin-based Domain Name: %s' % name)
            raise NoNameserverException()

        sld = '%s.%s.' % (domains[1], domains[0])
        ds_record = ' '.join([str(x) for x in nc_value['ds'][0][0:3]])

        # Handle both Hex and Base64 encoding (Base64 is the preferred encoding) per:
        # https://wiki.namecoin.info/index.php?title=Domain_Name_Specification
        if re.match('^[0-9a-fA-F]*$', nc_value['ds'][0][3]):
            ds_record += ' %s' % nc_value['ds'][0][3]
        else:
            ds_record += ' %s' % base64.b64decode(nc_value['ds'][0][3]).encode('hex').upper()

        ds_ta = '%s IN DS %s' % (sld, ds_record)

        ns_ctx = ub_ctx()
        ns_ctx.resolvconf(self.resolv_conf)

        if not os.path.isfile(self.dnssec_root_key):
            log.error("Trust anchor missing or inaccessible")
            raise Exception("Trust anchor is missing or inaccessible: %s" % self.dnssec_root_key)
        else:
            ns_ctx.add_ta_file(self.dnssec_root_key)

        last_error = None
        for ns in nc_value.get('ns', []):

            lookup_value = None

            status, result = ns_ctx.resolve(ns, rdatatype.from_text('A'), rdataclass.from_text('IN'))

            # NOTE: We do not require secure DNS resolution here because the Blockchain-stored DS records work as the trust anchor
            # and the signed RRSIG DNS results from the final DNS+DNSSEC lookup will be able to complete the chain of trust
            if status == 0 and result and result.data and not result.bogus:
                tmp_config_file = self._build_temp_unbound_config(sld, result.data.as_address_list()[0])
            else:
                last_error = InvalidNameserverException()
                log.warn('No or Invalid Resolution Result for Nameserver: %s' % ns)
                continue

            ctx = ub_ctx()
            ctx.config(tmp_config_file)
            ctx.add_ta(str(ds_ta))

            _qtype = None
            try:
                _qtype = rdatatype.from_text(qtype)
            except Exception as e:
                log.error('Unable to get RDATAType for Given Query Type [%s]: %s' % (qtype, str(e)))
                raise ValueError('Unable to get RDATAType for Query Type %s' % qtype)

            status, result = ctx.resolve(name, _qtype, rdataclass.from_text('IN'))
            if status != 0:
                log.info("DNS Resolution Failed: %s [%s]" % (name, _qtype))
            elif status == 0:

                if not result.secure:
                    log.info("DNS Resolution Returned Insecure Result: %s [%s]" % (name, qtype))
                    last_error = InsecureResultException()

                elif result.bogus:
                    log.info("DNS Resolution Returned Bogus Result: %s [%s]" % (name, qtype))
                    last_error = BogusResultException()

                elif not result.havedata:
                    log.info("DNS Resolution Returned Empty Result: %s [%s]" % (name, qtype))
                    last_error = EmptyResultException()

                else:
                    # Get appropriate data by query type
                    if qtype in ['A','AAAA']:
                        lookup_value = result.data.as_address_list()
                    elif qtype in ['CNAME','TXT']:
                        lookup_value = result.data.as_domain_list()
                    elif qtype in ['MX']:
                        lookup_value = result.data.as_mx_list()
                    else:
                        last_error = NotImplementedError('Unsupported DNS Query Type: %s' % qtype)

            self._delete_temp_unbound_config(tmp_config_file)

            if lookup_value:
                return lookup_value[0]

            if last_error and isinstance(last_error, NotImplementedError):
                raise last_error

        log.error('DNS Resolution Failed: %s [%s]' % (name, qtype))
        if last_error:
            raise last_error

        return None

if __name__ == '__main__':

    resolver = NamecoinResolver(
        host='127.0.0.1',
        user='namecoin',
        password='v9WF1Cm_Mxl88d.vav6Yud',
    )

    result = resolver.resolve('www.mattdavid.bit', 'A')
    print result
    result = resolver.resolve('www2.mattdavid.bit', 'CNAME')
    print result
    result = resolver.resolve('mattdavid.bit', 'MX')
    print result
    result = resolver.resolve('_btc._wallet.sample.walletname.bit', 'TXT')
    print result