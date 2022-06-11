from Data import *
from ThreadManager import ThreadManager, Timeout, setTimeout
from Utils import getTime
from Web3Manager import *
from os import stat, _exit
from threading import Lock
from time import sleep
from tkinter import Tk, Frame, Menu, Scrollbar, Label, Entry, Button, Menu, Toplevel, DoubleVar, IntVar, StringVar, ttk, simpledialog, BooleanVar
import webbrowser

#################### Thread-safe class counters ####################
class Nonce:
    __value = w3.eth.getTransactionCount(acct.address)
    __lock  = Lock()
    
    def getAndIncrement():
        with Nonce.__lock:
            Nonce.__value += 1
            return Nonce.__value - 1

class SessionProfit:
    var = None
    __lock  = Lock()
    
    def init(mainframe):
        SessionProfit.var = DoubleVar(mainframe)
        return SessionProfit.var
        
    def add(value):
        with SessionProfit.__lock:
            SessionProfit.var.set(round(SessionProfit.var.get() + value, 8))

#################### Setup ####################
config  = Data(CONFIG.get('AutoHarvester'))
runtime = Data({
    '_gasPriceMultiplier': None,
    '_gasPrice'          : None,
    '_log'               : {},
    '_autoScroll'        : None,
    '_paused'            : None,
    '_toLog'             : {}
})
rewardCalc        = loadContract('RewardCalc', config.get('rewardCalcAddress'), 'RewardCalc')
isDebugMode       = config.get('debug')
allowZeroGasLimit = config.get('allowZeroGasLimit')

#################### Misc ####################
def ExceptionHandler(function):
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            insert(f'ExceptionHandler', function.__qualname__, 'Error', additional={'type': 'exception', 'exceptionType': str(type(e)), 'exceptionMsg': str(e)})
    return wrapper

def startMonitor(identifier):
    runtime.set(identifier, {'lastHarvest': 0})
    ThreadManager.run(loadContract, f'{identifier}[harvest]', STRATEGIES.get(identifier, 'address'), STRATEGIES.get(identifier, 'platformABI'), onlyNew=False, threadID=f'{identifier}[harvest]')
    ThreadManager.run(monitor, identifier, threadID=identifier, loopDelay=0)

#################### Threaded jobs ####################
def job_GasPriceUpdater():
    gasVar    = runtime.get('_gasPrice')
    pausedVar = runtime.get('_paused')
    gasVar.set(w3.eth.gasPrice * runtime.get('_gasPriceMultiplier').get() / 1e9)
    shouldPause = gasVar.get() >= config.get('pauseHarvestOnHighGasPriceThreshold')
    if str(shouldPause) != pausedVar.get() and runtime.get('_toLog', 'GasPriceUpdater').get():
        insert('GasPriceUpdater', gasVar.get(), 'Paused' if shouldPause else 'Unpaused')
    pausedVar.set(str(shouldPause))

def job_NativeUnwrapper():
    if w3.eth.getBalance(acct.address) / 1e18 <= config.get('unwrapThreshold'):
        txhash  = unwrapNative(Nonce.getAndIncrement())
        iid = insert('NativeUnwrapper', '-', 'Pending', additional={'type': 'unwrap', 'txhash': txhash})
        while True:
            try:
                w3.eth.getTransactionReceipt(txhash)
            except:
                pass
        update(iid, 'NativeUnwrapper', '-', 'Success', additional={'type': 'unwrap', 'txhash': txhash})

strategiesLastMTime = stat(STRATEGIES.filepath).st_mtime
def job_StrategiesRefresher():
    global strategiesLastMTime
    if stat(STRATEGIES.filepath).st_mtime != strategiesLastMTime:
        strategiesLastMTime = stat(STRATEGIES.filepath).st_mtime
        STRATEGIES.load()
        insert('StrategiesRefresher', '-', '-')

