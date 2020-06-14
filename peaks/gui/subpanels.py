'''
Implementation of classes derived from wx controls and specific subpanels
of the application.
'''

# GENERAL MODULES
from pubsub import pub
import asyncio
import os

# WXPYTHON MODULES
import wx
from wxmplot import PlotPanel

# NAMESPACE MODULES
from peaks.data.data_helpers import Trace
from peaks.data.ds import DataSource
from peaks.data.spec import Spectrum
from .dialogs import *
from .popups import *

class SubPanel():
    '''
    Superclass for panels in the application that implement their own widgets. Derived
    classes implement InitUI and other functions.
    '''

    def __init__(self, parent, datasrc):
        '''
        Initializer for the SubPanel class. Parent must be a pointer
        to either a panel or a window.
        '''
        super(SubPanel, self).__init__()
        self.parent = parent
        self.panel = wx.Panel(self.parent)
        self.datasrc = datasrc
        self.InitUI()

    def InitUI(self):
        '''
        Unimplemented functions as a placeholder for custom widgets
        defined by derived classes.
        '''
        raise NotImplementedError(
            "InitUI must be defined for all derived subpanels"
        )

    def GetPanel(self):
        '''
        Return a pointer to the panel (i.e. the widget container) for this
        SubPanel.
        '''
        return self.panel


class CatalogTab(SubPanel):
    '''
    Implements a window for viewing files in the current working directory
    and a file selection control for changing the working directory.
    '''

    def __init__(self, parent, datasrc):
        super(CatalogTab, self).__init__(parent, datasrc)

    def InitUI(self):
        '''
        Create widgets.
        '''
        vsizer = wx.BoxSizer(wx.VERTICAL)

        # View for files in the current working directory
        self.tree = wx.GenericDirCtrl(self.panel, dir=os.getcwd())
        self.tree.Bind(wx.EVT_DIRCTRL_FILEACTIVATED, self.OnDblClick)
        vsizer.Add(self.tree, 1, wx.EXPAND)

        self.panel.SetSizer(vsizer)

    def OnDblClick(self, event):
        '''
        Event handler for double clicking on an item in the file
        window.
        '''
        act_item = event.GetItem()
        if not self.tree.GetTreeCtrl().GetChildrenCount(act_item) > 0:
            # The item is a leaf, try and load it.
            abspath = self.tree.GetPath(act_item)
            dialog_data = {
                'path': abspath
            }
            pub.sendMessage('Dialog.Run', D=DialogLoad,
                            data=dialog_data)


