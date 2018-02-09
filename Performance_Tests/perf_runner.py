import os
import argparse
import time
import utils
import threading
import asyncio
import sys
import perf_add_requests
import perf_get_requests


#                   ==================== Notes and information ====================
# This script will run multiple instances (threaded) of the the perf_add_requests.py script or the Perf_get_nyms.py. The
# command line parameters for each script are different and can be set from this script without modifying Add_nyms or
# Get_nyms scripts.
# The settings for Perf runner are 'clients' and 'txns'.  Clients is the number of threads (or client machines) to use,
# the txns indicates how many transactions will run per client (thread).  These settings are specific to Perf_runner.py
#
# The command line for both performance scripts is created in the 'command' variable found below.  The default setting
# for perf_add_requests.py uses the -n and -s parameters to specify the number of threads and clients to use.  The value
# from clients is iterated through and uses 'i' to track which iteration is processing.
# The default vaiables for the Add_nyms script will be  used.  If any of the default settings for Add_nyms or Get_nyms
# needs to be modified, add the changes here to the perf runner by modifying the 'command' variable.
#                   ================================================================
# Example:
# Run perf_add_requests.py:   python3.6 Perf_runner.py -a
# Run Perf_gert_nyms.py using 3 clients (threads) - by setting clients to 3:  python3.6 Perf_runner.py -g

class Options:
    def __init__(self):
        parser = argparse.ArgumentParser(
            description='This script will create multiple threads of the perf_add_requests.py or '
                        'the Perf_get_nyms.py.')

        parser.add_argument('-a',
                            help='Use this parameter to start adding request performance testing',
                            action='store_true',
                            default=False, required=False, dest='adding')

        parser.add_argument('-g',
                            help='Use this parameter to start getting request performance testing',
                            action='store_true',
                            default=False, required=False, dest='getting')

        parser.add_argument('-c',
                            help='Number of client you want to create. Default value will be 1',
                            default=1, type=int, required=False,
                            dest='clients')

        parser.add_argument('-d',
                            help='Directory you want to store requests info when sending adding request. '
                                 'If you start getting request testing, program will collect info from this dir instead.'
                                 'Default value will be {}'.format(
                                os.path.dirname(__file__)),
                            default=os.path.dirname(__file__), required=False,
                            dest='info_dir')

        parser.add_argument('-n',
                            help='How many transactions you want to submit to ledger when starting adding requests.'
                                 'If you start getting request testing, this arg will be ignore.'
                                 'Default value will be 100',
                            default=100, type=int, required=False, dest='txns')

        parser.add_argument('-s',
                            help='Number of thread will be created by each client.'
                                 'Default value is 1',
                            default=1, type=int, required=False,
                            dest='thread_num')

        parser.add_argument('-k',
                            help='Kind of request to be sent. '
                                 'The default value will be "nym"',
                            action='store',
                            choices=['nym', 'schema', 'attribute', 'claim'],
                            default='nym', dest='kind')

        parser.add_argument('-l',
                            help='To see all log. If this flag does not exist,'
                                 'program just only print fail message',
                            action='store_true', default=False, dest='log')

        self.args = parser.parse_args()


