import pytest
import time
from web3 import Web3, HTTPProvider
from watcher import Watcher

class TestWatcher:
    web3 = Web3(HTTPProvider(endpoint_uri=f"http://localhost:8545", request_kwargs={"timeout":10}))
    watcher = Watcher(web3)


    def test_add_block_syncer(self):
        def callback():
            print("test")
        self.watcher.add_block_syncer(callback)
        assert 1 == len(self.watcher.block_syncers)

    def test_1(self):
        self.watcher._last_block_time = 1
        self.watcher._start_watching_blocks()

    def test_2(self):
        self.watcher._wait_for_node_sync()

    def test_3(self):
        def callback():
            print("test")
        self.watcher.add_block_syncer(callback)
        block = self.web3.eth.getBlock("latest")
        self.watcher._sync_block(block['hash'])
    
