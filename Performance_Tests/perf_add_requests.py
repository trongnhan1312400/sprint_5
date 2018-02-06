import os
import json
import asyncio
import time
import argparse
import utils
import request_sender
import threading
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
# -------------------------------------------------------------------------------

class Option:
    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Script to create multiple requests '
                        'and store their info in .txt files to be  '
                        'used by the \'perf_get_request.py\' script.\n\n',
            usage='To create 500 NYMs in the default \'nym_files\' directory '
                  'and use \nthe default \'stability_pool\' transaction file '
                  'in the current working directory, '
                  '\nuse: python3.6 perf_add_requests.py -p '
                  'testPool -n 500 -i 000000000000000000000000Steward1 -s 1')

        parser.add_argument('-d',
                            help='Specify the directory location to store '
                                 'information of sent request as .txt files.  '
                                 'The default directory is set to the '
                                 '"request_info" directory in this scripts '
                                 'current working '
                                 'directory.', action='store',
                            default=os.path.join(os.path.dirname(__file__),
                                                 "request_info"),
                            dest='info_dir')

        parser.add_argument(
            '-g',
            help='Path to the genesis transaction file.  '
                 'The default is '
                 '"/var/lib/indy/sandbox/pool/'
                 'pool_transaction_sandbox_genesis".',
            action='store',
            default='/var/lib/indy/sandbox/pool'
                    '/pool_transaction_sandbox_genesis',
            dest='pool_genesis_txn_file')

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
                            default='000000000000000000000000Trustee1',
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

        self.args = parser.parse_args()


