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

from Utility import Render_Sidebar

st.logo ("official-logo.png", size = "large", link = "https://philsa.gov.ph") 

st.title ("References") 
st.markdown ("All the references used to make this pipeline.")

Render_Sidebar()

############################################################################

st.divider(width = "stretch")

st.subheader ("Skynet Robotic Telescope Network")
st.caption   ("https://skynet.unc.edu/")
st.subheader ("NASA Exoplanet Archive")
st.caption   ("https://exoplanetarchive.ipac.caltech.edu/")
st.caption   ("J. L. Christiansen et al. Planet. Sci. J. 6 (186) 2025")
# st.caption   ("https://iopscience.iop.org/article/10.3847/PSJ/ade3c2")
# st.caption   ("Transit Algorithms: https://exoplanetarchive.ipac.caltech.edu/docs/transit/transit_algorithms.html")
st.subheader ("Astropy")
st.caption   ("Astropy Collaboration. Astrophys. J. 935 (167) 2022")
st.subheader ("Astroquery")
st.caption   ("A. Ginsburg et. al. Astron. J. 157 (98) 2019")
st.subheader ("Astroplan")
st.caption   ("B. M. Morris et. al. Astron. J. 155 (128) 2018")

st.divider   (width = "stretch")

############################################################################

st.markdown ("This Streamlit app was developed by **Arcy Layne L. Sace**<sup>1</sup>, **Darren Mykel V. Gapay**<sup>2</sup>, **Ernest P. Macalalad**<sup>1</sup>, & **Reinabelle C. Reyes**<sup>1,3</sup>", unsafe_allow_html = True)
st.write ("<sup>1</sup>Philippine Space Agency, Eastwood Avenue, Brgy. Bagumbayan, Quezon City, Philippines  \n<sup>2</sup>University of Glasgow, University Avenue, Glasgow, G12 8QQ, Scotland, United Kingdom  \n<sup>3</sup>Research Center for Theoretical Physics, Central Visayan Institute Foundation, Jagna, Bohol, Philippines", unsafe_allow_html = True)
# st.write ("<sup>1</sup>Philippine Space Agency, Eastwood Avenue, Brgy. Bagumbayan, Quezon City, Philippines", unsafe_allow_html = True)
# st.write ("<sup>2</sup>University of Glasgow, University Avenue, Glasgow, G12 8QQ, Scotland, United Kingdom", unsafe_allow_html = True)
# st.write ("<sup>3</sup>Research Center for Theoretical Physics, Central Visayan Institute Foundation, Jagna, Bohol, Philippines", unsafe_allow_html = True)
