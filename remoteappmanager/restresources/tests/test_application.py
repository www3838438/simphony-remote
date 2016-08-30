from unittest.mock import Mock, patch

from remoteappmanager import rest
from remoteappmanager.docker.image import Image
from remoteappmanager.rest import registry
from remoteappmanager.rest.http import httpstatus
from remoteappmanager.restresources import Application
from remoteappmanager.tests import utils
from remoteappmanager.tests.mocking.dummy import create_container_manager
from remoteappmanager.tests.utils import AsyncHTTPTestCase, mock_coro_factory
from tornado import web, escape


class TestApplication(AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()

    def get_app(self):
        handlers = rest.api_handlers('/')
        registry.registry.register(Application)
        app = web.Application(handlers=handlers)
        app.db = Mock()
        app.container_manager = Mock()
        app.container_manager.image = mock_coro_factory(
            return_value=Image(name="boo", ui_name="foo_ui"))
        app.container_manager.containers_from_mapping_id = mock_coro_factory(
            return_value=[])
        application_mock_1 = Mock()
        application_mock_1.image = "hello1"

        application_mock_2 = Mock()
        application_mock_2.image = "hello2"
        app.db.get_apps_for_user = Mock(return_value=[
            ("one", application_mock_1, Mock()),
            ("two", application_mock_2, Mock()),
        ])
        return app

    def test_items(self):
        def prepare_side_effect(*args, **kwargs):
            user = Mock()
            user.account = Mock()
            args[0].current_user = user

        with patch("remoteappmanager"
                   ".handlers"
                   ".base_handler"
                   ".BaseHandler"
                   ".prepare",
                   new_callable=utils.mock_coro_new_callable(
                    side_effect=prepare_side_effect)
                   ):
            res = self.fetch("/api/v1/applications/")

            self.assertEqual(res.code, httpstatus.OK)
            self.assertEqual(escape.json_decode(res.body),
                             {"items": ["one", "two"]})

    def test_retrieve(self):
        def prepare_side_effect(*args, **kwargs):
            user = Mock()
            user.account = Mock()
            args[0].current_user = user

        with patch("remoteappmanager"
                   ".handlers"
                   ".base_handler"
                   ".BaseHandler"
                   ".prepare",
                   new_callable=utils.mock_coro_new_callable(
                       side_effect=prepare_side_effect)
                   ):
            res = self.fetch("/api/v1/applications/one/")

            self.assertEqual(res.code, httpstatus.OK)
            self.assertEqual(escape.json_decode(res.body),
                             {'container': None,
                              'image': {'description': '',
                                        'docker_id': '',
                                        'icon_128': '',
                                        'name': 'boo',
                                        'ui_name': 'foo_ui'},
                              'mapping_id': 'one'})

            res = self.fetch("/api/v1/applications/two/")

            res = self.fetch("/api/v1/applications/three/")

            self.assertEqual(res.code, httpstatus.NOT_FOUND)
