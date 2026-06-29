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

from Utility import Render_Sidebar, Timezone_Finder, build_observational_data, Get_NEAdata, Get_Transits, Generate_Transit_Dates, show_data_loc, SN_obs, SN_long, SN_lat, SN_elev

st.set_page_config(layout="wide")

st.logo("official-logo.png", size = "large", link = "https://philsa.gov.ph") 

# Making the sidebar
Render_Sidebar()

############################################################################

st.title("Observational Scheduling Tool")

st.markdown("This pipeline is for helping users plan their observations by extracting data from the **NASA Exoplanet Archive (NEA)** to predict the next transit events.  \nThe current iteration of this tool focuses on ground-based telescopes that are part of the **Skynet Robotic Telescope Network (SkyNet)**.") 

st.divider(width = "stretch")

############################################################################

st.subheader("SkyNet Observatories")

############################################################################

# Finding the appropriate timezone and making our data set (Timezone_Finder(), build_observational_data())

# Defining our arrays

# Observatory names 
SN_obs = ['Cerro Tololo Inter-American Obs', 'Meckering Obs', 'Perth Obs', 'American Public University System Obs', 
              'Astronomical Obs of the Jagiellonian University', 'Fan Mountain Obs', 'Hampden-Sydney College Obs', 
              'Montana Learning Center', 'Morehead', 'Northern Skies Obs', 'Sleaford Obs', 'Carabao Island Obs'] 

# Longitudes 
SN_long       = [-70.805, 116.989, 116.136, -77.863, 19.828, -78.694, -78.471, -105.53, -79.05, -72.166, -105.921, 121.91442717417193]

# Latitudes
SN_lat        = [-30.168, -31.638, -32.007,  39.293, 50.054,  37.879,  37.238,  32.902, 35.914,  44.325,   52.085, 12.056992836862623]

# Elevations
SN_elev       = [   2286,     197,     386,     170,    318,     546,     164,    2225,    145,     384,      580, 200]

def build_observational_data():
    SN_timezone = [] ; SN_utcoffset = [] ; obs_tz = {}
    tz_offset = {'UTC' : 0, 'Asia/Manila' : 8, 'Australia/Perth' : 8}
    
    for lon, lat, elev in zip(SN_long, SN_lat, SN_elev):
        tz, offset = Timezone_Finder(lon, lat, elev)
        SN_timezone.append(tz) ; SN_utcoffset.append(offset)

    for obs, tz, offset in zip(SN_obs, SN_timezone, SN_utcoffset):
        obs_tz.update    ({obs : tz})
        tz_offset.update ({tz  : offset})

    tz_offset = dict(sorted(tz_offset.items(), key=lambda item: item[1]))

    SN_OBS = pd.DataFrame({
        'Observatory': SN_obs,
        'Longitude': SN_long,
        'Latitude': SN_lat,
        'Elevation': SN_elev,
        'Timezone': SN_timezone,
        'UTC Offset': SN_utcoffset,

    }).sort_values('Observatory').reset_index(drop = True)

    return SN_OBS, obs_tz, tz_offset


# Defining disabling boxes so both boxes cannot be checked at the same time
if "box1_disabled" not in st.session_state:
    st.session_state["box1_disabled"] = False
if "box2_disabled" not in st.session_state:
    st.session_state["box2_disabled"] = False 

def toggle_box2():
    if st.session_state["box1"]:
        st.session_state["box2_disabled"] = True
    else:
        st.session_state["box2_disabled"] = False

def toggle_box1():
    if st.session_state["box2"]:
        st.session_state["box1_disabled"] = True
    else:
        st.session_state["box1_disabled"] = False

st.caption("Do you want to add your own custom Observatory?")
yes = st.checkbox("Yes", key = "box1", on_change = toggle_box2, disabled = st.session_state["box1_disabled"])
no  = st.checkbox("No" , key = "box2", on_change = toggle_box1, disabled = st.session_state["box2_disabled"])

if yes:
    
    with st.form('Submission_Forms'):
        observatory_name = st.text_input(label='Observatory Name: ', placeholder="Example: 'Royal Observatory Edinburgh'")
        latitude  = st.number_input(label = 'Latitude' , placeholder = "Enter in Decimal Coordinates")
        longitude = st.number_input(label = 'Longitude', placeholder = "Enter in Decimal Coordinates")
        elevation = st.number_input(label = 'Elevation', placeholder = "Enter in Meters (m)")
        ed_submit = st.form_submit_button('Submit')
        
    if ed_submit:
        SN_obs.append(observatory_name) 
        SN_long.append(longitude)
        SN_lat.append(latitude)
        SN_elev.append(elevation)
        
        if 'SN_OBS' not in st.session_state:
            SN_OBS, obs_tz, tz_offset = build_observational_data()
            st.session_state['SN_OBS'] = SN_OBS
            st.session_state['obs_tz'] = obs_tz 
            st.session_state['tz_offset'] = tz_offset
        else:
            SN_OBS = st.session_state['SN_OBS']
            obs_tz = st.session_state['obs_tz']
            tz_offset = st.session_state['tz_offset']

