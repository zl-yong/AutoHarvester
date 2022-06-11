AutoHarvester
-------------
This program calls harvest() on Beefy.Finance strategies on the Fantom blockchain when it is profitable to do so


Main scripts
------------
AutoHarvester.pyw
- Main program - run this to start the monitoring of strategies

StrategyParser.py
- Fetches strategies from Beefy.finance's github and adding to the strategies pool to be monitored

StrategyCalibrator.py
- Uses FTMScan's API to check for previous harvest's statistics to find the suitable gas limit for a given strategy