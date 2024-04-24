import argparse
import collections
import configparser
from datetime import datetime
import grp, pwd
from fnmatch import fnmatch
import hashlib
from math import ceil
import os
import re       # regex
import sys      # need this in order to access command-line arguments (in sys.argv)
import zlib     # git compresses everything using zib

argparser = argparse.ArgumentParser(description="a random")