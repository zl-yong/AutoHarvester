from Data import *
from web3 import Web3, HTTPProvider, exceptions as Web3Exceptions
import requests

config  = CONFIG.get('Web3Manager')
w3      = Web3(Web3.HTTPProvider(config['rpcURL']))
acct    = w3.eth.account.from_key(CONFIG.get('privateKey'))
wrapped = config['wrappedNative']
######################################## Contracts ########################################
contracts = Data()

def addContract(identifier, address, abi, onlyNew=True):
    assert not onlyNew or identifier not in contracts.get(), f'Web3Manager::addContract: (error) contract with identifier "{identifier}" already exists'
    contracts.set(identifier, (a := w3.eth.contract(address, abi=abi)))
    return a

def loadAbi(identifier):
    return FileData('ABI.json').get(identifier)

def loadContract(identifier, address, abiID, onlyNew=True):
    return addContract(identifier, address, loadAbi(abiID), onlyNew)

def getContract(identifier):
    return contracts.get(identifier)

# Initialize useful contracts
loadContract(wrapped, config['wrappedNativeAddress'], 'WrappedNative')

######################################## Miscellaneous ########################################
def abiStrip(abi, wantFunctions, toStr=True):
    abi = [i for i in json.loads(abi) if 'name' in i and i['name'] in wantFunctions]
    return json.dumps(abi) if toStr else abi

def getNonce():
    return w3.eth.getTransactionCount(acct.address)

def signAndSend(unsignedTx):
    return w3.eth.sendRawTransaction(w3.eth.account.sign_transaction(unsignedTx,acct.privateKey).rawTransaction).hex()

def balance():
    return (w3.eth.get_balance(acct.address) + getContract(wrapped).functions.balanceOf(acct.address).call()) / 1e18

def unwrapNative(nonce=None):
    return signAndSend(getContract(wrapped).functions.withdraw(getContract(wrapped).functions.balanceOf(acct.address).call()).buildTransaction({
        'gas'  : int(5e4),
        'nonce': nonce or w3.eth.getTransactionCount(acct.address)
    }))

def waitForTransactionReceipt(txhash):
    try:
        return w3.eth.wait_for_transaction_receipt(txhash, timeout=3600)
    except Web3Exceptions.TimeExhausted:
        pass