class PerformanceTesterForAddingRequest:
    def __init__(self, info_dir=os.path.join(os.path.dirname(__file__),
                                             "request_info"),
                 genesis_txn_file='/var/lib/indy/sandbox/pool'
                                  '/pool_transaction_sandbox_genesis',
                 request_num=100, request_kind='nym',
                 seed='000000000000000000000000Trustee1', thread_num=1,
                 debug=False):
        self.info_dir = info_dir
        self.genesis_file = genesis_txn_file
        self.req_num = request_num
        self.req_kind = request_kind
        self.seed = seed
        if thread_num <= 0:
            self.thread_num = 1
        else:
            self.thread_num = thread_num
        self.debug = debug
        self.pool_name = utils.generate_random_string(prefix="pool")
        self.wallet_name = utils.generate_random_string(prefix="wallet")
        self.pool_handle = self.wallet_handle = 0
        self.req_counter = 0
        self.submitter_did = ""

        self.info_file_path = "{}_{}_{}.txt".format(
            self.req_kind, str(self.thread_num),
            time.strftime("%d-%m-%Y_%H-%M-%S"))

        self.info_file_path = os.path.join(self.info_dir, self.req_kind,
                                           self.info_file_path)
        self.req_info = list()
        self.threads = list()

        utils.create_folder(os.path.join(self.info_dir, self.req_kind))

    async def test(self):

        if self.debug:
            print("Pool name: %s" % self.pool_name)
            print("Number of NYMs to create: %s" % str(self.req_num))
            print("Key to use %s" % str(self.seed))
            print("Thread Number %d" % self.thread_num)
            print("Where the requests info are stored: " + self.info_file_path)
            print(
                "Name and location of the genesis file: " + self.genesis_file)
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

        # 4.5 Create and sender DID
        await self.__create_submitter_did()

        if self.debug:
            print("Their DID: %s" % str(self.submitter_did))

        # 5. Send requests to ledger via threading.
        self.__start_threads()
        self.__finish_threads()

        await self.__cleanup()

        utils.print_header("\n\t========  Finished")

    def __divide_work(self):
        fixed_works = self.req_num // self.thread_num
        extra_works = self.req_num % self.thread_num

        works = list()
        for _ in range(self.thread_num):
            temp = fixed_works
            if extra_works > 0:
                temp += 1
                extra_works -= 1
            works.append(temp)

        return works

    def __send_requests_in_thread(self, work):
        if work <= 0:
            return
        for _ in range(work):
            temp_info = utils.run_async_method(asyncio.new_event_loop(),
                                               request_sender.send_request,
                                               self.pool_handle,
                                               self.wallet_handle,
                                               self.submitter_did,
                                               self.req_kind)
            if temp_info:
                self.req_info.append(temp_info)

    def __start_threads(self):
        works = self.__divide_work()
        for work in works:
            req_thread = threading.Thread(
                target=self.__send_requests_in_thread, kwargs={'work': work})
            self.threads.append(req_thread)
            req_thread.start()

    def __finish_threads(self):
        for sub_thread in self.threads:
            sub_thread.join()
        with open(self.info_file_path, "w") as info_file:
            info_file.writelines(self.req_info)

    async def __create_pool_config(self):
        try:
            pool_config = json.dumps({'genesis_txn': self.genesis_file})
            await pool.create_pool_ledger_config(self.pool_name, pool_config)
            utils.print_header("\n\n\tCreated ledger config "
                               "from genesis txn file")
        except IndyError as e:
            if e.error_code == 306:
                utils.print_error("The ledger already exists, moving on...")
            else:
                raise

    async def __open_pool(self):
        try:
            self.pool_handle = await pool.open_pool_ledger(self.pool_name,
                                                           None)
            utils.print_header("\n\tOpened pool ledger %s" %
                               str(self.pool_handle))
        except IndyError as e:
            utils.print_error(str(e))

    async def __create_wallet(self):
        try:
            await wallet.create_wallet(self.pool_name, self.wallet_name,
                                       None, None, None)
            utils.print_header("\n\t======== Created wallet")
        except IndyError as e:
            if e.error_code == 203:
                utils.print_error(
                    "Wallet '%s' already exists.  "
                    "Skipping wallet creation..." % str(self.pool_name))
            else:
                raise

    async def __open_wallet(self):
        try:
            self.wallet_handle = await wallet.open_wallet(self.wallet_name,
                                                          None, None)
            utils.print_header("\n\t======== Opened wallet")
        except IndyError as e:
            utils.print_error(str(e))
            raise

    async def __create_submitter_did(self):
        try:
            self.submitter_did, _ = await signus.create_and_store_my_did(
                self.wallet_handle, json.dumps({'seed': self.seed}))

            utils.print_header("\n\tCreated DID to use when adding NYMS %s "
                               % str(self.submitter_did))
        except Exception as e:
            utils.print_error(str(e))
            raise

    async def __cleanup(self):
        utils.print_header("\n\tClose wallet")
        try:
            await wallet.close_wallet(self.wallet_handle)
        except Exception as e:
            utils.print_error("Cannot close wallet."
                              "Skip closing wallet... Abort")
            utils.print_error(str(e))

        utils.print_header("\n\tDelete wallet")
        try:
            await wallet.delete_wallet(self.wallet_name, None)
        except Exception as e:
            utils.print_error("Cannot delete wallet."
                              "Skip deleting wallet... Abort")
            utils.print_error(str(e))

        utils.print_header("\n\tClose pool")
        try:
            await pool.close_pool_ledger(self.pool_handle)
        except Exception as e:
            utils.print_error("Cannot close pool."
                              "Skip closing pool... Abort")
            utils.print_error(str(e))

        utils.print_header("\n\tDelete pool")
        try:
            await pool.delete_pool_ledger_config(self.pool_name)
        except Exception as e:
            utils.print_error("Cannot delete pool."
                              "Skip deleting pool... Abort")
            utils.print_error(str(e))


if __name__ == '__main__':
    options = Option()
    args = options.args
    tester = PerformanceTesterForAddingRequest(args.info_dir,
                                               args.pool_genesis_txn_file,
                                               args.number_of_requests,
                                               args.kind, args.seed,
                                               args.thread_num, args.debug)

    # Start the timer to track how long it takes to run the test
    start_time = time.time()
    utils.run_async_method(None, tester.test)

    # Stop the timer after the test is complete
    elapsed_time = time.time() - start_time

    # Format the time display to look nice
    hours = elapsed_time / 3600
    elapsed_time = 3600 * hours
    minutes = elapsed_time / 60
    seconds = 60 * minutes
    print("\n------ Elapsed time: %dh:%dm:%ds" % (
        hours, minutes, seconds) + " ------")

    # Example syntax:
    # python3.6 add_nyms.py testPool 500 000000000000000000000000Steward1 number_of_threads
    #          |     0     |    1   | 2 |           3                             4
