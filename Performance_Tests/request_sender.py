import json
import utils

from indy import signus, ledger


async def send_nym_request(pool_handle, wallet_handle, submiter_did):
    try:
        did, _, = await signus.create_and_store_my_did(wallet_handle, '{}')
        utils.print_header("DID: {}".format(did))

        # Send NYM to ledger
        utils.print_header("\n======== Create NYM request ========")
        nym_req = await ledger.build_nym_request(submiter_did, did, None,
                                                 None, None)

        utils.print_header("\n======== Send NYM request ========")
        await ledger.sign_and_submit_request(pool_handle, wallet_handle,
                                             submiter_did, nym_req)

        return json.dumps({'kind': 'nym', 'data': {'target_did': did}})

    except Exception as e:
        utils.print_error("Cannot send nym request. Skip sending... Abort")
        utils.print_error(str(e))
        return ""


async def send_schema_request(pool_handle, wallet_handle, submiter_did):
    try:
        data = {
            'name': utils.generate_random_string(prefix='test'),
            'version': '1.0',
            'attr_names': ['test']
        }

        utils.print_header("\n======= Build schema request =======")
        schema_req = await ledger.build_schema_request(submiter_did,
                                                       json.dumps(data))

        utils.print_header("\n======= Send schema request =======")
        await ledger.sign_and_submit_request(pool_handle, wallet_handle,
                                             submiter_did, schema_req)

        del data['attr_names']
        data['dest'] = submiter_did
        return json.dumps({'kind': 'schema', 'data': data})

    except Exception as e:
        utils.print_error("Cannot send schema request. Skip sending... Abort")
        utils.print_error(str(e))
        return ""


async def send_attribute_request(pool_handle, wallet_handle, submiter_did):
    try:
        utils.print_header("\n======= Create did =======")
        did, verkey = await signus.create_and_store_my_did(wallet_handle,
                                                           '{}')

        utils.print_header("\n======= Build nym request =======")
        nym_req = await ledger.build_nym_request(submiter_did, did, verkey,
                                                 None, None)

        utils.print_header("\n======= Send nym request =======")
        await ledger.sign_and_submit_request(pool_handle, wallet_handle,
                                             submiter_did, nym_req)

        data = {'endpoint': {'ha': '127.0.0.1:5555'}}

        utils.print_header("\n======= Build attribute request =======")
        attr_req = await ledger.build_attrib_request(did, did, None,
                                                     json.dumps(data), None)

        utils.print_header("\n======= Send attribute request =======")
        await ledger.sign_and_submit_request(pool_handle, wallet_handle,
                                             did, attr_req)

        return json.dumps({'kind': 'attribute',
                           'data': {'target_did': did,
                                    'raw_name': 'endpoint'}})

    except Exception as e:
        utils.print_error("Cannot send attribute request. "
                          "Skip sending... Abort")
        utils.print_error(str(e))
        return ""


async def send_claim_request(pool_handle, wallet_handle, submiter_did):
    import string
    import random
    try:
        utils.print_header("\n======= Create did =======")
        did, verkey = await signus.create_and_store_my_did(wallet_handle,
                                                           '{}')

        utils.print_header("\n======= Build nym request =======")
        nym_req = await ledger.build_nym_request(submiter_did, did, verkey,
                                                 None, None)

        utils.print_header("\n======= Send nym request =======")
        await ledger.sign_and_submit_request(pool_handle, wallet_handle,
                                             submiter_did, nym_req)

        seq_no = random.randint(1, 1000000)
        signature_type = 'CL'
        data = {"primary": {
            "n": utils.generate_random_string(characters=string.digits),
            "s": utils.generate_random_string(characters=string.digits),
            "rms": utils.generate_random_string(characters=string.digits),
            "r": {"name": utils.generate_random_string(
                characters=string.digits)},
            "rctxt": utils.generate_random_string(characters=string.digits),
            "z": utils.generate_random_string(characters=string.digits)}}

        utils.print_header("\n======= Build claim request =======")
        claim_req = await ledger.build_claim_def_txn(did, seq_no,
                                                     signature_type,
                                                     json.dumps(data))

        utils.print_header("\n======= Send claim request =======")
        await ledger.sign_and_submit_request(pool_handle, wallet_handle,
                                             did, claim_req)

        return json.dumps({'kind': 'claim',
                           'data': {'issuer_did': did, 'seq_no': seq_no,
                                    'signature_type': signature_type}})

    except Exception as e:
        utils.print_error("Cannot send claim request. Skip sending... Abort")
        utils.print_error(str(e))
        return ""


async def send_request(pool_hanle, wallet_handle, submitter_did,
                       kind_of_request: str = "nym"):
    if kind_of_request == 'nym':
        executor = send_nym_request
    elif kind_of_request == 'schema':
        executor = send_schema_request
    elif kind_of_request == 'attribute':
        executor = send_attribute_request
    elif kind_of_request == 'claim':
        executor = send_claim_request
    else:
        executor = None

    if executor:
        return await executor(pool_hanle, wallet_handle, submitter_did)

    return ""
