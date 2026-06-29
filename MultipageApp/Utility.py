import numpy as np
import math
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import sys
import os
import glob
import timeit
from PIL import Image
import datetime
from timezonefinder import TimezoneFinder
import pytz
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
import io

####################################################################################################
# Render Sidebar
# Function to make the sidebar 
####################################################################################################

def Render_Sidebar():
    st.sidebar.markdown("This app is developed by the Interdisciplinary Space Missions Development Division (ISMDD) of the Philippine Space Agency (PhilSA).")
    st.sidebar.link_button("Contact Us", "https://linktr.ee/PhilSpaceAgency" , icon=":material/mail:")
        
####################################################################################################
# Timezone Finder
# Used to find the timezone given a longitude, latitude and elevation
####################################################################################################

def Timezone_Finder(lon, lat, elev):
    location = EarthLocation(lon = lon*u.deg, lat = lat*u.deg, height = elev*u.m)
    tf = TimezoneFinder()                         
    timezone_str = tf.certain_timezone_at(lng=location.lon.deg, lat=location.lat.deg)

    if timezone_str is None:
        return ("UTC", 0)
    else:
        t_utc     = at.Time.now()
        dt_utc    = t_utc.to_datetime(timezone=datetime.timezone.utc)
        local_tz  = pytz.timezone(timezone_str)
        dt_local  = dt_utc.astimezone(local_tz)
        dt_local_str = dt_local.strftime('%Y-%m-%d %H:%M:%S %Z%z')
        return (timezone_str, int(dt_local_str[-5:-2].replace('0', '')))


####################################################################################################
# Build Observational Data
# Takes array of latitudes, longitudes and elevations, finds timezones, builds SN_OBS DataFrame
####################################################################################################

SN_obs  = ['Cerro Tololo Inter-American Obs', 'Meckering Obs', 'Perth Obs', 'American Public University System Obs',
           'Astronomical Obs of the Jagiellonian University', 'Fan Mountain Obs', 'Hampden-Sydney College Obs',
           'Montana Learning Center', 'Morehead', 'Northern Skies Obs', 'Sleaford Obs', 'Carabao Island Obs']
SN_long = [-70.805, 116.989, 116.136, -77.863, 19.828, -78.694, -78.471, -105.53, -79.05, -72.166, -105.921, 121.91442717417193]
SN_lat  = [-30.168, -31.638, -32.007,  39.293, 50.054,  37.879,  37.238,  32.902, 35.914,  44.325,   52.085, 12.056992836862623]
SN_elev = [   2286,     197,     386,     170,    318,     546,     164,    2225,    145,     384,      580, 200]

def build_observational_data(SN_obs, SN_long, SN_lat, SN_elev):
    SN_timezone  = []
    SN_utcoffset = []
    obs_tz       = {}
    tz_offset    = {"UTC": 0, "Asia/Manila": 8, "Australia/Perth": 8}

    for lon, lat, elev in zip(SN_long, SN_lat, SN_elev):
        tz, offset = Timezone_Finder(lon, lat, elev)
        SN_timezone.append(tz)
        SN_utcoffset.append(offset)

    for obs, tz, offset in zip(SN_obs, SN_timezone, SN_utcoffset):
        obs_tz.update({tz: obs})
        tz_offset.update({tz: offset})

    tz_offset = dict(sorted(tz_offset.items(), key=lambda item: item[1]))

    SN_OBS = pd.DataFrame({
        'Observatory': SN_obs,
        'Longitude':   SN_long,
        'Latitude':    SN_lat,
        'Elevation':   SN_elev,
        'Timezone':    SN_timezone,
        'UTC Offset':  SN_utcoffset,
    }).sort_values('Observatory')

    return SN_OBS, obs_tz, tz_offset  


####################################################################################################
# Get NEA Data
# Queries NASA Exoplanet Archive and returns a cleaned DataFrame
####################################################################################################

