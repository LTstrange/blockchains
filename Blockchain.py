# -*- coding: utf-8 -*-
# @Time    : 2021/3/30 14:04
# @Author  : LTstrange

import hashlib
import json
import re
from time import time
from uuid import uuid4

from urllib.parse import urlparse
import requests


class BlockChain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # todo: 使用公钥私钥替换 identifier
        self.host = None
        self.Account = str(uuid4()).replace('-', '')
        self.nodes = set()

        # create the genesis block
        self.new_block(previous_hash='0' * 64)

    def get_host(self, ip, port):
        self.host = f"{ip}:{port}"
        self.register_node(self.host)

    def __len__(self):
        return len(self.chain)

    @property
    def last_block(self):
        return self.chain[-1]

    def new_block(self, previous_hash: str = None) -> dict:
        """
        Create a new Block in the Blockchain, also called "mining"
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        # We must receive a reward for finding the proof.
        # The sender is "0" to signify that this node has mined a new coin.
        self.new_transaction({
            "sender": '0',
            "recipient": self.Account,
            "amount": 1,
        })

        new_block = self.proof_of_work(previous_hash)

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(new_block)
        return new_block

    # todo: 需要实现公钥 私钥
    def new_transaction(self, transaction: dict) -> bool:
        """
        Creates a new transaction to go into the next mined Block
        :param transaction: <dict>
        :return: <bool> True if transaction if valid and added, False if not
        """
        # Check that the required fields are in the POSTed data
        required = ['sender', 'recipient', 'amount']
        if not all(k in transaction for k in required):
            return False

        for key in transaction:
            if not transaction[key]:
                return False
        transaction = dict(transaction)
        if not transaction.get('uuid'):
            transaction['uuid'] = str(uuid4()).replace('-', '')
        # 检查同样的交易有无重复
        if self.check_transaction(transaction):
            self.current_transactions.append(transaction)
        else:
            return False
        return True

    def proof_of_work(self, previous_hash: str) -> dict:
        """
        Proof of Work Algorithm
        :param previous_hash: <str>
        :return next_block: <dict>
        """

        proof = 0
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        while self.valid_proof(block, difficulty=4) is False:
            proof += 1
            block['proof'] = proof

        return block

    def register_node(self, address: str):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http: 192.168.0.5:5000'
        :return: None
        """
        address = f"http://{address}" if address[:7] != "http://" else address
        if re.findall(r"http://(.*):.*", address)[0] in ['localhost', '0.0.0.0', '127.0.0.1']:
            return False
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
            return True
        else:
            return False

    def resolve_conflicts(self) -> bool:
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            try:
                response = requests.get(f'http://{node}/chain', timeout=0.5)
            except requests.exceptions.Timeout:
                continue

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if len(chain) != length:
                    return False

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    # todo: 添加验证账号和公钥是否匹配的问题
    @staticmethod
    def valid_chain(chain: list) -> bool:
        """
        Determine if a given blockchain is valid
        :param chain: <list> A Blockchain
        :return: <bool> True if valid, False if not
        """

        last_block = chain[0]
        # valid the first block
        # Check that the Proof of world if correct
        if not BlockChain.valid_proof(last_block, 4):
            return False
        # Check that the number of reward transactions
        if len([transaction['sender'] == "0" for transaction in last_block['transactions']]) != 1:
            return False
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            # Check that the Proof of world if correct
            if not BlockChain.valid_proof(block, 4):
                return False

            # Check that the hash of the block if correct
            if block['previous_hash'] != BlockChain.hash(last_block):
                return False

            # Check that the number of reward transactions
            if len([transaction['sender'] == "0" for transaction in last_block['transactions']]) != 1:
                return False

            last_block = block
            current_index += 1

        return True

    @staticmethod
    def hash(block: dict) -> str:
        """
        Create a SHA-256 hash of Block
        :param block: <dict> Block
        :return: <str>
        """
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @staticmethod
    def valid_proof(block: dict, difficulty: int) -> bool:
        """
        Validates the Proof: Does block contain "$difficulty" leading zeroes?
        :param block: <dict>
        :param difficulty: <int> the num of zeros above the block's hash
        :return: <bool> True if correct, False if not.
        """

        sha_256 = BlockChain.hash(block)

        return sha_256[:difficulty] == "0" * difficulty

    def check_transaction(self, transaction):
        trans_uuid = transaction['uuid']
        if transaction in self.current_transactions:
            return False

        for block in self.chain[::-1]:
            for trans in block['transactions']:
                if trans['uuid'] == trans_uuid:
                    return False

        return True
