'''
Rackspace Cloud Module
======================

The Rackspace cloud module. This module uses the preferred means to set up a
libcloud based cloud module and should be used as the general template for
setting up additional libcloud based modules.

The rackspace cloud module interfaces with the Rackspace public cloud service
and requires that two configuration paramaters be set for use:

.. code-block:: yaml

    # The Rackspace login user
    HPCLOUD.user: fred
    # The Rackspace user's apikey
    HPCLOUD.apikey: 901d3f579h23c8v73q9

'''

# The import section is mostly libcloud boilerplate

# Import python libs
import os
import types
import paramiko
import tempfile

# Import libcloud 
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.deployment import MultiStepDeployment, ScriptDeployment, SSHKeyDeployment

# Import generic libcloud functions
from saltcloud.libcloudfuncs import *

# Some of the libcloud functions need to be in the same namespace as the
# functions defined in the module, so we create new function objects inside
# this module namespace
avail_images = types.FunctionType(avail_images.__code__, globals())
avail_sizes = types.FunctionType(avail_sizes.__code__, globals())
script = types.FunctionType(script.__code__, globals())
destroy = types.FunctionType(destroy.__code__, globals())
list_nodes = types.FunctionType(list_nodes.__code__, globals())
list_nodes_full = types.FunctionType(list_nodes_full.__code__, globals())


# Only load in this module is the HPCLOUD configurations are in place
def __virtual__():
    '''
    Set up the libcloud funcstions and check for HPCLOUD configs
    '''
    if 'HPCLOUD.user' in __opts__ and 'HPCLOUD.apikey' in __opts__:
        return 'hpcs'
    return False


def get_conn():
    '''
    Return a conn object for the passed vm data
    '''
    driver = get_driver(Provider.HPCLOUD)
    return driver(
            __opts__['HPCLOUD.user'],
            __opts__['HPCLOUD.apikey'],
            ex_force_auth_url = __opts__['HPCLOUD.auth_endpoint'],
            ex_force_auth_version = '2.0_password',
            ex_tenant_name = __opts__['HPCLOUD.tenant_name']
            )


def create(vm_):
    '''
    Create a single vm from a data dict
    '''
    print('Creating Cloud VM {0}'.format(vm_['name']))
    conn = get_conn()
    deploy_script = script(vm_)
    kwargs = {}
    kwargs['name'] = vm_['name']
    kwargs['image'] = get_image(conn, vm_)
    kwargs['size'] = get_size(conn, vm_)
    try:
        data = conn.create_node(**kwargs)
    except Exception as exc:
        err = ('Error creating {0} on HPCLOUD\n\n'
               'The following exception was thrown by libcloud when trying to '
               'run the initial deployment: \n{1}').format(
                       vm_['name'], exc
                       )
        sys.stderr.write(err)
        return False
    # NOTE
    # We need to insert a wait / poll until we have
    # public ips for our node.  Otherwise, we cannot
    # complete the next step of deploying a script to the new
    # server : (
    if data.public_ips:
        host_addr = public_ips[0]
    else:
        host_addr = None
    deployed = saltcloud.utils.deploy_script(
        host=host_addr,
        username='root',
        password=data.extra['password'],
        script=deploy_script.script,
        name=vm_['name'],
        sock_dir=__opts__['sock_dir'])
    if deployed:
        print('Salt installed on {0}'.format(vm_['name']))
    else:
        print('Failed to start Salt on Cloud VM {0}'.format(vm_['name']))

    print('Created Cloud VM {0} with the following values:'.format(
        vm_['name']
        ))
    for key, val in data.__dict__.items():
        print('  {0}: {1}'.format(key, val))
