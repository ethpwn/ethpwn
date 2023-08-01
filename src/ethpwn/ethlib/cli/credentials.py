import functools
from . import subcommand_callable, cmdline
from ..config import update_config
from ..config.credentials import add_credentials_for

credentials_handler = subcommand_callable(cmdline, 'credentials', doc='Manage credentials for ethlib')

@credentials_handler
def add(service: str, cred: str, **kwargs):
    """
    Add a credential

    :param service: the service to add the credential for
    :param cred: the credential to add
    """
    add_credentials_for(service, cred)
    update_config()

@credentials_handler
def list(**kwargs):
    """
    List credentials
    """
    from ..config.credentials import all_credentials
    return all_credentials()

@credentials_handler
def get(service: str, **kwargs):
    """
    Get a credential

    :param service: the service to get the credential for
    """
    from ..config.credentials import get_credentials_for
    return get_credentials_for(service)