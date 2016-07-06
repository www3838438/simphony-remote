from urllib import parse

from tornado import gen
from jupyterhub import orm as jupyterhub_orm
from traitlets import HasTraits, Unicode

from remoteappmanager.logging.logging_mixin import LoggingMixin


class ReverseProxy(LoggingMixin, HasTraits):
    """Represents the remote reverse proxy. It is meant to have a high
    level API."""
    # The endpoint url at which the reverse proxy has its api
    endpoint_url = Unicode()

    #: The authorization token to authenticate the request
    auth_token = Unicode()

    def __init__(self, *args, **kwargs):
        """Initializes the reverse proxy connection object."""
        super().__init__(*args, **kwargs)

        # Note, we use jupyterhub orm Proxy, but not for database access,
        # just for interface convenience.
        self._reverse_proxy = jupyterhub_orm.Proxy(
            auth_token=self.auth_token,
            api_server=_server_from_url(self.endpoint_url)
        )

        self.log.info("Reverse proxy setup on {}".format(
            self.endpoint_url
        ))

    @gen.coroutine
    def remove_container(self, container):
        """Removes a container from the reverse proxy at the associated url.

        Parameters
        ----------
        container : Container
            A container object.
        """
        proxy = self._reverse_proxy

        urlpath = container.absurlpath
        self.log.info("Deregistering url {} to {} on reverse proxy.".format(
            urlpath,
            container.host_url
        ))

        yield proxy.api_request(urlpath, method='DELETE')

    @gen.coroutine
    def add_container(self, container):
        """Adds the url associated to a given container on the reverse proxy.

        Parameters
        ----------
        container : Container
            A container object.
        """

        proxy = self._reverse_proxy
        urlpath = container.absurlpath

        self.log.info("Registering url {} to {} on reverse proxy.".format(
            urlpath,
            container.host_url
        ))

        yield proxy.api_request(
            urlpath,
            method='POST',
            body=dict(
                target=container.host_url,
            )
        )


def _server_from_url(url):
    """Creates a orm.Server from a given url"""
    parsed = parse.urlparse(url)
    return jupyterhub_orm.Server(
        proto=parsed.scheme,
        ip=parsed.hostname,
        port=parsed.port,
        base_url=parsed.path
    )
