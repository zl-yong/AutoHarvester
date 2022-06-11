from Data import *
from ThreadManager import *
from Utils import *
from Web3Manager import *
import requests

def mode(array):
    d = dict()
    for i in array:
        try:
            d[i] += 1
        except:
            d[i] = 1
    m = [0, 0]
    for i in d:
        if d[i] > m[1]:
            m = [i, d[i]]
    return m[0]

config      = Data(CONFIG.get('StrategyCalibrator'))
alias       = Data(config.get('alias'))
##toCalibrate = STRATEGIES.filter(ignoreCalibrate=False).keys
toCalibrate = STRATEGIES.filter(lambda k, v: str(v['gasLimit'])[-2:] != '00', ignoreCalibrate=False).keys
t           = Data()

# Returns (lastHarvestProfit, lastHarvestTime, lastHarvester, lastHarvestGasUsed, arrayOfGasUsed)
def getLastProfit(address):
    events        = requests.get(f'{CONFIG.get("blockExplorerAPIURL")}?module=account&action=txlist&address={address}&sort=desc&apikey={CONFIG.get("blockExplorerAPIKey")}')     
    inputToCheck  = '0xd389800f' if STRATEGIES.filter(address=address).selectUnique('platformABI') == ['EsterStrategy'] else '0x4641257d'
    result        = list(filter(lambda x: x['input'] == inputToCheck, events.json()['result']))
    lastHarvester = w3.eth.getTransactionReceipt(result[0]['hash'])['from'] if len(result) else '-'
    for i in result[:config.get('checkNLastHarvests')]:
        if (time() - int(i['timeStamp'])) / 86400 >= config.get('ignoreDayThreshold'):
            break
        receipt = w3.eth.getTransactionReceipt(i['hash'])
        sender  = receipt['from']
        for j in list(filter(lambda x: x['address'] == CONFIG.get('Web3Manager', 'wrappedNativeAddress'), receipt['logs'])):
            if j['topics'][0].hex() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef' and w3.toChecksumAddress('0x' + j['topics'][2].hex()[-40:]) == sender:
                profit = int(j['data'], 16) / 1e18 - receipt['gasUsed'] * int(i['gasPrice']) / 1e18
                if profit < 0:
                    break
                return (profit,
                        getTime(int(i['timeStamp'])),
                        sender,
                        int(i['gasUsed']),
                        [int(i['gasUsed']) for i in result])
    return (0, '-', lastHarvester, 0, [0])

def adjustGas(identifier, gasArray):
    return max(gasArray)

def update(strats):
    for i in strats:
        try:
            profit = getLastProfit(STRATEGIES.get(i, 'address'))
            # Set gasLimit of strategy to most frequent gas used
            STRATEGIES.set(i, 'gasLimit', adjustGas(i, profit[4]))
            t.set(i, {'lastHarvest'      : profit[1],
                      'lastHarvestProfit': f'{profit[0]:.8f}',
                      'harvester'        : alias.get(profit[2]) or profit[2],
                      'gasLimit'         : STRATEGIES.get(i, 'gasLimit'),
                      'lastHarvestGas'   : profit[3]})
        except Exception as e:
            t.set(i, {'lastHarvest'      : '',
                      'lastHarvestProfit': '',
                      'harvester'        : str(e),
                      'gasLimit'         : '',
                      'lastHarvestGas'   : ''})

if __name__ == '__main__':
    print('Note: toCalibrate ignores gasLimit that ends with 00 - most likely user modified')
    try:
        for i in group(toCalibrate, 2):
            ThreadManager.run(update, i)
        while not all([ThreadManager.killed[i] for i in ThreadManager.killed]):
            progressBar(len(t), len(toCalibrate), 'Calibrating')
        STRATEGIES.store()
        (t.store('StrategyCalibrator.json')
          .exportTable('StrategyCalibrator', alignments=['left'] * 3 + ['right'] * 2, indexLabel='strategy', filepath='StrategyCalibrator.txt'))
    except Exception as e:
        input(str(e))
    
