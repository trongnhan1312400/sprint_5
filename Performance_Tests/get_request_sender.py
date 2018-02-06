import json
import utils

from indy import ledger


async def send_get_nym_request(pool_handle, submitter_did,
                               data: str = None):
    if not data:
        return

    try:
        data = json.loads(data)
        if data['kind'] != 'nym':
            return

        utils.print_header_for_step('Build get nym request')
        target_did = data['data']['target_did']
        get_nym_req = await ledger.build_get_nym_request(submitter_did,
                                                         target_did)

        utils.print_header_for_step('Send get nym request')
        await ledger.submit_request(pool_handle, get_nym_req)

    except Exception as e:
        utils.print_error("Cannot send get NYM request. Skip sending... Abort")
        utils.print_error(str(e))


async def send_get_schema_request(pool_handle, submitter_did,
                                  data: str = None):
    if not data:
        return

    try:
        data = json.loads(data)
        if data['kind'] != 'schema':
            return

        utils.print_header_for_step('Build get schema request')
        dest = data['data']['dest']
        schema_data = {'name': data['data']['name'],
                       'version': data['data']['version']}
        get_schema_req = await ledger.build_get_schema_request(
            submitter_did, dest, json.dumps(schema_data))

        utils.print_header_for_step('Send get schema request')
        await ledger.submit_request(pool_handle, get_schema_req)

    except Exception as e:
        utils.print_error("Cannot send get schema request. "
                          "Skip sending... Abort")
        utils.print_error(str(e))


async def send_get_attribute_request(pool_handle, submitter_did,
                                     data: str = None):
    if not data:
        return

    try:
        data = json.loads(data)
        if data['kind'] != 'attribute':
            return

        utils.print_header_for_step('Build get attribute request')
        target_did = data['data']['target_did']
        raw_name = data['data']['raw_name']
        get_attr_req = await ledger.build_get_attrib_request(submitter_did,
                                                             target_did,
                                                             raw_name)

        utils.print_header_for_step('Send get attribute request')
        await ledger.submit_request(pool_handle, get_attr_req)

    except Exception as e:
        utils.print_error("Cannot send get attribute request. "
                          "Skip sending... Abort")
        utils.print_error(str(e))


async def send_get_claim_request(pool_handle, submitter_did,
                                 data: str = None):
    if not data:
        return

    try:
        data = json.loads(data)
        if data['kind'] != 'claim':
            return

        utils.print_header_for_step('Build get claim def request')
        issuer_did = data['data']['issuer_did']
        seq_no = data['data']['seq_no']
        signature_type = data['data']['signature_type']
        get_claim_req = await ledger.build_get_claim_def_txn(submitter_did,
                                                             seq_no,
                                                             signature_type,
                                                             issuer_did)

        utils.print_header_for_step('Send get claim def request')
        await ledger.submit_request(pool_handle, get_claim_req)

    except Exception as e:
        utils.print_error("Cannot send get claim request. "
                          "Skip sending... Abort")
        utils.print_error(str(e))


async def send_get_request(pool_handle, submitter_did, data: str = None,
                           kind_of_request: str = 'nym'):
    if kind_of_request == 'nym':
        executor = send_get_nym_request
    elif kind_of_request == 'schema':
        executor = send_get_schema_request
    elif kind_of_request == 'attribute':
        executor = send_get_attribute_request
    elif kind_of_request == 'claim':
        executor = send_get_claim_request
    else:
        executor = None

    if executor:
        await executor(pool_handle, submitter_did, data)
