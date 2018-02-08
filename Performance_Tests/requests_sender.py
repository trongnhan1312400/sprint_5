import json
import utils
import threading
import asyncio
import time
import os

from indy import ledger


class RequestsSender:
    def __init__(self, log=False):
        self.log = log
        self.passed_req = self.failed_req = 0
        self.start_time = self.finish_time = 0
        pass

    def print_success_msg(self, kind, response):
        if self.log:
            utils.force_print_green_to_console(
                '\nSubmit {} request '
                'successfully with response:\n{}'.format(kind, response))

    def print_error_msg(self, kind, request):
        utils.force_print_error_to_console(
            '\nCannot submit {} request:\n{}'.format(kind, request))

    def sign_and_submit_several_reqs_from_files(self, args, files, kind):
        threads = list()
        utils.print_header('\n\tSigning and submitting {} requests...'
                           .format(kind))
        if not self.log:
            utils.start_capture_console()

        self.start_time = time.time()
        for file_name in files:
            temp_thread = threading.Thread(
                target=self.sign_and_submit_reqs_in_thread,
                kwargs={'args': args, 'file': file_name, 'kind': kind})
            temp_thread.start()
            threads.append(temp_thread)

        for thread in threads:
            thread.join()
        self.finish_time = time.time()

        utils.stop_capture_console()
        utils.print_header('\n\tSubmitting requests complete')

    def sign_and_submit_reqs_in_thread(self, args, file, kind):
        with open(file, "r") as req_file:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            for line in req_file:
                utils.run_async_method(loop, self.sign_and_submit_req, args,
                                       kind, line)

        try:
            os.remove(file)
        except IOError:
            pass

    async def sign_and_submit_req(self, args, kind, data):
        wallet_handle = args['wallet_handle']
        pool_handle = args['pool_handle']
        submitter_did = args['submitter_did']

        req_data = json.loads(data)
        if 'submitter_did' in req_data:
            submitter_did = req_data['submitter_did']

        req = req_data['request']

        try:
            utils.print_header_for_step('Sending {} request'.format(kind))
            response = await ledger.sign_and_submit_request(pool_handle,
                                                            wallet_handle,
                                                            submitter_did, req)
            self.passed_req += 1
            self.print_success_msg(kind, response)
        except Exception as e:
            self.print_error_msg(kind, req)
            utils.force_print_error_to_console(str(e) + "\n")
            self.failed_req += 1

    def submit_several_reqs_from_files(self, args, files, kind):
        threads = list()
        utils.print_header('\n\tSubmitting {} requests...'
                           .format(kind))
        if not self.log:
            utils.start_capture_console()

        self.start_time = time.time()
        for file_name in files:
            temp_thread = threading.Thread(
                target=self.submit_reqs_in_thread,
                kwargs={'args': args, 'file': file_name, 'kind': kind})
            temp_thread.start()
            threads.append(temp_thread)

        for thread in threads:
            thread.join()
        self.finish_time = time.time()

        utils.stop_capture_console()
        utils.print_header('\n\tSubmitting requests complete')

    def submit_reqs_in_thread(self, args, file, kind):
        with open(file, "r") as req_file:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            for line in req_file:
                utils.run_async_method(loop, self.submit_req, args,
                                       kind, line)

        try:
            os.remove(file)
        except IOError:
            pass

    async def submit_req(self, args, kind, data):
        pool_handle = args['pool_handle']

        req = data

        try:
            utils.print_header_for_step('Sending get {} request'.format(kind))
            response = await ledger.submit_request(pool_handle, req)
            self.passed_req += 1
            self.print_success_msg(kind, response)
        except Exception as e:
            self.print_error_msg(kind, req)
            utils.force_print_error_to_console(str(e) + "\n")
            self.failed_req += 1