@st.cache_data
def Get_NEAdata(targets = None, Vband_limit = None):   
    if targets is not None:
        if type(targets) == str and ',' in targets:
            targets = targets.split(', ')
        if type(targets) == list:
            targets = targets
        if type(targets[0]) == list:
            targets = targets[0]

    select_data = ['hostname',   'pl_name',          'ra',           'dec',
                   'sy_dist',    'sy_snum',           'sy_pnum',      'sy_vmag',
                   'st_mass',    'st_rad',            'pl_masse',     'pl_rade',
                   'pl_eqt',
                   'st_lum',
                   'pl_orbper',  'pl_orbpererr1',     'pl_orbpererr2','pl_orbsmax',
                   'pl_tranmid', 'pl_tranmiderr1',    'pl_tranmiderr2',
                   'pl_trandur', 'pl_trandurerr1',    'pl_trandurerr2',
                   'pl_orblper', 'pl_orbtper',        'pl_orbeccen',
                   'pl_trandep']

    cond_standards = ['hostname', 'pl_name', 'ra', 'dec', 'st_rad', 'pl_rade', 'sy_vmag',
                      'pl_orbper', 'pl_tranmid', 'pl_trandur']

    not_null    = [column + ' is not null' for column in select_data    
                   if column in cond_standards or 'err' in column]
    other_conds = ["discoverymethod = 'Transit'", 'tran_flag = 1']

    if Vband_limit is not None:
        other_conds.append('sy_vmag <= %i' % Vband_limit)  

    where_conds = np.append(not_null, other_conds)

    select_text = ''
    where_text  = ''

    for d in select_data:
        if   d == select_data[-1]: select_text += '%s' % d
        else:                      select_text += '%s, ' % d   

    for c in where_conds:
        if   c == where_conds[-1]: where_text += '%s' % c
        else:                      where_text += '%s AND ' % c  

    NEAdata = NEA.query_criteria(
        table  = "pscomppars",
        select = select_text,
        where  = where_text)

    NEAcsv = NEAdata.to_pandas(index=False).sort_values('pl_name')

    # FIX: check for 'All' BEFORE filtering, otherwise [' '] wipes everything
    if targets is not None and targets != [' ']:
        for target in targets:
          if target == targets[0]:
            dummy_pd = NEAcsv[NEAcsv['pl_name'].str.contains(target, case = False)]
          else:
            dummy_pd = pd.concat ([dummy_pd, NEAcsv[NEAcsv['pl_name'].str.contains(target, case = False)]], ignore_index=True)
        NEAcsv = dummy_pd

    NEAcsv = NEAcsv.drop(columns=['sky_coord.ra', 'sky_coord.dec'])

    NEAcsv.rename(columns={
        'hostname'        : 'Host Name',
        'pl_name'         : 'Planet Name',
        'ra'              : 'RA',
        'dec'             : 'Dec',
        'sy_dist'         : 'Distance [pc]',
        'sy_snum'         : 'Number of Stars',
        'sy_pnum'         : 'Number of Planets',
        'sy_vmag'         : 'V-band Magnitude',
        'st_mass'         : 'Stellar Mass [Solar]',
        'st_rad'          : 'Stellar Radius [Solar]',
        'st_lum'          : 'Stellar Luminosity [log10(Solar)]',
        'pl_masse'        : 'Planet Mass [Earth]',
        'pl_rade'         : 'Planet Radius [Earth]',
        'pl_eqt'          : 'Planet Temperature [K]',
        'pl_trandep'      : 'Transit Depth [%]',
        'pl_orbper'       : 'Orbital Period [days]',
        'pl_orbpererr1'   : 'Orbital Period [err 1]',
        'pl_orbpererr2'   : 'Orbital Period [err 2]',
        'pl_orbsmax'      : 'Orbit Semi-Major Axis [au]',
        'pl_tranmid'      : 'Transit Midpoint [days]',
        'pl_tranmiderr1'  : 'Transit Midpoint [err 1]',
        'pl_tranmiderr2'  : 'Transit Midpoint [err 2]',
        'pl_trandur'      : 'Transit Duration [hours]',
        'pl_trandurerr1'  : 'Transit Duration [err 1]',
        'pl_trandurerr2'  : 'Transit Duration [err 2]',
        'pl_orblper'      : 'Periastron Argument [deg]',
        'pl_orbtper'      : 'Periastron Passage Time [deg]',
        'pl_orbeccen'     : 'Eccentricity',
    }, inplace=True)

    NEAcsv.to_csv('NEAcsv.csv', index=False, header=True)
    NEAcsv = pd.read_csv('NEAcsv.csv')

    return NEAcsv


