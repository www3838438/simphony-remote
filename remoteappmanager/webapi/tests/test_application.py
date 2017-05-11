from unittest.mock import Mock

from tornado import web, gen

from remoteappmanager.db import orm
from remoteappmanager.tests.utils import mock_coro_factory
from tornadowebapi import registry
from tornadowebapi.authenticator import NullAuthenticator
from tornadowebapi.http import httpstatus

from remoteappmanager.docker.container import Container
from remoteappmanager.docker.image import Image
from remoteappmanager.webapi import ApplicationHandler
from remoteappmanager.tests.webapi_test_case import WebAPITestCase
from remoteappmanager.tests.mocking.dummy import create_hub


class DummyAuthenticator:
    @classmethod
    @gen.coroutine
    def authenticate(cls, handler):
        user = Mock()
        user.account = Mock()
        return user


class TestApplication(WebAPITestCase):
    def setUp(self):
        super().setUp()

    def get_app(self):
        self.reg = registry.Registry()
        self.reg.register(ApplicationHandler)
        self.reg.authenticator = DummyAuthenticator
        handlers = self.reg.api_handlers('/')
        app = web.Application(handlers=handlers)
        app.db = Mock()
        app.hub = create_hub()
        app.container_manager = Mock()
        app.container_manager.image = mock_coro_factory(
            return_value=Image(name="boo", ui_name="foo_ui"))
        app.container_manager.find_containers = mock_coro_factory(
            return_value=[])
        image_mock_1 = Mock(spec=orm.Image)
        image_mock_1.name = "hello1"

        image_mock_2 = Mock(spec=orm.Image)
        image_mock_2.name = "hello2"

        policy = Mock(
            allow_home=True,
            volume_source="foo",
            volume_target="bar",
            volume_mode="ro",
        )

        app.db.get_accounting_for_user = Mock(return_value=[
            Mock(spec=orm.Accounting,
                 id="one",
                 image=image_mock_1,
                 application_policy=policy),
            Mock(spec=orm.Accounting,
                id="two",
                image=image_mock_2,
                application_policy=policy),
        ])
        return app

    def test_items(self):
        _, data = self.get("/api/v1/applications/", httpstatus.OK)
        self.assertEqual(data, {
            'total': 2,
            'items': {
                'two': {
                    'image': {
                        'policy': {
                            'volume_mode': 'ro',
                            'volume_source': 'foo',
                            'allow_home': True,
                            'volume_target': 'bar'
                        },
                        'name': 'boo',
                        'icon_128': '',
                        'ui_name': 'foo_ui',
                        'description': '',
                        'configurables': []
                    },
                    'mapping_id': 'two'
                },
                'one': {
                    'image': {
                        'policy': {
                            'volume_mode': 'ro',
                            'volume_source': 'foo',
                            'allow_home': True,
                            'volume_target': 'bar'
                        },
                        'name': 'boo',
                        'icon_128': '',
                        'ui_name': 'foo_ui',
                        'description': '',
                        'configurables': []
                    },
                    'mapping_id': 'one'
                }
            },
            'identifiers': ['one', 'two'],
            'offset': 0
        })

        # Check if nothing is returned if no images are present
        self._app.container_manager.image = mock_coro_factory(
            return_value=None)

        _, data = self.get("/api/v1/applications/", httpstatus.OK)
        self.assertEqual(data, {
            "offset": 0,
            "total": 0,
            "items": {},
            "identifiers": []})

    def test_items_no_user(self):
        self.reg.authenticator = NullAuthenticator
        self.get("/api/v1/applications/", httpstatus.NOT_FOUND)

    def test_retrieve(self):
        _, data = self.get("/api/v1/applications/one/", httpstatus.OK)

        self.assertEqual(data,
                         {
                             'mapping_id': "one",
                             'image': {
                              'configurables': [],
                              'description': '',
                              'icon_128': '',
                              'name': 'boo',
                              'policy': {
                                    "allow_home": True,
                                    "volume_mode": 'ro',
                                    "volume_source": "foo",
                                    "volume_target": "bar",
                              },
                              'ui_name': 'foo_ui'}})

        self._app.container_manager.find_containers = \
            mock_coro_factory(return_value=[Container(
                name="container",
                image_name="xxx",
                url_id="yyy")])

        _, data = self.get("/api/v1/applications/one/", httpstatus.OK)

        self.assertEqual(data,
                         {
                             'mapping_id': "one",
                             'container': {
                                 'image_name': 'xxx',
                                 'name': 'container',
                                 'url_id': 'yyy'
                                 },
                             'image': {
                                 'description': '',
                                 'icon_128': '',
                                 'name': 'boo',
                                 'ui_name': 'foo_ui',
                                 'policy': {
                                     "allow_home": True,
                                     "volume_mode": 'ro',
                                     "volume_source": "foo",
                                     "volume_target": "bar",
                                 },
                                 'configurables': [],
                             }
                          })

        self.get("/api/v1/applications/three/", httpstatus.NOT_FOUND)

        # Check the not found case if the image is not present
        self._app.container_manager.image = mock_coro_factory(None)

        self.get("/api/v1/applications/one/", httpstatus.NOT_FOUND)

    def test_retrieve_no_user(self):
        self.reg.authenticator = NullAuthenticator
        self.get("/api/v1/applications/one/", httpstatus.NOT_FOUND)
