# -*- coding: utf-8 -*-
# @Time    : 2021/3/30 15:11
# @Author  : LTstrange
import requests
from Blockchain import BlockChain
from flask import Flask, jsonify, request, render_template

# Instantiate our Node
app = Flask(__name__)

# Instantiate the Blockchain
blockchain = BlockChain()


# GUI part
@app.route('/', methods=['POST', 'GET'])
def index():
    blockchain.host = request.host
    blockchain.register_node(blockchain.host)
    if request.method == 'GET':
        return render_template('index.html', host=blockchain.host, identifier=blockchain.node_identifier)


@app.route('/login')
def login():
    return "Login Page", 200


@app.route('/manual/new_transaction', methods=['POST'])
def new_transaction_manually():
    transaction = request.form

    # Create a new Transaction
    if blockchain.new_transaction(transaction):
        response = {'message': f'Transaction Submitted!'}

        return jsonify(response), 201
    else:
        return "Invalid transaction", 400


@app.route('/manual/Set_node', methods=['POST'])
def set_node_manually():
    ip = request.form
    host = ip['host']
    port = ip['port']

    address = f"{host}:{port}"
    if blockchain.register_node(address):
        self_nodes = {
            'nodes': list(blockchain.nodes),
        }
        try:
            requests.post(f"http://{address}/sync_nodes", json=self_nodes, timeout=0.5).json()
        except requests.exceptions.Timeout:
            pass
        response = {
            'message': 'New nodes have been added',
            'new_node': address,
            'total_nodes': list(blockchain.nodes),
        }
    else:
        response = {
            'message': 'New nodes is INVALID.',
            'new_node': address,
            'total_nodes': list(blockchain.nodes),
        }
    return jsonify(response), 201


@app.route('/get_nodes', methods=['GET'])
def get_nodes():
    return render_template("Nodes.html", nodes=blockchain.nodes), 201


# API part
@app.route('/mine', methods=['GET'])
def mine():
    # Forge the new Block
    block = blockchain.new_block()

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transaction': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
        'block_hash': BlockChain.hash(block)
    }

    for node in blockchain.nodes:
        if node == blockchain.host:
            continue
        try:
            requests.get(f"http://{node}/nodes/resolve", timeout=0.5)
        except requests.exceptions.Timeout:
            continue

    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def add_transactions():
    values = request.get_json()

    if 'transactions' in values.keys():
        valid_transactions = []
        for ind, transaction in enumerate(values['transactions']):
            # Create a new Transaction
            if blockchain.new_transaction(transaction):
                valid_transactions.append(transaction)
        # if block_index is None, means all transactions is invalid
        if len(valid_transactions):
            response = {'message': f'Following Transactions will be added to Block {len(blockchain) + 1}',
                        'transactions': valid_transactions}
            return jsonify(response), 201

    return 'Invalid transactions', 400


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain),
    }

    return jsonify(response), 200


@app.route('/sync_nodes', methods=['POST'])
def set_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if not nodes:
        return 'Missing Nodes', 400
    for node in nodes:
        blockchain.register_node(node)

    response = {
        'total_nodes': list(blockchain.nodes),
    }

    return jsonify(response), 201


@app.route('/nodes/Search', methods=['GET'])
def search_nodes():
    add_nodes = set()
    self_nodes = {
        'nodes': list(blockchain.nodes),
    }
    for node in blockchain.nodes:
        if node == blockchain.host:
            continue
        try:
            resp = requests.post(f"http://{node}/sync_nodes", json=self_nodes, timeout=0.5).json()
            nodes = resp['total_nodes']
            add_nodes.update(nodes)
        except requests.exceptions.ConnectionError:
            pass
    for node in add_nodes:
        blockchain.register_node(node)
    response = {
        "add_nodes": list(add_nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain,
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain,
        }

    return jsonify(response), 200