####################################################################################################
# Get Transits
# Predicts next transit events within a date range using NEA ephemeris data
####################################################################################################

def Get_Transits(targets, start_date, end_date, obs_csv, Vband_limit = 10):
    print (targets)
    if type(targets) == str and ',' in targets:
        targets = targets.split(', ')
    elif ',' not in targets and type(targets) != list:  
        targets = [targets]
    if targets[0].lower() == 'all' or targets[0] == ' ':
        targets = [' ']

    obs   = obs_csv['Observatory']
    longs = obs_csv['Longitude']   
    lats  = obs_csv['Latitude']
    elevs = obs_csv['Elevation']

    NEAcsv = Get_NEAdata(targets, Vband_limit = Vband_limit) 

    time_tdb = at.Time(start_date).tdb
    time_jd  = time_tdb.jd * u.day

    NextTransits_ALL    = []
    NextTransits_Tearly = []
    NextTransits_err1   = []
    NextTransits_Tlate  = []
    NextTransits_err2   = []

    end_date = at.Time(end_date, format='iso', scale='utc')

    for i in range(len(NEAcsv)):
        MidTransit      = at.Time(NEAcsv['Transit Midpoint [days]' ][i], format='jd', scale='utc').jd * u.day
        MidTransit_err1 =         NEAcsv['Transit Midpoint [err 1]'][i] * u.day
        MidTransit_err2 =         NEAcsv['Transit Midpoint [err 2]'][i] * u.day

        OrbitalPeriod      = at.Time(NEAcsv['Orbital Period [days]'][i], format='jd', scale='utc').jd * u.day
        OrbitalPeriod_err1 =         NEAcsv['Orbital Period [err 1]'][i] * u.day
        OrbitalPeriod_err2 =         NEAcsv['Orbital Period [err 2]'][i] * u.day

        TransitDuration      = NEAcsv['Transit Duration [hours]'][i] * u.hour
        TransitDuration_err1 = NEAcsv['Transit Duration [err 1]'][i] * u.hour
        TransitDuration_err2 = NEAcsv['Transit Duration [err 2]'][i] * u.hour

        k = math.ceil((time_jd - MidTransit) / OrbitalPeriod)
        if k < 0:
            k = 0

        epoch_num    = 1
        nexttransits = [0]

        while float(max(nexttransits)) <= float(end_date.jd):
            epochs           = k + np.arange(epoch_num)
            nexttransit      = MidTransit      + epochs * np.asarray(OrbitalPeriod     ) * u.day
            NextTransit_err1 = MidTransit_err1 + epochs * np.asarray(OrbitalPeriod_err1) * u.day
            NextTransit_err2 = MidTransit_err2 + epochs * np.asarray(OrbitalPeriod_err2) * u.day
            nexttransits     = [float(at.Time(jd, format='jd', scale='utc').value) for jd in nexttransit]
            epoch_num += 1

        NextTransits     = [float(date)       for date       in nexttransits                            if date <= end_date.jd]
        NextTransit_err1 = [float(err1.value) for date, err1 in zip(nexttransits, NextTransit_err1)     if date <= end_date.jd]
        NextTransit_err2 = [float(err2.value) for date, err2 in zip(nexttransits, NextTransit_err2)     if date <= end_date.jd]

        T_early = epochs * np.asarray(OrbitalPeriod_err1) * u.day + MidTransit_err1 + 0.5 * TransitDuration + TransitDuration_err1
        T_late  = epochs * np.asarray(OrbitalPeriod_err2) * u.day + MidTransit_err2 + 0.5 * TransitDuration + TransitDuration_err2

        NextTransits_ALL.append    (NextTransits)
        NextTransits_Tearly.append ((T_early / u.day).value)
        NextTransits_err1.append   (NextTransit_err1)
        NextTransits_Tlate.append  ((T_late  / u.day).value)
        NextTransits_err2.append   (NextTransit_err2)

    NEAcsv['Next Transits [JD]'   ] = NextTransits_ALL
    NEAcsv['Next Transits [err 1]'] = NextTransits_err1
    NEAcsv['Next Transits [err 2]'] = NextTransits_err2
    NEAcsv['Next Transits [early]'] = NextTransits_Tearly
    NEAcsv['Next Transits [late]' ] = NextTransits_Tlate

    NEAcsv.to_csv('NEAcsv.csv', index=False, header=True)

    st.session_state['NEAcsv'] = NEAcsv  
    return NEAcsv


