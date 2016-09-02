import os
import shutil
import tempfile

from traitlets import Any, Unicode
from tornado import gen

from jupyterhub.spawner import LocalProcessSpawner
from jupyterhub import orm

# TODO: Both Spawner and VirtualUserSpawner have `get_args` that
# are identical and they need to be updated when the remoteappmanager
# config is updated.  Refactoring would mitigate potential risk
# of not updating one of them.


class SystemUserSpawner(LocalProcessSpawner):
    ''' Start remoteappmanager as a local process for a system user.

    The user identifier of the process is set to be the system user.
    The current directory is set to the system user's home directory.
    '''

    #: The instance of the orm Proxy.
    #: We use Any in agreement with base class practice.
    proxy = Any()

    #: The path of the configuration file for the cmd executable
    config_file_path = Unicode(config=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # We get the first one. Strangely enough, jupyterhub has a table
        # containing potentially multiple proxies, but it's enforced to
        # contain only one.
        self.proxy = self.db.query(orm.Proxy).first()
        self.cmd = ['remoteappmanager']

    def get_args(self):
        args = super().get_args()

        for iarg, arg in enumerate(args):
            args[iarg] = arg.replace('--base-url=', '--base-urlpath=')

        args.append("--proxy-api-url={}".format(self.proxy.api_server.url))

        if self.config_file_path:
            args.append("--config-file={}".format(self.config_file_path))

        return args

    def get_env(self):
        env = super().get_env()
        env["PROXY_API_TOKEN"] = self.proxy.auth_token
        env.update(_docker_envvars())
        return env


class VirtualUserSpawner(LocalProcessSpawner):
    ''' Start remoteappmanager as a local process for a virtual user.

    A virtual user is not recognised as a system user, even if the
    user's name conincide with an existing system user.  As a result,
    the user does not need to be a system user for this spawner.

    The user identifier and the current work directory of the spawned
    local process are the same as the one that is running jupyterhub.
    '''

    #: The instance of the orm Proxy.
    #: We use Any in agreement with base class practice.
    proxy = Any()

    #: The path of the configuration file for the cmd executable
    config_file_path = Unicode(config=True)

    #: Directory in which temporary home directory for the virtual
    #: user is created.  No directory is created if this is not
    #: defined and HOME directory would not be available.
    workspace_dir = Unicode(config=True)

    #: The path to the temporary workspace directory
    _virtual_workspace = Unicode()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # We get the first one. Strangely enough, jupyterhub has a table
        # containing potentially multiple proxies, but it's enforced to
        # contain only one.
        self.proxy = self.db.query(orm.Proxy).first()
        self.cmd = ['remoteappmanager']

    def make_preexec_fn(self, name):
        # We don't set user uid for virtual user
        # Nor do we try to start the process in the user's
        # home directory (it does not exist)
        pass

    def load_state(self, state):
        super().load_state(state)
        virtual_workspace = state.get('virtual_workspace')
        if virtual_workspace:
            if os.path.isdir(virtual_workspace):
                self._virtual_workspace = virtual_workspace
            else:
                self.log.warn('Previous virtual workspace is gone.')

    def get_state(self):
        state = super().get_state()
        if self._virtual_workspace:
            state['virtual_workspace'] = self._virtual_workspace
        return state

    def clear_state(self):
        super().clear_state()
        self._virtual_workspace = ''

    def get_args(self):
        args = super().get_args()

        for iarg, arg in enumerate(args):
            args[iarg] = arg.replace('--base-url=', '--base-urlpath=')

        args.append("--proxy-api-url={}".format(self.proxy.api_server.url))

        if self.config_file_path:
            args.append("--config-file={}".format(self.config_file_path))

        return args

    def user_env(self, env):
        env['USER'] = self.user.name

        if self._virtual_workspace:
            env['HOME'] = self._virtual_workspace

        return env

    def get_env(self):
        # LocalProcessSpawner.get_env calls user_env as well
        env = super().get_env()
        env["PROXY_API_TOKEN"] = self.proxy.auth_token
        env.update(_docker_envvars())
        return env

    @gen.coroutine
    def start(self):
        """ Start the process and create the virtual user's
        temporary home directory if `workspace_dir` is set
        """
        # Create the temporary directory as the user's workspace
        if self.workspace_dir and not self._virtual_workspace:
            try:
                self._virtual_workspace = tempfile.mkdtemp(
                    dir=self.workspace_dir)
            except Exception as exception:
                # A whole lot of reasons why temporary directory cannot
                # be created. e.g. workspace_dir does not exist
                # the owner of the process has no write permission
                # for the directory, etc.
                msg = ("Failed to create temporary directory for '{user}' in "
                       "'{tempdir}'.  Temporary workspace would not be "
                       "available. Please assign the spawner's `workspace_dir`"
                       " to a directory path where it has write permission. "
                       "Error: {error}")
                # log as error to avoid ugly traceback
                self.log.error(
                    msg.format(user=self.user.name,
                               tempdir=self.workspace_dir,
                               error=str(exception)))
            else:
                self.log.info("Created %s's temporary workspace in: %s",
                              self.user.name, self._virtual_workspace)

        # Make sure we clean up in case `start` fails
        try:
            yield super().start()
        except Exception:
            self._clean_up_workspace_dir()
            raise

    @gen.coroutine
    def stop(self, now=False):
        """ Stop the process

        If virtual user has a temporary home directory,
        clean up the directory.
        """
        self._clean_up_workspace_dir()
        yield super().stop(now=now)

    def _clean_up_workspace_dir(self):
        """ Clean up the virtual user's temporary directory, if exists
        """
        if not self._virtual_workspace:
            return

        # Clean up the directory
        # Make sure the temporary directory is not /, ./ or ../
        if os.path.normpath(self._virtual_workspace) in ('/', '.', '..'):
            self.log.warning("Virtual workspace is '%s'.  Seriously? "
                             "Not removing.", self._virtual_workspace)
        else:
            try:
                shutil.rmtree(self._virtual_workspace)
            except Exception as exception:
                self.log.error("Failed to remove %s, error %s",
                               self._virtual_workspace, str(exception))
            else:
                self.log.info('Removed %s', self._virtual_workspace)


def _docker_envvars():
    """Returns a dictionary containing the docker environment variables, if
    present. If not present, returns an empty dictionary"""
    env = {envvar: os.environ[envvar]
           for envvar in ["DOCKER_HOST",
                          "DOCKER_CERT_PATH",
                          "DOCKER_MACHINE_NAME",
                          "DOCKER_TLS_VERIFY"]
           if envvar in os.environ}

    return env