if no: 
    if 'SN_OBS' not in st.session_state:
        SN_OBS, obs_tz, tz_offset = build_observational_data()
        st.session_state['SN_OBS'] = SN_OBS
        st.session_state['obs_tz'] = obs_tz 
        st.session_state['tz_offset'] = tz_offset
    else:
        SN_OBS = st.session_state['SN_OBS']
        obs_tz = st.session_state['obs_tz']
        tz_offset = st.session_state['tz_offset']

if 'SN_OBS' not in st.session_state:
    st.stop()


if 'SN_OBS' not in st.session_state:
    st.session_state['SN_OBS'] = SN_OBS
    st.session_state['obs_tz'] = obs_tz 
    st.session_state['tz_offset'] = tz_offset
else:
    SN_OBS = st.session_state['SN_OBS']
    obs_tz = st.session_state['obs_tz']
    tz_offset = st.session_state['tz_offset']

data = (SN_OBS, obs_tz, tz_offset)
st.markdown ("This table displays all the accessible SkyNet observatories and their geographical coordinates (**Longitude**, **Latitude**, and **Elevation**) including their **Timezone** and **UTC offset**.  \nThe **Carabao Island Observatory** is included in this pipeline.")
st.dataframe (SN_OBS)
st.divider (width = 'stretch')

############################################################################

st.subheader("NASA Exoplanet Archive (NEA) Data")
st.markdown("This Table displays the data of all the **host stars**, and their respective **exoplanets**, from the **NASA Exoplanet Archive**.")

############################################################################

# Getting the data from the NASA Exoplanet Archive (Get_NEAdata() function)

NEAcsv = Get_NEAdata()

Display_Option = st.radio ("Display the data of all available NEA transiting exoplanets? (This may help you if you are unsure of the target you want to observe.)", ['No', 'Yes'])
if Display_Option == 'Yes':
    # st.caption ('This table/CSV contains all the available data of transiting exoplanets in the NASA Exoplanet Archive (NEA)')
    if 'All_NEAcsv' not in st.session_state:
        All_NEAcsv = Get_NEAdata(Vband_limit = 9999)
        st.session_state['All_NEAcsv'] = All_NEAcsv
    All_NEAcsv = st.session_state['All_NEAcsv']
    st.dataframe(st.session_state['All_NEAcsv'])
    st.write ('Host Stars:', len(sorted(set(All_NEAcsv['Host Name']))), '| Exoplanets', len(sorted(set(All_NEAcsv['Planet Name']))))
    

st.divider(width = 'stretch')

############################################################################

st.subheader ("Generate Transit Dates")
st.markdown  ("Generates the **dates** of the **predicted transit events** of all exoplanets within the time window specified by the user.")

options = [(tz, offset) for tz, offset in tz_offset.items()]

with st.form('Submission_Form'):
    targets    = st.text_input (label='Target planet: ', placeholder="Example: 'TRAPPIST-1 c' or 'All'")
    start_date = st.datetime_input (label='Start date: ')
    end_date   = st.datetime_input (label='End date: **(Must be later than the Start Date)**')
    timezone = st.selectbox (label = 'Timezone of output dates / UTC offset', options = options, index = options.index(('UTC', 0)))
    min_alt     = st.number_input (label = 'Minimum Altitude **(Default value = 20.00)**'      , value = 20.00, min_value = 0.00, max_value = 89.00, placeholder = "Default value = 20")
    Vband_limit = st.number_input (label = 'V-band Magnitude limit **(Default value = 10.00)**', value = 10.00, placeholder = "Default value = 10")
    ed_submit  = st.form_submit_button('Submit')

if ed_submit:
    NEAcsv = Get_Transits(targets=targets, start_date=str(start_date), end_date=str(end_date), obs_csv = SN_OBS, Vband_limit = Vband_limit)
    st.session_state['NEAcsv'] = NEAcsv  

if 'NEAcsv' in st.session_state:
    NEAcsv = st.session_state['NEAcsv']
    st.dataframe(NEAcsv)

    st.divider(width = 'stretch')

    tz_name, tz_offset_val = timezone
    TDates = Generate_Transit_Dates(NEAcsv, obs_csv = SN_OBS, min_alt = min_alt, timezone = tz_name, tz_offset = tz_offset)
    filtered_obs = show_data_loc(TDates)
    st.session_state['TDates'       ] = TDates
    st.session_state['timezone'     ] = timezone
    st.session_state['tz_name'      ] = tz_name
    st.session_state['tz_offset_val'] = tz_offset_val
    st.session_state['filtered_obs' ] = filtered_obs
    st.session_state['Vband_limit'  ] = Vband_limit
    st.session_state['min_alt'      ] = min_alt
        
    st.divider(width = 'stretch')