####################################################################################################
# Generate Transit Dates
# Checks observability per observatory and returns visible transit windows
####################################################################################################

def Generate_Transit_Dates(CSV, timezone='UTC', obs_csv=None, min_alt=20, specific_obs='', tz_offset=None):
    if tz_offset is None:
        tz_offset = {'UTC': 0}

    obs_names = obs_csv['Observatory']
    longs     = obs_csv['Longitude']
    lats      = obs_csv['Latitude']
    elevs     = obs_csv['Elevation']

    DF              = pd.DataFrame()
    Obs_All         = []
    Host_All        = [] ; Planet_All      = []
    Obs_Ingress     = [] ; Obs_Midpoint    = [] ; Obs_Egress      = []
    Obs_RA          = [] ; Obs_Dec         = []
    Transit_Numbers = []

    constraints = [ap.AltitudeConstraint(min=min_alt*u.deg, max=90*u.deg),
                   ap.AtNightConstraint(-12*u.deg)]

    for idx in range(len(CSV)):
        print('%-4s/%-4s' % (idx+1, len(CSV)), end='\r')

        ra         = CSV['RA'         ][idx]
        dec        = CSV['Dec'        ][idx]
        HostName   = CSV['Host Name'  ][idx]
        PlanetName = CSV['Planet Name'][idx]

        # FIX: was reading from global NEAcsv instead of the CSV parameter
        NextTransits_ALL = CSV['Next Transits [JD]'   ][idx]
        Tearly_ALL       = CSV['Next Transits [early]'][idx]
        Tlate_ALL        = CSV['Next Transits [late]' ][idx]

        for obs_name, lon, lat, elev in zip(obs_names, longs, lats, elevs):
            if specific_obs != '' and obs_name not in specific_obs:
                continue

            transit_number = 0
            location = ac.EarthLocation.from_geodetic(lon, lat, elev*u.m)
            observer = ap.Observer(location=location, name=obs_name)
            coord    = SkyCoord(ra=ra, dec=dec, unit='deg')
            target   = FixedTarget(coord=coord, name=obs_name)

            for Tmid, Tearly, Tlate in zip(NextTransits_ALL, Tearly_ALL, Tlate_ALL):
                T_mid      = at.Time(Tmid,          format='jd', scale='utc')
                Day_Tearly = at.Time(Tmid - Tearly, format='jd', scale='utc')
                if Tlate > 0:
                    Tlate = Tlate * -1
                Day_Tlate = at.Time(Tmid - Tlate, format='jd', scale='utc')

                if ap.is_observable(constraints, observer, target, time_range=[Day_Tearly, Day_Tlate]):
                    transit_number += 1
                    T_mid      += tz_offset[timezone] * u.hour
                    Day_Tearly += tz_offset[timezone] * u.hour
                    Day_Tlate  += tz_offset[timezone] * u.hour
                    Host_All.append (HostName)
                    Planet_All.append (PlanetName)
                    Obs_All.append (obs_name)
                    Transit_Numbers.append (int(transit_number))
                    Obs_Ingress.append (Day_Tearly.iso)
                    Obs_Midpoint.append (T_mid.iso)
                    Obs_Egress.append (Day_Tlate.iso)
                    Obs_RA.append (ra)
                    Obs_Dec.append (dec)

    DF['Host Name'      ] = Host_All
    DF['Planet Name'    ] = Planet_All
    DF['Observatory'    ] = Obs_All
    DF['Transit Number' ] = Transit_Numbers
    DF['Ingress'        ] = Obs_Ingress
    DF['Midpoint'       ] = Obs_Midpoint
    DF['Egress'         ] = Obs_Egress
    DF['RA'             ] = Obs_RA
    DF['Dec'            ] = Obs_Dec

    droplist = [idx for idx in range(len(DF)) if len(DF['Ingress'][idx]) == 0]
    DF = DF.drop(droplist).reset_index(drop=True)

    DF.to_csv('Observatory Visible Transit Dates - UTC.csv', index=False, header=True)
    return DF


