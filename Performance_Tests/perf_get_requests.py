import os
import sys
import json
import glob
import utils
import request_builder
import requests_sender
import argparse
from indy import signus, wallet, pool
from indy.error import IndyError


# Run this script to process output from the .txt output from
# perf_add_requests.py or the add_nyms.py file.  This script will run the
# getting request command on all the requests info found in the .txt output
# files. The .txt files that used by this script should be stored in a
# subdirectory in the same location this script is running from.
# The command line options allow the user to specify the location of the text
# files to process, the location of the genesis transaction file and the name
# of the genesis transaction file.
# If these options are not specified, default values will be used.

# Examples:
# specify the location for a genesis transaction file:
#   python3.6 Perf_get_nyms.py -t ~/PycharmProjects/multithread/stability_pool
# specify the directory name that contains the NYM files to process:
#     python3.6 Perf_get_nyms.py -d /home/devone/PycharmProjects/multithread
# specify the name of the genesis transaction file:
#     python3.6 Perf_get_nyms.py -g test_file


class Options:
    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Script to feed multiple NYMs from files created '
                        'by the \'perf_add_requests.py\'')

        parser.add_argument('-d',
                            help='Specify the directory that contains the .txt'
                                 ' files with requests info.  The default '
                                 'directory is set to the "request_info" '
                                 'directory in the scripts current working '
                                 'directory.', action='store',
                            default=os.path.join(os.path.dirname(__file__),
                                                 "request_info"),
                            dest='info_dir')

        parser.add_argument('-k',
                            help='Kind of request to be sent. '
                                 'The default value will be "nym"',
                            action='store',
                            choices=['nym', 'schema', 'attribute', 'claim'],
                            default='nym', dest='kind')

        parser.add_argument('-b',
                            help='To see additional output,'
                                 ' set debug output to true',
                            action='store_true', default=False,
                            dest='debug')

        parser.add_argument('-s',
                            help='Specify the number of threads'
                                 'The default value will be 1', action='store',
                            type=int, default=1, dest='thread_num')

        parser.add_argument('-l',
                            help='To see all log. If this flag does not exist,'
                                 'program just only print fail message',
                            action='store_true', default=False)

        self.args = parser.parse_args()


class PerformanceTesterGetSentRequestFromLedger:
    def __init__(self, info_dir=os.path.join(os.path.dirname(__file__),
                                             "request_info"),
                 kind='nym', thread_num=1, debug=False, log=False):
        if thread_num <= 0:
            self.thread_num = 1
        else:
            self.thread_num = thread_num
        self.info_dir = info_dir
        self.req_kind = kind
        self.debug = debug
        self.config = utils.parse_config()
        self.pool_handle = self.wallet_handle = 0
        self.submitter_did = ''
        self.seed = '000000000000000000000000Steward1'
        self.log = log

        self.threads = list()
        self.works_per_threads = list()
        self.lst_req_info = list()
        self.start_time = self.finish_time = 0
        self.passed_req = self.failed_req = 0
        self.pool_name = utils.generate_random_string(prefix="pool")
        self.wallet_name = utils.generate_random_string(prefix='wallet')

    async def test(self):
        """  Process to run the Ger NYMs command """

        infor_files = self.__collect_requests_info_files()

        if self.debug:
            print("\n\n" + 50 * "-")
            print("Pool name: %s" % self.pool_name)
            print("Key to use: %s" % str(self.seed))
            print("Directory to use: " + self.info_dir)
            print("Path to genesis transaction file: " +
                  str(self.config.pool_genesis_file))
            print(50 * '-')
            # print("Thread Number %d" % repr(threadnum))
            # input("Wait.........")

        # 1. Create ledger config from genesis txn file
        await self.__create_pool_config()

        # 2. Open pool
        await self.__open_pool()

        # 3. Create My Wallet and Get Wallet Handle
        await self.__create_wallet()
        await self.__open_wallet()

        # 4. Create the DID to use
        await self.__create_submitter_did()

        args = {'submitter_did': self.submitter_did,
                'pool_handle': self.pool_handle,
                'wallet_handle': self.wallet_handle}

        # 5. Build getting request from info from files.
        builder = request_builder.RequestBuilder(None, self.log)
        req_files = await builder.build_several_getting_req_to_files(
            args, self.req_kind, self.thread_num, infor_files)

        # 6. Submit getting request to ledger.
        sender = requests_sender.RequestsSender(self.log)
        try:
            await sender.submit_several_reqs_from_files(args, req_files,
                                                    self.req_kind)
        except Exception:
            pass

        self.passed_req, self.failed_req = sender.passed_req, sender.failed_req
        self.start_time, self.finish_time = (sender.start_time,
                                             sender.finish_time)

        # 7. Run the cleanup
        await self.__close_pool_and_wallet()

        utils.print_header('\n\t========= Finish =========')

    def get_elapsed_time(self):
        return self.finish_time - self.start_time

    def __collect_requests_info_files(self):

        lst_files = glob.glob(os.path.join(
            self.info_dir, '{}_requests_info*{}'.format(self.req_kind,
                                                        '.txt')))
        if not lst_files:
            utils.print_error('Cannot found any request info. '
                              'Skip sending get request... Abort')
            sys.exit(1)

        return lst_files

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
    options = Options()
    args = options.args
    tester = PerformanceTesterGetSentRequestFromLedger(args.info_dir,
                                                       args.kind,
                                                       args.thread_num,
                                                       args.debug, args.l)

    # Start the method
    elapsed_time = utils.run_async_method(None, tester.test)

    utils.print_client_result(tester.passed_req, tester.failed_req,
                              elapsed_time)
