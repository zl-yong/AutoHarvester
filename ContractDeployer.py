from Web3Manager import *
from solc import compile_standard

deployGas = int(5e6)

def loadContractFromFile(filepath, contractName):    
    with open(filepath) as f:
        a = ''.join([l for l in f])
    compiled = compile_standard({
	'language': 'Solidity',
	'sources' : {f'{contractName}.sol': {'content': a}},
	'settings': {'outputSelection': {'*': {'*': ['metadata', 'evm.bytecode', 'evm.bytecode.sourceMap']}}}
    })
    return w3.eth.contract(abi=json.loads(compiled['contracts'][f'{contractName}.sol'][f'{contractName}']['metadata'])['output']['abi'],
                           bytecode=compiled['contracts'][f'{contractName}.sol'][f'{contractName}']['evm']['bytecode']['object'])

def deployContract(contract):
    return signAndSend(contract.constructor().buildTransaction({
        'gas'  : deployGas,
        'nonce': w3.eth.getTransactionCount(acct.address)}))

def main():
    if input(f'Deploying RewardCalc with {deployGas} gas. Enter CONFIRM to deploy\n> ') == 'CONFIRM':
        contract = loadContractFromFile('RewardCalcV2.txt', 'RewardCalc')
        txhash   = deployContract(contract)
        while True:
            try:
                receipt = w3.eth.getTransactionReceipt(txhash)
                CONFIG.set('AutoHarvester', 'rewardCalcAddress', receipt['contractAddress']).store()
                FileData('ABI.json').set('RewardCalc', json.dumps(contract.abi)).store()
                break
            except:
                pass

if __name__ == '__main__':
    main()
