__author__ = 'mdavid'

from bcresolver import *

if __name__ == '__main__':

    nc_resolver = NamecoinResolver(
        host='127.0.0.1',
        user='rpcuser',
        password='rpcpassword',
        port=8336,
        temp_dir='/tmp'
    )

    try:
        txt_result = nc_resolver.resolve('_wallet.wallet.mattdavid.bit', 'TXT')
        print('Resolved _wallet.wallet.mattdavid.bit (TXT): %s' % txt_result)

        a_result = nc_resolver.resolve('www.mattdavid.bit', 'A')
        print('Resolved www.mattdavid.bit (A): %s' % a_result)

        cname_result = nc_resolver.resolve('www2.mattdavid.bit', 'CNAME')
        print('Resolved www2.mattdavid.bit (CNAME): %s' % cname_result)

        mx_result = nc_resolver.resolve('mattdavid.bit', 'MX')
        print('Resolved mattdavid.bit (MX): %s [PRIORITY: %s]' % (mx_result[1], mx_result[0]))

        walletname_bit_result = nc_resolver.resolve('_btc._wallet.sample.walletname.bit', 'TXT')
        print('Resolved _btc._wallet.sample.walletname.bit (TXT): %s' % walletname_bit_result)

    except Exception as e:
        print('Valid DNS Entries Should Not Throw an Exception')

    try:
        no_resolve = nc_resolver.resolve('doesnotexist.non-existing-domain.bit', 'A')
    except NamecoinValueException:
        print('doesnotexist.non-existing-domain.bit does not exist on the blockchain')

    try:
        no_ds_records_configured = nc_resolver.resolve('example.domain.bit', 'A')
    except NoDSRecordException:
        print('Blockchain (Namecoin) record for example.domain.bit is missing DS records')

    # Display Additional Possible Exceptions with descriptions
    try:
        result = nc_resolver.resolve('www.mattdavid.bit', 'A')
        print('Resolved www.mattdavid.bit (A) without error: %s' % result)
    except NoNameserverException:
        print('Blockchain name entry has no nameserver (NS) records')

    except InvalidNameserverException:
        print('Unable to resolve NS server names for domain')

    except InsecureResultException:
        print('Insecure Result Returned')

    except BogusResultException:
        print('Resolution Result is Bogus')

    except EmptyResultException:
        print('Result returned without data')