####################################################################################################
# show_data_loc
# Filters transit table by observatory for easier viewing
####################################################################################################

def show_data_loc(data):
    filtered_df      = data.copy()
    obs_options      = data['Observatory'].unique().tolist()
    selected_locations = st.multiselect("Filtered by observatory", obs_options, default=obs_options, key="obs_filter")
    filtered_df      = filtered_df[filtered_df['Observatory'].isin(selected_locations)]
    st.write(f"Showing {len(filtered_df)} of {len(data)} rows")
    st.dataframe(filtered_df)
    return filtered_df  


####################################################################################################
# show_data_exo
# Filters transit table by exoplanet for easier viewing
####################################################################################################

def show_data_exo(data):
    filtered_df        = data.copy()
    exo_options        = data['Planet Name'].unique().tolist()
    selected_exoplanets = st.multiselect("Filtered by planet", exo_options, default=exo_options, key="exo_filter")
    filtered_df        = filtered_df[filtered_df['Planet Name'].isin(selected_exoplanets)]
    st.write(f"Showing {len(filtered_df)} of {len(data)} rows")
    st.dataframe(filtered_df)
    return filtered_df


####################################################################################################
# Visible_Airmass_Plots
# Generates and saves airmass plots for each observable transit
####################################################################################################

def Visible_Airmass_Plots(input_csv, transit_dates, min_alt = 20, obs_csv = None, main_observatory='Cerro Tololo', exoplanet_filter = None, timezone = ('UTC', 0)):
    starttime = timeit.default_timer()

    constraints = [ap.AltitudeConstraint(min = min_alt*u.deg, max = 90*u.deg),
                   ap.AtNightConstraint(-12*u.deg)]

    tz_name = timezone[0] ; tz_offset_val = timezone[1]

    for target_name, ra, dec in zip(input_csv['Planet Name'], input_csv['RA'], input_csv['Dec']):
        target_name = str(target_name)
        if exoplanet_filter != None:
            if target_name != exoplanet_filter: continue
        ra          = float(ra)
        dec         = float(dec)

        if not os.path.isdir(os.getcwd() + '/AirmassPlots'):
            os.mkdir(os.getcwd() + '/AirmassPlots')
        if not os.path.isdir(os.getcwd() + '/AirmassPlots/%s' % target_name):
            os.mkdir(os.getcwd() + '/AirmassPlots/%s' % target_name)

        for obs_name, lat, lon, elev in zip(obs_csv['Observatory'], obs_csv['Latitude'], obs_csv['Longitude'], obs_csv['Elevation']):
            if main_observatory in obs_name:
                main_location = ac.EarthLocation.from_geodetic(lon, lat, elev*u.m)
                main_observer = ap.Observer(location=main_location, name=obs_name)
                main_coord    = SkyCoord(ra=ra, dec=dec, unit='deg')
                main_target   = FixedTarget(coord=main_coord, name=obs_name)

        target_csv      = transit_dates[transit_dates['Planet Name'] == target_name].reset_index(drop = True)
        target_transits = sorted(list(set(target_csv['Midpoint'])))
        target_ingress  = [] ; target_egress = []
        for midtransit in target_transits:
            for idx in range(len(target_csv)):
                if target_csv['Midpoint'][idx] == midtransit:
                    if target_csv['Ingress'][idx] not in target_ingress: target_ingress.append (target_csv['Ingress'][idx])
                    if target_csv[ 'Egress'][idx] not in  target_egress: target_egress.append  (target_csv[ 'Egress'][idx])

        for transit_time, ingress, egress in zip(target_transits, target_ingress, target_egress):
            fig  = plt.figure()
            transit_time = str(at.Time(transit_time, format = 'iso', scale = 'utc') - tz_offset_val * u.hour)
            ingress      = str(at.Time(     ingress, format = 'iso', scale = 'utc') - tz_offset_val * u.hour)
            egress       = str(at.Time(      egress, format = 'iso', scale = 'utc') - tz_offset_val * u.hour)
            YMD = str(transit_time).split(' ')[0] ; YY, Mon, DD = YMD.split('-') ; DD = int(DD)
            HMS = str(transit_time).split(' ')[1] ; HH, Min, SS = HMS.split(':') ; HH = int(HH)
            if 0 <= HH and HH < 6:
                start_time = '%s-%s-%s %s:%s:%s' % (YY, Mon, DD, '00', '00', '00')
                start_time = at.Time(start_time  , scale = 'utc', format = 'iso')
                time       = start_time + np.linspace(-18,  +6, 97) * u.hour
            if 6 <= HH and HH < 12:
                start_time = '%s-%s-%s %s:%s:%s' % (YY, Mon, DD, '06', '00', '00')
                start_time = at.Time(start_time, scale = 'utc', format = 'iso')
                time       = start_time + np.linspace(-12, +12, 97) * u.hour
            if 12 <= HH and HH < 18:
                start_time = '%s-%s-%s %s:%s:%s' % (YY, Mon, DD, '12', '00', '00')
                start_time = at.Time(start_time, scale = 'utc', format = 'iso')
                time       = start_time + np.linspace( -6, +18, 97) * u.hour
            if 18 <= HH:
                start_time = '%s-%s-%s %s:%s:%s' % (YY, Mon, DD, '18', '00', '00')
                start_time = at.Time(start_time, scale = 'utc', format = 'iso')
                time       = start_time + np.linspace(  0, +24, 97) * u.hour

            current_date = YMD

            night_time  = main_observer.tonight(time=time[0], horizon=-12*u.deg)
            night_start = at.Time(night_time[0].iso)
            night_end   = at.Time(night_time[1].iso)

            ingress_time = at.Time(ingress, scale = 'utc', format = 'iso')
            egress_time  = at.Time( egress, scale = 'utc', format = 'iso')

            if not ap.is_observable(constraints, main_observer, main_target, time_range=[ingress_time, egress_time]):
                plt.close()
                continue

            for obs_name, lat, lon, elev in zip(obs_csv['Observatory'], obs_csv['Latitude'], obs_csv['Longitude'], obs_csv['Elevation']):
                location = ac.EarthLocation.from_geodetic(lon, lat, elev*u.m)
                observer = ap.Observer(location=location, name=obs_name)
                coord    = SkyCoord(ra=ra, dec=dec, unit='deg')
                target   = FixedTarget(coord=coord, name=obs_name)

                if not ap.is_observable(constraints, observer, target, time_range=[ingress_time, egress_time]):
                    continue

                m_ls = {'markersize': 0, 'color': 'black', 'linewidth': 4, 'linestyle': ':'}
                ls   = {'markersize': 0}
                if lat > 0: ls.update({'linestyle': '-'})
                if lat < 0: ls.update({'linestyle': '--'})

                if main_observatory in obs_name:
                    ls.update({'color': 'black', 'linewidth': 4})
                    moon        = observer.moon_altaz(time)
                    moon_radec  = moon.transform_to('icrs')
                    moon_coord  = SkyCoord(ra=moon_radec.ra, dec=moon_radec.dec, unit='deg')
                    moon_target = FixedTarget(coord=moon_coord, name='Moon (%s)' % main_observatory)
                    ap.plots.plot_altitude(target,      observer, time, brightness_shading=True,  min_altitude=0, style_kwargs=ls)
                    ap.plots.plot_altitude(moon_target, observer, time, brightness_shading=False, min_altitude=0, style_kwargs=m_ls)
                else:
                    ap.plots.plot_altitude(target, observer, time, brightness_shading=False, min_altitude=0, style_kwargs=ls)

            label_fs = 14
            plt.xticks(np.linspace(plt.xticks()[0][0], plt.xticks()[0][-1], 13).tolist())
            xlabel_date = plt.gca().get_xlabel().split(' ')[2]
            plt.title('%s | Transit on %s [UTC]' % (target_name, current_date), fontsize=35)
            plt.xlabel('Time [UTC]', size=label_fs)
            plt.ylabel('Altitude $[\u00b0]$', size=label_fs)

            raw_xticks  = [x for x in plt.gca().get_xticks()]
            whole_ticks = [i for i, x in enumerate(raw_xticks) if x == int(x)]
            if len(whole_ticks) > 0:
                zero_UTC = whole_ticks[0]
                plt.gca().get_xticklabels()[zero_UTC].set_weight("bold")
                plt.gca().get_xticklabels()[zero_UTC].set_color("red")

            ay2           = plt.gca().secondary_yaxis('right')
            custom_locs   = np.linspace(10, 90, 9, dtype=int).tolist()
            custom_yticks = [5.86, 2.9, 1.993, 1.553, 1.304, 1.154, 1.064, 1.015, 1.0]
            ay2.set_yticks(custom_locs)
            ay2.set_yticklabels(custom_yticks)
            ay2.set_ylabel('Airmass', rotation=270, labelpad=15, size=label_fs)

            plt.grid(axis='y', linewidth=4)
            plt.legend(bbox_to_anchor=(1, 1), loc='upper left', framealpha=0.9)
            plt.ylim(min_alt, 90)
            plt.axvspan(at.Time(ingress_time).datetime64, at.Time(egress_time).datetime64, color = 'green', alpha = 0.1)
            plt.axvline(at.Time(transit_time).datetime64, color = 'green', linestyle = '-.', linewidth = 2, label = 'Transit Midpoint')
            plt.gcf().set_size_inches(24, 12)

            filename = os.getcwd() + '/AirmassPlots/%s/AIR_%s.png' % (target_name, current_date)
            plt.savefig(filename, bbox_inches='tight', dpi=600)
            st.pyplot(fig)
            st.divider(width='stretch')
            plt.close()

    stoptime = timeit.default_timer()
    runtime  = stoptime - starttime
    minute   = math.floor(runtime / 60)
    seconds  = runtime - 60 * minute
    print("\rDONE! | Runtime: %im %+8s" % (minute, str(np.round(seconds, 2)) + 's |'))

####################################################################################################
# Generate Calendar
# Generates a downloadable calendar in ics form 
####################################################################################################

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
      st.write(pn)
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
     
      st.download_button(label="Download ICS file", data=ics_content,file_name=f"{pn}.ics", mime="text/calendar", icon=":material/download:",)
      
      st.divider(width = 'stretch')  

####################################################################################################
# Dates
# Dates Generated
####################################################################################################

# TDates = st.session_state['TDates']
