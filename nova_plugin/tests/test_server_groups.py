import os
import unittest

from tempfile import mkdtemp
from shutil import rmtree

from mock import MagicMock
from novaclient.v2 import client

from cloudify.workflows import local


class TestPlugin(unittest.TestCase):

    def setUp(self):

        self.temp_dir = mkdtemp()
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'resources', 'test-server-groups.yaml')


        # setup local workflow execution environment
        self.env = local.init_env(blueprint_path,
                                  name=self._testMethodName,
                                  ignored_modules=['worker_installer.tasks',
                                                   'plugin_installer.tasks'],
                                  inputs={'private_key_path' : os.path.join(self.temp_dir, 'key.pem')})


    def tearDown(self):
        rmtree(self.temp_dir)

    def test_create(self):

        client.server_groups.ServerGroupsManager.create = MagicMock(return_value={
            'server_group': {
                'id': 'test_sg_id',
                'name': 'test_sg_name'
            }})

        self.env.execute('install', task_retries=0)

        # extract single node instance
        # instance = self.env.storage.get_node_instances()[0]

        # assert runtime properties is properly set in node instance
        # self.assertEqual(instance.runtime_properties['value_of_some_property'],
        #                  'new_test_input')

        # assert deployment outputs are ok
        # self.assertDictEqual(self.env.outputs(),
        #                      {'test_output': 'new_test_input'})