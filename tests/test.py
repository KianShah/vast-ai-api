from random import randint
import unittest
import time

from src.vast_ai_api import VastAPIHelper

# Make sure to check on Vast.ai to ensure that the test instance was actually deleted after running the tests
class TestVastAPIHelper(unittest.TestCase):
    
    @classmethod
    def wait_for_instance_startup(cls, instance_id: str):
        instance = cls.api_helper.get_instance(instance_id)
        for delay in [10, 20, 30, 40, 50, 60]:
            if instance['actual_status'] == 'running':
                break
            time.sleep(delay)
            instance = cls.api_helper.get_instance(instance_id)
        if instance['actual_status'] != 'running':
            raise Exception("Instance did not start in time")

    @classmethod
    def setUpClass(cls):
        cls.api_helper = VastAPIHelper()
        # Reserve an instance to run tests on
        instances = cls.api_helper.list_available_instances(max_price=0.5)
        instance = instances.iloc[randint(0, len(instances))]
        
        cls.api_helper.launch_instance(instance['id'], use_jupyter_lab=False)
        rented_instances = cls.api_helper.list_current_instances()
        cls.test_instance = rented_instances.loc[rented_instances["machine_id"] == instance['machine_id']].squeeze()
        cls.wait_for_instance_startup(cls.test_instance['id'])

    @classmethod
    def tearDownClass(cls):
        cls.api_helper.delete_instance(cls.test_instance['id'])
    
    def test_launch_instance(self):
        self.assertTrue(self.test_instance['cur_state'] == 'running')
        
    def test_instance_logs(self):
        logs = self.api_helper.get_instance_logs(self.test_instance['id'])
        self.assertIsNotNone(logs)
        self.assertTrue(len(logs) > 0)
    
    def test_instance_stop_start(self):
        self.api_helper.stop_instance(self.test_instance['id'])
        self.test_instance = self.api_helper.get_instance(self.test_instance['id'])
        self.assertTrue(self.test_instance['next_state'] == 'stopped')
        
        self.api_helper.start_instance(self.test_instance['id'])
        self.test_instance = self.api_helper.get_instance(self.test_instance['id'])
        self.assertTrue(self.test_instance['next_state'] == 'running')
        self.wait_for_instance_startup(self.test_instance['id'])
    
    def test_ssh_connect(self):
        client = self.api_helper.connect_ssh(self.test_instance['id'])
        try:
            stdin, stdout, stderr = client.exec_command('ls -a')
            output = stdout.readlines()
            error = stderr.readlines()
            self.assertTrue(len(output) > 0)
            self.assertTrue(len(error) == 0)
        finally:
            client.close()
        
if __name__ == '__main__':
    unittest.main()
