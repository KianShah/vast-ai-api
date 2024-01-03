from random import randint
import unittest
import time

import pandas as pd

from src.vast_ai_api.vast_ai import VastAPIHelper

class TestVastAPIHelper(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.api_helper = VastAPIHelper()
        
    def tearDown(self):
        rented_instances = self.api_helper.list_current_instances()
        for instance_id in rented_instances['id']:
            self.api_helper.stop_instance(instance_id)
            time.sleep(1)
            self.api_helper.delete_instance(instance_id)

    def test_launch_instance(self):
        instances = self.api_helper.list_available_instances(max_price=0.5)
        self.assertIsInstance(instances, pd.DataFrame)
        instance = instances.iloc[randint(0, len(instances))]
        
        self.api_helper.launch_instance(instance['id'])
        time.sleep(5)
        
        rented_instances = self.api_helper.list_current_instances()
        self.assertTrue(len(rented_instances) > 0)
        rented_machine = rented_instances.loc[rented_instances["machine_id"] == instance['machine_id']].squeeze()
        self.assertTrue(rented_machine['cur_state'] == 'running')
        
if __name__ == '__main__':
    unittest.main()
