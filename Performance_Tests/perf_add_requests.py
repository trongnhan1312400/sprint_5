import os
import json
import time
import argparse
import utils
import threading
import requests_builder
import requests_sender
from indy import signus, wallet, pool
from indy.error import IndyError


# The genesis pool transaction file and the
# script (perf_add_requests.py) should both
# be in the same directory.
# To run, make sure to pass the key to use when creating the DIDs, for
# example: python3.6 perf_add_requests.py
# testPool 100 TestAddNodeWithTrustAnchor000001
#          python3.6 perf_add_requests.py testPool 500
# 000000000000000000000000Steward1 <number_of_threads>
# -----------------------------------------------------------------------------

class Option:
    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Script to create multiple requests '
                        'and store their info in .txt files to be  '
                        'used by the \'perf_get_requests.py\' script.\n\n',
            usage='To create 500 NYMs in the default \'request_info\' directory '
                  'and use \nthe default \'stability_pool\' transaction file '
                  'in the current working directory, '
                  '\nuse: python3.6 perf_add_requests.py -p '
                  'testPool -n 500 -i 000000000000000000000000Steward1 -s 1')

        parser.add_argument('-d',
                            help='Specify the directory location to store '
                                 'information of sent request as .txt files.  '
                                 'The default directory is set to the '
                                 'directory in this scripts '
                                 'current working '
                                 'directory.', action='store',
                            default=os.path.join(os.path.dirname(__file__),
                                                 "request_info"),
                            dest='info_dir')

        parser.add_argument('-n',
                            help='Specify the number of requests to be '
                                 'created.  The default value will be 100',
                            action='store', type=int, default=100,
                            dest='number_of_requests')

        parser.add_argument('-k',
                            help='Kind of request to be sent. '
                                 'The default value will be "nym"',
                            action='store',
                            choices=['nym', 'schema', 'attribute', 'claim'],
                            default='nym', dest='kind')

        parser.add_argument('-i',
                            help='Specify the role to use to create the NYMs. '
                                 ' The default trustee ID will be  used',
                            action='store',
                            default='000000000000000000000000Steward1',
                            dest='seed')

        parser.add_argument('-s',
                            help='Specify the number of threads'
                                 'The default value will be 1', action='store',
                            type=int, default=1, dest='thread_num')

        parser.add_argument('-b',
                            help='To see additional output, use -b in addition'
                                 ' to the other command line options',
                            action='store_true', default=False,
                            dest='debug')

        parser.add_argument('-l',
                            help='To see all log. If this flag does not exist,'
                                 'program just only print fail message',
                            action='store_true', default=False, dest='log')

        self.args = parser.parse_args()


