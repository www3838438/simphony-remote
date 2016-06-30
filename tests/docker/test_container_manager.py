import os
from unittest import mock

from docker.errors import NotFound
from tornado.testing import AsyncTestCase, gen_test

from remoteappmanager.docker.container import Container
from remoteappmanager.docker.container_manager import ContainerManager
from remoteappmanager.docker.image import Image
from tests import utils


class TestContainerManager(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.manager = ContainerManager()
        self.mock_docker_client = utils.mock_docker_client()
        self.manager.docker_client.client = self.mock_docker_client

    def test_instantiation(self):
        self.assertIsNotNone(self.manager.docker_client)

    @gen_test
    def test_start_stop(self):
        mock_client = self.mock_docker_client

        result = yield self.manager.start_container("username",
                                                    "imageid",
                                                    "mapping_id",
                                                    None)
        self.assertTrue(mock_client.start.called)
        self.assertIsInstance(result, Container)
        self.assertFalse(mock_client.stop.called)
        self.assertFalse(mock_client.remove_container.called)

        yield self.manager.stop_and_remove_container(result.docker_id)

        self.assertTrue(mock_client.stop.called)
        self.assertTrue(mock_client.remove_container.called)

    @gen_test
    def test_containers_from_mapping_id(self):
        ''' Test containers_for_mapping_id returns a list of Container '''
        # The mock client mocks the output of docker Client.containers
        docker_client = utils.mock_docker_client_with_running_containers()
        self.mock_docker_client = docker_client
        self.manager.docker_client.client = docker_client

        result = yield self.manager.containers_from_mapping_id("user",
                                                               "mapping")
        expected = Container(docker_id='someid',
                             name='/remoteexec-image_3Alatest_user',
                             image_name='simphony/mayavi-4.4.4:latest',  # noqa
                             image_id='imageid', ip='0.0.0.0', port=None)

        self.assertEqual(len(result), 1)
        utils.assert_containers_equal(self, result[0], expected)

    @gen_test
    def test_race_condition_spawning(self):
        # Start the operations, and retrieve the future.
        # they will stop at the first yield and not go further until
        # we yield them
        f1 = self.manager.start_container("username",
                                          "imageid",
                                          "mapping_id",
                                          None)

        f2 = self.manager.start_container("username",
                                          "imageid",
                                          "mapping_id",
                                          None)

        # If these yielding raise a KeyError, it is because the second
        # one tries to remove the same key from the list, but it has been
        # already removed by the first one. Race condition.
        yield f1
        yield f2

        self.assertEqual(self.mock_docker_client.start.call_count, 1)

    @gen_test
    def test_start_already_present_container(self):
        mock_client = \
            utils.mock_docker_client_with_existing_stopped_container()
        self.manager.docker_client.client = mock_client

        result = yield self.manager.start_container(
            "vagrant",
            "simphony/simphony-remote-docker:simphony-framework-paraview",
            "mapping",
            None)
        self.assertTrue(mock_client.start.called)
        self.assertIsInstance(result, Container)

        # Stop should have been called and the container removed
        self.assertTrue(mock_client.stop.called)
        self.assertTrue(mock_client.remove_container.called)

    @gen_test
    def test_image(self):
        image = yield self.manager.image('simphony/mayavi-4.4.4:latest')
        self.assertIsInstance(image, Image)
        self.assertEqual(image.description,
                         'Ubuntu machine with mayavi preinstalled')
        self.assertEqual(image.icon_128, "")
        self.assertEqual(image.ui_name, "")
        self.assertEqual(image.docker_id,
                         'sha256:e54d71dde57576e9d2a4c77ce0c98501c8aa6268de5b2987e4c80e2e157cffe4')  # noqa

        def raiser(*args, **kwargs):
            raise NotFound("not found", mock.Mock())

        self.mock_docker_client.inspect_image = mock.Mock(side_effect=raiser)
        image = yield self.manager.image("whatev")
        self.assertIsNone(image)

    @gen_test
    def test_start_container_with_nonexisting_volume_source(self):
        # These volume sources are invalid
        volumes = {'~no_way_this_be_valid': {'bind': '/target_vol1',
                                             'mode': 'ro'},
                   '/no_way_this_be_valid': {'bind': '/target_vol2',
                                             'mode': 'ro'}}

        # This volume source is valid
        good_path = os.path.abspath('.')
        volumes[good_path] = {'bind': '/target_vol3',
                              'mode': 'ro'}

        yield self.manager.start_container("username",
                                           "imageid",
                                           "mapping_id",
                                           volumes)

        # Call args and keyword args that create_container receives
        args = self.manager.docker_client.client.create_container.call_args
        actual_volume_targets = args[1]['volumes']

        # Invalid volume paths should have been filtered away
        self.assertNotIn('/target_vol1', actual_volume_targets)
        self.assertNotIn('/target_vol2', actual_volume_targets)

        # The current directory is valid, should stay
        self.assertIn('/target_vol3', actual_volume_targets)

    @gen_test
    def test_start_container_exception_cleanup(self):
        self.assertFalse(self.mock_docker_client.stop.called)
        self.assertFalse(self.mock_docker_client.remove_container.called)

        def raiser(*args, **kwargs):
            raise Exception("Boom!")

        self.manager.docker_client.start = mock.Mock(side_effect=raiser)

        with self.assertRaises(Exception):
            yield self.manager.start_container("username",
                                               "imageid",
                                               "mapping_id",
                                               None)

        self.assertTrue(self.mock_docker_client.stop.called)
        self.assertTrue(self.mock_docker_client.remove_container.called)

    @gen_test
    def test_start_container_exception_cleanup_2(self):
        # Same test as above, but checks after the start (at ip and port)
        self.assertFalse(self.mock_docker_client.stop.called)
        self.assertFalse(self.mock_docker_client.remove_container.called)

        def raiser(*args, **kwargs):
            raise Exception("Boom!")

        self.manager.docker_client.port = mock.Mock(side_effect=raiser)

        with self.assertRaises(Exception):
            yield self.manager.start_container("username",
                                               "imageid",
                                               "mapping_id",
                                               None)

        self.assertTrue(self.mock_docker_client.stop.called)
        self.assertTrue(self.mock_docker_client.remove_container.called)
