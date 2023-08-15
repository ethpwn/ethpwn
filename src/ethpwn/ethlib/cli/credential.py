import functools
from . import rename, subcommand_callable, cmdline
from ..config import update_config
from ..config.credentials import add_credentials_for

credential_handler = subcommand_callable(cmdline, 'credential', __subcommand_doc='Manage credentials for ethlib')

@credential_handler
def add(service: str, cred: str, **kwargs):
    """
    Add a credential

    :param service: the service to add the credential for
    :param cred: the credential to add
    """
    add_credentials_for(service, cred)
    update_config()

@credential_handler
@rename('list')
def _list(**kwargs):
    """
    Show credentials
    """
    from ..config.credentials import all_credentials
    return all_credentials()

@credential_handler
def get(service: str, **kwargs):
    """
    Get a credential

    :param service: the service to get the credential for
    """
    from ..config.credentials import get_credentials_for
    return get_credentials_for(service)