class DataTab(SubPanel):
    '''
    Implements UI elements for the trace window on the right hand side
    of the screen.
    '''

    def __init__(self, parent, datasrc):
        self.btns = []
        super(DataTab, self).__init__(parent, datasrc)

        pub.subscribe(self.AddTrace, 'UI.Tree.AddTrace')

    def InitUI(self):
        '''
        Create widgets.
        '''
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # Create the root nodes in the tree
        self.tree = wx.TreeCtrl(
            self.panel,
            style=wx.TR_DEFAULT_STYLE
        )
        root = self.tree.AddRoot("Project")

        # Section headers
        self.tree_spec = self.tree.AppendItem(root, "Spectra")
        self.tree_mode = self.tree.AppendItem(root, "Models")
        self.tree_scpt = self.tree.AppendItem(root, "Scripts")
        self.tree_tchn = self.tree.AppendItem(root, "Tool Chains")

        # Show the tree by default
        self.tree.Expand(root)

        self.sizer.Add(self.tree, 1, wx.EXPAND)
        self.panel.SetSizer(self.sizer)

        # Bind events
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnDblClick)
        self.tree.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
        self.tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnRgtClick)

    # Tree modifiers
    def AddTrace(self, trace, type='spec'):
        '''
        Add a new trace to the tree
        '''
        # Determine which heading the new item should go under
        hook = self.tree_spec if type == 'spec' else self.tree_mode

        try:
            assert(trace is not None)
        except AssertionError:
            pub.sendMessage('Logging.Error', caller='DataTab.AddTrace',
                            msg="Received a null trace object.")
            return

        field = str(trace)
        newid = self.tree.AppendItem(hook, field, data=trace)
        self.tree.EnsureVisible(newid)

    def RemoveTrace(self, trace_item):
        '''
        Remove a trace from the tree, including from the plot window
        if the spectrum is currently plotted.
        '''
        trace_data = self.tree.GetItemData(trace_item)
        with wx.MessageDialog(
            self.panel,
            "Do you want to remove trace {}?".format(trace_data.label()),
            style=wx.CENTRE | wx.YES_NO | wx.CANCEL
        ) as dialog:
            if dialog.ShowModal() == wx.ID_YES:
                # Actually delete the trace from the plot, tree, and data manager
                self.tree.Delete(trace_item)
                pub.sendMessage('Data.DeleteTrace', target_id=trace_data.id)

    def TogglePlotted(self, trace_item):
        '''
        Toggles whether the trace object is shown in the plot window.
        '''
        trace = self.tree.GetItemData(trace_item)
        if trace.is_plotted:
            # Remove the item from the plot
            pub.sendMessage('Plotting.RemoveTrace', t_id=trace.id)
            self.tree.SetItemBold(trace_item, bold=False)
        else:
            trace.is_plotted = True
            # Plot it and make it boldface
            pub.sendMessage('Plotting.AddTrace', t_id=trace.id)
            self.tree.SetItemBold(trace_item, bold=True)

    # Event handlers
    def OnDblClick(self, event):
        '''
        Handles double-click events on tree entries. Depending on item type,
        has the following behavior:

        Spectrum: toggles whether the spectrum is plotted
        Nodes: toggles whether the node is expanded/collapsed
        '''
        item = event.GetItem()
        # Determine if the doubleclicked object is plottable
        if issubclass(type(self.tree.GetItemData(item)), Trace):
            self.TogglePlotted(item)
        else:
            # Expand/collapse this item
            if self.tree.IsExpanded(item):
                self.tree.Collapse(item)
            else:
                self.tree.Expand(item)

    def OnKeyPress(self, event):
        '''
        Handles key-press events. Defined for the following keys:

        DELETE: If the highlighted tree item is a Spectrum, launch
        a removal dialog window.
        '''
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_DELETE:
            # Determine if the current selection is a spectrum
            sel_item = self.tree.GetSelection()
            sel_data = self.tree.GetItemData(sel_item)
            if issubclass(type(sel_data), Trace):
                self.RemoveTrace(sel_item)

        event.Skip()  # Pass it up the chain

    def OnRgtClick(self, event):
        '''
        Handles right-click events by launching a context menu.
        Defined for the following item types:

        Spectrum: Shows a Remove | Add to plot popup menu. (See Menu_TreeCtrlSpectrum)
        '''
        # Figure out the type of the item involved
        clk_item = event.GetItem()
        popup = None
        if issubclass(type(self.tree.GetItemData(clk_item)), Trace):
            popup = Menu_TreeCtrlTrace(self, clk_item, self.tree.GetItemData(clk_item))

        if popup:
            self.tree.PopupMenu(popup, event.GetPoint())


class TabPanel(SubPanel):
    '''
    Class implementing a notebook-style collection of panels.
    '''

    def __init__(self, parent, datasrc):
        self.data_tab_idx = 0
        super(TabPanel, self).__init__(parent, datasrc)

    def InitUI(self):
        '''
        Initialize self.ntabs panels
        '''
        # Create notebook object
        nb = wx.Notebook(self.panel)
        # Create tab objects
        tabs = []
        self.data_tab = DataTab(nb, self.datasrc)
        tabs.append(self.data_tab.GetPanel())

        self.catalog = CatalogTab(nb, self.datasrc)
        tabs.append(self.catalog.GetPanel())

        # Names of each tab
        names = ["Data", "Directory"]
        # Add all tabs to the notebook object
        assert(len(names) == len(tabs))
        for i in range(len(tabs)):
            nb.AddPage(tabs[i], names[i])

        # Place notebook in a sizer so it expands to the size of the panel
        sizer = wx.BoxSizer()
        sizer.Add(nb, 1, wx.EXPAND)

        self.panel.SetSizerAndFit(sizer)
    
    def CreateModelTuner(self, model=None):
        '''
        Launch a model tuning dialog as a new page in the notebook.
        '''
        # verify integrity of passed object
        if not model:
            pub.sendMessage(
                'Logging.Error', 
                caller='TabPanel.CreateModelTuner', 
                msg="Received a null model object."
            )
            return
        if not issubclass(type(model), Model):
            pub.sendMessage(
                'Logging.Error',
                caller='TabPanel.CreateModelTuner',
                msg='Passed object is not a Model subclass.'
            )
            return
        
        # Create the subpanel to append to the  



class TextPanel(SubPanel):
    '''
    Static panel showing a centered StaticText control
    '''

    def __init__(self, parent, datasrc, text=wx.EmptyString):
        self.text = text
        super(TextPanel, self).__init__(parent, datasrc)

    def InitUI(self):
        txt = wx.StaticText(self.panel, label=self.text)

        # Create BoxSizers to center static text
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(txt, 0, wx.CENTER)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add((0, 0), 1, wx.EXPAND)
        vbox.Add(hbox, 0, wx.CENTER)
        vbox.Add((0, 0), 1, wx.EXPAND)

        self.panel.SetSizer(vbox)


