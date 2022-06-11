from Data import *
from ThreadManager import *
from Web3Manager import *
import js2py
import requests

def strategyFormat(address, gasLimit=0, ignoreCalibrate=False, ignoreRemoval=False, platformABI=None, rewardCalc=None):
    return {
        'address'        : address,
        'gasLimit'       : gasLimit,
        'ignoreCalibrate': ignoreCalibrate,
        'ignoreRemoval'  : ignoreRemoval,
        'platformABI'    : platformABI or 'BeefyStrategy',
        'rewardCalc'     : rewardCalc or 'callReward'
    }

def parseBeefyStrategies(raw=False):
    # Fetch vault data
    r  = requests.get('https://raw.githubusercontent.com/beefyfinance/beefy-app/master/src/features/configure/vault/fantom_pools.js')
    
    # Convert JavaScript array to Python list
    js = js2py.eval_js(r.text[r.text.find('export') + 7:])

    # Convert list to Data
    vaults = Data({f"{i['platform']} {i['name']}" if 'status' in i and i['status'] == 'active' else i['id']: i for i in js}) \
                .removeColumns(['addLiquidityUrl', 'assets', 'buyTokenUrl', 'depositFee', 'depositsPaused', 'earnContractAddress', 'earnedToken',
                                'logo', 'name', 'oracle', 'oracleId', 'oraclePrice', 'pricePerFullShare', 'removeLiquidityUrl', 'token',
                                'tokenAddress', 'tokenDecimals', 'tokenDescriptionUrl', 'tvl', 'withdrawalFee', 'stratType', 'risks'] if not raw else [], False)

    # Fetch strategy addresses
    def fetchStrategyAddress(key, vaultAddress):
        addContract(vaultAddress,
                    vaultAddress,
                    '[{"inputs":[],"name":"strategy","outputs":[{"internalType":"contract IStrategy","name":"","type":"address"}],"stateMutability":"view","type":"function"}]')
        vaults.set(key, 'strategyAddress', getContract(vaultAddress).functions.strategy().call())
    for i in vaults:
        progressBar(vaults.keys.index(i) + 1, len(vaults), 'BEEFY:GetStrategyAddress', i)
        ThreadManager.run(fetchStrategyAddress, i, w3.toChecksumAddress(vaults.get(i, 'earnedTokenAddress')))
    while not all([ThreadManager.killed[i] for i in ThreadManager.killed]):
        sleep(0.01)
    vaults.store('Beefy.json')

    # Delete eol vaults from STRATEGIES
    # ...by checking status
    eol = vaults.filter(status='eol').selectAsList('strategyAddress')
    for strat in STRATEGIES.filter(lambda k, v: v['address'] in eol):
        STRATEGIES.delete(strat)
        log(f'StrategyParser[BEEFY]: Removed[eol] {strat}')
    
    # ...by checking active strategy of referenced vault
##    for key in s.filter(ignoreRemoval=False, platformABI='BeefyStrategy').keys:
##        progressBar(s.keys.index(key) + 1, len(s), 'CheckActive', key)
##        sAddress = s.get(key, 'address')
##
##        # sAddress is not the active address of any vault derived from Beefy.json
##        if sAddress not in vaults.selectUnique('strategyAddress'):
##            loadContract('updateBeefyJson', sAddress, 'BeefyStrategy', False)
##            vAddress = contracts.get('updateBeefyJson').functions.vault().call()
##
##            # vAddress not found in vaults
##            if vAddress not in vaults.selectUnique('earnedTokenAddress'):
##                log.set(f'[HiddenVault]{key}', vAddress)
##                addContract(vAddress,
##                            vAddress,
##                            '[{"inputs":[],"name":"strategy","outputs":[{"internalType":"contract IStrategy","name":"","type":"address"}],"stateMutability":"view","type":"function"}]',
##                            False)
##
##            activeSAddress = getContract(vAddress).functions.strategy().call()
##            
##            # sAddress is not the active strategy of its vault
##            if activeSAddress != sAddress:
##                log.set(key, f'Removed [NotActiveOfVault - {activeSAddress}]')
##                s.delete(key)
##            

    # Parse and store strategies with built-in callReward()
    strategyAddresses = STRATEGIES.selectAsList('address')
    for strat in (newStrats := vaults.filter(lambda k, v: v['strategyAddress'] not in strategyAddresses, status=['active', None]).keys):
        progressBar(newStrats.index(strat) + 1, len(newStrats), 'BEEFY:CheckCallReward', strat)
        loadContract(strat, vaults.get(strat, 'strategyAddress'), 'BeefyStrategy')
        try:
            getContract(strat).functions.callReward().call()
            STRATEGIES.set(strat, strategyFormat(vaults.get(strat, 'strategyAddress')))
            log(f'StrategyParser[BEEFY]: added {strat}')
        except:
            pass
    STRATEGIES.store()

def parseReaperStrategies():
    rewardCalcMapping = {
        'bomb'    : 'ReaperBombSwap',
        'popsicle': 'ReaperPopsicle',
        'spooky'  : 'ReaperSpookySwap',
        'spirit'  : 'ReaperSpiritSwap',
        'tomb'    : 'ReaperTomb',
    }
    # Fetch vault data
    r         = requests.get('https://yzo0r3ahok.execute-api.us-east-1.amazonaws.com/dev/api/crypts').json()['data']
    crypts    = Data()
    for crypt in r:
        c = crypt['cryptContent']
        crypts.set(c['name'], {
            'address' : c['strategy']['address'],
            'provider': crypt['provider'],
            'active'  : not c['dead']
        })
        # Not found in Strategies.json AND Crypt not dead AND provider is supported
        if c['name'] not in STRATEGIES and not c['dead'] and crypt['provider'] in rewardCalcMapping:
            STRATEGIES.set(c['name'], strategyFormat(c['strategy']['address'], platformABI='ReaperStrategy', rewardCalc=rewardCalcMapping[crypt['provider']]))
            log(f'StrategyParser[REAPER]: added {c["name"]}')
    crypts.store('Reaper.json')
    STRATEGIES.store()
    
if __name__ == '__main__':
    parseBeefyStrategies()
    parseReaperStrategies()
