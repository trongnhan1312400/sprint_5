import json
import utils
import threading
import asyncio
import time
import os

from indy import ledger


class RequestsSender:
    __log_file = None
    start_time = finish_time = -1
    lock = threading.Lock()

    def __init__(self, log=False):
        self.log = log
        self.passed_req = self.failed_req = 0
        self.start_time = self.finish_time = -1
        self.__lock = threading.Lock()
        self.first_txn = -1
        self.last_txn = -1
        pass

    def print_success_msg(self, kind, response):
        if self.log:
            utils.force_print_green_to_console(
                '\nSubmit {} request '
                'successfully with response:\n{}'.format(kind, response))

    @staticmethod
    def print_error_msg(kind, request):
        utils.force_print_error_to_console(
            '\nCannot submit {} request:\n{}'.format(kind, request))

    @staticmethod
    def init_log_file(path: str):
        RequestsSender.close_log_file()
        utils.create_folder(os.path.dirname(path))
        RequestsSender.__log_file = open(path, 'w')

    @staticmethod
    def close_log_file():
        if RequestsSender.__log_file \
                and not RequestsSender.__log_file.closed:
            RequestsSender.__log_file.close()

    @staticmethod
    def print_log(status, elapsed_time, req):
        req = req.strip()
        log_req = "======== Request: {}".format(req)
        log_status = "======== Status: {}".\
            format('Failed' if not status else 'Passed')
        if status:
            log = '{}\n{}\n{}\n\n'.format(
                log_req, log_status,
                "======== Processed time: {}seconds".format(str(elapsed_time)))
        else:
            log = '{}\n{}\n\n'.format(log_req, log_status)

        if RequestsSender.__log_file \
                and not RequestsSender.__log_file.closed:
            RequestsSender.__log_file.write(log)

    def update_start_and_finish_time(self, new_start_time, new_finish_time):
        self.lock.acquire()
        if self.start_time < 0 \
                or self.start_time > new_start_time:
            self.start_time = new_start_time
        if self.finish_time < new_finish_time:
            self.finish_time = new_finish_time

        self.lock.release()

    def sign_and_submit_several_reqs_from_files(self, args, files, kind):
        """
        Sign and submit several request that stored in files.

        :param args: arguments to sign and submit requests.
        :param files: return by
        request_builder.RequestBuilder.build_several_adding_req_to_files
        :param kind: kind of request.
        """
        threads = list()
        utils.print_header('\n\tSigning and submitting {} requests...'
                           .format(kind))
        if not self.log:
            utils.start_capture_console()

        for file_name in files:
            temp_thread = threading.Thread(
                target=self.sign_and_submit_reqs_in_thread,
                kwargs={'args': args, 'file': file_name, 'kind': kind})
            temp_thread.start()
            threads.append(temp_thread)

        for thread in threads:
            thread.join()

        utils.stop_capture_console()
        utils.print_header('\n\tSubmitting requests complete')

    def sign_and_submit_reqs_in_thread(self, args, file, kind):
        """
        Thread function that sign and submit request from one request file.

        :param args: arguments to sign and submit requests.
        :param file: request file (store all request you want to submit).
        :param kind: kind of request.
        """
        start_time = finish_time = 0
        with open(file, "r") as req_file:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            for line in req_file:
                # delay - NAK
                response_time = \
                    utils.run_async_method(
                        loop, self.sign_and_submit_req, args, kind, line)
                if start_time == 0:
                    start_time = response_time
                if response_time > finish_time:
                    finish_time = response_time

            loop.close()
        self.update_start_and_finish_time(start_time, finish_time)
        try:
            os.remove(file)
        except IOError:
            pass

    async def sign_and_submit_req(self, args, kind, data):
        """
        Sign and submit one request to ledger.

        :param args: arguments to sign and submit requests.
        :param kind: kind of request.
        :param data: request info.
        """
        wallet_handle = args['wallet_handle']
        pool_handle = args['pool_handle']
        submitter_did = args['submitter_did']

        req_data = json.loads(data)
        if 'submitter_did' in req_data:
            submitter_did = req_data['submitter_did']

        req = req_data['request']

        elapsed_time = 0
        response_time = None

        try:
            utils.print_header_for_step('Sending {} request'.format(kind))
            start_time = time.time()
            response = await ledger.sign_and_submit_request(pool_handle,
                                                            wallet_handle,
                                                            submitter_did, req)
            response_time = time.time()
            elapsed_time = response_time - start_time
            self.passed_req += 1
            self.print_success_msg(kind, response)
            status = True
        except Exception as e:
            self.print_error_msg(kind, req)
            utils.force_print_error_to_console(str(e) + "\n")
            self.failed_req += 1
            status = False

        RequestsSender.print_log(status, elapsed_time, req)
        return response_time

    def submit_several_reqs_from_files(self, args, files, kind):
        """
        Submit several request that stored in files.

        :param args: arguments to submit requests.
        :param files: return by
        request_builder.RequestBuilder.build_several_adding_req_to_files
        :param kind: kind of request.
        """
        threads = list()
        utils.print_header('\n\tSubmitting {} requests...'
                           .format(kind))
        if not self.log:
            utils.start_capture_console()

        for file_name in files:
            temp_thread = threading.Thread(
                target=self.submit_reqs_in_thread,
                kwargs={'args': args, 'file': file_name, 'kind': kind})
            temp_thread.start()
            threads.append(temp_thread)

        for thread in threads:
            thread.join()

        utils.stop_capture_console()
        utils.print_header('\n\tSubmitting requests complete')

    def submit_reqs_in_thread(self, args, file, kind):
        """
        Thread function that submit request from one request file.

        :param args: arguments to submit requests.
        :param file: request file (store all request you want to submit).
        :param kind: kind of request.
        """
        start_time = finish_time = 0
        with open(file, "r") as req_file:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            for line in req_file:
                response_time = utils.run_async_method(
                    loop, self.submit_req, args, kind, line)
                if start_time == 0:
                    start_time = response_time
                if response_time > finish_time:
                    finish_time = response_time
            loop.close()
        try:
            os.remove(file)
        except IOError:
            pass

        self.update_start_and_finish_time(start_time, finish_time)

    async def submit_req(self, args, kind, data):
        """
        Submit one request to ledger.

        :param args: arguments to submit requests.
        :param kind: kind of request.
        :param data: request info.
        :return:
        """
        pool_handle = args['pool_handle']

        req = data

        elapsed_time = 0

        response_time = None

        try:
            utils.print_header_for_step('Sending get {} request'.format(kind))
            start_time = time.time()
            response = await ledger.submit_request(pool_handle, req)
            response_time = time.time()
            elapsed_time = response_time - start_time

            self.passed_req += 1
            self.print_success_msg(kind, response)
            status = True
        except Exception as e:
            self.print_error_msg(kind, req)
            utils.force_print_error_to_console(str(e) + "\n")
            self.failed_req += 1
            status = False

        RequestsSender.print_log(status, elapsed_time, req)

        return response_time

    async def send_request(self, args, kind, data):
        if kind.startswith("get_"):
            return await self.submit_req(args, kind.replace("get_", ""), data)
        else:
            return await self.sign_and_submit_req(args, kind, data)
