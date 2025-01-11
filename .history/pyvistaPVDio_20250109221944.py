import streamlit as st
from stpyvista import stpyvista
from firedrake import *
from viamr import VIAMR
from viamr.utility import SphereObstacleProblem
from viamr.utility import SpiralObstacleProblem
import threading
from time import sleep