class PerformanceTestRunner:
    def __init__(self):
        self.options = Options().args

        self.tester = None
        if not self.options.adding and not self.options.getting:
            utils.print_error(
                'Cannot determine any kind of request for testing')
            utils.print_error(
                'May be you missing both arguments "-a" and "-b"')
            sys.exit(1)

        if self.options.adding and self.options.getting:
            utils.force_print_error_to_console(
                '"-a" and "-g" cannot exist at the same time\n')
            sys.exit(1)

        self.list_tester = list()

        self.start_time = self.finish_time = 0
        self.lowest = self.fastest = 0
        self.passed_req = self.failed_req = 0
        self.result_path = os.path.join(os.path.dirname(__file__), 'results')
        utils.create_folder(self.result_path)
        self.result_path = os.path.join(self.result_path,
                                        'result_{}.txt'.format(time.strftime(
                                            "%d-%m-%Y_%H-%M-%S")))

    def run(self):
        if not self.options.log:
            utils.start_capture_console()
        self.start_time = time.time()
        if self.options.clients > 1:
            self.start_tester_in_thread()
        else:
            self.list_tester.append(self.create_tester())
            utils.run_async_method(None, self.list_tester[-1].test)
        self.finish_time = time.time()

        utils.stop_capture_console()
        self.collect_result()
        with open(self.result_path, 'w') as result:
            self.write_result(result)
        self.write_result(sys.stdout)

    def collect_result(self):
        self.passed_req = self.failed_req = 0
        for tester in self.list_tester:
            self.failed_req += tester.failed_req
            self.passed_req += tester.passed_req

        self.find_lowest_and_fastest_tester_duration()

        self.find_start_and_finish_time()

    def write_result(self, result_file):
        total_time = self.finish_time - self.start_time
        hours = total_time / 3600
        minutes = total_time / 60 % 60
        seconds = total_time % 60

        ttl_txns = self.passed_req + self.failed_req
        ttl_seconds = total_time
        txns_per_second = int(ttl_txns / ttl_seconds)
        txns_per_client = ttl_txns / self.options.clients

        print("\n -----------  Total time to run the test: %dh:%dm:%ds" % (
            hours, minutes, seconds) + "  -----------", file=result_file)
        print("\n Clients = " + str(self.options.clients), file=result_file)
        print("\n Fastest client = " + str(self.fastest), file=result_file)
        print("\n Lowest client = " + str(self.lowest), file=result_file)
        print("\n Transaction per client = " + str(txns_per_client),
              file=result_file)
        print("\n Total requested transactions = " + str(ttl_txns),
              file=result_file)
        print("\n Total passed transactions = " + str(self.passed_req),
              file=result_file)
        print("\n Total failed transactions = " + str(self.failed_req),
              file=result_file)
        print("\n Average time of a transaction = "
              + str((self.finish_time - self.start_time) / ttl_txns),
              file=result_file)
        print("\n Estimated transactions per second = " + str(txns_per_second),
              file=result_file)

    def find_lowest_and_fastest_tester_duration(self):

        self.lowest = self.fastest = self.list_tester[0].get_elapsed_time()

        for tester in self.list_tester:
            temp_elapsed_time = tester.get_elapsed_time()
            if self.lowest < temp_elapsed_time:
                self.lowest = temp_elapsed_time
            if self.fastest > temp_elapsed_time:
                self.fastest = temp_elapsed_time

    def find_start_and_finish_time(self):
        self.start_time = self.list_tester[0].start_time
        self.finish_time = self.list_tester[0].finish_time

        for tester in self.list_tester:
            if self.start_time > tester.start_time:
                self.start_time = tester.start_time

            if self.finish_time < tester.finish_time:
                self.finish_time = tester.finish_time

    def start_tester_in_thread(self):
        threads = list()
        for _ in range(self.options.clients):
            tester = self.create_tester()
            self.list_tester.append(tester)
            thread = threading.Thread(target=self.run_tester_in_thread,
                                      kwargs={'tester': tester})
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

    def run_tester_in_thread(self, tester):
        loop = asyncio.new_event_loop()
        utils.run_async_method(loop, tester.test)
        loop.close()

    def create_tester(self):
        if self.options.adding:
            return perf_add_requests.PerformanceTesterForAddingRequest(
                self.options.info_dir, self.options.txns, self.options.kind,
                thread_num=self.options.thread_num, log=self.options.log
            )
        elif self.options.getting:
            return perf_get_requests.PerformanceTesterGetSentRequestFromLedger(
                self.options.info_dir, self.options.kind,
                self.options.thread_num, log=self.options.log
            )

        return None


if __name__ == '__main__':
    PerformanceTestRunner().run()