class PerformanceTesterForAddingRequest:
    def __init__(self, info_dir=os.path.dirname(__file__),
                 request_num=100, request_kind='nym',
                 seed='000000000000000000000000Trustee1', thread_num=1,
                 debug=False, log=False):
        self.config = utils.parse_config()

        self.info_dir = os.path.join(info_dir, request_kind)
        self.req_num = request_num
        self.req_kind = request_kind
        self.log = log
        self.seed = seed
        if thread_num <= 0:
            self.thread_num = 1
        else:
            self.thread_num = thread_num
        self.debug = debug
        self.pool_handle = self.wallet_handle = 0
        self.submitter_did = ""

        self.info_file_path = "{}_{}_{}.txt".format(
            self.req_kind + "_requests_info", str(threading.get_ident()),
            time.strftime("%d-%m-%Y_%H-%M-%S"))

        self.info_file_path = os.path.join(self.info_dir,
                                           self.info_file_path)
        self.req_info = list()
        self.threads = list()

        self.passed_req = self.failed_req = 0
        self.start_time = self.finish_time = 0
        self.pool_name = utils.generate_random_string(prefix="pool")
        self.wallet_name = utils.generate_random_string(prefix='wallet')

        utils.create_folder(self.info_dir)

    async def test(self):

        if self.debug:
            print("Pool name: %s" % self.pool_name)
            print("Number of NYMs to create: %s" % str(self.req_num))
            print("Key to use %s" % str(self.seed))
            print("Thread Number %d" % self.thread_num)
            print("Where the requests info are stored: " + self.info_file_path)
            print(
                "Name and location of the genesis file: " +
                self.config.pool_genesis_file)
            input("Wait.........")

        # 1. Create pool config.
        await self.__create_pool_config()

        # 2. Open pool ledger
        await self.__open_pool()

        # 3. Create My Wallet and Get Wallet Handle
        await self.__create_wallet()
        await self.__open_wallet()

        if self.debug:
            print("Wallet:  %s" % str(self.wallet_handle))

        # 4 Create and sender DID
        await self.__create_submitter_did()

        if self.debug:
            print("Their DID: %s" % str(self.submitter_did))

        args = {'wallet_handle': self.wallet_handle,
                'pool_handle': self.pool_handle,
                'submitter_did': self.submitter_did}

        # 5. Build requests and save them in to files.
        builder = requests_builder.RequestBuilder(self.info_file_path,
                                                  self.log)

        req_files = await builder.build_several_adding_req_to_files(
            args, self.req_kind, self.thread_num, self.req_num)

        # 6. Sign and submit several request into ledger.
        sender = requests_sender.RequestsSender(self.log)
        try:
            await sender.sign_and_submit_several_reqs_from_files(
            args, req_files, self.req_kind)
        except Exception:
            pass
        self.passed_req, self.failed_req = sender.passed_req, sender.failed_req

        self.start_time, self.finish_time = (sender.start_time,
                                             sender.finish_time)

        await self.__close_pool_and_wallet()
        utils.print_header("\n\t======== Finished ========")

    def get_elapsed_time(self):
        return self.finish_time - self.start_time

    async def __create_pool_config(self):
        try:
            utils.print_header("\n\n\tCreate ledger config "
                               "from genesis txn file")

            pool_config = json.dumps(
                {'genesis_txn': self.config.pool_genesis_file})
            await pool.create_pool_ledger_config(self.pool_name,
                                                 pool_config)
        except IndyError as e:
            if e.error_code == 306:
                utils.print_warning("The ledger already exists, moving on...")
            else:
                utils.print_error(str(e))
                raise

    async def __open_pool(self):
        try:
            utils.print_header("\n\tOpen pool ledger")
            self.pool_handle = await pool.open_pool_ledger(
                self.pool_name,
                None)
        except IndyError as e:
            utils.print_error(str(e))

    async def __create_wallet(self):
        try:
            utils.print_header("\n\tCreate wallet")
            await wallet.create_wallet(self.pool_name,
                                       self.wallet_name,
                                       None, None, None)
        except IndyError as e:
            if e.error_code == 203:
                utils.print_warning(
                    "Wallet '%s' already exists.  "
                    "Skipping wallet creation..." % str(
                        self.wallet_name))
            else:
                utils.print_error(str(e))
                raise

    async def __open_wallet(self):
        try:
            utils.print_header("\n\tOpen wallet")
            self.wallet_handle = await wallet.open_wallet(
                self.wallet_name,
                None, None)
        except IndyError as e:
            utils.print_error(str(e))
            raise

    async def __create_submitter_did(self):
        try:
            utils.print_header("\n\tCreate DID to use when sending")

            self.submitter_did, _ = await signus.create_and_store_my_did(
                self.wallet_handle, json.dumps({'seed': self.seed}))

        except Exception as e:
            utils.print_error(str(e))
            raise

    async def __close_pool_and_wallet(self):
        utils.print_header("\n\tClose wallet")
        try:
            await wallet.close_wallet(self.wallet_handle)
        except Exception as e:
            utils.print_error("Cannot close wallet."
                              "Skip closing wallet...")
            utils.print_error(str(e))

        utils.print_header("\n\tClose pool")
        try:
            await pool.close_pool_ledger(self.pool_handle)
        except Exception as e:
            utils.print_error("Cannot close pool."
                              "Skip closing pool...")
            utils.print_error(str(e))

        utils.print_header("\n\tDelete wallet")
        try:
            await wallet.delete_wallet(self.wallet_name, None)
        except Exception as e:
            utils.print_error("Cannot delete wallet."
                              "Skip deleting wallet...")
            utils.print_error(str(e))

        utils.print_header("\n\tDelete pool")
        try:
            await pool.delete_pool_ledger_config(self.pool_name)
        except Exception as e:
            utils.print_error("Cannot delete pool."
                              "Skip deleting pool...")
            utils.print_error(str(e))


if __name__ == '__main__':
    options = Option()
    args = options.args
    tester = PerformanceTesterForAddingRequest(
        args.info_dir, args.number_of_requests, args.kind, args.seed,
        args.thread_num, args.debug, args.log)

    utils.run_async_method(None, tester.test)

    elapsed_time = tester.finish_time - tester.start_time

    utils.print_client_result(tester.passed_req, tester.failed_req,
                              elapsed_time)