def job_DebugThreadExceptions():
    if ThreadManager.exceptions:
        insert('DebugThreadExceptions', '-', 'Error', additional={'type': 'debug', 'extra': str(ThreadManager.exceptions)})
        ThreadManager.exceptions = {}
        
def job_Blink():
    o = tree.tag_configure('pending')
    tree.tag_configure('pending', foreground=o['background'], background=o['foreground'])        
#################### Onclick - show details ####################
def OnMonitorClicked():
    def OnStartMonitorClicked():
        identifier = var.get()
        if identifier in STRATEGIES and (identifier not in ThreadManager.killed or ThreadManager.killed[identifier]):
            startMonitor(identifier)
            insert('OnMonitorClicked', identifier, 'Info')
        window.destroy()
    window = Toplevel(mainframe, name='monitor')
    window.title('Start monitor')
    var = StringVar()
    Entry(window, textvariable=var, width=50).grid(column=1, row=0, sticky='w')
    Label(window, text='Identifier').grid(column=0, row=0, sticky='e')
    Button(window, text='Start monitor', command=OnStartMonitorClicked).grid(column=1, row=1, sticky='e')

def OnToggleAutoScrollClicked():
    runtime.get('_autoScroll').set('False' if runtime.get('_autoScroll').get() == 'True' else 'True')

def OnEditGasPriceMultiplierClicked():
    if (newMult := simpledialog.askfloat('Modify gas price multiplier', 'Enter new gas price multiplier')):
        runtime.get('_gasPriceMultiplier').set(newMult)
        job_GasPriceUpdater()
      
def OnDoubleClickedTree():
    row  = tree.identify_row(mainframe.winfo_pointery() - tree.winfo_rooty())
    info = runtime.get('_log', row)
    if info:
        func = {
            'exception': createExceptionDetailsWindow,
            'harvest': createHarvestDetailsWindow
        }
        (func[info['type']] if info['type'] in func else createGenericDetailsWindow)(tree.set(row), info)

def createDetailsWindow(title):
    window = Toplevel(mainframe, name='details')
    window.title(title)
    window.geometry(f'+{int((window.winfo_screenwidth() - window.winfo_reqwidth()) / 2)}+{int((window.winfo_screenheight() - window.winfo_reqheight()) / 2)}')
    return window
    
def createHarvestDetailsWindow(treeData, additionalInfo):
    window = createDetailsWindow('Harvest Details')
    labels = createLabels(window, {
        'Start timestamp': treeData['Timestamp'],
        'End timestamp'  : additionalInfo['endTimestamp'],
        'Strategy'       : treeData['Identifier'],
        'Gas price'      : f'{additionalInfo["gasPrice"] / 1e9:.8f}',
        'Txhash'         : additionalInfo['txhash'],
        'Nonce'          : additionalInfo['nonce'],
        'Profit'         : f'{additionalInfo["profit"]:.8f}',
        'Status'         : treeData['Status']
    })
    # Hyperlinks to view strategy address and transaction information
    labels['Strategy'].configure(fg='blue')
    labels['Strategy'].bind('<Button-1>', lambda _: webbrowser.open_new_tab(f'{CONFIG.get("blockExplorerURL")}address/{STRATEGIES.get(treeData["Identifier"], "address")}'))
    labels['Txhash'].configure(fg='blue')
    labels['Txhash'].bind('<Button-1>', lambda _: webbrowser.open_new_tab(f'{CONFIG.get("blockExplorerURL")}tx/{additionalInfo["txhash"]}'))

def createExceptionDetailsWindow(treeData, additionalInfo):
    window = createDetailsWindow('Exception Details')
    createLabels(window, {
        'Timestamp'        : treeData['Timestamp'],
        'Identifier'       : treeData['Identifier'],
        'Exception type'   : additionalInfo['exceptionType'],
        'Exception message': additionalInfo['exceptionMsg']
    })

