import json
import time
from typing import Dict, Literal, Tuple
import pandas as pd
import requests
from datetime import date
import os
from collections import defaultdict
from urllib import parse
import paramiko
import logging

from src.vast_ai_api.util import forward_tunnel

logging.basicConfig()
logger = logging.getLogger('vast')

# https://vast.ai/
class VastAPIHelper:
    BASE_URL = 'https://console.vast.ai/api/v0'

    def __init__(self):
        self.API_KEY = os.environ['VAST_AI_API_KEY']
        
    def _build_query(self, params):
        query = defaultdict(dict, {
            "verified": {'eq': params['verified']},
            "external": {'eq': False},
            "rentable": {'eq': True},
            "rented": {'eq': False},
            "order": [["dph_total", "desc"]],
            "type": params['instance_type'],
            "allocated_storage": params['disk_space']
        })
        del params['verified']
        del params['disk_space']
        del params['instance_type']
        
        available_fields = {
            'price': 'dph_total', 
            'ram': 'cpu_ram',
            'vram': 'gpu_ram',
            'region': 'geolocation'
        }
        
        for k, v in params.items():
            if v is None:
                continue
            if '_' in k:
                op, key = k.split('_')
                op_name = 'gte' if op == 'min' else 'lte'
                query[available_fields[key]].update({op_name: str(v)})
            elif k == "region":
                query[available_fields[key]] = {'=', v}
            else:
                raise ValueError(f"Unknown parameter {k}")
        return query

    
    """
        Important parameters:
            disk_space: float    // The amount of disk space in GB to allocate
            region:              // Two letter country code
            verified:            // Whether to only show instances in verified datacenters
        
        Returns:
            Returns a dataframe of available instances, in the same format as Vast.ai cli
            The dataframe is sorted by default by price, descending
            For more information, consult the Vast.ai documentation
    """
    def list_available_instances(self, 
                                 min_price: float = None, 
                                 max_price: float = None,
                                 min_ram: int = None,
                                 max_ram: int = None,
                                 min_vram: int = None,
                                 max_vram: int = None,
                                 disk_space: float = 5.0,
                                 instance_type: Literal['on-demand', 'bid'] = 'on-demand',
                                 region: str = None,
                                 verified: bool = True) -> pd.DataFrame:
        params = dict(list(locals().items())[-10:]) # Update whenever adding parameters. Creates a dictionary from all the parameters
        query = {"q": self._build_query(params)}
        
        query_str = "&".join([f"{k}={parse.quote_plus(str(v) if isinstance(v, str) else json.dumps(v))}" for k, v in query.items()])


        res = requests.get(f"{self.BASE_URL}/bundles?{query_str}")
        res.raise_for_status()
        df = pd.DataFrame.from_records(res.json()['offers'])
        logger.debug(f"Recieved {len(df)} results")
        return df

    def list_current_instances(self) -> pd.DataFrame:
        res = requests.get(f"{self.BASE_URL}/instances",
                           params={"owner": "me", "api_key": self.API_KEY})
        res.raise_for_status()
        return pd.DataFrame.from_records(res.json()['instances'])

    def _set_instance_state(self, instance_id: str, method: Literal["PUT", "DELETE"], state: str = None) -> None:
        if method == "PUT":
            res = requests.put(f"{self.BASE_URL}/instances/{instance_id}/",
                               params={"api_key": self.API_KEY}, json={'state': state})
        elif method == "DELETE":
            res = requests.delete(
                f"{self.BASE_URL}/instances/{instance_id}/", params={"api_key": self.API_KEY})
        else:
            raise Exception("Unkown Method used")
        res.raise_for_status()
        res = res.json()
        if 'msg' in res:
            raise Exception(res['msg'])

    """
        Launch an instance. Note that this modifies the id of the instance if rented (the machine id remains unchanged)
        Ensure that the instance is allowed to allocate the amount of disk_size requested
    """
    def launch_instance(self, 
                        instance_id: str, 
                        docker_image_name: str = "pytorch/pytorch", 
                        label: str = None, 
                        env: Dict = None, 
                        disk_size: int = 50,
                        use_jupyter_lab: bool = True,
                        bid_price_per_machine: float = None) -> None:
        payload = {
            "client_id": "me",
            "image": docker_image_name,
            "env": {},
            "price": bid_price_per_machine, # $/hr
            "disk": disk_size,
            "label": label,
            "runtype": "jupyter_direc ssh_direc ssh_proxy" if use_jupyter_lab else "ssh_direc ssh_proxy",
            "use_jupyter_lab": use_jupyter_lab,
        }
        res = requests.put(f"{self.BASE_URL}/asks/{instance_id}/", 
                           headers={"Authorization": f"Bearer {self.API_KEY}"}, 
                           params={"api_key": self.API_KEY}, 
                           json=payload)
        res.raise_for_status()
        
    def change_bid(self, instance_id: str, price: float) -> None:
        res = requests.put(f"{self.BASE_URL}/instances/bid_price/{instance_id}/", {"client_id": "me", "price": price})
        res.raise_for_status()
        
    def get_instance(self, instance_id: str) -> pd.Series:
        df = self.list_current_instances()
        return df[df['id'] == instance_id].squeeze()

    # SSH key required
    def start_instance(self, instance_id: str) -> pd.DataFrame:
        self._set_instance_state(instance_id, 'PUT', 'running')

    # SSH key required
    def stop_instance(self, instance_id: str) -> None:
        self._set_instance_state(instance_id, 'PUT', 'stopped')
    
    # SSH key required     
    def reboot_instance(self, instance_id: str) -> None:
        self.stop_instance(instance_id)
        self.start_instance(instance_id)
        
    def label_instance(self, instance_id: str, label: str) -> None:
        res = requests.put(f"{self.BASE_URL}/instances/{instance_id}/", {"label": label})
        res.raise_for_status()
    
    # SSH key required
    def delete_instance(self, instance_id: str) -> None:
        self._set_instance_state(instance_id, 'PUT', 'stopped')
        self._set_instance_state(instance_id, 'DELETE')
        
    # SSH key required
    def connect_ssh(self, instance_id: str, use_vast_proxy: bool = True, port_forwarding: Tuple[int, int] = None) -> paramiko.SSHClient:
        instance = self.get_instance(instance_id)
        if use_vast_proxy:
            ssh_host = instance['ssh_host']
            ssh_port = int(instance['ssh_port'])
        else:
            ssh_host = instance['public_ipaddr']
            ssh_port = int(instance['direct_port_start'])

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ssh_host, port=ssh_port, username='root')
        if not client.get_transport().is_active():
            raise Exception("Could not connect to the SSH server using any key from SSH agent; make sure you've added it using `ssh-add <PATH_TO_PRIVATE_KEYFILE>")
        
        if port_forwarding is not None:
            local_port, remote_port = port_forwarding
            forward_tunnel(local_port, 'localhost', remote_port, client.get_transport())
        return client
        
        
    def get_instance_logs(self, instance_id: str, tail: int = 1000) -> str:
        res = requests.put(f"{self.BASE_URL}/instances/request_logs/{instance_id}/",
                           params={"api_key": self.API_KEY},
                           json={"tail": tail})
        res.raise_for_status()
        s3_url = res.json()['result_url']
        for _ in range(10):
            r = requests.get(s3_url)
            if (r.status_code == 200):
                return r.text
            logger.debug(f"Waiting on logs for instance {instance_id} fetching from {s3_url}")
            time.sleep(0.5)

    """
        Host actions
    """
        
    def show_hosted_machines(self) -> None:
        res = requests.get(f"{self.BASE_URL}/machines", {'owner': 'me'})
        res.raise_for_status()
        return res
    
    def list_machine_for_rent(self, price_per_gpu: float, storage_price: float, price_inet_up: float, price_inet_down: float, min_gpus: int, end_date: date, discount_rate: float = 0.4):
        raise NotImplementedError()
        
    def unlist_machine_for_rent(self, instance_id: str) -> None:
        res = requests.delete(f"{self.BASE_URL}/machines/{instance_id}/asks/")
        res.raise_for_status()
        