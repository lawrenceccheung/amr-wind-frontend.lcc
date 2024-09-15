# Get the location where this script is being run
import sys, os
scriptpath = os.path.dirname(os.path.realpath(__file__))
basepath   = os.path.dirname(scriptpath)
# Add any possible locations of amr-wind-frontend here
amrwindfedirs = ['../',
                 basepath]
for x in amrwindfedirs: sys.path.insert(1, x)

from postproengine import registerplugin, mergedicts, registeraction, contourplottemplate
from postproengine import compute_axis1axis2_coords, get_mapping_xyz_to_axis1axis2
import postproamrwindsample_xarray as ppsamplexr
import postproamrwindsample as ppsample
import numpy as np
import pickle
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from postproengine import interpolatetemplate, circavgtemplate
from postproengine import compute_axis1axis2_coords

"""
Plugin for post processing phase averaged planes

See README.md for details on the structure of classes here
"""

def loadpickle(picklefile):
    pfile          = open(picklefile, 'rb')
    ds             = pickle.load(pfile)
    pfile.close()
    return ds

@registerplugin
class postpro_phaseavgplanes():
    """
    Postprocess averaged planes
    """
    # Name of task (this is same as the name in the yaml)
    name      = "phaseavgplanes"
    # Description of task
    blurb     = "Phase average netcdf sample planes"
    inputdefs = [
        # -- Execute parameters ----
        {'key':'name',     'required':True,  'default':'',
         'help':'An arbitrary name',},
        {'key':'ncfile',   'required':True,  'default':'',
        'help':'NetCDF sampling file', },
        {'key':'tstart',    'required':True,  'default':None,
         'help':'Time to start phase averaging', },
        {'key':'tend',    'required':True,  'default':None,
         'help':'Time to end phase averaging', },
        {'key':'tstart',    'required':True,  'default':None,
         'help':'Time period of phase averaging', },
        # -- optional parameters ----
        {'key':'calcavg', 'required':False,  'default':False,
         'help':'Also calculate average variables', },
        {'key':'calcrestress', 'required':False,  'default':False,
         'help':'Also calculate Reynolds stresses', },
        {'key':'saveavgpklfile', 'required':False,  'default':'',
        'help':'Name of pickle file to save average results', },
        {'key':'loadavgpklfile', 'required':False,  'default':'',
        'help':'Name of pickle file to load average results', },
        {'key':'loadpklfile', 'required':False,  'default':'',
        'help':'Load previously computed results from this pickle file', },        
        {'key':'savepklfile', 'required':False,  'default':'',
        'help':'Name of pickle file to save results', },
        {'key':'group',   'required':False,  'default':None,
         'help':'Which group to pull from netcdf file', },
        {'key':'varnames',  'required':False,  'default':['velocityx', 'velocityy', 'velocityz'],
         'help':'Variables to extract from the netcdf file',},        
        {'key':'axis_rotation',  'required':False,  'default':0,
        'help':'Degrees to rotate axis for velocitya1,a2,a3 transformation',},        
    ]
    actionlist = {}                    # Dictionary for holding sub-actions
    example = """
"""
    # --- Stuff required for main task ---
    def __init__(self, inputs, verbose=False):
        self.yamldictlist = []
        inputlist = inputs if isinstance(inputs, list) else [inputs]
        for indict in inputlist:
            self.yamldictlist.append(mergedicts(indict, self.inputdefs))
        if verbose: print('Initialized '+self.name)
        return

    def execute(self, verbose=False):
        if verbose: print('Running '+self.name)
        # Loop through and create plots
        for iplane, plane in enumerate(self.yamldictlist):
            self.tstart   = plane['tstart']
            self.tend     = plane['tend']
            self.tperiod  = plane['tperiod']
            self.ncfile   = plane['ncfile']
            self.group    = plane['group']
            loadpkl  = plane['loadpklfile']            
            self.pklfile  = plane['savepklfile']
            self.varnames = plane['varnames']
            self.axis_rotation = plane['axis_rotation']
            self.calcavg  = plane['calcavg']
            self.calcrestress    = plane['calcrestress']
            self.saveavgpklfile  = plane['saveavgpklfile']
            self.loadavgpklfile  = plane['loadavgpklfile']
                        
            # Compute or load phase averaging
            if len(loadpkl)>0:
                # Load from existing file
                pfile          = open(loadpkl, 'rb')
                self.dbavg     = pickle.load(pfile)
                pfile.close()
            else:
                # Do phase averaging
                self.dbpavg  = ppsamplexr.phaseAvgPlaneXR(self.ncfile, self.tstart, self.tend, self.tperiod,
                                                          varnames=self.varnames, groupname=self.group, includeattr=True,
                                                          savepklfile=self.pklfile, verbose=verbose, axis_rotation=self.axis_rotation)

            # Compute the normal average
            if self.calcavg or self.calcrestress:
                if len(self.loadavgpklfile)>0:
                    # Load from existing file
                    pfile     = open(self.loadavgpklfile, 'rb')
                    dbavg     = pickle.load(pfile)
                    pfile.close()
                else:
                    tavg = [self.tstart, self.tend]
                    dbavg  = ppsamplexr.avgPlaneXR(self.ncfile, tavg,
                                                   varnames=self.varnames, groupname=self.group,includeattr=True,
                                                   savepklfile=self.saveavgpklfile, verbose=verbose, axis_rotation=self.axis_rotation)
                self.dbpavg.update(dbavg)


            # Do any sub-actions required for this task
            for a in self.actionlist:
                action = self.actionlist[a]
                # Check to make sure required actions are there
                if action.required and (action.actionname not in self.yamldictlist[iplane].keys()):
                    # This is a problem, stop things
                    raise ValueError('Required action %s not present'%action.actionname)
                if action.actionname in self.yamldictlist[iplane].keys():
                    actionitem = action(self, self.yamldictlist[iplane][action.actionname])
                    actionitem.execute()

        return 

    # --- Inner classes for action list ---

    @registeraction(actionlist)
    class contourplot(contourplottemplate):
        actionname = 'contourplot'
        def __init__(self, parent, inputs):
            super().__init__(parent, inputs)
            self.plotdb = self.parent.dbpavg
            return
