import shutil
import utils
import os


def delete_wallet_and_pool():
    """  Delete all files out of the .indy/pool and .indy/wallet directories  """
    config = utils.parse_config()

    print("\nCheck if the wallet and pool for this test already exist and delete them...\n")

    user_home = os.path.expanduser('~') + os.sep
    work_dir = user_home + ".indy_client"

    try:
        shutil.rmtree(work_dir + "/pool/" + config.pool_name)
    except IOError as E:
        print(str(E))

    try:
        shutil.rmtree(work_dir + "/wallet/" + config.wallet_name)
    except IOError as E:
        print(str(E))

    print("Finished deleting wallet and pool folders in " + repr(work_dir))


if __name__ == '__main__':
    delete_wallet_and_pool()
