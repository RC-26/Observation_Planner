import numpy as np ; import math
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import sys ; import os ; import glob
import timeit
from PIL import Image
import datetime
from timezonefinder import TimezoneFinder ; import pytz
import streamlit as st

import astropy
import astropy.units as u
import astropy.time as at
from astropy.io import fits
from astropy.wcs import WCS
from astropy.utils.data import get_pkg_data_filename
import astropy.utils.data as aud
from astropy.coordinates import SkyCoord, AltAz, EarthLocation, get_body
import astropy.coordinates as ac
import astropy.constants as constants

import astroquery.jplhorizons as jpl
from astroquery.simbad import Simbad
from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive as NEA
from astroquery.vizier import Vizier

from astroplan import FixedTarget, Observer
import astroplan as ap
import astroplan.plots as app
from astroplan.plots import plot_sky

from ics import Calendar, Event

from Utility import Render_Sidebar, Generate_Calendar

st.set_page_config (layout="wide")

st.logo ("official-logo.png", size = "large", link = "https://philsa.gov.ph") 

Render_Sidebar()

############################################################################

st.subheader ('Generate Calendars')
st.markdown  ("This function produces an **ICS** file for users to import in their calendar (Gmail and/or Outlook Calendar) for their planning purposes.")
st.markdown  ("**NOTE**: The times written in the ICS files correspond to the timezone you have specified in the 'Observation Planner' tab.")
st.divider   (width = 'stretch')

############################################################################

if 'TDates' not in st.session_state:
    st.warning('No transit data found. Please go back and submit the form first.')
    st.stop()

TDates = st.session_state['TDates']

############################################################################

def Generate_Calendar (TDatesCSV):
    if os.path.isdir(os.getcwd() + '/ICS_files') == False:
        os.mkdir (os.getcwd() + '/ICS_files')
 
    pns = sorted(list(set(TDates['Planet Name'])))
    for pn in pns:
      c = Calendar() ; time_dict = {}
      pn_csv = pd.DataFrame(TDatesCSV[TDatesCSV['Planet Name'] == pn], columns = ['Host Name', 'Planet Name', 'Observatory', 'Ingress', 'Egress'])
      hosts = pn_csv['Host Name'] ; pns = pn_csv['Planet Name'] ; obss  = pn_csv['Observatory']
      ings  = pn_csv['Ingress']   ; egs = pn_csv['Egress']
      time_dict = {}
      for obs, ing, eg in zip (obss, ings, egs):
          if (ing, eg) not in time_dict.keys() and obs not in time_dict.values():
              time_dict.update({(ing, eg) : [obs]})
          if (ing, eg)     in time_dict.keys() and obs not in time_dict[(ing, eg)]:
              time_dict[(ing, eg)].append (obs)
      for key, val in time_dict.items():
          e = Event()
          e.name = pn
          e.begin = at.Time(key[0]).datetime
          e.end   = at.Time(key[1]).datetime
          loc_text = ''
          for loc in val:
              if loc == val[-1]: loc_text = loc_text + loc
              else:              loc_text = loc_text + loc + ', '
          # st.write(key[0], '--', key[1], '||', loc_text)
          e.location = loc_text
          c.events.add(e)
      ics_content = c.serialize()  

      with open(os.getcwd() + '/ICS_files/' + '%s.ics' % pn, 'w') as f:
          f.write(ics_content)

      st.write('**%s**' % pn)
      st.download_button(label="Download ICS file", data = ics_content,file_name=f"{pn}.ics", mime = "text/calendar", icon = ":material/download:")
      
      st.divider(width = 'stretch')  

############################################################################

Generate_Calendar(TDates)
