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

import io

import matplotlib.axes as maxes
if not hasattr(maxes.Axes, 'plot_date'):
    maxes.Axes.plot_date = lambda self, x, y, **kwargs: self.plot(x, y, **kwargs)

from Utility import Render_Sidebar, show_data_exo, Visible_Airmass_Plots

st.set_page_config (layout="wide")

st.logo ("official-logo.png", size = "large", link = "https://philsa.gov.ph") 

# Making the sidebar
Render_Sidebar()

############################################################################

st.title ("Airmass Plots") 

st.markdown ("This displays all the relevant **transit events** and their **airmass plots**.") 

st.divider(width = 'stretch')

############################################################################

if 'TDates' not in st.session_state:
    st.warning('No transit data found. Please go back and submit the form first.')
    st.stop()

TDates = st.session_state['TDates']
TDates.columns = TDates.columns.str.strip()
timezone = st.session_state['timezone']
# tz_name = st.session_state['tz_name']
# tz_offset_val = st.session_state['tz_offset_val']
filtered_obs = st.session_state['filtered_obs']
NEAcsv = st.session_state['NEAcsv']
SN_OBS = st.session_state['SN_OBS']
min_alt = st.session_state['min_alt']

############################################################################

st.subheader('Transit Dates')
st.markdown ('These are the transit dates generated in the previous page. **(Please generate the predicted transit dates before using this page.)**    \n**NOTE**: The generated airmass plots are always in **UTC**.') 

exo_filter = show_data_exo(filtered_obs)
st.divider(width = 'stretch')

############################################################################

st.subheader('Airmass Plots')


st.markdown('Specifiy the **exoplanet** you want to observe, and the **main observatory** you would like to use within the Skynet Telescope Network.')
pn_options  = list(sorted(set(exo_filter['Planet Name'])))
obs_options = list(sorted(set(exo_filter['Observatory'])))
with st.form('Submisson_Form'):
    exoplanet_filter = st.selectbox (label = 'Exoplanet'       , options =  pn_options, index =  pn_options.index( pn_options[0]))
    main_observatory = st.selectbox (label = 'Main Observatory', options = obs_options, index = obs_options.index(obs_options[0]))
    ed_submit = st.form_submit_button('Submit')

if ed_submit:
    st.write ("The **dark shaded regions** represent the **civil**, **nautical**, and **astronomical twilights**. The darkest region represents **night time**.")
    Air_Mass = Visible_Airmass_Plots(
        input_csv        = NEAcsv,
        transit_dates    = exo_filter,
        min_alt          = min_alt,
        timezone         = timezone,
        obs_csv          = SN_OBS,
        main_observatory = str(main_observatory),
        exoplanet_filter = str(exoplanet_filter)
    )