class PlotRegion(SubPanel):
    '''
    Class implementing the plot window. Utilizes a wxmplot
    PlotPanel for plotting and includes member functions for efficient
    plotting/replotting of spectra.
    '''

    def __init__(self, parent, datasrc):
        # List of trace ID's that have already been plotted
        app = wx.GetApp()
        self.plotted_traces = []
        self.is_blank = True
        super(PlotRegion, self).__init__(parent, datasrc)
        pub.subscribe(self.AddTraceToPlot, 'Plotting.AddTrace')
        pub.subscribe(self.RemoveTraceFromPlot, 'Plotting.RemoveTrace')
        pub.subscribe(self.UpdateTraces, 'Plotting.Replot')
        
    def _SuppressStatus(self, *args, **kwargs):
            '''
            Suppress PlotPanel messenger calls.
            '''
            return
    
    def InitUI(self):
        '''
        Create widgets.
        '''
        self.plot_data = TextPanel(self.panel,
                                   self.datasrc,
                                   text="Additional plot information goes here")
        self.plot_panel = PlotPanel(self.panel, messenger=self._SuppressStatus)

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(self.plot_panel, 2, wx.EXPAND)
        vbox.Add(self.plot_data.GetPanel(), 1, wx.EXPAND)

        self.panel.SetSizerAndFit(vbox)

    def AddTracesToPlot(self, traces):
        '''
        Reset the current plot and show all passed traces
        '''
        to_plot = []
        self.plotted_traces.clear()
        for t in self.datasrc.traces:
            if t.id in traces:
                t.is_plotted = True
                to_plot.append(t)
                self.plotted_traces.append(t.id)

        self.PlotMany(to_plot)

    def AddTraceToPlot(self, t_id):
        '''
        Add a single trace to the plot
        '''
        def run(t_id):
            pub.sendMessage('UI.SetStatus', text='Adding trace...')
            self.PlotTrace(self.datasrc.GetTraceByID(t_id))
            self.plotted_traces.append(t_id)
            pub.sendMessage('UI.SetStatus', text='Done.')

        asyncio.get_running_loop().run_in_executor(
            None, lambda: run(t_id)
        )

    def RemoveTraceFromPlot(self, t_id):
        '''
        Remove a single trace from the plot. Remove the id from the internal
        list of plotted traces and set internal trace.is_plotted property
        to False.
        '''
        def start_replot():
            pub.sendMessage('UI.SetStatus', text='Removing trace...')
            # Clear and re-draw the plot
            self.Replot()
            pub.sendMessage('UI.SetStatus', text='Done.')

        # The blocking segment of this routine is the replotting,
        # so management of the internal IDs can happen before the thread
        # starts to prevent out of turn trace IO operations. 
        t_obj = self.datasrc.GetTraceByID(t_id)
        if t_obj:
            t_obj.is_plotted = False

        try:
            self.plotted_traces.remove(t_id)
        except ValueError:
            pub.sendMessage(
                'Logging.Error', 
                caller='PlotRegion.RemoveTraceFromPlot', 
                msg="Plot window does not have trace with id {}.".format(t_id))
        
        asyncio.get_running_loop().run_in_executor(
            None, lambda: start_replot()
        )

    def UpdateTraces(self, traces):
        '''
        Updating a single trace without re-rendering the entire
        plot window is not currently supported.
        '''
        raise NotImplementedError('Updating traces not supported. Use Replot() instead.')

    def Replot(self):
        '''
        Replot all loaded traces.
        '''
        self.is_blank = True
        self.plot_panel.reset_config()  # Remove old names of traces
        if len(self.plotted_traces) > 0:
            to_plot = list()
            for id in self.plotted_traces:
                # Get the trace from the data manager
                spec = self.datasrc.GetTraceByID(id)
                if not spec:
                    continue  # Make sure the spectrum isn't null
                to_plot.append(spec)
                spec.is_plotted = True
            self.PlotMany(to_plot)
        else:
            self.plot_panel.clear()  # This call forces the plot to update visually
            self.plot_panel.unzoom_all()

    def PlotTrace(self, t_obj, **kwargs):
        '''
        Plot a trace object. Used internally to standardize plotting style.
        '''
        if self.is_blank:
            self.plot_panel.plot(t_obj.getx(), t_obj.gety(),
                                 label=t_obj.label(), show_legend=True, **kwargs)
            t_obj.is_plotted = True
            self.is_blank = False
        else:
            self.plot_panel.oplot(t_obj.getx(), t_obj.gety(),
                                  label=t_obj.label(), show_legend=True, **kwargs)

    def PlotMany(self, traces, **kwargs):
        '''
        Plot a list of trace objects
        '''
        if len(traces) > 0:
            # Get x and y arrays for each trace and associate labels with each
            plot_dict = [
                {
                    'xdata': t.getx(),
                    'ydata': t.gety(),
                    'label': t.label()}
                for t in traces
            ]
            self.plot_panel.plot_many(plot_dict, show_legend=True)
            self.is_blank = False
