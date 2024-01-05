import subprocess
from random import randint
import unittest
import time

import requests

from src.vast_ai_api import VastAPIHelper
from definitions import ROOT_DIR

path_to_copied_file = ROOT_DIR / "tests" / "remote_test.py"


# Make sure to check on Vast.ai to ensure that the test instance was actually deleted after running the tests
class TestVastAPIHelper(unittest.TestCase):
    
    @classmethod
    def wait_for_instance_startup(cls, instance_id: str):
        instance = cls.api.get_instance(instance_id)
        for delay in [10, 20, 30, 40, 50, 60]:
            if instance['actual_status'] == 'running':
                break
            time.sleep(delay)
            instance = cls.api.get_instance(instance_id)
        if instance['actual_status'] != 'running':
            raise Exception("Instance did not start in time")

    @classmethod
    def setUpClass(cls):
        cls.api = VastAPIHelper()
        # Reserve an instance to run tests on
        instances = cls.api.list_available_instances(max_price=0.5)
        instance = instances.iloc[randint(0, len(instances))]
        
        cls.api.launch_instance(instance['id'], use_jupyter_lab=False)
        rented_instances = cls.api.list_current_instances()
        cls.test_instance = rented_instances.loc[rented_instances["machine_id"] == instance['machine_id']].squeeze()
        cls.wait_for_instance_startup(cls.test_instance['id'])

    @classmethod
    def tearDownClass(cls):
        cls.api.delete_instance(cls.test_instance['id'])
        
    def setUp(self):
        pass
        
    def tearDown(self):
        path_to_copied_file.unlink(missing_ok=True)

    
    def test_launch_instance(self):
        self.assertTrue(self.test_instance['cur_state'] == 'running')
        
    def test_instance_logs(self):
        logs = self.api.get_instance_logs(self.test_instance['id'])
        self.assertIsNotNone(logs)
        self.assertTrue(len(logs) > 0)
    
    def test_instance_stop_start(self):
        self.api.stop_instance(self.test_instance['id'])
        self.test_instance = self.api.get_instance(self.test_instance['id'])
        self.assertTrue(self.test_instance['next_state'] == 'stopped')
        
        self.api.start_instance(self.test_instance['id'])
        self.test_instance = self.api.get_instance(self.test_instance['id'])
        self.assertTrue(self.test_instance['next_state'] == 'running')
        self.wait_for_instance_startup(self.test_instance['id'])
    
    def test_ssh_connect(self):
        client = self.api.connect_ssh(self.test_instance['id'])
        try:
            stdin, stdout, stderr = client.exec_command('ls -a')
            output = stdout.readlines()
            error = stderr.readlines()
            self.assertTrue(len(output) > 0)
            self.assertTrue(len(error) == 0)
        finally:
            client.close()
            
    def test_ssh_connect_with_port_forwarding(self):
        client = self.api.connect_ssh(self.test_instance['id'], port_forwarding=(8085, 8085))
        try:
            stdin, stdout, stderr = client.exec_command('ls -a')
            output = stdout.readlines()
            error = stderr.readlines()
            self.assertTrue(len(output) > 0)
            self.assertTrue(len(error) == 0)
            
            # Start a web server on port 8085 on remote machine
            stdin, stdout, stderr = client.exec_command("while true; do { echo -e 'HTTP/1.1 200 OK\r\n'; echo 'Hello, World!'; } | nc -l -p 8085; done")
            res = requests.get('http://localhost:8085')
            res.raise_for_status()
            self.assertEqual(res.text, 'Hello, World!')
        finally:
            client.close()

            
    def test_file_copy_with_client(self):
        try:
            client = self.api.connect_ssh(self.test_instance['id'])
            self.api.copy('localhost:22:./tests/helloWorld.py', "remote:donotcare:~/helloWorld_with_client.py", client)
            _, stdout, _ = client.exec_command('cd ~ && ls')
            output = stdout.readlines()
            self.assertIn('helloWorld_with_client', output)
            
            _, _, stdout = client.exec_command("echo 'test = 1' > remote_test.py")
            self.assertTrue(len(stdout.readlines()) == 0)
            self.api.copy('localhost:22:./tests/remote_test.py', "remote:donotcare:~/remote_test.py", client)
            self.assertTrue(path_to_copied_file.exists())
        finally:
            client.close()
            
    def test_file_copy_without_client(self):
        try:
            client = self.api.connect_ssh(self.test_instance['id'])
            ssh_host, ssh_port = self.test_instance['ssh_host'], self.test_instance['ssh_port']
            self.api.copy('localhost:22:./tests/helloWorld.py', f"{ssh_host}:{ssh_port}:~/helloWorld_without_client.py")
            _, stdout, _ = client.exec_command('cd ~ && ls')
            output = stdout.readlines()
            self.assertIn('helloWorld_without_client', output)
            
            _, _, stdout = client.exec_command("echo 'test = 2' > remote_test.py")
            self.assertTrue(len(stdout.readlines()) == 0)
            self.api.copy('localhost:22:./tests/remote_test.py', f"{ssh_host}:{ssh_port}:~/remote_test.py")
            self.assertTrue(path_to_copied_file.exists())
        finally:
            client.close()

        
if __name__ == '__main__':
    unittest.main()