def createGenericDetailsWindow(treeData, additionalInfo):
    window = createDetailsWindow('Generic Details')
    createLabels(window, {
        'Type'      : additionalInfo['type'],
        'Timestamp' : treeData['Timestamp'],
        'Identifier': treeData['Identifier'],
        'Details'   : additionalInfo
    })
    
#################### Tree display ####################
def insert(*args, additional={}):
    assert len(args) == 3, f'insert: invalid args {args}'
    iid = tree.insert('', 'end', values=(getTime(), *args), tags=(args[-1].lower() if args[-1].lower() in ['success', 'failed', 'info', 'error', 'pending'] else 'info',))
    if runtime.get('_autoScroll').get() == 'True':
        tree.yview_moveto(1)
    runtime.set('_log', iid, additional)
    return iid

def update(iid, *args, additional={}):
    assert len(args) == 3, f'update: invalid args {args}'
    tree.item(iid, values=(tree.set(iid)['Timestamp'], *args), tags=(args[-1].lower() if args[-1].lower() in ['success', 'failed', 'info', 'error', 'pending'] else 'info',))
    runtime.set('_log', iid, additional)

def createLabels(window, labelAndText, rowCount=None):
    rowCount = rowCount or len(labelAndText)
    labels   = {}
    for idx, i in enumerate(labelAndText):
        Label(window, text=f'{i}:').grid(row=idx % rowCount, column=idx // rowCount * 2, sticky='e', padx=5, pady=5)
        labels[i] = Label(window, text=labelAndText[i])
        labels[i].grid(row=idx % rowCount, column=idx // rowCount * 2 + 1, sticky='w', padx=5, pady=5)
    return labels



#################### Harvester ####################
def getProfitOfTransaction(txReceipt, gasPrice):
    gasUsed = txReceipt['gasUsed']
    profit  = -gasUsed * gasPrice / 1e18
            
    # Get actual profit by checking for wrapped native transfers to self
    for j in filter(lambda x: x['address'] == getContract(wrapped).address, txReceipt['logs']):
        if ((j['topics'][0].hex() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef' \
             and w3.toChecksumAddress('0x' + j['topics'][2].hex()[-40:]) == acct.address)):
            profit += int(j['data'], 16) / 1e18 
            break
    return profit

def harvest(identifier):
    strategy = STRATEGIES.get(identifier)
    function = getContract(f'{identifier}[harvest]').functions.harvest()
    if strategy['platformABI'] not in ['BeefyStrategy', 'ReaperStrategy']:
        insert('Harvest', identifier, 'Warning', additional={'type': 'warning', 'msg': 'Invalid platformABI'})

    usedNonce    = Nonce.getAndIncrement()
    usedGasPrice = runtime.get('_gasPrice').get() * 1e9
    # If harvest no longer profitable, return
    if runtime.get(identifier, 'expectedRewards') < strategy['gasLimit'] * usedGasPrice:
        return
    try:
        harvestData = {'type': 'harvest', 'gasPrice': usedGasPrice, 'profit': 0, 'endTimestamp': '?', 'nonce': usedNonce}
        harvestData['txhash'] = signAndSend(function.buildTransaction({
            'gas'     : min(strategy['gasLimit'] * 2, 8_000_000),
            'gasPrice': int(usedGasPrice),
            'nonce'   : usedNonce
        }))
    except ValueError as e:
        # Transaction likely underpriced, return
        # If NOT transaction underpriced, show error
        if e.args[0]['message'] != 'transaction underpriced':
            insert('Harvest', identifier, 'Cancelled', additional={'type': 'info', 'msg': f'harvest cancelled - {e}, nonce: {usedNonce}'})
        return
    iid = insert('Harvest', identifier, 'Pending', additional=harvestData)

    # Wait for transaction to be mined
    receipt = None
    while True:
        try:
            receipt = receipt or setTimeout(waitForTransactionReceipt, config.get('maxHarvestPending'), harvestData['txhash'], threadID=f'{identifier}[harvest-timeout]')
            profit  = getProfitOfTransaction(receipt, usedGasPrice)
            if receipt['gasUsed'] > strategy['gasLimit'] and profit < 0:
                insert('Harvest', identifier, 'Info', additional={'type': 'info', 'msg': f'gasLimit should be raised from {strategy["gasLimit"]} to {receipt["gasUsed"]}'})
            status = 'Success' if profit > 0 else 'Failed'
            SessionProfit.add(profit)
            harvestData.update({'profit': profit, 'endTimestamp': getTime()})
            update(iid, 'Harvest', identifier, status, additional=harvestData)
            if profit < 0:
                insert('Harvest[TEMP]', identifier, 'Info', additional={'type': 'info', 'msg': f'set limit to at least {-profit * 1e18 / usedGasPrice + strategy["gasLimit"]:.0f}'})
            if profit <= -receipt['gasUsed'] * usedGasPrice / 1e18 * 0.95:
                insert('Harvest[TEMP]', identifier, 'Info', additional={'type': 'info', 'msg': f'severe loss - disabling strategy'})
                strategy['gasLimit'] = 0
            break
        except Timeout:
            # Transaction still pending after n seconds, increase gasPriceMultiplier and cancel harvest
            runtime.get('_gasPriceMultiplier').set(round(runtime.get('_gasPriceMultiplier').get() + 0.01, 2))
            if (receipt := cancelHarvest(identifier, usedNonce, iid, harvestData)):
                continue
            break

def startHarvest(identifier):
    harvest(identifier)
    runtime.set(identifier, 'lastHarvest', time())

def cancelHarvest(identifier, nonce, iid, harvestData):
    cancelData = {'type': 'harvest', 'gasPrice': harvestData['gasPrice'] * 1.1, 'profit': 0, 'endTimestamp': '?', 'txhash': '?', 'nonce': nonce}
    try:
        cancelData['txhash'] = signAndSend({
            'gas': 21000,
            'to': acct.address,
            'nonce': nonce,
            'gasPrice': int(cancelData['gasPrice']),
            'chainId': CONFIG.get('chainId')
        })
        update(iid, 'CancelHarvest', identifier, 'Pending', additional=cancelData)
        while True:
            try:
                receipt = w3.eth.getTransactionReceipt(cancelData['txhash'])
                cancelData.update({'profit': -cancelData['gasPrice'] * 21000 / 1e18, 'endTimestamp': getTime()})
                SessionProfit.add(cancelData['profit'])
                update(iid, 'CancelHarvest', identifier, 'Success', additional=cancelData)
                return
            except Web3Exceptions.TransactionNotFound:
                try:
                    # Harvest transaction completed, return back to harvest() for display()
                    return w3.eth.getTransactionReceipt(harvestData['txhash'])
                except Web3Exceptions.TransactionNotFound:
                    pass
    except Exception as e:
        if e.args[0]['message'] == 'nonce too low':
            # Attempts multiple times to get harvest receipt, as "nonce too low" most likely indicates harvest complete
            for _ in range(10):
                try:
                    # Harvest transaction completed, return back to harvest() for display()
                    return w3.eth.getTransactionReceipt(harvestData['txhash'])
                except Web3Exceptions.TransactionNotFound:
                    sleep(1)
            insert('CancelHarvest', identifier, 'Error', additional={'type': 'exception', 'exceptionType': str(type(e)), 'exceptionMsg': 'Matched nonce too low'})
        cancelData.update({'txhash': harvestData['txhash'], 'endTimestamp': getTime()})
        update(iid, 'CancelHarvest', identifier, 'Failed', additional=cancelData)
        insert('CancelHarvest', identifier, 'Error', additional={'type': 'exception', 'exceptionType': str(type(e)), 'exceptionMsg': str(e) + str(e.args)})

def getProgress(identifier):
    strategy = STRATEGIES.get(identifier)    
    try:
        gasLimit = max(strategy['gasLimit'], getContract(f'{identifier}[harvest]').functions.harvest().estimateGas({'from': acct.address}))
        if strategy['rewardCalc'] == 'callReward':
            rewards = getContract(f'{identifier}[harvest]').functions.callReward().call() 
        else:
            rewards = eval(f'rewardCalc.functions.{strategy["rewardCalc"]}("{strategy["address"]}").call()')
        runtime.set(identifier, 'expectedRewards', rewards)
        return rewards / (runtime.get('_gasPrice').get() * 1e9 * gasLimit) * 100
    except:
        return 0

def monitor(identifier):
    if not STRATEGIES.get(identifier, 'gasLimit') and not allowZeroGasLimit:
        ThreadManager.kill(identifier)
        insert('Monitor', identifier, 'Info', additional={'type': 'info', 'msg': 'monitor terminated'})
        return
    progress = getProgress(identifier)
    # TEMP - check last seen gas limit
    lastProgress = runtime.get(identifier, 'TEMPlastProgress')
    # If last progress is more than current by 70%, and current is less than 5%, and not harvested within timeframe by me, means harvested by others
    if lastProgress and lastProgress > progress + 70 and progress < 5 and time() - runtime.get(identifier, 'lastHarvest') > config.get('minTimeBetweenHarvests') and runtime.get('_toLog', 'Monitor[LastProgress]').get():
        impliedLimit = int(lastProgress / 100 * STRATEGIES.get(identifier, 'gasLimit'))
        insert('Monitor', identifier, 'Info', additional={'type': 'info', 'msg': f'last seen at {lastProgress:.2f}% -> gaslimit of {impliedLimit} ({impliedLimit - STRATEGIES.get(identifier, "gasLimit")})'})
    runtime.set(identifier, 'TEMPlastProgress', progress)
    if (not isDebugMode and
        progress >= 100 and
        not runtime.get('_paused').get() == 'True' and
        time() - runtime.get(identifier, 'lastHarvest') >= config.get('minTimeBetweenHarvests')):
        startHarvest(identifier)
    elif progress < config.get('noDelayThreshold'):
        sleep(config.get('delay'))

def OnClose():
    mainframe.destroy()
    _exit(0)

def setupThreads():
    ThreadManager.run(job_Blink, loopDelay=0.5, threadID='job_Blink')
    ThreadManager.run(job_GasPriceUpdater, loopDelay=5, threadID='job_GasPriceUpdater')
    ThreadManager.run(job_NativeUnwrapper, loopDelay=10, threadID='job_NativeUnwrapper')
    ThreadManager.run(job_StrategiesRefresher, loopDelay=1, threadID='job_StrategiesRefresher')
    ThreadManager.run(job_DebugThreadExceptions, loopDelay=1, threadID='job_DebugThreadExceptions')
    toMonitor = STRATEGIES.filter(lambda k, v: (allowZeroGasLimit or v['gasLimit']) and v['gasLimit'] != -1)
    insert('Startup', '-', '-', additional={'type': 'info', 'msg': f'strategies count: {len(toMonitor)} ({len(toMonitor) / len(STRATEGIES) * 100:.2f}%)'})
    # Display all things from TODO.txt
    with open('TODO.txt') as f:
        for l in f:
            insert('Main[TODO]', '-', 'Info', additional={'type': 'info', 'msg': l.strip()})
    for identifier in toMonitor:
        startMonitor(identifier)        
    STRATEGIES.exportTable('Strategies', indexLabel='strategy', filepath='Strategies.txt')
    
def main():
    global mainframe, tree

    # Tkinter mainframe
    mainframe = Tk()
    mainframe.title('AutoHarvesterGUI')
    mainframe.geometry(f'+{int((mainframe.winfo_screenwidth() - mainframe.winfo_reqwidth()) / 2)}+{int((mainframe.winfo_screenheight() - mainframe.winfo_reqheight()) / 2)}')
    runtime.set('_gasPrice', DoubleVar(mainframe))
    runtime.set('_paused', StringVar(mainframe, 'True'))
    runtime.set('_autoScroll', StringVar(mainframe, 'True'))
    runtime.set('_gasPriceMultiplier', DoubleVar(mainframe, config.get('gasPriceMultiplier')))
    labels = createLabels(mainframe, {'Gas price': '-', 'Gas price multiplier': '-', 'Session profit': '-', 'Debug mode': str(isDebugMode), 'Paused': '-', 'AutoScroll': '-'}, rowCount=3)
    labels['Gas price'].configure(textvariable=runtime.get('_gasPrice'))
    labels['Gas price multiplier'].configure(textvariable=runtime.get('_gasPriceMultiplier'))
    labels['Session profit'].configure(textvariable=SessionProfit.init(mainframe))
    labels['Paused'].configure(textvariable=runtime.get('_paused'))
    labels['AutoScroll'].configure(textvariable=runtime.get('_autoScroll'))
    
    # Menu
    menubar  = Menu(mainframe)
    logsMenu = Menu(menubar, tearoff=False)
    runtime.set('_toLog', 'GasPriceUpdater', BooleanVar(value=True))
    runtime.set('_toLog', 'Monitor[LastProgress]', BooleanVar(value=True))
    for setting in runtime.get('_toLog'):
        logsMenu.add_checkbutton(label=setting, onvalue=True, offvalue=False, variable=runtime.get('_toLog', setting))
    menubar.add_cascade(label='Logs', menu=logsMenu)
    menubar.add_cascade(label='Monitor', command=OnMonitorClicked)
    menubar.add_cascade(label='Toggle AutoScroll', command=OnToggleAutoScrollClicked)
    menubar.add_cascade(label='Modify gas price multiplier', command=OnEditGasPriceMultiplierClicked)
    mainframe.config(menu=menubar)

    # Tabs
    tabControl    = ttk.Notebook(mainframe)    
    logsFrame     = Frame(tabControl)
    progressFrame = Frame(tabControl)
    Label(progressFrame, text='Unimplemented').pack()
    tabControl.add(logsFrame, text='Logs')
    tabControl.add(progressFrame, text='Progress')
    tabControl.grid(row=3, column=0, columnspan=4)

    #################### Logs tab ####################
    # Scrollbars
    yScroll = Scrollbar(logsFrame)
    yScroll.pack(side='right', fill='y')

    xScroll = Scrollbar(logsFrame, orient='horizontal')
    xScroll.pack(side='bottom', fill='x')

    tree = ttk.Treeview(logsFrame, yscrollcommand=yScroll.set, xscrollcommand=xScroll.set)
    tree.pack()

    yScroll.config(command=tree.yview)
    xScroll.config(command=tree.xview)

    # Columns & Headings
    tree['columns'] = ('Timestamp', 'Action', 'Identifier', 'Status')
    tree.column("#0", width=0, stretch=0)

    for col in tree['columns']:
        tree.heading(col, text=col, anchor='center')

    tree.column("Timestamp", anchor='center', width=120, minwidth=120)
    tree.column("Action", anchor='w', width=120, minwidth=120)
    tree.column("Identifier", anchor='w', width=150, minwidth=150)
    tree.column("Status", anchor='center', width=120, minwidth=120)
    tree.pack()
    tree.bind('<Double-1>', func=lambda _: OnDoubleClickedTree())
    tree.bind('<Button-3>', func=lambda event: print('Right-clicked'))

    tree.tag_configure('success', foreground='black', background='#00FF00')
    tree.tag_configure('failed', foreground='black', background='red')
    tree.tag_configure('info', foreground='blue', background='white')
    tree.tag_configure('error', foreground='red', background='white')
    tree.tag_configure('pending', foreground='black', background='white')
    
    mainframe.bind('<Escape>', lambda event: print('Escaped'))
    mainframe.protocol("WM_DELETE_WINDOW", OnClose)
    mainframe.resizable(False, False)
    ThreadManager.run(setupThreads)
    mainframe.mainloop()

if __name__ == '__main__':
    main()
