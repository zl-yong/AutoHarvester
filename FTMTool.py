from tkinter import *
from tkinter import ttk, simpledialog
from Data import *
import webbrowser

def OnOpenFTMScanClicked(*args):
    address = STRATEGIES.get(strategy.get(), 'address')
    if address:
        webbrowser.open_new_tab('https://ftmscan.com/address/' + address)

def OnModifyGasLimitClicked(*args):
    strat = strategy.get()
    while True:
        newLimit = simpledialog.askstring('',f'Current limit is {STRATEGIES.get(strat, "gasLimit")}\nEnter new gas limit for {strat}:')
        if not newLimit:
            return
        try:
            STRATEGIES.set(strat, 'gasLimit', int(newLimit)).store()
            break
        except:
              pass  

root = Tk()
root.title("QuickOpenFTMScan")
root.option_add('*tearOff', FALSE)

mainframe = ttk.Frame(root)
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))

strategy = ttk.Entry(mainframe, width=50)
strategy.grid(column=2, row=1, sticky=W)
ttk.Label(mainframe, text='Strategy name:').grid(column=1, row=1, sticky=E)

ttk.Button(mainframe, text='Open FTMScan', command=OnOpenFTMScanClicked).grid(column=1, row=2)
ttk.Button(mainframe, text='Modify gas limit', command=OnModifyGasLimitClicked).grid(column=2, row=2)

for child in mainframe.winfo_children(): 
    child.grid_configure(padx=10, pady=10)

strategy.focus()
root.mainloop()
