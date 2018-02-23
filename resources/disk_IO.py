# -*- coding: utf-8 -*-
# Advanced MAME Launcher filesystem I/O functions
#

# Copyright (c) 2016-2017 Wintermute0110 <wintermute0110@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# --- Python standard library ---
from __future__ import unicode_literals
from __future__ import division
import json
import io
import codecs, time
import subprocess
import re
import threading
import copy
import gc
# import resource # Module not available on Windows

# --- XML stuff ---
# ~~~ cElementTree sometimes fails to parse XML in Kodi's Python interpreter... I don't know why
# import xml.etree.cElementTree as ET

# ~~~ Using ElementTree seems to solve the problem
import xml.etree.ElementTree as ET

# --- AEL packages ---
from constants import *
from utils import *
try:
    from utils_kodi import *
except:
    from utils_kodi_standalone import *
from mame import *

# -------------------------------------------------------------------------------------------------
# Advanced MAME Launcher data model
# -------------------------------------------------------------------------------------------------
# http://xmlwriter.net/xml_guide/attlist_declaration.shtml#CdataEx
# #REQUIRED  The attribute must always be included
# #IMPLIED   The attribute does not have to be included.
#
# Example from MAME 0.190:
#   <!ELEMENT device (instance*, extension*)>
#     <!ATTLIST device type CDATA #REQUIRED>
#     <!ATTLIST device tag CDATA #IMPLIED>
#     <!ATTLIST device fixed_image CDATA #IMPLIED>
#     <!ATTLIST device mandatory CDATA #IMPLIED>
#     <!ATTLIST device interface CDATA #IMPLIED>
#     <!ELEMENT instance EMPTY>
#       <!ATTLIST instance name CDATA #REQUIRED>
#       <!ATTLIST instance briefname CDATA #REQUIRED>
#     <!ELEMENT extension EMPTY>
#       <!ATTLIST extension name CDATA #REQUIRED>
#
# <device> tags. Example of machine aes (Neo Geo AES)
# <device type="memcard" tag="memcard">
#   <instance name="memcard" briefname="memc"/>
#   <extension name="neo"/>
# </device>
# <device type="cartridge" tag="cslot1" interface="neo_cart">
#   <instance name="cartridge" briefname="cart"/>
#   <extension name="bin"/>
# </device>
#
# This is how it is stored:
# devices = [
#   {
#     'att_type' : string,
#     'att_tag' : string,
#     'att_mandatory' : bool,
#     'att_interface' : string,
#     'instance' : {'name' : string, 'briefname' : string}
#     'ext_name' : [string1, string2],
#   }, ...
# ]
#
# Rendering on AML Machine Information text window.
# devices[0, att_type]:
#   att_type: string
#   att_tag: string
#   att_mandatory: unicode(bool)
#   att_interface: string
#   instance: unicode(dictionary),
#   ext_names: unicode(string list),
# devices[1, att_type]: unicode(device[1])
#   ...
#
def fs_new_machine_dic():
    m = {
        # >> <machine> attributes
        'sourcefile'     : '',
        'isMechanical'   : False,
        'romof'          : '',
        'sampleof'       : '',
        # >> Other <machine> tags from MAME XML
        'display_tag'    : [],
        'display_type'   : [], # (raster|vector|lcd|unknown) #REQUIRED>
        'display_rotate' : [], # (0|90|180|270) #REQUIRED>
        'control_type'   : [],
        'coins'          : 0,
        'softwarelists'  : [],
        'devices'        : [], # List of dictionaries. See comments avobe.
        # >> Custom AML data
        'catver'         : '', # External catalog
        'nplayers'       : '', # External catalog
        'catlist'        : '', # External catalog
        'genre'          : '', # External catalog
        'bestgames'      : '', # External catalog
        'series'         : '', # External catalog
        'isDead'         : False
    }

    return m

#
# Object used in MAME_render_db.json
#   flags -> ROM, CHD, Samples, SoftwareLists, Devices
#
# Status flags meaning:
#   -  Machine doesn't have ROMs | Machine doesn't have Software Lists
#   ?  Machine has own ROMs and ROMs not been scanned
#   r  Machine has own ROMs and ROMs doesn't exist
#   R  Machine has own ROMs and ROMs exists | Machine has Software Lists
#
# Status device flag:
#   -  Machine has no devices
#   d  Machine has device/s but are not mandatory (can be booted without the device).
#   D  Machine has device/s and must be plugged in order to boot.
#
def fs_new_machine_render_dic():
    m = {
        # >> <machine> attributes
        'isBIOS'         : False,
        'isDevice'       : False,
        'cloneof'        : '',
        # >> Other <machine> tags from MAME XML
        'description'    : '',
        'year'           : '',
        'manufacturer'   : '',
        'driver_status'  : '',
        # >> Custom AML data
        'genre'          : '',      # Taken from Genre.ini, Catver.ini or Catlist.ini
        'nplayers'       : '',      # Taken from NPlayers.ini
        'flags'          : '-----',
        'plot'           : '',      # Generated from other fields
    }

    return m

#
# Object used in MAME_DB_roms.json
# machine_roms = {
#     'machine_name' : {
#         'bios'  : [ ... ],
#         'disks' : [ ... ],
#         'roms'  : [ ... ]
#     }
# }
#
def fs_new_roms_object():
    r = {
        'bios'  : [],
        'roms'  : [],
        'disks' : []
    }

    return r

def fs_new_bios_dic():
    m = {
        'name'        : '',
        'description' : ''
    }

    return m

def fs_new_rom_dic():
    m = {
        'name'  : '',
        'merge' : '',
        'bios'  : '',
        'size'  : 0,
        'crc'  : '' # crc allows to know if ROM is valid or not
    }

    return m

def fs_new_disk_dic():
    m = {
        'name'  : '',
        'merge' : '',
        'sha1'  : '' # sha1 allows to know if CHD is valid or not. CHDs don't have crc
    }

    return m

#
# Object used in MAME_assets_db.json
#
ASSET_MAME_KEY_LIST  = ['cabinet',  'cpanel',  'flyer',  'marquee',  'PCB',  'snap',  'title',  'clearlogo',  'trailer',    'manual']
ASSET_MAME_PATH_LIST = ['cabinets', 'cpanels', 'flyers', 'marquees', 'PCBs', 'snaps', 'titles', 'clearlogos', 'videosnaps', 'manuals']
def fs_new_MAME_asset():
    a = {
        'cabinet'   : '',
        'cpanel'    : '',
        'flyer'     : '',
        'marquee'   : '',
        'PCB'       : '',
        'snap'      : '',
        'title'     : '',
        'clearlogo' : '',
        'trailer'   : '',
        'manual'    : '',
    }

    return a

# Status flags meaning:
#   ?  SL ROM not scanned
#   r  Missing ROM
#   R  Have ROM
def fs_new_SL_ROM_part():
    p = {
        'name'      : '',
        'interface' : ''
    }

    return p

def fs_new_SL_ROM():
    R = {
        'description' : '',
        'year'        : '',
        'publisher'   : '',
        'cloneof'     : '',
        'parts'       : [],
        'hasROMs'     : False,
        'hasCHDs'     : False,
        'status_ROM'  : '-',
        'status_CHD'  : '-',
    }

    return R

ASSET_SL_KEY_LIST  = ['title',     'snap',     'boxfront',  'trailer',       'manual']
ASSET_SL_PATH_LIST = ['titles_SL', 'snaps_SL', 'covers_SL', 'videosnaps_SL', 'manuals_SL']
def fs_new_SL_asset():
    a = {
        'title'    : '',
        'snap'     : '',
        'boxfront' : '',
        'trailer'   : '',
        'manual'    : '',
    }

    return a

def fs_new_control_dic():
    C = {
        # --- Filed in when extracting MAME XML ---
        'stats_total_machines' : 0,

        # --- Filed in when building main MAME database ---
        # >> Numerical MAME version. Allows for comparisons like ver_mame >= MAME_VERSION_0190
        # >> MAME string version, as reported by the executable stdout. Example: '0.194 (mame0194)'
        'ver_mame'      : 0,
        'ver_mame_str'  : 'Unknown. MAME database not built',
        'ver_catver'    : 'Unknown. MAME database not built',
        'ver_catlist'   : 'Unknown. MAME database not built',
        'ver_genre'     : 'Unknown. MAME database not built',
        'ver_nplayers'  : 'Unknown. MAME database not built',
        'ver_bestgames' : 'Unknown. MAME database not built',
        'ver_series'    : 'Unknown. MAME database not built',

        'stats_processed_machines' : 0,
        'stats_parents'            : 0,
        'stats_clones'             : 0,
        'stats_devices'            : 0,
        'stats_devices_parents'    : 0,
        'stats_devices_clones'     : 0,
        'stats_runnable'           : 0,
        'stats_runnable_parents'   : 0,
        'stats_runnable_clones'    : 0,
        'stats_samples'            : 0,
        'stats_samples_parents'    : 0,
        'stats_samples_clones'     : 0,
        'stats_BIOS'               : 0,
        'stats_BIOS_parents'       : 0,
        'stats_BIOS_clones'        : 0,
        'stats_coin'               : 0,
        'stats_coin_parents'       : 0,
        'stats_coin_clones'        : 0,
        'stats_nocoin'             : 0,
        'stats_nocoin_parents'     : 0,
        'stats_nocoin_clones'      : 0,
        'stats_mechanical'         : 0,
        'stats_mechanical_parents' : 0,
        'stats_mechanical_clones'  : 0,
        'stats_dead'               : 0,
        'stats_dead_parents'       : 0,
        'stats_dead_clones'        : 0,

        # --- Filed in when building SL index ---
        # Number of ROM ZIP files in the Merged, Split or Non-merged sets.
        'MAME_ZIP_files' : 0,
        # Number of CHD files in the Merged, Split or Non-merged sets.
        'MAME_CHD_files' : 0,

        # Number of SL databases (equal to the number of XML files).
        'SL_XML_files' : 0,
        'SL_with_ROMs' : 0,
        'SL_with_CHDs' : 0,

        # --- Filed in by the MAME ROM/CHD/Samples scanner ---
        # Number of ZIP files, including devices.
        'scan_ZIP_files_total'   : 0,
        'scan_ZIP_files_have'    : 0,
        'scan_ZIP_files_missing' : 0,
        # Number of CHD files.
        'scan_CHD_files_total'   : 0,
        'scan_CHD_files_have'    : 0,
        'scan_CHD_files_missing' : 0,

        # Number of machines that need a ROM ZIP file to run, excluding devices.
        'scan_ROM_machines_total'   : 0,
        # Number of machines you can run, excluding devices.
        'scan_ROM_machines_have'    : 0,
        # Number of machines you cannot run, excluding devices.
        'scan_ROM_machines_missing' : 0,
        # Number of machines that need a CHD or CHDs to run.
        'scan_CHD_machines_total'   : 0,
        # Number of machines with CHDs you can run.
        'scan_CHD_machines_have'    : 0,
        # Number of machines with CHDs you cannot run.
        'scan_CHD_machines_missing' : 0,

        'scan_Samples_have'    : 0,
        'scan_Samples_total'   : 0,
        'scan_Samples_missing' : 0,

        # --- Filed in by the SL ROM scanner ---
        'scan_SL_ROMs_have'    : 0,
        'scan_SL_ROMs_total'   : 0,
        'scan_SL_ROMs_missing' : 0,
        'scan_SL_CHDs_have'    : 0,
        'scan_SL_CHDs_total'   : 0,
        'scan_SL_CHDs_missing' : 0,
    }

    return C

# --- Constants ---
# >> Make sure these strings are equal to the ones in settings.xml
VIEW_MODE_FLAT         = 0 # 'Flat'
VIEW_MODE_PCLONE       = 1 # 'Parent/Clone'
VIEW_MODE_PARENTS_ONLY = 2 # 'Parents only'
MAME_MERGED    = 0 # 'Merged'
MAME_SPLIT     = 1 # 'Split'
MAME_NONMERGED = 2 # 'Non-merged'
SL_MERGED      = 0 # 'Merged'
SL_SPLIT       = 1 # 'Split'
SL_NONMERGED   = 2 # 'Non-merged'

# >> Used to build the properties list. 
#    1) Must match names in main.py @_render_root_list()
#    2) Must match names in disk_IO.py @fs_build_MAME_catalogs()
CATALOG_NAME_LIST  = ['None', 'Catver', 'Catlist', 'Genre', 'NPlayers', 'Bestgames', 'Series',
                      'Manufacturer', 'Year', 'Driver', 'Controls', 
                      'Display_Tag', 'Display_Type', 'Display_Rotate',
                      'Devices', 'BySL']

def fs_get_cataloged_dic_parents(PATHS, catalog_name):
    if   catalog_name == 'Main':           catalog_dic = fs_load_JSON_file(PATHS.CATALOG_MAIN_PARENT_PATH.getPath())
    elif catalog_name == 'Binary':         catalog_dic = fs_load_JSON_file(PATHS.CATALOG_BINARY_PARENT_PATH.getPath())
    elif catalog_name == 'Catver':         catalog_dic = fs_load_JSON_file(PATHS.CATALOG_CATVER_PARENT_PATH.getPath())
    elif catalog_name == 'Catlist':        catalog_dic = fs_load_JSON_file(PATHS.CATALOG_CATLIST_PARENT_PATH.getPath())
    elif catalog_name == 'Genre':          catalog_dic = fs_load_JSON_file(PATHS.CATALOG_GENRE_PARENT_PATH.getPath())
    elif catalog_name == 'NPlayers':       catalog_dic = fs_load_JSON_file(PATHS.CATALOG_NPLAYERS_PARENT_PATH.getPath())
    elif catalog_name == 'Bestgames':      catalog_dic = fs_load_JSON_file(PATHS.CATALOG_BESTGAMES_PARENT_PATH.getPath())
    elif catalog_name == 'Series':         catalog_dic = fs_load_JSON_file(PATHS.CATALOG_SERIES_PARENT_PATH.getPath())
    elif catalog_name == 'Manufacturer':   catalog_dic = fs_load_JSON_file(PATHS.CATALOG_MANUFACTURER_PARENT_PATH.getPath())
    elif catalog_name == 'Year':           catalog_dic = fs_load_JSON_file(PATHS.CATALOG_YEAR_PARENT_PATH.getPath())
    elif catalog_name == 'Driver':         catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DRIVER_PARENT_PATH.getPath())
    elif catalog_name == 'Controls':       catalog_dic = fs_load_JSON_file(PATHS.CATALOG_CONTROL_PARENT_PATH.getPath())
    elif catalog_name == 'Display_Tag':    catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DISPLAY_TAG_PARENT_PATH.getPath())
    elif catalog_name == 'Display_Type':   catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DISPLAY_TYPE_PARENT_PATH.getPath())
    elif catalog_name == 'Display_Rotate': catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DISPLAY_ROTATE_PARENT_PATH.getPath())
    elif catalog_name == 'Devices':        catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DEVICE_LIST_PARENT_PATH.getPath())
    elif catalog_name == 'BySL':           catalog_dic = fs_load_JSON_file(PATHS.CATALOG_SL_PARENT_PATH.getPath())
    else:
        log_error('fs_get_cataloged_dic_parents() Unknown catalog_name = "{0}"'.format(catalog_name))

    return catalog_dic

def fs_get_cataloged_dic_all(PATHS, catalog_name):
    if   catalog_name == 'Main':           catalog_dic = fs_load_JSON_file(PATHS.CATALOG_MAIN_ALL_PATH.getPath())
    elif catalog_name == 'Binary':         catalog_dic = fs_load_JSON_file(PATHS.CATALOG_BINARY_ALL_PATH.getPath())
    elif catalog_name == 'Catver':         catalog_dic = fs_load_JSON_file(PATHS.CATALOG_CATVER_ALL_PATH.getPath())
    elif catalog_name == 'Catlist':        catalog_dic = fs_load_JSON_file(PATHS.CATALOG_CATLIST_ALL_PATH.getPath())
    elif catalog_name == 'Genre':          catalog_dic = fs_load_JSON_file(PATHS.CATALOG_GENRE_ALL_PATH.getPath())
    elif catalog_name == 'NPlayers':       catalog_dic = fs_load_JSON_file(PATHS.CATALOG_NPLAYERS_ALL_PATH.getPath())
    elif catalog_name == 'Bestgames':      catalog_dic = fs_load_JSON_file(PATHS.CATALOG_BESTGAMES_ALL_PATH.getPath())
    elif catalog_name == 'Series':         catalog_dic = fs_load_JSON_file(PATHS.CATALOG_SERIES_ALL_PATH.getPath())
    elif catalog_name == 'Manufacturer':   catalog_dic = fs_load_JSON_file(PATHS.CATALOG_MANUFACTURER_ALL_PATH.getPath())
    elif catalog_name == 'Year':           catalog_dic = fs_load_JSON_file(PATHS.CATALOG_YEAR_ALL_PATH.getPath())
    elif catalog_name == 'Driver':         catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DRIVER_ALL_PATH.getPath())
    elif catalog_name == 'Controls':       catalog_dic = fs_load_JSON_file(PATHS.CATALOG_CONTROL_ALL_PATH.getPath())
    elif catalog_name == 'Display_Tag':    catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DISPLAY_TAG_ALL_PATH.getPath())
    elif catalog_name == 'Display_Type':   catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DISPLAY_TYPE_ALL_PATH.getPath())
    elif catalog_name == 'Display_Rotate': catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DISPLAY_ROTATE_ALL_PATH.getPath())
    elif catalog_name == 'Devices':        catalog_dic = fs_load_JSON_file(PATHS.CATALOG_DEVICE_LIST_ALL_PATH.getPath())
    elif catalog_name == 'BySL':           catalog_dic = fs_load_JSON_file(PATHS.CATALOG_SL_ALL_PATH.getPath())
    else:
        log_error('fs_get_cataloged_dic_all() Unknown catalog_name = "{0}"'.format(catalog_name))

    return catalog_dic

# -------------------------------------------------------------------------------------------------
# Exceptions raised by this module
# -------------------------------------------------------------------------------------------------
class DiskError(Exception):
    """Base class for exceptions in this module."""
    pass

class CriticalError(DiskError):
    def __init__(self, msg):
        self.msg = msg

class GeneralError(DiskError):
    def __init__(self, msg):
        self.msg = msg

# -------------------------------------------------------------------------------------------------
# JSON write/load
# -------------------------------------------------------------------------------------------------
COMPACT_JSON = False
def fs_load_JSON_file(json_filename):
    # --- If file does not exist return empty dictionary ---
    data_dic = {}
    if not os.path.isfile(json_filename): return data_dic
    log_verb('fs_load_ROMs_JSON() "{0}"'.format(json_filename))
    with open(json_filename) as file:
        data_dic = json.load(file)

    return data_dic

def fs_write_JSON_file(json_filename, json_data):
    log_verb('fs_write_JSON_file() "{0}"'.format(json_filename))
    try:
        with io.open(json_filename, 'wt', encoding='utf-8') as file:
            if COMPACT_JSON:
                file.write(unicode(json.dumps(json_data, ensure_ascii = False, sort_keys = True, separators = (',', ':'))))
            else:
                file.write(unicode(json.dumps(json_data, ensure_ascii = False, sort_keys = True, indent = 1, separators = (',', ':'))))
    except OSError:
        gui_kodi_notify('Advanced MAME Launcher - Error', 'Cannot write {0} file (OSError)'.format(roms_json_file))
    except IOError:
        gui_kodi_notify('Advanced MAME Launcher - Error', 'Cannot write {0} file (IOError)'.format(roms_json_file))

# -------------------------------------------------------------------------------------------------
# Threaded JSON loader
# -------------------------------------------------------------------------------------------------
class Threaded_Load_JSON(threading.Thread):
    def __init__(self, json_filename): 
        threading.Thread.__init__(self) 
        self.json_filename = json_filename
 
    def run(self): 
        self.output_dic = fs_load_JSON_file(self.json_filename)

# -------------------------------------------------------------------------------------------------
def fs_extract_MAME_version(PATHS, mame_prog_FN):
    (mame_dir, mame_exec) = os.path.split(mame_prog_FN.getPath())
    log_info('fs_extract_MAME_version() mame_prog_FN "{0}"'.format(mame_prog_FN.getPath()))
    log_debug('fs_extract_MAME_version() mame_dir     "{0}"'.format(mame_dir))
    log_debug('fs_extract_MAME_version() mame_exec    "{0}"'.format(mame_exec))
    with open(PATHS.MAME_STDOUT_VER_PATH.getPath(), 'wb') as out, open(PATHS.MAME_STDERR_VER_PATH.getPath(), 'wb') as err:
        p = subprocess.Popen([mame_prog_FN.getPath(), '-?'], stdout=out, stderr=err, cwd=mame_dir)
        p.wait()

    # --- Check if everything OK ---
    # statinfo = os.stat(PATHS.MAME_XML_PATH.getPath())
    # filesize = statinfo.st_size

    # --- Read version ---
    with open(PATHS.MAME_STDOUT_VER_PATH.getPath()) as f:
        lines = f.readlines()
    version_str = ''
    for line in lines:
        m = re.search('^MAME v([0-9\.]+?) \(([a-z0-9]+?)\)$', line.strip())
        if m:
            version_str = m.group(1)
            break

    return version_str

# MAME_XML_PATH -> (FileName object) path of MAME XML output file.
# mame_prog_FN  -> (FileName object) path to MAME executable.
# Returns filesize -> (int) file size of output MAME.xml
#
def fs_extract_MAME_XML(PATHS, mame_prog_FN):
    (mame_dir, mame_exec) = os.path.split(mame_prog_FN.getPath())
    log_info('fs_extract_MAME_XML() mame_prog_FN "{0}"'.format(mame_prog_FN.getPath()))
    log_debug('fs_extract_MAME_XML() mame_dir     "{0}"'.format(mame_dir))
    log_debug('fs_extract_MAME_XML() mame_exec    "{0}"'.format(mame_exec))
    pDialog = xbmcgui.DialogProgress()
    pDialog_canceled = False
    pDialog.create('Advanced MAME Launcher',
                   'Extracting MAME XML database. Progress bar is not accurate.')
    with open(PATHS.MAME_XML_PATH.getPath(), 'wb') as out, open(PATHS.MAME_STDERR_PATH.getPath(), 'wb') as err:
        p = subprocess.Popen([mame_prog_FN.getPath(), '-listxml'], stdout=out, stderr=err, cwd=mame_dir)
        count = 0
        while p.poll() is None:
            pDialog.update((count * 100) // 100)
            time.sleep(1)
            count = count + 1
    pDialog.close()

    # --- Check if everything OK ---
    statinfo = os.stat(PATHS.MAME_XML_PATH.getPath())
    filesize = statinfo.st_size

    # --- Count number of machines. Useful for progress dialogs ---
    log_info('fs_extract_MAME_XML() Counting number of machines...')
    total_machines = fs_count_MAME_Machines(PATHS)
    log_info('fs_extract_MAME_XML() Found {0} machines.'.format(total_machines))
    # kodi_dialog_OK('Found {0} machines in MAME.xml.'.format(total_machines))

    # -----------------------------------------------------------------------------
    # Create MAME control dictionary
    # -----------------------------------------------------------------------------
    control_dic = fs_new_control_dic()
    control_dic['total_machines'] = total_machines
    fs_write_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath(), control_dic)

    return (filesize, total_machines)

def fs_count_MAME_Machines(PATHS):
    pDialog = xbmcgui.DialogProgress()
    pDialog_canceled = False
    pDialog.create('Advanced MAME Launcher', 'Counting number of MAME machines...')
    pDialog.update(0)
    num_machines = 0
    with open(PATHS.MAME_XML_PATH.getPath(), 'rt') as f:
        for line in f:
            if line.decode('utf-8').find('<machine name=') > 0: num_machines = num_machines + 1
    pDialog.update(100)
    pDialog.close()

    return num_machines

# Valid ROM: ROM has CRC hash
# Valid CHD: CHD has SHA1 hash
def fs_initial_flags(machine, machine_render, m_roms):
    # >> Machine has own ROMs (at least one ROM is valid and has empty 'merge' attribute)
    has_own_ROMs = False
    for rom in m_roms['roms']:
        if not rom['merge'] and rom['crc']:
            has_own_ROMs = True
            break
    flag_ROM = '?' if has_own_ROMs else '-'

    # >> Machine has own CHDs
    has_own_CHDs = False
    for rom in m_roms['disks']:
        if not rom['merge'] and rom['sha1']:
            has_own_CHDs = True
            break
    flag_CHD = '?' if has_own_CHDs else '-'

    # >> Samples flag
    flag_Samples = '?' if machine['sampleof'] else '-'

    # >> Software List flag
    flag_SL = 'L' if machine['softwarelists'] else '-'

    # >> Devices flag
    if machine['devices']:
        num_dev_mandatory = 0
        for device in machine['devices']:
            if device['att_mandatory']: 
                flag_Devices = 'D'
                num_dev_mandatory += 1
            else: 
                flag_Devices  = 'd'
        if num_dev_mandatory > 2:
            message = 'Machine {0} has {1} mandatory devices'.format(machine_name, num_dev_mandatory)
            raise CriticalError(message)
    else:
        flag_Devices  = '-'

    return '{0}{1}{2}{3}{4}'.format(flag_ROM, flag_CHD, flag_Samples, flag_SL, flag_Devices)

#
# Update m_render using Python pass by assignment.
# Remember that strings are inmutable!
#
def fs_set_ROM_flag(m_render, new_ROM_flag):
    old_flags_str = m_render['flags']
    flag_ROM      = old_flags_str[0]
    flag_CHD      = old_flags_str[1]
    flag_Samples  = old_flags_str[2]
    flag_SL       = old_flags_str[3]
    flag_Devices  = old_flags_str[4]
    flag_ROM      = new_ROM_flag
    m_render['flags'] = '{0}{1}{2}{3}{4}'.format(flag_ROM, flag_CHD, flag_Samples, flag_SL, flag_Devices)

def fs_set_CHD_flag(m_render, new_CHD_flag):
    old_flags_str = m_render['flags']
    flag_ROM      = old_flags_str[0]
    flag_CHD      = old_flags_str[1]
    flag_Samples  = old_flags_str[2]
    flag_SL       = old_flags_str[3]
    flag_Devices  = old_flags_str[4]
    flag_CHD      = new_CHD_flag
    m_render['flags'] = '{0}{1}{2}{3}{4}'.format(flag_ROM, flag_CHD, flag_Samples, flag_SL, flag_Devices)

def fs_set_Sample_flag(m_render, new_Sample_flag):
    old_flags_str = m_render['flags']
    flag_ROM      = old_flags_str[0]
    flag_CHD      = old_flags_str[1]
    flag_Samples  = old_flags_str[2]
    flag_SL       = old_flags_str[3]
    flag_Devices  = old_flags_str[4]
    flag_Samples  = new_Sample_flag
    m_render['flags'] = '{0}{1}{2}{3}{4}'.format(flag_ROM, flag_CHD, flag_Samples, flag_SL, flag_Devices)

#
# Retrieves machine from distributed database.
# This is very quick for retrieving individual machines, very slow for multiple machines.
#
def fs_get_machine_main_db_hash(PATHS, machine_name):
    log_debug('fs_get_machine_main_db_hash() machine {0}'.format(machine_name))
    md5_str = hashlib.md5(machine_name).hexdigest()
    hash_DB_FN = PATHS.MAIN_DB_HASH_DIR.pjoin(md5_str[0] + '.json')
    hashed_db_dic = fs_load_JSON_file(hash_DB_FN.getPath())

    return hashed_db_dic[machine_name]

def fs_build_catalog_helper(catalog_parents, catalog_all, machines, machines_render, main_pclone_dic, db_field):
    for parent_name in main_pclone_dic:
        # >> Skip device machines in calatogs.
        if machines_render[parent_name]['isDevice']: continue
        catalog_key = machines[parent_name][db_field]
        if catalog_key in catalog_parents:
            catalog_parents[catalog_key]['parents'].append(parent_name)
            catalog_parents[catalog_key]['num_parents'] = len(catalog_parents[catalog_key]['parents'])
            catalog_all[catalog_key]['machines'].append(parent_name)
            for clone in main_pclone_dic[parent_name]: catalog_all[catalog_key]['machines'].append(clone)
            catalog_all[catalog_key]['num_machines'] = len(catalog_all[catalog_key]['machines'])
        else:
            catalog_parents[catalog_key] = {'parents' : [parent_name], 'num_parents' : 1}
            all_list = [parent_name]
            for clone in main_pclone_dic[parent_name]: all_list.append(clone)
            catalog_all[catalog_key] = {'machines' : all_list, 'num_machines' : len(all_list)}

def fs_catalog_counter(cat_name, catalog_count_dic, catalog_all, catalog_parents):
    for cat_key in catalog_all:
        catalog_count_dic[cat_name]['cats'][cat_key] = {}
        catalog_count_dic[cat_name]['cats'][cat_key]['num_parents']  = len(catalog_parents[cat_key]['parents'])
        catalog_count_dic[cat_name]['cats'][cat_key]['num_machines'] = len(catalog_all[cat_key]['machines'])
    num_items = len(catalog_count_dic[cat_name]['cats'])
    catalog_count_dic[cat_name]['num_categories'] = num_items

# -------------------------------------------------------------------------------------------------
# Reads and processes MAME.xml
#
# Saves:
#   MAIN_DB_PATH
#   RENDER_DB_PATH
#   ROMS_DB_PATH
#   MAIN_ASSETS_DB_PATH  (empty JSON file)
#   MAIN_PCLONE_DIC_PATH
#   MAIN_CONTROL_PATH    (updated and then JSON file saved)
#   ROM_SETS_PATH
#
STOP_AFTER_MACHINES = 100000
def fs_build_MAME_main_database(PATHS, settings, control_dic):
    # --- Progress dialog ---
    pDialog_canceled = False
    pDialog = xbmcgui.DialogProgress()

    # --- Load INI files to include category information ---
    pDialog.create('Advanced MAME Launcher')
    pDialog.update(0, 'Processing INI file: catver.ini ...')
    (categories_dic, catver_version) = mame_load_Catver_ini(settings['catver_path'])
    pDialog.update(16, 'Processing INI file: catlist.ini ...')
    (catlist_dic, catlist_version) = mame_load_INI_datfile(settings['catlist_path'])
    pDialog.update(32, 'Processing INI file: genre.ini ...')
    (genre_dic, genre_version) = mame_load_INI_datfile(settings['genre_path'])
    pDialog.update(48, 'Processing INI file: nplayers.ini ...')
    (nplayers_dic, nplayers_version) = mame_load_nplayers_ini(settings['nplayers_path'])
    pDialog.update(64, 'Processing INI file: bestgames.ini ...')
    (bestgames_dic, bestgames_version) = mame_load_INI_datfile(settings['bestgames_path'])
    pDialog.update(80, 'Processing INI file: series.ini ...')
    (series_dic, series_version) = mame_load_INI_datfile(settings['series_path'])
    pDialog.update(100)
    pDialog.close()

    # --- Load DAT files to include category information ---
    pDialog.create('Advanced MAME Launcher')
    pDialog.update(0, 'Processing DAT file: history.dat ...')
    (history_idx_dic, history_dic) = mame_load_History_DAT(settings['history_path'])
    pDialog.update(25, 'Processing DAT file: mameinfo.dat ...')
    (mameinfo_idx_dic, mameinfo_dic) = mame_load_MameInfo_DAT(settings['mameinfo_path'])
    pDialog.update(50, 'Processing DAT file: gameinit.dat ...')
    (gameinit_idx_dic, gameinit_dic) = mame_load_GameInit_DAT(settings['gameinit_path'])
    pDialog.update(75, 'Processing DAT file: command.dat ...')
    (command_idx_dic, command_dic) = mame_load_Command_DAT(settings['command_path'])
    pDialog.update(100)
    pDialog.close()

    # ---------------------------------------------------------------------------------------------
    # Incremental Parsing approach B (from [1])
    # ---------------------------------------------------------------------------------------------
    # Do not load whole MAME XML into memory! Use an iterative parser to
    # grab only the information we want and discard the rest.
    # See http://effbot.org/zone/element-iterparse.htm [1]
    #
    pDialog.create('Advanced MAME Launcher')
    pDialog.update(0, 'Building main MAME database ...')
    log_info('fs_build_MAME_main_database() Loading "{0}"'.format(PATHS.MAME_XML_PATH.getPath()))
    context = ET.iterparse(PATHS.MAME_XML_PATH.getPath(), events=("start", "end"))
    context = iter(context)
    event, root = context.next()
    mame_version_raw = root.attrib['build']
    mame_version_int = mame_get_numerical_version(mame_version_raw)
    log_info('fs_build_MAME_main_database() MAME str version "{0}"'.format(mame_version_raw))
    log_info('fs_build_MAME_main_database() MAME numerical version {0}'.format(mame_version_int))

    # --- Process MAME XML ---
    total_machines = control_dic['total_machines']
    machines = {}
    machines_render = {}
    machines_roms = {}
    machines_devices = {}
    stats_processed_machines = 0
    stats_parents            = 0
    stats_clones             = 0
    stats_devices            = 0
    stats_devices_parents    = 0
    stats_devices_clones     = 0
    stats_runnable           = 0
    stats_runnable_parents   = 0
    stats_runnable_clones    = 0
    stats_samples            = 0
    stats_samples_parents    = 0
    stats_samples_clones     = 0
    stats_BIOS               = 0
    stats_BIOS_parents       = 0
    stats_BIOS_clones        = 0
    stats_coin               = 0
    stats_coin_parents       = 0
    stats_coin_clones        = 0
    stats_nocoin             = 0
    stats_nocoin_parents     = 0
    stats_nocoin_clones      = 0
    stats_mechanical         = 0
    stats_mechanical_parents = 0
    stats_mechanical_clones  = 0
    stats_dead               = 0
    stats_dead_parents       = 0
    stats_dead_clones        = 0

    log_info('fs_build_MAME_main_database() Parsing MAME XML file ...')
    num_iteration = 0
    for event, elem in context:
        # --- Debug the elements we are iterating from the XML file ---
        # print('Event     {0:6s} | Elem.tag    "{1}"'.format(event, elem.tag))
        # print('                   Elem.text   "{0}"'.format(elem.text))
        # print('                   Elem.attrib "{0}"'.format(elem.attrib))

        # <machine> tag start event includes <machine> attributes
        if event == 'start' and elem.tag == 'machine':
            machine  = fs_new_machine_dic()
            m_render = fs_new_machine_render_dic()
            m_roms   = fs_new_roms_object()
            device_list = []
            runnable = False
            num_displays = 0

            # --- Process <machine> attributes ----------------------------------------------------
            # name is #REQUIRED attribute
            if 'name' not in elem.attrib:
                log_error('name attribute not found in <machine> tag.')
                raise CriticalError('name attribute not found in <machine> tag')
            else:
                m_name = elem.attrib['name']

            # sourcefile #IMPLIED attribute
            if 'sourcefile' not in elem.attrib:
                log_error('sourcefile attribute not found in <machine> tag.')
                raise CriticalError('sourcefile attribute not found in <machine> tag.')
            else:
                # >> Remove trailing '.cpp' from driver name
                raw_driver_name = elem.attrib['sourcefile']

                # >> In MAME 0.174 some driver end with .cpp and others with .hxx
                # if raw_driver_name[-4:] == '.cpp':
                #     driver_name = raw_driver_name[0:-4]
                # else:
                #     print('Unrecognised driver name "{0}"'.format(raw_driver_name))

                # >> Assign driver name
                machine['sourcefile'] = raw_driver_name

            # Optional, default no
            if 'isbios' not in elem.attrib:       m_render['isBIOS'] = False
            else:                                 m_render['isBIOS'] = True if elem.attrib['isbios'] == 'yes' else False
            if 'isdevice' not in elem.attrib:     m_render['isDevice'] = False
            else:                                 m_render['isDevice'] = True if elem.attrib['isdevice'] == 'yes' else False
            if 'ismechanical' not in elem.attrib: machine['isMechanical'] = False
            else:                                 machine['isMechanical'] = True if elem.attrib['ismechanical'] == 'yes' else False
            # Optional, default yes
            if 'runnable' not in elem.attrib:     runnable = True
            else:                                 runnable = False if elem.attrib['runnable'] == 'no' else True

            # cloneof is #IMPLIED attribute
            if 'cloneof' in elem.attrib: m_render['cloneof'] = elem.attrib['cloneof']

            # romof is #IMPLIED attribute
            if 'romof' in elem.attrib: machine['romof'] = elem.attrib['romof']

            # sampleof is #IMPLIED attribute
            if 'sampleof' in elem.attrib: machine['sampleof'] = elem.attrib['sampleof']

            # >> Add catver/catlist/genre
            if m_name in categories_dic: machine['catver']    = categories_dic[m_name]
            else:                        machine['catver']    = '[ Not set ]'
            if m_name in nplayers_dic:   machine['nplayers']  = nplayers_dic[m_name]
            else:                        machine['nplayers']  = '[ Not set ]'
            if m_name in catlist_dic:    machine['catlist']   = catlist_dic[m_name]
            else:                        machine['catlist']   = '[ Not set ]'
            if m_name in genre_dic:      machine['genre']     = genre_dic[m_name]
            else:                        machine['genre']     = '[ Not set ]'
            if m_name in bestgames_dic:  machine['bestgames'] = bestgames_dic[m_name]
            else:                        machine['bestgames'] = '[ Not set ]'
            if m_name in series_dic:     machine['series']    = series_dic[m_name]
            else:                        machine['series']    = '[ Not set ]'

            # >> Increment number of machines
            stats_processed_machines += 1

        elif event == 'start' and elem.tag == 'description':
            m_render['description'] = unicode(elem.text)

        elif event == 'start' and elem.tag == 'year':
            m_render['year'] = unicode(elem.text)

        elif event == 'start' and elem.tag == 'manufacturer':
            m_render['manufacturer'] = unicode(elem.text)

        # >> Check in machine has BIOS
        # <biosset> name and description attributes are mandatory
        elif event == 'start' and elem.tag == 'biosset':
            # --- Add BIOS to ROMS_DB_PATH ---
            bios = fs_new_bios_dic()
            bios['name'] = unicode(elem.attrib['name'])
            bios['description'] = unicode(elem.attrib['description'])
            m_roms['bios'].append(bios)

        # >> Check in machine has ROMs
        # A) ROM is considered to be valid if SHA1 has exists. 
        #    Are there ROMs with no sha1? There are a lot, for example 
        #    machine 1941j <rom name="yi22b.1a" size="279" status="nodump" region="bboardplds" />
        #
        # B) A ROM is unique to that machine if the <rom> tag does not have the 'merge' attribute.
        #    For example, snes and snespal both have <rom> tags that point to exactly the same
        #    BIOS. However, in a split set only snes.zip ROM set exists.
        #    snes    -> <rom name="spc700.rom" size="64" crc="44bb3a40" ... >
        #    snespal -> <rom name="spc700.rom" merge="spc700.rom" size="64" crc="44bb3a40" ... >
        #
        # C) In AML, hasROM actually means "machine has it own ROMs not found somewhere else".
        #
        elif event == 'start' and elem.tag == 'rom':
            # --- Research ---
            # if not 'sha1' in elem.attrib:
            #     raise GeneralError('ROM with no sha1 (machine {0})'.format(machine_name))

            # --- Add BIOS to ROMS_DB_PATH ---
            rom = fs_new_rom_dic()
            rom['name']  = unicode(elem.attrib['name'])
            rom['merge'] = unicode(elem.attrib['merge']) if 'merge' in elem.attrib else ''
            rom['bios']  = unicode(elem.attrib['bios']) if 'bios' in elem.attrib else ''
            rom['size']  = int(elem.attrib['size']) if 'size' in elem.attrib else 0
            rom['crc']   = unicode(elem.attrib['crc']) if 'crc' in elem.attrib else ''
            m_roms['roms'].append(rom)

        # >> Machine devices
        elif event == 'start' and elem.tag == 'device_ref':
            device_list.append(unicode(elem.attrib['name']))

        # >> Check in machine has CHDs
        # A) CHD is considered valid if and only if SHA1 hash exists.
        #    Keep in mind that there can be multiple disks per machine, some valid, some invalid.
        #    Just one valid CHD is OK.
        # B) A CHD is unique to a machine if the <disk> tag does not have the 'merge' attribute.
        #    See comments for ROMs avobe.
        #
        elif event == 'start' and elem.tag == 'disk':
            # <!ATTLIST disk name CDATA #REQUIRED>
            # if 'sha1' in elem.attrib and 'merge' in elem.attrib:     machine['CHDs_merged'].append(elem.attrib['name'])
            # if 'sha1' in elem.attrib and 'merge' not in elem.attrib: machine['CHDs'].append(elem.attrib['name'])

            # --- Add BIOS to ROMS_DB_PATH ---
            disk = fs_new_disk_dic()
            disk['name']  = unicode(elem.attrib['name'])
            disk['merge'] = unicode(elem.attrib['merge']) if 'merge' in elem.attrib else ''
            disk['sha1']  = unicode(elem.attrib['sha1']) if 'sha1' in elem.attrib else ''
            m_roms['disks'].append(disk)

        # Some machines have more than one display tag (for example aquastge has 2).
        # Other machines have no display tag (18w)
        elif event == 'start' and elem.tag == 'display':
            rotate_str = elem.attrib['rotate'] if 'rotate' in elem.attrib else '0'
            machine['display_tag'].append(elem.attrib['tag'])
            machine['display_type'].append(elem.attrib['type'])
            machine['display_rotate'].append(rotate_str)
            num_displays += 1

        # Some machines have no controls at all.
        elif event == 'start' and elem.tag == 'input':
            # coins is #IMPLIED attribute
            if 'coins' in elem.attrib:
                machine['coins'] = int(elem.attrib['coins'])

            # >> Iterate children of <input> and search for <control> tags
            for control_child in elem:
                if control_child.tag == 'control':
                    machine['control_type'].append(control_child.attrib['type'])

        elif event == 'start' and elem.tag == 'driver':
            # status is #REQUIRED attribute
            m_render['driver_status'] = unicode(elem.attrib['status'])

        elif event == 'start' and elem.tag == 'softwarelist':
            # name is #REQUIRED attribute
            machine['softwarelists'].append(elem.attrib['name'])

        # >> Device tag for machines that support loading external files
        elif event == 'start' and elem.tag == 'device':
            att_type      = elem.attrib['type'] # The only mandatory attribute
            att_tag       = elem.attrib['tag']       if 'tag'       in elem.attrib else ''
            att_mandatory = elem.attrib['mandatory'] if 'mandatory' in elem.attrib else ''
            att_interface = elem.attrib['interface'] if 'interface' in elem.attrib else ''
            # >> Transform device_mandatory into bool
            if att_mandatory and att_mandatory == '1': att_mandatory = True
            else:                                      att_mandatory = False

            # >> Iterate children of <device> and search for <instance> tags
            instance_tag_found = False
            inst_name = ''
            inst_briefname = ''
            ext_names = []
            for device_child in elem:
                if device_child.tag == 'instance':
                    # >> Stop if <device> tag has more than one <instance> tag. In MAME 0.190 no
                    # >> machines trigger this.
                    if instance_tag_found:
                        raise GeneralError('Machine {0} has more than one <instance> inside <device>')
                    inst_name      = device_child.attrib['name']
                    inst_briefname = device_child.attrib['briefname']
                    instance_tag_found = True
                elif device_child.tag == 'extension':
                    ext_names.append(device_child.attrib['name'])

            # >> NOTE Some machines have no instance inside <device>, for example 2020bb
            # >>      I don't know how to launch those machines
            # if not instance_tag_found:
                # log_warning('<instance> tag not found inside <device> tag (machine {0})'.format(machine_name))
                # device_type = '{0} (NI)'.format(device_type)

            # >> Add device to database
            device_dic = {'att_type'      : att_type,      'att_tag'        : att_tag,
                          'att_mandatory' : att_mandatory, 'att_interface'  : att_interface,
                          'instance'      : { 'name' : inst_name, 'briefname' : inst_briefname},
                          'ext_names'     : ext_names}
            machine['devices'].append(device_dic)

        # --- <machine> tag closing. Add new machine to database ---
        elif event == 'end' and elem.tag == 'machine':
            # >> Assumption 1: isdevice = True if and only if runnable = False
            if m_render['isDevice'] == runnable:
                print("Machine {0}: machine['isDevice'] == runnable".format(machine_name))
                raise GeneralError

            # >> Are there machines with more than 1 <display> tag. Answer: YES
            # if num_displays > 1:
            #     print("Machine {0}: num_displays = {1}".format(machine_name, num_displays))
            #     raise GeneralError

            # >> All machines with 0 displays are mechanical? NO, 24cdjuke has no screen and is not mechanical. However
            # >> 24cdjuke is a preliminary driver.
            # if num_displays == 0 and not machine['ismechanical']:
            #     print("Machine {0}: num_displays == 0 and not machine['ismechanical']".format(machine_name))
            #     raise GeneralError

            # >> Mark dead machines. A machine is dead if Status is preliminary AND have no controls
            if m_render['driver_status'] == 'preliminary' and not machine['control_type']:
                machine['isDead'] = True

            # >> Delete XML element once it has been processed
            elem.clear()

            # >> Fill machine status
            # r/R flag takes precedence over * flag
            m_render['flags'] = fs_initial_flags(machine, m_render, m_roms)

            # --- Compute statistics ---
            if m_render['cloneof']: stats_clones += 1
            else:                   stats_parents += 1
            if m_render['isDevice']:
                stats_devices += 1
                if m_render['cloneof']: stats_devices_clones += 1
                else:                   stats_devices_parents += 1
            if runnable:
                stats_runnable += 1
                if m_render['cloneof']: stats_runnable_clones += 1
                else:                   stats_runnable_parents += 1
            if machine['sampleof']:
                stats_samples += 1
                if m_render['cloneof']: stats_samples_clones += 1
                else:                   stats_samples_parents += 1
            if m_render['isBIOS']:
                stats_BIOS += 1
                if m_render['cloneof']: stats_BIOS_clones += 1
                else:                   stats_BIOS_parents += 1
            if runnable:
                if machine['coins'] > 0:
                    stats_coin += 1
                    if m_render['cloneof']: stats_coin_clones += 1
                    else:                   stats_coin_parents += 1
                else:
                    stats_nocoin += 1
                    if m_render['cloneof']: stats_nocoin_clones += 1
                    else:                   stats_nocoin_parents += 1
                if machine['isMechanical']:
                    stats_mechanical += 1
                    if m_render['cloneof']: stats_mechanical_clones += 1
                    else:                   stats_mechanical_parents += 1
                if machine['isDead']:
                    stats_dead += 1
                    if m_render['cloneof']: stats_dead_clones += 1
                    else:                   stats_dead_parents += 1

            # >> Add new machine
            machines[m_name] = machine
            machines_render[m_name] = m_render
            machines_roms[m_name] = m_roms
            machines_devices[m_name] = device_list

        # --- Print something to prove we are doing stuff ---
        num_iteration += 1
        if num_iteration % 1000 == 0:
            pDialog.update((stats_processed_machines * 100) // total_machines)
            # log_debug('Processed {0:10d} events ({1:6d} machines so far) ...'.format(num_iteration, stats_processed_machines))
            # log_debug('stats_processed_machines   = {0}'.format(stats_processed_machines))
            # log_debug('total_machines = {0}'.format(total_machines))
            # log_debug('Update number  = {0}'.format(update_number))

        # --- Stop after STOP_AFTER_MACHINES machines have been processed for debug ---
        if stats_processed_machines >= STOP_AFTER_MACHINES: break
    pDialog.update(100)
    pDialog.close()
    log_info('Processed {0} MAME XML events'.format(num_iteration))
    log_info('Processed machines {0}'.format(stats_processed_machines))
    log_info('Parents            {0}'.format(stats_parents))
    log_info('Clones             {0}'.format(stats_clones))
    log_info('Dead machines      {0}'.format(stats_dead))

    # ---------------------------------------------------------------------------------------------
    # Main parent-clone list
    # ---------------------------------------------------------------------------------------------
    # Create a couple of data struct for quickly know the parent of a clone game and
    # all clones of a parent.
    #
    # main_pclone_dic          = { 'parent_name' : ['clone_name', 'clone_name', ... ] , ... }
    # main_clone_to_parent_dic = { 'clone_name' : 'parent_name', ... }
    log_info('Making PClone list...')
    main_pclone_dic = {}
    main_clone_to_parent_dic = {}
    for machine_name in machines_render:
        machine = machines_render[machine_name]
        # >> Exclude devices
        # if machine['isDevice']: continue

        if machine['cloneof']:
            # >> Machine is a clone
            parent_name = machine['cloneof']
            # >> If parent already in main_pclone_dic then add clone to parent list.
            # >> If parent not there, then add parent first and then add clone.
            if parent_name not in main_pclone_dic: main_pclone_dic[parent_name] = []
            main_pclone_dic[parent_name].append(machine_name)
            # >> Add clone machine to main_clone_to_parent_dic
            main_clone_to_parent_dic[machine_name] = parent_name            
        else:
            # >> Machine is a parent. Add to main_pclone_dic if not already there.
            if machine_name not in main_pclone_dic: main_pclone_dic[machine_name] = []

    # ---------------------------------------------------------------------------------------------
    # Make empty asset list
    # ---------------------------------------------------------------------------------------------
    assets_dic = {}
    for key in machines: assets_dic[key] = fs_new_MAME_asset()

    # ---------------------------------------------------------------------------------------------
    # Improve information fields in RENDER_DB_PATH
    # ---------------------------------------------------------------------------------------------
    # >> Add genre infolabel
    if genre_dic:
        for machine_name in machines_render:
            machines_render[machine_name]['genre'] = machines[machine_name]['genre']
    elif categories_dic:
        for machine_name in machines_render:
            machines_render[machine_name]['genre'] = machines[machine_name]['catver']
    elif catlist_dic:
        for machine_name in machines_render:
            machines_render[machine_name]['genre'] = machines[machine_name]['catlist']

    # >> Add nplayers infolabel
    if nplayers_dic:
        for machine_name in machines_render:
            machines_render[machine_name]['nplayers'] = machines[machine_name]['nplayers']

    # ---------------------------------------------------------------------------------------------
    # Improve name in DAT indices and machine names
    # ---------------------------------------------------------------------------------------------
    # >> History DAT categories are Software List names.
    if history_idx_dic:
        log_debug('Updating History DAT cateogories and machine names ...')
        # >> Open Software List index if it exists.
        SL_main_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
        # >> Update category names.
        for cat_name in history_idx_dic:
            if cat_name == 'mame':
                history_idx_dic[cat_name]['name'] = 'MAME'
                # >> Improve MAME machine names
                for machine_list in history_idx_dic[cat_name]['machines']:
                    if machine_list[0] in machines_render:
                        machine_list[1] = machines_render[machine_list[0]]['description']
            elif cat_name in SL_main_catalog_dic:
                history_idx_dic[cat_name]['name'] = SL_main_catalog_dic[cat_name]['display_name']
                # >> Improve SL machine names
                

    # >> MameInfo DAT machine names.
    if mameinfo_idx_dic:
        log_debug('Updating Mameinfo DAT machine names ...')
        for cat_name in mameinfo_idx_dic:
            for machine_list in mameinfo_idx_dic[cat_name]:
                if machine_list[0] in machines_render:
                    machine_list[1] = machines_render[machine_list[0]]['description']

    # >> GameInit DAT machine names.
    if gameinit_idx_dic:
        log_debug('Updating GameInit DAT machine names ...')
        for machine_list in gameinit_idx_dic:
            if machine_list[0] in machines_render:
                machine_list[1] = machines_render[machine_list[0]]['description']

    # >> Command DAT machine names.
    if command_idx_dic:
        log_debug('Updating Command DAT machine names ...')
        for machine_list in command_idx_dic:
            if machine_list[0] in machines_render:
                machine_list[1] = machines_render[machine_list[0]]['description']

    # ---------------------------------------------------------------------------------------------
    # Generate plot in render database
    # Line 1) Controls are {Joystick}
    # Line 2) {One Vertical Raster screen}
    # Line 3) Machine [is|is not] mechanical and driver is neogeo.hpp
    # Line 4) Machine has [no coin slots| N coin slots]
    # Line 5) DAT info
    # Line 6) Machine [supports|does not support] a Software List.
    # ---------------------------------------------------------------------------------------------
    log_info('Building machine plots/descriptions ...')
    # >> Do not crash if DAT files are not used.
    if history_idx_dic:
        history_info_set  = set([ machine[0] for machine in history_idx_dic['mame']['machines'] ])
    else:
        history_info_set  = set()
    if mameinfo_idx_dic:
        mameinfo_info_set = set([ machine[0] for machine in mameinfo_idx_dic['mame'] ])
    else:
        mameinfo_info_set = set()
    gameinit_info_set = set([ machine[0] for machine in gameinit_idx_dic ])
    command_info_set  = set([ machine[0] for machine in command_idx_dic ])
    for machine_name in machines:
        m = machines[machine_name]
        DAT_list = []
        if machine_name in history_info_set: DAT_list.append('History')
        if machine_name in mameinfo_info_set: DAT_list.append('Info')
        if machine_name in gameinit_info_set: DAT_list.append('Gameinit')
        if machine_name in command_info_set: DAT_list.append('Command')
        DAT_str = ', '.join(DAT_list)
        if m['control_type']:
            controls_str = 'Controls {0}'.format(mame_get_control_str(m['control_type']))
        else:
            controls_str = 'No controls'
        mecha_str = 'Mechanical' if m['isMechanical'] else 'Non-mechanical'
        coin_str  = 'Machine has {0} coin slots'.format(m['coins']) if m['coins'] > 0 else 'Machine has no coin slots'
        SL_str    = ', '.join(m['softwarelists']) if m['softwarelists'] else ''

        plot_str_list = []
        plot_str_list.append('{0}'.format(controls_str))
        plot_str_list.append('{0}'.format(mame_get_screen_str(machine_name, m)))
        plot_str_list.append('{0} / Driver is {1}'.format(mecha_str, m['sourcefile']))
        plot_str_list.append('{0}'.format(coin_str))
        if DAT_str: plot_str_list.append('{0}'.format(DAT_str))
        if SL_str: plot_str_list.append('SL {0}'.format(SL_str))
        machines_render[machine_name]['plot'] = '\n'.join(plot_str_list)

    # ---------------------------------------------------------------------------------------------
    # Build main distributed hashed database
    # ---------------------------------------------------------------------------------------------
    log_info('Building main hashed database index ...')
    # machine_name -> MD5 -> take first letter -> a.json, b.json, ...
    # A) First create an index
    #    db_main_hash_idx = { 'machine_name' : 'a', ... }
    # B) Then traverse a list [0, 1, ..., f] and write the machines in that sub database section.
    pDialog.create('Advanced MAME Launcher', 'Building main hashed database index ...')
    db_main_hash_idx = {}
    for key in machines:
        md5_str = hashlib.md5(key).hexdigest()
        db_main_hash_idx[key] = md5_str[0]
        # log_debug('Machine {0:12s} / hash {1} / db file {2}'.format(key, md5_str, md5_str[0]))
    pDialog.update(100)
    pDialog.close()

    log_info('Building main hashed database JSON files ...')
    distributed_db_files = ['0', '1', '2', '3', '4', '5', '6', '7', 
                            '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
    pDialog.create('Advanced MAME Launcher', 'Building main hashed database JSON files ...')
    num_items = len(distributed_db_files)
    item_count = 0
    for db_prefix in distributed_db_files:
        # --- Generate dictionary in this JSON file ---
        hashed_db_dic = {}
        for key in db_main_hash_idx:
            if db_main_hash_idx[key] == db_prefix:
                machine_dic = machines[key].copy()
                # >> returns None because it mutates machine_dic
                machine_dic.update(machines_render[key])
                hashed_db_dic[key] = machine_dic
        # --- Save JSON file ---
        hash_DB_FN = PATHS.MAIN_DB_HASH_DIR.pjoin(db_prefix + '.json')
        fs_write_JSON_file(hash_DB_FN.getPath(), hashed_db_dic)
        item_count += 1
        pDialog.update(int((item_count*100) / num_items))
    pDialog.close()

    # -----------------------------------------------------------------------------
    # Update MAME control dictionary
    # -----------------------------------------------------------------------------
    control_dic['ver_mame']        = mame_version_int
    control_dic['ver_mame_str']    = mame_version_raw
    control_dic['ver_catver']      = catver_version
    control_dic['ver_catlist']     = catlist_version
    control_dic['ver_genre']       = genre_version
    control_dic['ver_nplayers']    = nplayers_version
    control_dic['ver_bestgames']   = bestgames_version
    control_dic['ver_series']      = series_version

    # >> Statistics
    control_dic['stats_processed_machines'] = stats_processed_machines
    control_dic['stats_parents']            = stats_parents
    control_dic['stats_clones']             = stats_clones
    control_dic['stats_devices']            = stats_devices
    control_dic['stats_devices_parents']    = stats_devices_parents
    control_dic['stats_devices_clones']     = stats_devices_clones
    control_dic['stats_runnable']           = stats_runnable
    control_dic['stats_runnable_parents']   = stats_runnable_parents
    control_dic['stats_runnable_clones']    = stats_runnable_clones
    control_dic['stats_samples']            = stats_samples
    control_dic['stats_samples_parents']    = stats_samples_parents
    control_dic['stats_samples_clones']     = stats_samples_clones
    control_dic['stats_BIOS']               = stats_BIOS
    control_dic['stats_BIOS_parents']       = stats_BIOS_parents
    control_dic['stats_BIOS_clones']        = stats_BIOS_clones
    control_dic['stats_coin']               = stats_coin
    control_dic['stats_coin_parents']       = stats_coin_parents
    control_dic['stats_coin_clones']        = stats_coin_clones
    control_dic['stats_nocoin']             = stats_nocoin
    control_dic['stats_nocoin_parents']     = stats_nocoin_parents
    control_dic['stats_nocoin_clones']      = stats_nocoin_clones
    control_dic['stats_mechanical']         = stats_mechanical
    control_dic['stats_mechanical_parents'] = stats_mechanical_parents
    control_dic['stats_mechanical_clones']  = stats_mechanical_clones
    control_dic['stats_dead']               = stats_dead
    control_dic['stats_dead_parents']       = stats_dead_parents
    control_dic['stats_dead_clones']        = stats_dead_clones

    # -----------------------------------------------------------------------------
    # Write JSON databases
    # -----------------------------------------------------------------------------
    log_info('Saving database JSON files ...')
    num_items = 15
    pDialog.create('Advanced MAME Launcher', 'Saving databases ...')
    pDialog.update(int((0*100) / num_items))
    fs_write_JSON_file(PATHS.MAIN_DB_PATH.getPath(), machines)
    pDialog.update(int((1*100) / num_items))
    fs_write_JSON_file(PATHS.RENDER_DB_PATH.getPath(), machines_render)
    pDialog.update(int((2*100) / num_items))
    fs_write_JSON_file(PATHS.ROMS_DB_PATH.getPath(), machines_roms)
    pDialog.update(int((3*100) / num_items))
    fs_write_JSON_file(PATHS.DEVICES_DB_PATH.getPath(), machines_devices)
    pDialog.update(int((4*100) / num_items))
    fs_write_JSON_file(PATHS.MAIN_ASSETS_DB_PATH.getPath(), assets_dic)
    pDialog.update(int((5*100) / num_items))
    fs_write_JSON_file(PATHS.MAIN_PCLONE_DIC_PATH.getPath(), main_pclone_dic)
    pDialog.update(int((6*100) / num_items))
    fs_write_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath(), control_dic)
    pDialog.update(int((7*100) / num_items))

    # >> DAT files
    fs_write_JSON_file(PATHS.HISTORY_IDX_PATH.getPath(), history_idx_dic)
    pDialog.update(int((8*100) / num_items))
    fs_write_JSON_file(PATHS.HISTORY_DB_PATH.getPath(), history_dic)
    pDialog.update(int((9*100) / num_items))
    # log_debug('mameinfo_idx_dic = {0}'.format(unicode(mameinfo_idx_dic)))
    fs_write_JSON_file(PATHS.MAMEINFO_IDX_PATH.getPath(), mameinfo_idx_dic)
    pDialog.update(int((10*100) / num_items))
    fs_write_JSON_file(PATHS.MAMEINFO_DB_PATH.getPath(), mameinfo_dic)
    pDialog.update(int((11*100) / num_items))
    fs_write_JSON_file(PATHS.GAMEINIT_IDX_PATH.getPath(), gameinit_idx_dic)
    pDialog.update(int((12*100) / num_items))
    fs_write_JSON_file(PATHS.GAMEINIT_DB_PATH.getPath(), gameinit_dic)
    pDialog.update(int((13*100) / num_items))
    fs_write_JSON_file(PATHS.COMMAND_IDX_PATH.getPath(), command_idx_dic)
    pDialog.update(int((14*100) / num_items))
    fs_write_JSON_file(PATHS.COMMAND_DB_PATH.getPath(), command_dic)
    pDialog.update(int((15*100) / num_items))
    pDialog.close()

# -------------------------------------------------------------------------------------------------
# Generates the ROM audit database. This database contains invalid ROMs also to display information
# in "View / Audit", "View MAME machine ROMs" context menu. This database also includes
# device ROMs (<device_ref> ROMs).
#
# audit_roms_dic = {
#     'machine_name ' : [
#         {
#             'crc'      : string,
#             'location' : 'zip_name/rom_name.rom'
#             'name'     : string,
#             'size'     : int,
#             'type'     : 'ROM' or 'BROM' or 'MROM' or 'XROM'
#         },
#         {
#             'location' : 'machine_name/chd_name.chd'
#             'name'     : string,
#             'sha1'     : string,
#             'type'     : 'DISK'
#         }, ...
#     ],
#     ...
# }
#
# A) Used by the ROM scanner to check how many machines may be run or not depending of the
#    ZIPs/CHDs you have. Note that depeding of the ROM set (Merged, Split, Non-merged) the number
#    of machines you can run changes.
# B) For every machine stores the ZIP/CHD required files to run the machine.
# C) A ZIP/CHD exists if and only if it is valid (CRC/SHA1 exists). Invalid ROMs are excluded.
#
# machine_archives_dic = {
#     'machine_name ' : { 'ROMs' : [name1, name2, ...], 'CHDs' : [dir/name1, dir/name2, ...] }, ...
# }
#
# A) Used by the ROM scanner to determine how many ZIPs/CHDs files you have or not.
# B) Both lists have unique elements (instead of lists there should be sets but sets are 
#    not JSON serializable).
# C) A ZIP/CHD exists if and only if it is valid (CRC/SHA1 exists). Invalid ROMs are excluded.
#
# ROM_archive_list = [ name1, name2, ..., nameN ]
# CHD_archive_list = [ dir1/name1, dir2/name2, ..., dirN/nameN ]
#
# Saves:
#   ROM_AUDIT_DB_PATH
#   ROM_SET_MACHINE_ARCHIVES_DB_PATH
#   ROM_SET_ROM_ARCHIVES_DB_PATH
#   ROM_SET_CHD_ARCHIVES_DB_PATH
#
def fs_build_ROM_audit_databases(PATHS, settings, control_dic, machines, machines_render, devices_db_dic, machine_roms):
    log_info('fs_build_ROM_audit_databases() Initialising ...')

    # --- Initialise ---
    rom_set = ['MERGED', 'SPLIT', 'NONMERGED'][settings['mame_rom_set']]
    chd_set = ['MERGED', 'SPLIT', 'NONMERGED'][settings['mame_chd_set']]
    log_info('fs_build_ROM_audit_databases() ROM set is {0}'.format(rom_set))
    log_info('fs_build_ROM_audit_databases() CHD set is {0}'.format(chd_set))
    audit_roms_dic = {}
    pDialog = xbmcgui.DialogProgress()

    # --- ROM set ---
    pDialog.create('Advanced MAME Launcher')
    if rom_set == 'MERGED':
        # In the Merged set all Parent and Clone ROMs are in the parent archive.
        # However, according to the Pleasuredome DATs, ROMs are organised like
        # this:
        #   clone_name\clone_rom_1
        #   clone_name\clone_rom_2
        #   parent_rom_1
        #   parent_rom_2
        log_info('fs_build_ROM_databases() Building Merged ROM set ...')
        pDialog.update(0, 'Building Split ROM set ...')
        num_items = len(machines)
        item_count = 0
        for m_name in sorted(machines):
            # >> Skip Devices
            if machines_render[m_name]['isDevice']: continue
            machine = machines[m_name]
            cloneof = machines_render[m_name]['cloneof']
            romof   = machine['romof']
            m_roms  = machine_roms[m_name]['roms']

            # --- ROMs ------------------------------------------------------------
            nonmerged_roms = []
            for rom in m_roms:
                location = m_name + '/' + rom['name']
                # >> Remove unused fields to save space in JSON database
                rom_t = copy.deepcopy(rom)
                if       rom_t['bios'] and     rom_t['merge']: r_type = ROM_TYPE_BROM
                elif     rom_t['bios'] and not rom_t['merge']: r_type = ROM_TYPE_XROM
                elif not rom_t['bios'] and     rom_t['merge']: r_type = ROM_TYPE_MROM
                elif not rom_t['bios'] and not rom_t['merge']: r_type = ROM_TYPE_ROM
                else:                                          r_type = ROM_TYPE_ERROR
                rom_t['type'] = r_type
                rom_t['location'] = location
                rom_t.pop('merge')
                rom_t.pop('bios')
                nonmerged_roms.append(rom_t)
            # --- Make a dictionary with device ROMs ---
            device_roms_list = []
            for device in devices_db_dic[m_name]:
                device_roms_dic = machine_roms[device]
                for rom in device_roms_dic['roms']:
                    rom_t = copy.deepcopy(rom)
                    rom_t['type'] = ROM_TYPE_DROM
                    rom_t['location'] = device + '/' + rom['name']
                    rom_t.pop('merge')
                    rom_t.pop('bios')
                    device_roms_list.append(rom_t)
            if device_roms_list: nonmerged_roms.extend(device_roms_list)
            audit_roms_dic[m_name] = nonmerged_roms

            # --- Update dialog ---
            item_count += 1
            pDialog.update((item_count*100)//num_items)
    elif rom_set == 'SPLIT':
        log_info('fs_build_ROM_databases() Building Split ROM set ...')
        pDialog.update(0, 'Building Split ROM set ...')
        num_items = len(machines)
        item_count = 0
        for m_name in sorted(machines):
            # >> Skip Devices
            if machines_render[m_name]['isDevice']: continue
            machine = machines[m_name]
            cloneof = machines_render[m_name]['cloneof']
            romof   = machine['romof']
            m_roms  = machine_roms[m_name]['roms']
            # log_info('m_name {0}'.format(m_name))
            # log_info('len(m_roms) {0}'.format(len(m_roms)))

            # --- ROMs ------------------------------------------------------------
            split_roms = []
            for rom in m_roms:
                if not cloneof:
                    # --- Parent machine ---
                    # 1. In the Split set non-merge ROMs are in the machine archive and merged ROMs
                    #    are in the parent archive.
                    if rom['merge']:
                        location = romof + '/' + rom['name']
                    else:
                        location = m_name + '/' + rom['name']
                else:
                    # --- Clone machine ---
                    # 1. In the Split set, non-merged ROMs are in the machine ZIP archive and
                    #    merged ROMs are in the parent archive. 
                    # 2. If ROM is a BIOS it is located in the romof of the parent. BIOS ROMs 
                    #    always have the merge attribute. 
                    # 3. Some machines (notably mslugN) also have non-BIOS common ROMs merged in 
                    #    neogeo.zip BIOS archive.
                    # 4. Some machines (notably XXXXX) have all ROMs merged. In other words, do not
                    #    have their own ROMs.
                    # 5. Special case: there could be duplicate ROMs with different regions.
                    #    For example, in neogeo.zip
                    #    <rom name="sm1.sm1" size="131072" crc="94416d67" sha1="42f..." region="audiobios" offset="0"/>
                    #    <rom name="sm1.sm1" size="131072" crc="94416d67" sha1="42f..." region="audiocpu" offset="0"/>
                    #
                    #    Furthermore, some machines may have more than 2 identical ROMs:
                    #    <machine name="aa3000" sourcefile="aa310.cpp" cloneof="aa310" romof="aa310">
                    #    <rom name="cmos_riscos3.bin" merge="cmos_riscos3.bin" bios="300" size="256" crc="0da2d31d" region="i2cmem"/>
                    #    <rom name="cmos_riscos3.bin" merge="cmos_riscos3.bin" bios="310" size="256" crc="0da2d31d" region="i2cmem"/>
                    #    <rom name="cmos_riscos3.bin" merge="cmos_riscos3.bin" bios="311" size="256" crc="0da2d31d" region="i2cmem"/>
                    #    <rom name="cmos_riscos3.bin" merge="cmos_riscos3.bin" bios="319" size="256" crc="0da2d31d" region="i2cmem"/>
                    #
                    if rom['merge']:
                        # >> Get merged ROM from parent
                        parent_name = cloneof
                        parent_romof = machines[parent_name]['romof']
                        parent_roms =  machine_roms[parent_name]['roms']
                        clone_rom_merged_name = rom['merge']
                        # >> Pick ROMs with same name and choose the first one.
                        parent_merged_rom_l = filter(lambda r: r['name'] == clone_rom_merged_name, parent_roms)
                        # if len(parent_merged_rom_l) != 1:
                        #     log_error('Machine "{0}" / ROM "{1}"\n'.format(m_name, rom['name']))
                        #     log_error('len(parent_merged_rom_l) = {0}'.format(len(parent_merged_rom_l)))
                        #     raise CriticalError('CriticalError')
                        parent_merged_rom = parent_merged_rom_l[0]
                        # >> Check if clone merged ROM is also merged in parent
                        if parent_merged_rom['merge']:
                            # >> ROM is in the 'romof' archive of the parent ROM
                            super_parent_name = parent_romof
                            super_parent_roms =  machine_roms[super_parent_name]['roms']
                            parent_rom_merged_name = parent_merged_rom['merge']
                            # >> Pick ROMs with same name and choose the first one.
                            super_parent_merged_rom_l = filter(lambda r: r['name'] == parent_rom_merged_name, super_parent_roms)
                            # if len(super_parent_merged_rom_l) > 1:
                            #     log_error('Machine "{0}" / ROM "{1}"\n'.format(m_name, rom['name']))
                            #     log_error('len(super_parent_merged_rom_l) = {0}\n'.format(len(super_parent_merged_rom_l)))
                            #     raise CriticalError('CriticalError')
                            super_parent_merged_rom = super_parent_merged_rom_l[0]
                            location = super_parent_name + '/' + super_parent_merged_rom['name']
                        else:
                            location = parent_name + '/' + parent_merged_rom['name']
                    else:
                        location = m_name + '/' + rom['name']
                # >> Remove unused fields to save space in JSON database
                rom_t = copy.deepcopy(rom)
                if       rom_t['bios'] and     rom_t['merge']: r_type = ROM_TYPE_BROM
                elif     rom_t['bios'] and not rom_t['merge']: r_type = ROM_TYPE_XROM
                elif not rom_t['bios'] and     rom_t['merge']: r_type = ROM_TYPE_MROM
                elif not rom_t['bios'] and not rom_t['merge']: r_type = ROM_TYPE_ROM
                else:                                          r_type = ROM_TYPE_ERROR
                rom_t['type'] = r_type
                rom_t['location'] = location
                rom_t.pop('merge')
                rom_t.pop('bios')
                split_roms.append(rom_t)

            # --- Make a dictionary with device ROMs ---
            device_roms_list = []
            for device in devices_db_dic[m_name]:
                device_roms_dic = machine_roms[device]
                for rom in device_roms_dic['roms']:
                    rom_t = copy.deepcopy(rom)
                    rom_t['type'] = ROM_TYPE_DROM
                    rom_t['location'] = device + '/' + rom['name']
                    rom_t.pop('merge')
                    rom_t.pop('bios')
                    device_roms_list.append(rom_t)
            if device_roms_list: split_roms.extend(device_roms_list)
            audit_roms_dic[m_name] = split_roms

            # --- Update dialog ---
            item_count += 1
            pDialog.update((item_count*100)//num_items)
    elif rom_set == 'NONMERGED':
        # >> In the NonMerged set all ROMs are in the machine archive, including BIOSes.
        log_info('fs_build_ROM_databases() Building Nonmerged ROM set ...')
        pDialog.update(0, 'Building Split ROM set ...')
        num_items = len(machines)
        item_count = 0
        for m_name in sorted(machines):
            # >> Skip Devices
            if machines_render[m_name]['isDevice']: continue
            machine = machines[m_name]
            cloneof = machines_render[m_name]['cloneof']
            romof   = machine['romof']
            m_roms  = machine_roms[m_name]['roms']

            # --- ROMs ------------------------------------------------------------
            nonmerged_roms = []
            for rom in m_roms:
                location = m_name + '/' + rom['name']
                # >> Remove unused fields to save space in JSON database
                rom_t = copy.deepcopy(rom)
                if       rom_t['bios'] and     rom_t['merge']: r_type = ROM_TYPE_BROM
                elif     rom_t['bios'] and not rom_t['merge']: r_type = ROM_TYPE_XROM
                elif not rom_t['bios'] and     rom_t['merge']: r_type = ROM_TYPE_MROM
                elif not rom_t['bios'] and not rom_t['merge']: r_type = ROM_TYPE_ROM
                else:                                          r_type = ROM_TYPE_ERROR
                rom_t['type'] = r_type
                rom_t['location'] = location
                rom_t.pop('merge')
                rom_t.pop('bios')
                nonmerged_roms.append(rom_t)
            # --- Make a dictionary with device ROMs ---
            device_roms_list = []
            for device in devices_db_dic[m_name]:
                device_roms_dic = machine_roms[device]
                for rom in device_roms_dic['roms']:
                    rom_t = copy.deepcopy(rom)
                    rom_t['type'] = ROM_TYPE_DROM
                    rom_t['location'] = device + '/' + rom['name']
                    rom_t.pop('merge')
                    rom_t.pop('bios')
                    device_roms_list.append(rom_t)
            if device_roms_list: nonmerged_roms.extend(device_roms_list)
            audit_roms_dic[m_name] = nonmerged_roms

            # --- Update dialog ---
            item_count += 1
            pDialog.update((item_count*100)//num_items)
    pDialog.close()

    # --- CHD set ---
    pDialog.create('Advanced MAME Launcher')
    if chd_set == 'MERGED':
        log_info('fs_build_ROM_databases() Building Merged CHD set ...')
        pDialog.update(0, 'Building Merged CHD set ...')
        num_items = len(machines)
        item_count = 0
        for m_name in sorted(machines):
            # >> Skip Devices
            if machines_render[m_name]['isDevice']: continue
            machine = machines[m_name]
            cloneof = machines_render[m_name]['cloneof']
            romof   = machine['romof']
            m_disks = machine_roms[m_name]['disks']

            # --- CHDs ------------------------------------------------------------
            split_chds = []
            for disk in m_disks:
                if not cloneof:
                    # --- Parent machine ---
                    if disk['merge']:
                        location = romof + '/' + disk['name']
                    else:
                        location = m_name + '/' + disk['name']
                else:
                    # --- Clone machine ---
                    parent_romof = machines[cloneof]['romof']
                    if disk['merge']:
                        location = romof + '/' + disk['name']
                    else:
                        location = m_name + '/' + disk['name']
                disk_t = copy.deepcopy(disk)
                disk_t['type'] = ROM_TYPE_DISK
                disk_t['location'] = location + '.chd'
                disk_t.pop('merge')
                split_chds.append(disk_t)
            # >> Apend CHDs at the end of the ROM list.
            if m_name in audit_roms_dic: audit_roms_dic[m_name].extend(split_chds)
            else:                        audit_roms_dic[m_name] = split_chds

            # --- Update dialog ---
            item_count += 1
            pDialog.update((item_count*100)//num_items)
    elif chd_set == 'SPLIT':
        log_info('fs_build_ROM_databases() Building Split CHD set ...')
        pDialog.update(0, 'Building Split CHD set ...')
        num_items = len(machines)
        item_count = 0
        for m_name in sorted(machines):
            # >> Skip Devices
            if machines_render[m_name]['isDevice']: continue
            machine = machines[m_name]
            cloneof = machines_render[m_name]['cloneof']
            romof   = machine['romof']
            m_disks = machine_roms[m_name]['disks']

            # --- CHDs ------------------------------------------------------------
            split_chds = []
            for disk in m_disks:
                if not cloneof:
                    # --- Parent machine ---
                    if disk['merge']:
                        location = romof + '/' + disk['name']
                    else:
                        location = m_name + '/' + disk['name']
                else:
                    # --- Clone machine ---
                    parent_romof = machines[cloneof]['romof']
                    if disk['merge']:
                        location = romof + '/' + disk['name']
                    else:
                        location = m_name + '/' + disk['name']
                disk_t = copy.deepcopy(disk)
                disk_t['type'] = ROM_TYPE_DISK
                disk_t['location'] = location + '.chd'
                disk_t.pop('merge')
                split_chds.append(disk_t)
            if m_name in audit_roms_dic: audit_roms_dic[m_name].extend(split_chds)
            else:                        audit_roms_dic[m_name] = split_chds

            # --- Update dialog ---
            item_count += 1
            pDialog.update((item_count*100)//num_items)
    elif chd_set == 'NONMERGED':
        log_info('fs_build_ROM_databases() Building Non-merged ROM set ...')
        pDialog.update(0, 'Building Non-merged CHD set ...')
        num_items = len(machines)
        item_count = 0
        for m_name in sorted(machines):
            # >> Skip Devices
            if machines_render[m_name]['isDevice']: continue
            machine = machines[m_name]
            cloneof = machines_render[m_name]['cloneof']
            romof   = machine['romof']
            m_disks = machine_roms[m_name]['disks']

            # --- CHDs ------------------------------------------------------------
            nonmerged_chds = []
            for disk in m_disks:
                location = m_name + '/' + disk['name']
                disk_t = copy.deepcopy(disk)
                disk_t['type'] = ROM_TYPE_DISK
                disk_t['location'] = location + '.chd'
                disk_t.pop('merge')
                nonmerged_chds.append(disk_t)
            if m_name in audit_roms_dic: audit_roms_dic[m_name].extend(split_chds)
            else:                        audit_roms_dic[m_name] = split_chds

            # --- Update dialog ---
            item_count += 1
            pDialog.update((item_count*100)//num_items)
    pDialog.close()

    # --- ROM/CHD machine index ---
    # NOTE roms_dic and chds_dic may have invalid ROMs/CHDs. However, machine_archives_dic must
    #      have only valid ROM archives (ZIP/7Z).
    # For every machine, it goes ROM by ROM and makes a list of ZIP archive locations. Then, it
    # transforms the list into a set to have a list with unique elements.
    # roms_dic/chds_dic have invalid ROMs. Skip invalid ROMs.
    machine_archives_dic = {}
    full_ROM_archive_set = set()
    full_CHD_archive_set = set()
    pDialog.create('Advanced MAME Launcher')
    pDialog.update(0, 'Building ROM and CHD archive lists ...')
    num_items = len(machines)
    item_count = 0
    for m_name in audit_roms_dic:
        rom_list = audit_roms_dic[m_name]
        machine_rom_archive_set = set()
        machine_chd_archive_set = set()
        # --- ROM list ---
        for rom in rom_list:
            if rom['type'] == ROM_TYPE_DISK:
                # >> Skip invalid CHDs
                if not rom['sha1']: continue
                chd_name = rom['location']
                machine_chd_archive_set.add(chd_name)
                full_CHD_archive_set.add(rom['location'])
            else:
                # >> Skip invalid ROMs
                if not rom['crc']: continue
                rom_str_list = rom['location'].split('/')
                zip_name = rom_str_list[0]
                machine_rom_archive_set.add(zip_name)
                archive_str = rom['location'].split('/')[0]
                # if not archive_str: continue
                full_ROM_archive_set.add(archive_str)
        machine_archives_dic[m_name] = {'ROMs' : list(machine_rom_archive_set),
                                        'CHDs' : list(machine_chd_archive_set)}
        # --- Update dialog ---
        item_count += 1
        pDialog.update((item_count*100)//num_items)
    pDialog.close()
    ROM_archive_list = list(sorted(full_ROM_archive_set))
    CHD_archive_list = list(sorted(full_CHD_archive_set))

    # -----------------------------------------------------------------------------
    # Update MAME control dictionary
    # -----------------------------------------------------------------------------
    control_dic['MAME_ZIP_files'] = len(ROM_archive_list)
    control_dic['MAME_CHD_files'] = len(CHD_archive_list)

    # --- Save databases ---
    line1_str = 'Saving audit/scanner databases ...'
    pDialog.create('Advanced MAME Launcher')
    pDialog.update(0, line1_str, 'ROM Audit DB')
    fs_write_JSON_file(PATHS.ROM_AUDIT_DB_PATH.getPath(), audit_roms_dic)
    pDialog.update(20, line1_str, 'Machine archives DB list')
    fs_write_JSON_file(PATHS.ROM_SET_MACHINE_ARCHIVES_DB_PATH.getPath(), machine_archives_dic)
    pDialog.update(40, line1_str, 'ROM List index')
    fs_write_JSON_file(PATHS.ROM_SET_ROM_ARCHIVES_DB_PATH.getPath(), ROM_archive_list)
    pDialog.update(60, line1_str, 'CHD list index')
    fs_write_JSON_file(PATHS.ROM_SET_CHD_ARCHIVES_DB_PATH.getPath(), CHD_archive_list)
    pDialog.update(80, line1_str, 'Control dictionary')
    fs_write_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath(), control_dic)
    pDialog.update(100)
    pDialog.close()

# -------------------------------------------------------------------------------------------------
#
# A) Builds the following catalog files
#    CATALOG_MAIN_PARENT_PATH
#    CATALOG_MAIN_ALL_PATH
#    CATALOG_CATVER_PARENT_PATH
#    CATALOG_CATVER_ALL_PATH
#    ...
#
# B) Build per-catalog, per-category properties database.
#    At the moment is disabled -> There are global properties in addon settings.
#    MAIN_PROPERTIES_PATH
#
# C) Catalog, Machines, etc. count
#    CATALOG_COUNT_PATH
#
#    catalog_count_dic = {
#      'Main' : {
#        num_categories : int,
#        categories : {
#          'cat_key' : { 'num_machines' : int, 'num_parents' : int }, ...
#        }, ...
#      }, ...
#    }
#
def fs_build_MAME_catalogs(PATHS, machines, machines_render, machine_roms, main_pclone_dic):
    # >> Progress dialog
    pDialog_line1 = 'Building catalogs ...'
    pDialog = xbmcgui.DialogProgress()
    pDialog.create('Advanced MAME Launcher', pDialog_line1)
    processed_filters = 0
    update_number = 0

    # --- Machine count ---
    catalog_count_dic = {
        'Main'           : { 'num_categories' : 0, 'cats' : {} },
        'Binary'         : { 'num_categories' : 0, 'cats' : {} },
        'Catver'         : { 'num_categories' : 0, 'cats' : {} },
        'Catlist'        : { 'num_categories' : 0, 'cats' : {} },
        'Genre'          : { 'num_categories' : 0, 'cats' : {} },
        'NPlayers'       : { 'num_categories' : 0, 'cats' : {} },
        'Bestgames'      : { 'num_categories' : 0, 'cats' : {} },
        'Series'         : { 'num_categories' : 0, 'cats' : {} },
        'Manufacturer'   : { 'num_categories' : 0, 'cats' : {} },
        'Year'           : { 'num_categories' : 0, 'cats' : {} },
        'Driver'         : { 'num_categories' : 0, 'cats' : {} },
        'Controls'       : { 'num_categories' : 0, 'cats' : {} },
        'Display_Tag'    : { 'num_categories' : 0, 'cats' : {} },
        'Display_Type'   : { 'num_categories' : 0, 'cats' : {} },
        'Display_Rotate' : { 'num_categories' : 0, 'cats' : {} },
        'Devices'        : { 'num_categories' : 0, 'cats' : {} },
        'BySL'           : { 'num_categories' : 0, 'cats' : {} }
    }
    NUM_CATALOGS = len(catalog_count_dic)

    # ---------------------------------------------------------------------------------------------
    # Main filters (None catalog) -----------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------
    pDialog.update(update_number, pDialog_line1, 'Building Main Catalog ...')
    main_catalog_parents = {}
    main_catalog_all = {}

    # --- Normal and Unusual machine list ---
    # Machines with Coin Slot and Non Mechanical and not Dead and not Device
    log_info('Making None catalog - Coin index ...')
    normal_parent_list = []
    normal_all_list = []
    unusual_parent_list = []
    unusual_all_list = []
    for parent_name in main_pclone_dic:
        machine_main = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_main['isMechanical']: continue
        if machine_main['coins'] == 0: continue
        if machine_main['isDead']: continue
        if machine_render['isDevice']: continue

        # --- Determinte if machine is Normal or Unusual ----
        # >> Add parent to parent list and parents and clonse to all list
        # >> Unusual machine: control_type has "only_buttons" or "gambling" or "hanafuda" or "mahjong"
        # >> Unusual machine exceptions (must be Normal and not Unusual):
        # >>  A) sourcefile ""
        if machine_main['sourcefile'] == '88games.cpp' or \
           machine_main['sourcefile'] == 'cball.cpp' or \
           machine_main['sourcefile'] == 'asteroid.cpp':
            normal_parent_list.append(parent_name)
            normal_all_list.append(parent_name)
            for clone in main_pclone_dic[parent_name]: normal_all_list.append(clone)
        elif 'only_buttons' in machine_main['control_type'] or \
             'gambling' in machine_main['control_type'] or \
             'hanafuda' in machine_main['control_type'] or \
             'mahjong' in machine_main['control_type']:
            unusual_parent_list.append(parent_name)
            unusual_all_list.append(parent_name)
            for clone in main_pclone_dic[parent_name]: unusual_all_list.append(clone)
        else:
            normal_parent_list.append(parent_name)
            normal_all_list.append(parent_name)
            for clone in main_pclone_dic[parent_name]: normal_all_list.append(clone)
    main_catalog_parents['Normal']  = {'parents'  : normal_parent_list, 'num_parents'  : len(normal_parent_list)}
    main_catalog_all['Normal']      = {'machines' : normal_all_list,    'num_machines' : len(normal_all_list)}
    main_catalog_parents['Unusual'] = {'parents'  : unusual_parent_list, 'num_parents'  : len(unusual_parent_list)}
    main_catalog_all['Unusual']     = {'machines' : unusual_all_list,    'num_machines' : len(unusual_all_list)}
    catalog_count_dic['Main']['cats']['Normal'] = {}
    catalog_count_dic['Main']['cats']['Normal']['num_parents']  = len(normal_parent_list)
    catalog_count_dic['Main']['cats']['Normal']['num_machines'] = len(normal_all_list)
    catalog_count_dic['Main']['cats']['Unusual'] = {}
    catalog_count_dic['Main']['cats']['Unusual']['num_parents']  = len(unusual_parent_list)
    catalog_count_dic['Main']['cats']['Unusual']['num_machines'] = len(unusual_all_list)

    # --- NoCoin list ---
    # A) Machines with No Coin Slot and Non Mechanical and not Dead and not Device
    log_info('Making NoCoin index ...')
    parent_list = []
    all_list = []
    for parent_name in main_pclone_dic:
        machine_main = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_main['isMechanical']: continue
        if machine_main['coins'] > 0: continue
        if machine_main['isDead']: continue
        if machine_render['isDevice']: continue
        parent_list.append(parent_name)
        all_list.append(parent_name)
        for clone in main_pclone_dic[parent_name]: all_list.append(clone)
    main_catalog_parents['NoCoin'] = {'parents'  : parent_list, 'num_parents'  : len(parent_list)}
    main_catalog_all['NoCoin']     = {'machines' : all_list,    'num_machines' : len(all_list)}
    catalog_count_dic['Main']['cats']['NoCoin'] = {}
    catalog_count_dic['Main']['cats']['NoCoin']['num_parents']  = len(parent_list)
    catalog_count_dic['Main']['cats']['NoCoin']['num_machines'] = len(all_list)

    # --- Mechanical machines ---
    # >> Mechanical machines and not Dead and not Device
    log_info('Making Mechanical index ...')
    parent_list = []
    all_list = []
    for parent_name in main_pclone_dic:
        machine_main = machines[parent_name]
        machine_render = machines_render[parent_name]
        if not machine_main['isMechanical']: continue
        if machine_main['isDead']: continue
        if machine_render['isDevice']: continue
        parent_list.append(parent_name)
        all_list.append(parent_name)
        for clone in main_pclone_dic[parent_name]: all_list.append(clone)
    main_catalog_parents['Mechanical'] = {'parents'  : parent_list, 'num_parents'  : len(parent_list)}
    main_catalog_all['Mechanical']     = {'machines' : all_list,    'num_machines' : len(all_list)}
    catalog_count_dic['Main']['cats']['Mechanical'] = {}
    catalog_count_dic['Main']['cats']['Mechanical']['num_parents']  = len(parent_list)
    catalog_count_dic['Main']['cats']['Mechanical']['num_machines'] = len(all_list)

    # --- Dead machines ---
    # >> Dead machines
    log_info('Making Dead Machines index ...')
    parent_list = []
    all_list = []
    for parent_name in main_pclone_dic:
        machine_main = machines[parent_name]
        if not machine_main['isDead']: continue

        parent_list.append(parent_name)
        all_list.append(parent_name)
        for clone in main_pclone_dic[parent_name]: all_list.append(clone)
    main_catalog_parents['Dead'] = {'parents'  : parent_list, 'num_parents'  : len(parent_list)}
    main_catalog_all['Dead']     = {'machines' : all_list,    'num_machines' : len(all_list)}
    catalog_count_dic['Main']['cats']['Dead'] = {}
    catalog_count_dic['Main']['cats']['Dead']['num_parents']  = len(parent_list)
    catalog_count_dic['Main']['cats']['Dead']['num_machines'] = len(all_list)

    # --- Device machines ---
    # >> Device machines
    log_info('Making Device Machines index ...')
    parent_list = []
    all_list = []
    for parent_name in main_pclone_dic:
        machine_render = machines_render[parent_name]
        if not machine_render['isDevice']: continue

        parent_list.append(parent_name)
        all_list.append(parent_name)
        for clone in main_pclone_dic[parent_name]: all_list.append(clone)
    main_catalog_parents['Devices'] = {'parents'  : parent_list, 'num_parents'  : len(parent_list)}
    main_catalog_all['Devices']     = {'machines' : all_list,    'num_machines' : len(all_list)}
    catalog_count_dic['Main']['cats']['Devices'] = {}
    catalog_count_dic['Main']['cats']['Devices']['num_parents']  = len(parent_list)
    catalog_count_dic['Main']['cats']['Devices']['num_machines'] = len(all_list)

    # >> Save Main catalog JSON file
    catalog_count_dic['Main']['num_categories'] = len(catalog_count_dic['Main']['cats'])
    fs_write_JSON_file(PATHS.CATALOG_MAIN_PARENT_PATH.getPath(), main_catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_MAIN_ALL_PATH.getPath(), main_catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # ---------------------------------------------------------------------------------------------
    # Binary filters ------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------
    pDialog.update(update_number, pDialog_line1, 'Building Binary Catalog ...')
    binary_catalog_parents = {}
    binary_catalog_all = {}

    # --- No-ROM machines ---
    log_info('Making No-ROMs Machines index ...')
    parent_list = []
    all_list = []
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        m_roms = machine_roms[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        if m_roms['roms']: continue
        parent_list.append(parent_name)
        all_list.append(parent_name)
        for clone in main_pclone_dic[parent_name]: all_list.append(clone)
    binary_catalog_parents['NoROM'] = {'parents'  : parent_list, 'num_parents'  : len(parent_list)}
    binary_catalog_all['NoROM']     = {'machines' : all_list,    'num_machines' : len(all_list)}
    catalog_count_dic['Binary']['cats']['NoROM'] = {}
    catalog_count_dic['Binary']['cats']['NoROM']['num_parents']  = len(parent_list)
    catalog_count_dic['Binary']['cats']['NoROM']['num_machines'] = len(all_list)

    # --- CHD machines ---
    log_info('Making CHD Machines index ...')
    parent_list = []
    all_list = []
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        if not machine_roms[parent_name]['disks']: continue
        parent_list.append(parent_name)
        all_list.append(parent_name)
        for clone in main_pclone_dic[parent_name]: all_list.append(clone)
    binary_catalog_parents['CHD'] = {'parents'  : parent_list, 'num_parents'  : len(parent_list)}
    binary_catalog_all['CHD']     = {'machines' : all_list,    'num_machines' : len(all_list)}
    catalog_count_dic['Binary']['cats']['CHD'] = {}
    catalog_count_dic['Binary']['cats']['CHD']['num_parents']  = len(parent_list)
    catalog_count_dic['Binary']['cats']['CHD']['num_machines'] = len(all_list)

    # --- Machines with samples ---
    log_info('Making Samples Machines index ...')
    parent_list = []
    all_list = []
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        if not machine['sampleof']: continue
        parent_list.append(parent_name)
        all_list.append(parent_name)
        for clone in main_pclone_dic[parent_name]: all_list.append(clone)
    binary_catalog_parents['Samples'] = {'parents'  : parent_list, 'num_parents'  : len(parent_list)}
    binary_catalog_all['Samples']     = {'machines' : all_list,    'num_machines' : len(all_list)}
    catalog_count_dic['Binary']['cats']['Samples'] = {}
    catalog_count_dic['Binary']['cats']['Samples']['num_parents']  = len(parent_list)
    catalog_count_dic['Binary']['cats']['Samples']['num_machines'] = len(all_list)

    # --- BIOS ---
    log_info('Making BIOS Machines index ...')
    parent_list = []
    all_list = []
    for parent_name in main_pclone_dic:
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        if not machine_render['isBIOS']: continue
        parent_list.append(parent_name)
        all_list.append(parent_name)
        for clone in main_pclone_dic[parent_name]: all_list.append(clone)
    binary_catalog_parents['BIOS'] = {'parents'  : parent_list, 'num_parents'  : len(parent_list)}
    binary_catalog_all['BIOS']     = {'machines' : all_list,    'num_machines' : len(all_list)}
    catalog_count_dic['Binary']['cats']['BIOS'] = {}
    catalog_count_dic['Binary']['cats']['BIOS']['num_parents']  = len(parent_list)
    catalog_count_dic['Binary']['cats']['BIOS']['num_machines'] = len(all_list)

    # >> Save Binary catalog JSON file
    catalog_count_dic['Binary']['num_categories'] = len(catalog_count_dic['Binary']['cats'])
    fs_write_JSON_file(PATHS.CATALOG_BINARY_PARENT_PATH.getPath(), binary_catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_BINARY_ALL_PATH.getPath(), binary_catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # ---------------------------------------------------------------------------------------------
    # Cataloged machine lists ---------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------
    # --- Catver catalog ---
    log_info('Making Catver catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Catver catalog ...')
    catalog_parents = {}
    catalog_all = {}
    fs_build_catalog_helper(catalog_parents, catalog_all, machines, machines_render, main_pclone_dic, 'catver')
    fs_catalog_counter('Catver', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_CATVER_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_CATVER_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Catlist catalog ---
    log_info('Making Catlist catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Catlist catalog ...')
    catalog_parents = {}
    catalog_all = {}
    fs_build_catalog_helper(catalog_parents, catalog_all, machines, machines_render, main_pclone_dic, 'catlist')
    fs_catalog_counter('Catlist', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_CATLIST_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_CATLIST_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Genre catalog ---
    log_info('Making Genre catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Genre catalog ...')
    catalog_parents = {}
    catalog_all = {}
    fs_build_catalog_helper(catalog_parents, catalog_all, machines, machines_render, main_pclone_dic, 'genre')
    fs_catalog_counter('Genre', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_GENRE_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_GENRE_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Nplayers catalog ---
    log_info('Making Nplayers catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Nplayers catalog ...')
    catalog_parents = {}
    catalog_all = {}
    fs_build_catalog_helper(catalog_parents, catalog_all, machines, machines_render, main_pclone_dic, 'nplayers')
    fs_catalog_counter('NPlayers', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_NPLAYERS_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_NPLAYERS_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Bestgames catalog ---
    log_info('Making Bestgames catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Bestgames catalog ...')
    catalog_parents = {}
    catalog_all = {}
    fs_build_catalog_helper(catalog_parents, catalog_all, machines, machines_render, main_pclone_dic, 'bestgames')
    fs_catalog_counter('Bestgames', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_BESTGAMES_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_BESTGAMES_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Series catalog ---
    log_info('Making Series catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Series catalog ...')
    catalog_parents = {}
    catalog_all = {}
    fs_build_catalog_helper(catalog_parents, catalog_all, machines, machines_render, main_pclone_dic, 'series')
    fs_catalog_counter('Series', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_SERIES_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_SERIES_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Manufacturer catalog ---
    log_info('Making Manufacturer catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Manufacturer catalog ...')
    catalog_parents = {}
    catalog_all = {}
    fs_build_catalog_helper(catalog_parents, catalog_all, machines_render, machines_render, main_pclone_dic, 'manufacturer')
    fs_catalog_counter('Manufacturer', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_MANUFACTURER_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_MANUFACTURER_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Year catalog ---
    log_info('Making Year catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Year catalog ...')
    catalog_parents = {}
    catalog_all = {}
    fs_build_catalog_helper(catalog_parents, catalog_all, machines_render, machines_render, main_pclone_dic, 'year')
    fs_catalog_counter('Year', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_YEAR_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_YEAR_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Driver catalog ---
    log_info('Making Driver catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Driver catalog ...')
    catalog_parents = {}
    catalog_all = {}
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        catalog_key = machine['sourcefile']
        if catalog_key in mame_driver_name_dic: catalog_key = mame_driver_name_dic[catalog_key]
        if catalog_key in catalog_parents:
            catalog_parents[catalog_key]['parents'].append(parent_name)
            catalog_parents[catalog_key]['num_parents'] = len(catalog_parents[catalog_key]['parents'])
            catalog_all[catalog_key]['machines'].append(parent_name)
            for clone in main_pclone_dic[parent_name]: catalog_all[catalog_key]['machines'].append(clone)
            catalog_all[catalog_key]['num_machines'] = len(catalog_all[catalog_key]['machines'])
        else:
            catalog_parents[catalog_key] = {'parents' : [parent_name], 'num_parents' : 1}
            all_list = [parent_name]
            for clone in main_pclone_dic[parent_name]: all_list.append(clone)
            catalog_all[catalog_key] = {'machines' : all_list, 'num_machines' : len(all_list)}
    fs_catalog_counter('Driver', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DRIVER_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DRIVER_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Control catalog ---
    log_info('Making Control catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Control catalog ...')
    catalog_parents = {}
    catalog_all = {}
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        # >> Order alphabetically the list
        pretty_control_type_list = mame_improve_control_type_list(machine['control_type'])
        sorted_control_type_list = sorted(pretty_control_type_list)
        # >> Maybe a setting should be added for compact or non-compact control list
        # sorted_control_type_list = mame_compress_item_list(sorted_control_type_list)
        sorted_control_type_list = mame_compress_item_list_compact(sorted_control_type_list)
        catalog_key = " / ".join(sorted_control_type_list)
        # >> Change category name for machines with no controls
        if catalog_key == '': catalog_key = '[ No controls ]'
        if catalog_key in catalog_parents:
            catalog_parents[catalog_key]['parents'].append(parent_name)
            catalog_parents[catalog_key]['num_parents'] = len(catalog_parents[catalog_key]['parents'])
            catalog_all[catalog_key]['machines'].append(parent_name)
            for clone in main_pclone_dic[parent_name]: catalog_all[catalog_key]['machines'].append(clone)
            catalog_all[catalog_key]['num_machines'] = len(catalog_all[catalog_key]['machines'])
        else:
            catalog_parents[catalog_key] = {'parents' : [parent_name], 'num_parents' : 1}
            all_list = [parent_name]
            for clone in main_pclone_dic[parent_name]: all_list.append(clone)
            catalog_all[catalog_key] = {'machines' : all_list, 'num_machines' : len(all_list)}
    fs_catalog_counter('Controls', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_CONTROL_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_CONTROL_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Display tag catalog ---
    log_info('Making Display Tag catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Display tag catalog ...')
    catalog_parents = {}
    catalog_all = {}
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        catalog_key = " / ".join(machine['display_tag'])
        # >> Change category name for machines with no display
        if catalog_key == '': catalog_key = '[ No display ]'
        if catalog_key in catalog_parents:
            catalog_parents[catalog_key]['parents'].append(parent_name)
            catalog_parents[catalog_key]['num_parents'] = len(catalog_parents[catalog_key]['parents'])
            catalog_all[catalog_key]['machines'].append(parent_name)
            for clone in main_pclone_dic[parent_name]: catalog_all[catalog_key]['machines'].append(clone)
            catalog_all[catalog_key]['num_machines'] = len(catalog_all[catalog_key]['machines'])
        else:
            catalog_parents[catalog_key] = {'parents' : [parent_name], 'num_parents' : 1}
            all_list = [parent_name]
            for clone in main_pclone_dic[parent_name]: all_list.append(clone)
            catalog_all[catalog_key] = {'machines' : all_list, 'num_machines' : len(all_list)}
    fs_catalog_counter('Display_Tag', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DISPLAY_TAG_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DISPLAY_TAG_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Display type catalog ---
    log_info('Making Display Type catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Display type catalog ...')
    catalog_parents = {}
    catalog_all = {}
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        catalog_key = " / ".join(machine['display_type'])
        # >> Change category name for machines with no display
        if catalog_key == '': catalog_key = '[ No display ]'
        if catalog_key in catalog_parents:
            catalog_parents[catalog_key]['parents'].append(parent_name)
            catalog_parents[catalog_key]['num_parents'] = len(catalog_parents[catalog_key]['parents'])
            catalog_all[catalog_key]['machines'].append(parent_name)
            for clone in main_pclone_dic[parent_name]: catalog_all[catalog_key]['machines'].append(clone)
            catalog_all[catalog_key]['num_machines'] = len(catalog_all[catalog_key]['machines'])
        else:
            catalog_parents[catalog_key] = {'parents' : [parent_name], 'num_parents' : 1}
            all_list = [parent_name]
            for clone in main_pclone_dic[parent_name]: all_list.append(clone)
            catalog_all[catalog_key] = {'machines' : all_list, 'num_machines' : len(all_list)}
    fs_catalog_counter('Display_Type', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DISPLAY_TYPE_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DISPLAY_TYPE_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Display rotate catalog ---
    log_info('Making Display Rotate catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Display rotate catalog ...')
    catalog_parents = {}
    catalog_all = {}
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        catalog_key = " / ".join(machine['display_rotate'])
        # >> Change category name for machines with no display
        if catalog_key == '': catalog_key = '[ No display ]'
        if catalog_key in catalog_parents:
            catalog_parents[catalog_key]['parents'].append(parent_name)
            catalog_parents[catalog_key]['num_parents'] = len(catalog_parents[catalog_key]['parents'])
            catalog_all[catalog_key]['machines'].append(parent_name)
            for clone in main_pclone_dic[parent_name]: catalog_all[catalog_key]['machines'].append(clone)
            catalog_all[catalog_key]['num_machines'] = len(catalog_all[catalog_key]['machines'])
        else:
            catalog_parents[catalog_key] = {'parents' : [parent_name], 'num_parents' : 1}
            all_list = [parent_name]
            for clone in main_pclone_dic[parent_name]: all_list.append(clone)
            catalog_all[catalog_key] = {'machines' : all_list, 'num_machines' : len(all_list)}
    fs_catalog_counter('Display_Rotate', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DISPLAY_ROTATE_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DISPLAY_ROTATE_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- <device> catalog ---
    log_info('Making <device> tag catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making <device> catalog ...')
    catalog_parents = {}
    catalog_all = {}
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        # >> Order alphabetically the list
        device_list = [device['att_type'] for device in machine['devices']]
        pretty_device_list = mame_improve_device_list(device_list)
        sorted_device_list = sorted(pretty_device_list)
        # >> Maybe a setting should be added for compact or non-compact control list
        # sorted_device_list = mame_compress_item_list(sorted_device_list)
        sorted_device_list = mame_compress_item_list_compact(sorted_device_list)
        catalog_key = " / ".join(sorted_device_list)
        # >> Change category name for machines with no devices
        if catalog_key == '': catalog_key = '[ No devices ]'
        if catalog_key in catalog_parents:
            catalog_parents[catalog_key]['parents'].append(parent_name)
            catalog_parents[catalog_key]['num_parents'] = len(catalog_parents[catalog_key]['parents'])
            catalog_all[catalog_key]['machines'].append(parent_name)
            for clone in main_pclone_dic[parent_name]: catalog_all[catalog_key]['machines'].append(clone)
            catalog_all[catalog_key]['num_machines'] = len(catalog_all[catalog_key]['machines'])
        else:
            catalog_parents[catalog_key] = {'parents' : [parent_name], 'num_parents' : 1}
            all_list = [parent_name]
            for clone in main_pclone_dic[parent_name]: all_list.append(clone)
            catalog_all[catalog_key] = {'machines' : all_list, 'num_machines' : len(all_list)}
    fs_catalog_counter('Devices', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DEVICE_LIST_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_DEVICE_LIST_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)

    # --- Software List catalog ---
    log_info('Making Software List catalog ...')
    pDialog.update(update_number, pDialog_line1, 'Making Software List catalog ...')
    catalog_parents = {}
    catalog_all = {}
    for parent_name in main_pclone_dic:
        machine = machines[parent_name]
        machine_render = machines_render[parent_name]
        if machine_render['isDevice']: continue # >> Skip device machines
        # >> A machine may have more than 1 software lists
        for sl_name in machine['softwarelists']:
            catalog_key = sl_name
            if catalog_key in catalog_parents:
                catalog_parents[catalog_key]['parents'].append(parent_name)
                catalog_parents[catalog_key]['num_parents'] = len(catalog_parents[catalog_key]['parents'])
                catalog_all[catalog_key]['machines'].append(parent_name)
                for clone in main_pclone_dic[parent_name]: catalog_all[catalog_key]['machines'].append(clone)
                catalog_all[catalog_key]['num_machines'] = len(catalog_all[catalog_key]['machines'])
            else:
                catalog_parents[catalog_key] = {'parents' : [parent_name], 'num_parents' : 1}
                all_list = [parent_name]
                for clone in main_pclone_dic[parent_name]: all_list.append(clone)
                catalog_all[catalog_key] = {'machines' : all_list, 'num_machines' : len(all_list)}
    fs_catalog_counter('BySL', catalog_count_dic, catalog_all, catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_SL_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_SL_ALL_PATH.getPath(), catalog_all)
    processed_filters += 1
    update_number = int((float(processed_filters) / float(NUM_CATALOGS)) * 100)
    pDialog.update(update_number)
    pDialog.close()

    # --- Create properties database with default values ------------------------------------------
    # >> Now overwrites all properties when the catalog is rebuilt.
    #    New versions must kept user set properties!
    # >> Disabled
    # mame_properties_dic = {}
    # for catalog_name in CATALOG_NAME_LIST:
    #     catalog_dic = fs_get_cataloged_dic_parents(PATHS, catalog_name)
    #     for category_name in sorted(catalog_dic):
    #         prop_key = '{0} - {1}'.format(catalog_name, category_name)
    #         mame_properties_dic[prop_key] = {'vm' : VIEW_MODE_PCLONE}
    # fs_write_JSON_file(PATHS.MAIN_PROPERTIES_PATH.getPath(), mame_properties_dic)
    # log_info('mame_properties_dic has {0} entries'.format(len(mame_properties_dic)))

    # --- Save Catalog count ----------------------------------------------------------------------
    fs_write_JSON_file(PATHS.CATALOG_COUNT_PATH.getPath(), catalog_count_dic)

# -------------------------------------------------------------------------------------------------
# Software Lists and ROM audit database building function
# -------------------------------------------------------------------------------------------------
#
# https://www.mess.org/mess/swlist_format
# The basic idea (which leads basically the whole format) is that each <software> entry should 
# correspond to a game box you could have bought in a shop, and that each <part> entry should 
# correspond to a piece (i.e. a cart, a disk or a tape) that you would have found in such a box. 
#
# --- Example 1: 32x.xml-chaotix ---
# Stored as: SL_ROMS/32x/chaotix.zip
#
# <part name="cart" interface="_32x_cart">
#   <dataarea name="rom" size="3145728">
#     <rom name="knuckles' chaotix (europe).bin" size="3145728" crc="41d63572" sha1="5c1...922" offset="000000" />
#   </dataarea>
# </part>
#
# --- Example 2: 32x.xml-doom ---
# Stored as: SL_ROMS/32x/doom.zip
#
# <part name="cart" interface="_32x_cart">
#   <feature name="pcb" value="171-6885A" />
#   <dataarea name="rom" size="3145728">
#     <rom name="mpr-17351-f.ic1" size="2097152" crc="e0ef6ebc" sha1="302...79d" offset="000000" />
#     <rom name="mpr-17352-f.ic2" size="1048576" crc="c7079709" sha1="0f2...33b" offset="0x200000" />
#   </dataarea>
# </part>
#
# --- Example 3: a800.xml-diamond3 ---
# Stored as: SL_ROMS/a800/diamond3.zip (all ROMs from all parts)
#
# <part name="cart" interface="a8bit_cart">
#   <feature name="slot" value="a800_diamond" />
#   <dataarea name="rom" size="65536">
#     <rom name="diamond gos v3.0.rom" size="65536" crc="0ead07f8" sha1="e92...730" offset="0" />
#   </dataarea>
# </part>
# <part name="flop1" interface="floppy_5_25">
#   <dataarea name="flop" size="92176">
#     <rom name="diamond paint.atr" size="92176" crc="d2994282" sha1="be8...287" offset="0" />
#   </dataarea>
# </part>
# <part name="flop2" interface="floppy_5_25">
#   <dataarea name="flop" size="92176">
#     <rom name="diamond write.atr" size="92176" crc="e1e5b235" sha1="c3c...db5" offset="0" />
#   </dataarea>
# </part>
# <part name="flop3" interface="floppy_5_25">
#   <dataarea name="flop" size="92176">
#     <rom name="diamond utilities.atr" size="92176" crc="bb48082d" sha1="eb7...4e4" offset="0" />
#   </dataarea>
# </part>
#
# --- Example 4: a2600.xml-harmbios ---
# Stored as: SL_ROMS/a2600/harmbios.zip (all ROMs from all dataareas)
#
# <part name="cart" interface="a2600_cart">
#   <feature name="slot" value="a26_harmony" />
#   <dataarea name="rom" size="0x8000">
#     <rom name="bios_updater_NTSC.cu" size="0x8000" crc="03153eb2" sha1="cd9...009" offset="0" />
#   </dataarea>
#   <dataarea name="bios" size="0x21400">
#     <rom name="hbios_106_NTSC_official_beta.bin" size="0x21400" crc="1e1d237b" sha1="8fd...1da" offset="0" />
#     <rom name="hbios_106_NTSC_beta_2.bin"        size="0x21400" crc="807b86bd" sha1="633...e9d" offset="0" />
#     <rom name="eeloader_104e_PAL60.bin"          size="0x36f8" crc="58845532" sha1="255...71c" offset="0" />
#   </dataarea>
# </part>
#
# --- Example 5: psx.xml-traid ---
# Stored as: SL_CHDS/psx/traid/tomb raider (usa) (v1.6).chd
#
# <part name="cdrom" interface="psx_cdrom">
#   <diskarea name="cdrom">
#     <disk name="tomb raider (usa) (v1.6)" sha1="697...3ac"/>
#   </diskarea>
# </part>
#
# --- Example 6: psx.xml-traida cloneof=traid ---
# Stored as: SL_CHDS/psx/traid/tomb raider (usa) (v1.5).chd
#
# <part name="cdrom" interface="psx_cdrom">
#   <diskarea name="cdrom">
#     <disk name="tomb raider (usa) (v1.5)" sha1="d48...0a9"/>
#   </diskarea>
# </part>
#
# --- Example 7: pico.xml-sanouk5 ---
# Stored as: SL_ROMS/pico/sanouk5.zip (mpr-18458-t.ic1 ROM)
# Stored as: SL_CHDS/pico/sanouk5/imgpico-001.chd
#
# <part name="cart" interface="pico_cart">
#   <dataarea name="rom" size="524288">
#     <rom name="mpr-18458-t.ic1" size="524288" crc="6340c18a" sha1="101..." offset="000000" loadflag="load16_word_swap" />
#   </dataarea>
#   <diskarea name="cdrom">
#     <disk name="imgpico-001" sha1="c93...10d" />
#   </diskarea>
# </part>
#
# -------------------------------------------------------------------------------------------------
# A) One part may have a dataarea, a diskarea, or both.
#
# B) One part may have more than one dataarea with different names.
#
# SL_roms = {
#   'sl_rom_name' : [
#     {
#       'part_name' : string,
#       'part_interface' : string,
#       'dataarea' : [
#         {
#           'name' : string,
#           'roms' : [
#             {
#               'name' : string, 'size' : int, 'crc' : string
#             },
#           ]
#         }
#       ]
#       'diskarea' : [
#         {
#           'name' : string,
#           'disks' : [
#             {
#               'name' : string, 'sha1' : string
#             },
#           ]
#         }
#       ]
#     }, ...
#   ], ...
# }
#
# -------------------------------------------------------------------------------------------------
# --- SL List ROM Audit database ---
#
# A) For each SL ROM entry, create a list of the ROM files and CHD files, names, sizes, crc/sha1
#    and location.
# SL_roms = {
#   'sl_rom_name' : [
#     {
#       'type'     : string,
#       'name'     : string,
#       'size      : int,
#       'crc'      : sting,
#       'location' : string
#     }, ...
#   ], ...
# }

#
# SL_disks = {
#   'sl_rom_name' : [
#     {
#       'type' : string,
#       'name' : string,
#       'sha1' : sting,
#       'location' : string
#     }, ...
#   ], ...
# }
#
class SLDataObj:
    def __init__(self):
        self.roms = {}
        self.SL_roms = {}
        self.display_name = ''
        self.num_with_ROMs = 0
        self.num_with_CHDs = 0

def fs_load_SL_XML(xml_filename):
    __debug_xml_parser = False
    SLData = SLDataObj()

    # --- If file does not exist return empty dictionary ---
    if not os.path.isfile(xml_filename): return SLData

    # --- Parse using cElementTree ---
    log_debug('fs_load_SL_XML() Loading XML file "{0}"'.format(xml_filename))
    # If XML has errors (invalid characters, etc.) this will rais exception 'err'
    try:
        xml_tree = ET.parse(xml_filename)
    except:
        return SLData
    xml_root = xml_tree.getroot()
    SLData.display_name = xml_root.attrib['description']
    for root_element in xml_root:
        if __debug_xml_parser: print('Root child {0}'.format(root_element.tag))

        if root_element.tag == 'software':
            rom = fs_new_SL_ROM()
            SL_rom_list = []
            num_roms = 0
            num_disks = 0
            rom_name = root_element.attrib['name']
            if 'cloneof' in root_element.attrib: rom['cloneof'] = root_element.attrib['cloneof']
            if 'romof' in root_element.attrib:
                log_error('{0} -> "romof" in root_element.attrib'.format(rom_name))
                raise CriticalError('DEBUG')

            for rom_child in root_element:
                # >> By default read strings
                xml_text = rom_child.text if rom_child.text is not None else ''
                xml_tag  = rom_child.tag
                if __debug_xml_parser: print('{0} --> {1}'.format(xml_tag, xml_text))

                # --- Only pick tags we want ---
                if xml_tag == 'description' or xml_tag == 'year' or xml_tag == 'publisher':
                    rom[xml_tag] = xml_text

                elif xml_tag == 'part':
                    # <part name="cart" interface="_32x_cart">
                    part_dic = fs_new_SL_ROM_part()
                    part_dic['name'] = rom_child.attrib['name']
                    part_dic['interface'] = rom_child.attrib['interface']
                    rom['parts'].append(part_dic)
                    SL_roms_dic = {
                        'part_name' : rom_child.attrib['name'],
                        'part_interface' : rom_child.attrib['interface']
                    }

                    # --- Count number of <dataarea> and <diskarea> tags inside this <part tag> ---
                    num_dataarea = 0
                    num_diskarea = 0
                    for part_child in rom_child:
                        if part_child.tag == 'dataarea':
                            dataarea_dic = { 'name' : part_child.attrib['name'], 'roms' : [] }
                            dataarea_num_roms = 0
                            for dataarea_child in part_child:
                                rom_dic = { 'name' : '', 'size' : '', 'crc'  : '' }
                                rom_dic['name'] = dataarea_child.attrib['name'] if 'name' in dataarea_child.attrib else ''
                                rom_dic['size'] = dataarea_child.attrib['size'] if 'size' in dataarea_child.attrib else ''
                                rom_dic['crc'] = dataarea_child.attrib['crc'] if 'crc' in dataarea_child.attrib else ''
                                dataarea_dic['roms'].append(rom_dic)
                                dataarea_num_roms += 1
                                num_roms += 1
                                # --- DEBUG: Error if rom has merge attribute ---
                                if 'merge' in dataarea_child.attrib:
                                    log_error('software {0}'.format(rom_name))
                                    log_error('rom {0} has merge attribute'.format(dataarea_child.attrib['name']))
                                    raise CriticalError('DEBUG')
                            # >> Dataarea is valid ONLY if it contains valid ROMs
                            if dataarea_num_roms > 0: num_dataarea += 1
                            if 'dataarea' not in SL_roms_dic: SL_roms_dic['dataarea'] = []
                            SL_roms_dic['dataarea'].append(dataarea_dic)
                        elif part_child.tag == 'diskarea':
                            diskarea_dic = { 'name' : part_child.attrib['name'], 'disks' : [] }
                            diskarea_num_disks = 0
                            for diskarea_child in part_child:
                                disk_dic = { 'name' : '', 'sha1' : '' }
                                disk_dic['name'] = diskarea_child.attrib['name'] if 'name' in diskarea_child.attrib else ''
                                disk_dic['sha1'] = diskarea_child.attrib['sha1'] if 'sha1' in diskarea_child.attrib else ''
                                diskarea_dic['disks'].append(disk_dic)
                                diskarea_num_disks += 1
                                num_disks += 1
                            # >> diskarea is valid ONLY if it contains valid CHDs
                            if diskarea_num_disks > 0: num_diskarea += 1
                            if 'diskarea' not in SL_roms_dic: SL_roms_dic['diskarea'] = []
                            SL_roms_dic['diskarea'].append(diskarea_dic)
                        elif part_child.tag == 'feature':
                            pass
                        elif part_child.tag == 'dipswitch':
                            pass
                        else:
                            log_error('{0} -> Inside <part>, unrecognised tag <{0}>'.format(rom_name, part_child.tag))
                            raise CriticalError('DEBUG')
                    # --- Add ROMs/disks ---
                    SL_rom_list.append(SL_roms_dic)

                    # --- DEBUG/Research code ---
                    # if num_dataarea > 1:
                    #     log_error('{0} -> num_dataarea = {1}'.format(rom_name, num_dataarea))
                    #     raise CriticalError('DEBUG')
                    # if num_diskarea > 1:
                    #     log_error('{0} -> num_diskarea = {1}'.format(rom_name, num_diskarea))
                    #     raise CriticalError('DEBUG')
                    # if num_dataarea and num_diskarea:
                    #     log_error('{0} -> num_dataarea = {1}'.format(rom_name, num_dataarea))
                    #     log_error('{0} -> num_diskarea = {1}'.format(rom_name, num_diskarea))
                    #     raise CriticalError('DEBUG')

            # --- Finished processing of <software> element ---
            if num_roms:
                rom['hasROMs'] = True
                rom['status_ROM'] = '?'
                SLData.num_with_ROMs += 1
            else:
                rom['hasROMs'] = False
                rom['status_ROM'] = '-'
            if num_disks:
                rom['hasCHDs'] = True
                rom['status_CHD'] = '?'
                SLData.num_with_CHDs += 1
            else:
                rom['hasCHDs'] = False
                rom['status_CHD'] = '-'

            # >> Add <software> element (SL ROM) to database and software ROM/CHDs to database
            SLData.roms[rom_name] = rom
            SLData.SL_roms[rom_name] = SL_rom_list

    return SLData

# -------------------------------------------------------------------------------------------------
# SL_catalog = { 'name' : {
#     'display_name': u'', 'num_with_CHDs' : int, 'num_with_ROMs' : int, 'rom_DB_noext' : u'' }, ...
# }
#
# Saves:
# SL_INDEX_PATH,
# SL_MACHINES_PATH,
# SL_PCLONE_DIC_PATH,
# per-SL database                          (32x.json)
# per-SL database                          (32x_ROMs.json)
# per-SL ROM audit database                (32x_ROM_audit.json)
# per-SL software archies (ROMs and CHDs)  (32x_software_archives.json)
#
def fs_build_SoftwareLists_databases(PATHS, settings, machines, machines_render, main_pclone_dic, control_dic):
    SL_dir_FN = FileName(settings['SL_hash_path'])
    log_debug('fs_build_SoftwareLists_index() SL_dir_FN "{0}"'.format(SL_dir_FN.getPath()))

    # --- Scan all XML files in Software Lists directory and save SL and SL ROMs databases ---
    pDialog = xbmcgui.DialogProgress()
    pDialog_canceled = False
    pdialog_line1 = 'Building Sofware Lists ROM databases ...'
    pDialog.create('Advanced MAME Launcher', pdialog_line1)
    SL_file_list = SL_dir_FN.scanFilesInPath('*.xml')
    total_SL_files = len(SL_file_list)
    num_SL_with_ROMs = 0
    num_SL_with_CHDs = 0
    SL_catalog_dic = {}
    processed_files = 0
    for file in sorted(SL_file_list):
        # log_debug('fs_build_SoftwareLists_index() Processing "{0}"'.format(file))
        FN = FileName(file)

        # >> Open software list XML and parse it. Then, save data fields we want in JSON.
        SL_path_FN = FileName(file)
        SLData = fs_load_SL_XML(SL_path_FN.getPath())
        output_FN = PATHS.SL_DB_DIR.pjoin(FN.getBase_noext() + '.json')
        fs_write_JSON_file(output_FN.getPath(), SLData.roms)
        output_FN = PATHS.SL_DB_DIR.pjoin(FN.getBase_noext() + '_ROMs.json')
        fs_write_JSON_file(output_FN.getPath(), SLData.SL_roms)

        # >> Add software list to catalog
        num_SL_with_ROMs += SLData.num_with_ROMs
        num_SL_with_CHDs += SLData.num_with_CHDs
        SL = {'display_name'  : SLData.display_name, 
              'num_with_ROMs' : SLData.num_with_ROMs,
              'num_with_CHDs' : SLData.num_with_CHDs,
              'rom_DB_noext'  : FN.getBase_noext()
        }
        SL_catalog_dic[FN.getBase_noext()] = SL

        # >> Update progress
        processed_files += 1
        pDialog.update((processed_files*100) // total_SL_files, pdialog_line1, 'File {0} ...'.format(FN.getBase()))
    fs_write_JSON_file(PATHS.SL_INDEX_PATH.getPath(), SL_catalog_dic)

    # --- Make the SL ROM/CHD unified Audit databases ---
    log_info('Building Software List ROM Audit database ...')
    pdialog_line1 = 'Building Software List ROM Audit database ...'
    pDialog.update(0, pdialog_line1)
    total_files = len(SL_file_list)
    processed_files = 0
    for file in sorted(SL_file_list):
        # >> Filenames of the databases.
        FN = FileName(file)
        SL_ROMs_DB_FN = PATHS.SL_DB_DIR.pjoin(FN.getBase_noext() + '_ROMs.json')
        SL_ROM_Audit_DB_FN = PATHS.SL_DB_DIR.pjoin(FN.getBase_noext() + '_ROM_audit.json')
        SL_Soft_Archives_DB_FN = PATHS.SL_DB_DIR.pjoin(FN.getBase_noext() + '_software_archives.json')

        # >> Open software list XML and parse it. Then, save data fields we want in JSON.
        SL_roms = fs_load_JSON_file(SL_ROMs_DB_FN.getPath())

        # >> Traverse list of ROMs and make a list of ROMs and CHDs. Also compute ROM locations.
        SL_Audit_ROMs = {}
        SL_Software_Archives = {}
        SL_name = FN.getBase_noext()
        for SL_rom in SL_roms:
            SL_Audit_ROMs[SL_rom] = []

            # >> Iterate Parts in a SL Software item.
            rom_db_list = SL_roms[SL_rom]
            soft_item_has_ROMs = False
            soft_item_disk_list = []
            for part_dic in rom_db_list:
                # part_name = part_dic['part_name']
                # part_interface = part_dic['part_interface']
                if 'dataarea' in part_dic:
                    # >> Iterate Dataareas
                    for dataarea_dic in part_dic['dataarea']:
                        # dataarea_name = dataarea_dic['name']
                        # >> Interate ROMs in dataarea
                        for rom_dic in dataarea_dic['roms']:
                            rom_audit_dic = {'type' : '', 'name' : '', 'size' : '', 'crc' : '',
                                             'location' : ''}
                            rom_audit_dic['type']     = ROM_TYPE_ROM
                            rom_audit_dic['name']     = rom_dic['name']
                            rom_audit_dic['size']     = rom_dic['size']
                            rom_audit_dic['crc']      = rom_dic['crc']
                            rom_audit_dic['location'] = SL_name + '/' + SL_rom + '/' + rom_dic['name']
                            SL_Audit_ROMs[SL_rom].append(rom_audit_dic)
                            soft_item_has_ROMs = True
                if 'diskarea' in part_dic:
                    # >> Iterate Diskareas
                    for diskarea_dic in part_dic['diskarea']:
                        # diskarea_name = diskarea_dic['name']
                        # >> Iterate DISKs in diskarea
                        for disk_dic in diskarea_dic['disks']:
                            disk_audit_dic = {'type' : '', 'name' : '', 'sha1' : '', 'location' : ''}
                            disk_audit_dic['type']     = ROM_TYPE_DISK
                            disk_audit_dic['name']     = disk_dic['name']
                            disk_audit_dic['sha1']     = disk_dic['sha1']
                            disk_audit_dic['location'] = SL_name + '/' + SL_rom + '/' + disk_dic['name'] + '.chd'
                            SL_Audit_ROMs[SL_rom].append(disk_audit_dic)
                            soft_item_disk_list.append(disk_dic['name'] + '.chd')

            # >> Compute Software Archives
            SL_Software_Archives[SL_rom] = { 'ROMs' : [], 'CHDs' : [] }
            if soft_item_has_ROMs:
                SL_Software_Archives[SL_rom]['ROMs'].append(SL_rom)
            if soft_item_disk_list:
                SL_Software_Archives[SL_rom]['CHDs'].extend(soft_item_disk_list)

        # >> Save databases
        fs_write_JSON_file(SL_ROM_Audit_DB_FN.getPath(), SL_Audit_ROMs)
        fs_write_JSON_file(SL_Soft_Archives_DB_FN.getPath(), SL_Software_Archives)
        # >> Update progress
        processed_files += 1
        pDialog.update((processed_files*100) // total_files, pdialog_line1, 'File {0} ...'.format(FN.getBase()))

    # --- Make SL Parent/Clone databases ---
    log_info('Building Software List PClone list ...')
    pdialog_line1 = 'Building Software List PClone list ...'
    pDialog.update(0, pdialog_line1)
    total_files = len(SL_catalog_dic)
    processed_files = 0
    SL_PClone_dic = {}
    for sl_name in sorted(SL_catalog_dic):
        pclone_dic = {}
        SL_database_FN = PATHS.SL_DB_DIR.pjoin(sl_name + '.json')
        ROMs = fs_load_JSON_file(SL_database_FN.getPath())
        for rom_name in ROMs:
            ROM = ROMs[rom_name]
            if ROM['cloneof']:
                parent_name = ROM['cloneof']
                if parent_name not in pclone_dic: pclone_dic[parent_name] = []
                pclone_dic[parent_name].append(rom_name)
            else:
                if rom_name not in pclone_dic: pclone_dic[rom_name] = []
        SL_PClone_dic[sl_name] = pclone_dic
        # >> Update progress
        processed_files += 1
        pDialog.update((processed_files*100) // total_files, pdialog_line1, 'File {0} ...'.format(sl_name))
    fs_write_JSON_file(PATHS.SL_PCLONE_DIC_PATH.getPath(), SL_PClone_dic)

    # --- Make a list of machines that can launch each SL ---
    log_info('Making Software List machine list ...')
    pdialog_line1 = 'Building Software List machine list ...'
    pDialog.update(0, pdialog_line1)
    total_SL = len(SL_catalog_dic)
    processed_SL = 0
    SL_machines_dic = {}
    for SL_name in sorted(SL_catalog_dic):
        SL_machine_list = []
        for machine_name in machines:
            # if not machines[machine_name]['softwarelists']: continue
            for machine_SL_name in machines[machine_name]['softwarelists']:
                if machine_SL_name == SL_name:
                    SL_machine_dic = {'machine'     : machine_name,
                                      'description' : machines_render[machine_name]['description'],
                                      'devices'     : machines[machine_name]['devices']}
                    SL_machine_list.append(SL_machine_dic)
        SL_machines_dic[SL_name] = SL_machine_list

        # >> Update progress
        processed_SL += 1
        pDialog.update((processed_SL*100) // total_SL, pdialog_line1, 'SL {0} ...'.format(SL_name))
    fs_write_JSON_file(PATHS.SL_MACHINES_PATH.getPath(), SL_machines_dic)

    # --- Rebuild Machine by Software List catalog with knowledge of the SL proper name ---
    log_info('Making Software List catalog ...')
    pDialog.update(0, 'Rebuilding Software List catalog ...')
    catalog_parents = {}
    catalog_all = {}
    for parent_name in main_pclone_dic:
        # >> A machine may have more than 1 software lists
        for sl_name in machines[parent_name]['softwarelists']:
            if sl_name in SL_catalog_dic:
                sl_name = SL_catalog_dic[sl_name]['display_name']
            else:
                log_warning('sl_name = "{0}" not found in SL_catalog_dic'.format(sl_name))
                log_warning('In other words, there is no {0}.xlm SL database'.format(sl_name))
            catalog_key = sl_name
            if catalog_key in catalog_parents:
                catalog_parents[catalog_key]['parents'].append(parent_name)
                catalog_parents[catalog_key]['num_parents'] = len(catalog_parents[catalog_key]['parents'])
                catalog_all[catalog_key]['machines'].append(parent_name)
                for clone in main_pclone_dic[parent_name]: catalog_all[catalog_key]['machines'].append(clone)
                catalog_all[catalog_key]['num_machines'] = len(catalog_all[catalog_key]['machines'])
            else:
                catalog_parents[catalog_key] = {'parents' : [parent_name], 'num_parents' : 1}
                all_list = [parent_name]
                for clone in main_pclone_dic[parent_name]: all_list.append(clone)
                catalog_all[catalog_key] = {'machines' : all_list, 'num_machines' : len(all_list)}
    # >> Include Software Lists with no machines in the catalog. In other words, there are
    #    software lists that apparently cannot be launched by any machine.
    for sl_name in sorted(SL_catalog_dic):
        catalog_key = SL_catalog_dic[sl_name]['display_name']
        if not catalog_key in catalog_parents:
            catalog_parents[catalog_key] = {'parents' : list(), 'num_parents' : 0}
            catalog_all[catalog_key] = {'machines' : list(), 'num_machines' : 0}

    fs_write_JSON_file(PATHS.CATALOG_SL_PARENT_PATH.getPath(), catalog_parents)
    fs_write_JSON_file(PATHS.CATALOG_SL_ALL_PATH.getPath(), catalog_all)
    pDialog.update(100)
    pDialog.close()

    # --- Create properties database with default values ---
    # --- Make SL properties DB ---
    # >> Allows customisation of every SL list window
    # >> Not used at the moment -> Global properties
    # SL_properties_dic = {}
    # for sl_name in SL_catalog_dic:
    #     # 'vm' : VIEW_MODE_NORMAL or VIEW_MODE_ALL
    #     prop_dic = {'vm' : VIEW_MODE_NORMAL}
    #     SL_properties_dic[sl_name] = prop_dic
    # fs_write_JSON_file(PATHS.SL_MACHINES_PROP_PATH.getPath(), SL_properties_dic)
    # log_info('SL_properties_dic has {0} items'.format(len(SL_properties_dic)))

    # >> One of the MAME catalogs has changed, and so the property names.
    # >> Not used at the moment -> Global properties
    # mame_properties_dic = {}
    # for catalog_name in CATALOG_NAME_LIST:
    #     catalog_dic = fs_get_cataloged_dic_parents(PATHS, catalog_name)
    #     for category_name in sorted(catalog_dic):
    #         prop_key = '{0} - {1}'.format(catalog_name, category_name)
    #         mame_properties_dic[prop_key] = {'vm' : VIEW_MODE_NORMAL}
    # fs_write_JSON_file(PATHS.MAIN_PROPERTIES_PATH.getPath(), mame_properties_dic)
    # log_info('mame_properties_dic has {0} items'.format(len(mame_properties_dic)))

    # --- SL statistics and save control_dic ---
    control_dic['SL_XML_files'] = total_SL_files
    control_dic['SL_with_ROMs'] = num_SL_with_ROMs
    control_dic['SL_with_CHDs'] = num_SL_with_CHDs
    fs_write_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath(), control_dic)

# -------------------------------------------------------------------------------------------------
# ROM/CHD scanner
# -------------------------------------------------------------------------------------------------
# Does not save any file. machines_render and control_dic modified by assigment
def fs_scan_MAME_ROMs(PATHS, settings,
                      control_dic, machines, machines_render,
                      machine_archives_dic, ROM_archive_list, CHD_archive_list,
                      ROM_path_FN, CHD_path_FN, Samples_path_FN,
                      scan_CHDs, scan_Samples):
    # --- Initialise ---
    # mame_rom_set = settings['mame_rom_set']
    # mame_chd_set = settings['mame_chd_set']

    # --- Scan ROMs ---
    pDialog = xbmcgui.DialogProgress()
    pDialog_canceled = False
    pDialog.create('Advanced MAME Launcher', 'Scanning MAME machine archives (ROMs and CHDs) ...')
    total_machines = len(machines_render)
    processed_machines = 0
    scan_ROM_machines_total = 0
    scan_ROM_machines_have = 0
    scan_ROM_machines_missing = 0
    scan_CHD_machines_total = 0
    scan_CHD_machines_have = 0
    scan_CHD_machines_missing = 0
    report_list = []
    for key in sorted(machines_render):
        # --- Initialise machine ---
        # log_info('_command_setup_plugin() Checking machine {0}'.format(key))
        if machines_render[key]['isDevice']: continue # Skip Devices
        m_str_list = []

        # --- ROMs ---
        rom_list = machine_archives_dic[key]['ROMs']
        if rom_list:
            have_rom_list = [False] * len(rom_list)
            for i, rom in enumerate(rom_list):
                archive_name = rom + '.zip'
                ROM_FN = ROM_path_FN.pjoin(archive_name)
                if ROM_FN.exists():
                    have_rom_list[i] = True
                else:
                    m_str_list.append('Missing ROM {0}'.format(archive_name))
            scan_ROM_machines_total += 1
            if all(have_rom_list):
                # --- All ZIP files required to run this machine exist ---
                ROM_flag = 'R'
                scan_ROM_machines_have += 1
            else:
                ROM_flag = 'r'
                scan_ROM_machines_missing += 1
        else:
            ROM_flag = '-'
        fs_set_ROM_flag(machines_render[key], ROM_flag)

        # --- Disks ---
        chd_list = machine_archives_dic[key]['CHDs']
        if chd_list and scan_CHDs:
            scan_CHD_machines_total += 1
            has_chd_list = [False] * len(chd_list)
            for idx, chd_name in enumerate(chd_list):
                CHD_FN = CHD_path_FN.pjoin(chd_name)
                if CHD_FN.exists():
                    has_chd_list[idx] = True
                else:
                    m_str_list.append('Missing CHD {0}'.format(chd_name))
            if all(has_chd_list):
                CHD_flag = 'C'
                scan_CHD_machines_have += 1
            else:
                CHD_flag = 'c'
                scan_CHD_machines_missing += 1
        elif chd_list and not scan_CHDs:
            scan_CHD_machines_total += 1
            CHD_flag = 'c'
            scan_CHD_machines_missing += 1
        else:
            CHD_flag = '-'
        fs_set_CHD_flag(machines_render[key], CHD_flag)

        # >> Build report.
        if m_str_list:
            report_list.append('Machine {0} [{1}]'.format(key, machines_render[key]['description']))
            if machines_render[key]['cloneof']:
                cloneof = machines_render[key]['cloneof']
                report_list.append('cloneof {0} [{1}]'.format(cloneof, machines_render[cloneof]['description']))
            report_list.extend(m_str_list)
            report_list.append('')

        # >> Progress dialog
        processed_machines += 1
        pDialog.update((processed_machines*100) // total_machines)
    pDialog.close()

    # >> Write report
    log_info('Writing ROM machines report file "{0}"'.format(PATHS.REPORT_MAME_SCAN_MACHINE_ARCH_PATH.getPath()))
    with open(PATHS.REPORT_MAME_SCAN_MACHINE_ARCH_PATH.getPath(), 'w') as file:
        file.write('\n'.join(report_list).encode('utf-8'))

    # --- ROM list ---
    pDialog = xbmcgui.DialogProgress()
    pDialog_canceled = False
    pDialog.create('Advanced MAME Launcher', 'Scanning MAME archive ROMs ...')
    total_machines = len(machines_render)
    processed_machines = 0
    scan_ZIP_files_total = 0
    scan_ZIP_files_have = 0
    scan_ZIP_files_missing = 0
    r_list = []
    for rom_name in ROM_archive_list:
        scan_ZIP_files_total += 1
        ROM_FN = ROM_path_FN.pjoin(rom_name + '.zip')
        if ROM_FN.exists():
            scan_ZIP_files_have += 1
        else:
            scan_ZIP_files_missing += 1
            r_list.append('Missing {0}\n'.format(ROM_FN.getPath()))
        # >> Progress dialog
        processed_machines += 1
        pDialog.update((processed_machines*100) // total_machines)
    pDialog.close()
    # >> Write report
    log_info('Opening ROM archives report file "{0}"'.format(PATHS.REPORT_MAME_SCAN_ROM_LIST_PATH.getPath()))
    with open(PATHS.REPORT_MAME_SCAN_ROM_LIST_PATH.getPath(), 'w') as file:
        for line in r_list: file.write(line.encode('utf-8'))

    # --- CHD list ---
    pDialog.create('Advanced MAME Launcher', 'Scanning MAME CHDs ...')
    total_machines = len(machines_render)
    processed_machines = 0
    scan_CHD_files_total = 0
    scan_CHD_files_have = 0
    scan_CHD_files_missing = 0
    r_list = []
    for chd_name in CHD_archive_list:
        scan_CHD_files_total += 1
        CHD_FN = CHD_path_FN.pjoin(chd_name + '.chd')
        if CHD_FN.exists():
            scan_CHD_files_have += 1
        else:
            scan_CHD_files_missing += 1
            r_list.append('Missing CHD {0}\n'.format(CHD_FN.getPath()))
        # >> Progress dialog
        processed_machines += 1
        pDialog.update((processed_machines*100) // total_machines)
    pDialog.close()
    # >> Write report
    log_info('Opening CHD archives report file "{0}"'.format(PATHS.REPORT_MAME_SCAN_CHD_LIST_PATH.getPath()))
    with open(PATHS.REPORT_MAME_SCAN_CHD_LIST_PATH.getPath(), 'w') as file:
        for line in r_list: file.write(line.encode('utf-8'))

    # --- Scan Samples ---
    pDialog.create('Advanced MAME Launcher', 'Scanning MAME Samples ...')
    total_machines = len(machines_render)
    processed_machines = 0
    scan_Samples_have = 0
    scan_Samples_missing = 0
    scan_Samples_total = 0
    r_list = []
    for key in sorted(machines):
        if machines[key]['sampleof']:
            scan_Samples_total += 1
            if scan_Samples:
                Sample_FN = Samples_path_FN.pjoin(key + '.zip')
                if Sample_FN.exists():
                    Sample_flag = 'S'
                    scan_Samples_have += 1
                else:
                    Sample_flag = 's'
                    scan_Samples_missing += 1
                    r_list.append('Missing Sample {0}\n'.format(Sample_FN.getPath()))
            else:
                Sample_flag = 's'
                scan_Samples_missing += 1
        else:
            Sample_flag = '-'
        fs_set_Sample_flag(machines_render[key], Sample_flag)
        # >> Progress dialog
        processed_machines += 1
        pDialog.update((processed_machines*100) // total_machines)
    pDialog.close()
    # >> Write report
    log_info('Opening Samples report file "{0}"'.format(PATHS.REPORT_MAME_SCAN_SAMP_PATH.getPath()))
    with open(PATHS.REPORT_MAME_SCAN_SAMP_PATH.getPath(), 'w') as file:
        for line in r_list: file.write(line.encode('utf-8'))

    # --- Update statistics ---
    control_dic['scan_ZIP_files_total']      = scan_ZIP_files_total
    control_dic['scan_ZIP_files_have']       = scan_ZIP_files_have
    control_dic['scan_ZIP_files_missing']    = scan_ZIP_files_missing
    control_dic['scan_CHD_files_total']      = scan_CHD_files_total
    control_dic['scan_CHD_files_have']       = scan_CHD_files_have
    control_dic['scan_CHD_files_missing']    = scan_CHD_files_missing
    
    control_dic['scan_ROM_machines_total']   = scan_ROM_machines_total
    control_dic['scan_ROM_machines_have']    = scan_ROM_machines_have
    control_dic['scan_ROM_machines_missing'] = scan_ROM_machines_missing
    control_dic['scan_CHD_machines_total']   = scan_CHD_machines_total
    control_dic['scan_CHD_machines_have']    = scan_CHD_machines_have
    control_dic['scan_CHD_machines_missing'] = scan_CHD_machines_missing

    control_dic['scan_Samples_have']    = scan_Samples_have
    control_dic['scan_Samples_missing'] = scan_Samples_missing
    control_dic['scan_Samples_total']   = scan_Samples_total

# -------------------------------------------------------------------------------------------------
# Saves SL JSON databases, MAIN_CONTROL_PATH.
#
def fs_scan_SL_ROMs(PATHS, SL_catalog_dic, control_dic, SL_hash_dir_FN, SL_ROM_dir_FN):
    # >> SL ROMs: Traverse Software List, check if ROM exists, update and save database
    pDialog = xbmcgui.DialogProgress()
    pdialog_line1 = 'Scanning Sofware Lists ROMs/CHDs ...'
    pDialog.create('Advanced MAME Launcher', pdialog_line1)
    pDialog.update(0)
    total_files = len(SL_catalog_dic)
    processed_files = 0
    SL_ROMs_have = 0
    SL_ROMs_missing = 0
    SL_ROMs_total = 0
    SL_CHDs_have = 0
    SL_CHDs_missing = 0
    SL_CHDs_total = 0
    report_list = []
    for SL_name in sorted(SL_catalog_dic):
        SL_DB_FN = SL_hash_dir_FN.pjoin(SL_name + '.json')
        SL_SOFT_ARCHIVES_DB_FN = SL_hash_dir_FN.pjoin(SL_name + '_software_archives.json')
        sl_roms = fs_load_JSON_file(SL_DB_FN.getPath())
        soft_archives = fs_load_JSON_file(SL_SOFT_ARCHIVES_DB_FN.getPath())

        for rom_key in sorted(sl_roms):
            m_str_list = []
            rom = sl_roms[rom_key]

            # --- ROMs ---
            rom_list = soft_archives[rom_key]['ROMs']
            if rom_list:
                have_rom_list = [False] * len(rom_list)
                for i, rom_archive in enumerate(rom_list):
                    SL_ROMs_total += 1
                    archive_name = rom_archive + '.zip'
                    SL_ROM_FN = SL_ROM_dir_FN.pjoin(SL_name).pjoin(archive_name)
                    # log_debug('Scanning "{0}"'.format(SL_ROM_FN.getPath()))
                    if SL_ROM_FN.exists():
                        have_rom_list[i] = True
                    else:
                        m_str_list.append('Missing SL ROM {0}'.format(SL_ROM_FN.getPath()))
                if all(have_rom_list):
                    rom['status_ROM'] = 'R'
                    SL_ROMs_have += 1
                else:
                    rom['status_ROM'] = 'r'
                    SL_ROMs_missing += 1
            else:
                rom['status_ROM'] = '-'

            # --- Disks ---
            chd_list = soft_archives[rom_key]['CHDs']
            if chd_list:
                SL_CHDs_total += 1
                has_chd_list = [False] * len(chd_list)
                for idx, chd_name in enumerate(chd_list):
                    SL_CHD_FN = SL_ROM_dir_FN.pjoin(SL_name).pjoin(rom_key).pjoin(CHD_name + '.chd')
                    # log_debug('Scanning "{0}"'.format(SL_CHD_FN.getPath()))
                    if SL_CHD_FN.exists():
                        has_chd_list[idx] = True
                    else:
                        m_str_list.append('Missing SL CHD {0}'.format(SL_CHD_FN.getPath()))
                if all(has_chd_list):
                    rom['status_CHD'] = 'C'
                    SL_CHDs_have += 1
                else:
                    rom['status_CHD'] = 'c'
                    SL_CHDs_missing += 1
            else:
                rom['status_CHD'] = '-'

            # --- Build report ---
            if m_str_list:
                report_list.append('SL {0} Software Item {0}'.format(SL_name, rom_key))
                # if machines_render[rom_key]['cloneof']:
                #     cloneof = machines_render[rom_key]['cloneof']
                #     report_list.append('cloneof {0} [{1}]'.format(cloneof, machines_render[cloneof]['description']))
                report_list.extend(m_str_list)
                report_list.append('')
        # >> Save SL database to update flags.
        fs_write_JSON_file(SL_DB_FN.getPath(), sl_roms)
        processed_files += 1
        update_number = (processed_files*100) // total_files
        pDialog.update(update_number, pdialog_line1, 'Software List {0} ...'.format(SL_name))
    pDialog.close()

    # >> Write report
    log_info('Opening SL ROMs report file "{0}"'.format(PATHS.REPORT_SL_SCAN_MACHINE_ARCH_PATH.getPath()))
    with open(PATHS.REPORT_SL_SCAN_MACHINE_ARCH_PATH.getPath(), 'w') as file:
        file.write('\n'.join(report_list).encode('utf-8'))

    # >> Not coded yet
    # log_info('Opening SL ROMs report file "{0}"'.format(PATHS.REPORT_SL_SCAN_ROM_LIST_PATH.getPath()))
    # with open(PATHS.REPORT_SL_SCAN_ROM_LIST_PATH.getPath(), 'w') as file:
    #     file.write('\n'.join(report_list).encode('utf-8'))

    # >> Not coded yet
    # log_info('Opening SL ROMs report file "{0}"'.format(PATHS.REPORT_SL_SCAN_CHD_LIST_PATH.getPath()))
    # with open(PATHS.REPORT_SL_SCAN_CHD_LIST_PATH.getPath(), 'w') as file:
    #     file.write('\n'.join(report_list).encode('utf-8'))

    # >> Update statistics
    control_dic['SL_ROMs_have']    = SL_ROMs_have
    control_dic['SL_ROMs_missing'] = SL_ROMs_missing
    control_dic['SL_ROMs_total']   = SL_ROMs_total
    control_dic['SL_CHDs_have']    = SL_CHDs_have
    control_dic['SL_CHDs_missing'] = SL_CHDs_missing
    control_dic['SL_CHDs_total']   = SL_CHDs_total

    # >> Save databases
    fs_write_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath(), control_dic)

def fs_scan_MAME_assets(PATHS, machines, Asset_path_FN):
    # >> Iterate machines, check if assets/artwork exist.
    pDialog = xbmcgui.DialogProgress()
    pDialog_canceled = False
    pDialog.create('Advanced MAME Launcher', 'Scanning MAME assets/artwork...')
    total_machines = len(machines)
    processed_machines = 0
    assets_dic = {}
    table_str = []
    table_str.append(['left', 'left', 'left',   'left', 'left', 'left', 'left', 'left', 'left',  'left', 'left'])
    table_str.append(['Name', 'Cab',  'CPanel', 'Fly',  'Mar',  'PCB',  'Snap', 'Tit',  'Clear', 'Tra',  'Man'])
    have_count_list = [0] * len(ASSET_MAME_KEY_LIST)
    for key in sorted(machines):
        machine = machines[key]

        # >> Scan assets
        machine_assets = fs_new_MAME_asset()
        asset_row = ['---'] * len(ASSET_MAME_KEY_LIST)
        for idx, asset_key in enumerate(ASSET_MAME_KEY_LIST):
            full_asset_dir_FN = Asset_path_FN.pjoin(ASSET_MAME_PATH_LIST[idx])
            if asset_key == 'trailer':
                asset_FN = full_asset_dir_FN.pjoin(key + '.mp4')
            elif asset_key == 'manual':
                machine_assets[asset_key] = ''
                continue
            else:
                asset_FN = full_asset_dir_FN.pjoin(key + '.png')
            if asset_FN.exists():
                machine_assets[asset_key] = asset_FN.getOriginalPath()
                have_count_list[idx] += 1
                asset_row[idx] = 'YES'
            else:
                machine_assets[asset_key] = ''
        table_row = [key] + asset_row
        # table_row.extend(asset_row)
        table_str.append(table_row)
        assets_dic[key] = machine_assets
        processed_machines += 1
        pDialog.update((processed_machines*100) // total_machines)
    pDialog.close()

    # >> Asset statistics and report.
    report_str_list = []
    report_str_list.append('Number of MAME machines {0}'.format(total_machines))
    report_str_list.append('Have Cabinets   {0:5d} (Missing {1})'.format(have_count_list[0], total_machines - have_count_list[0]))
    report_str_list.append('Have CPanels    {0:5d} (Missing {1})'.format(have_count_list[1], total_machines - have_count_list[1]))
    report_str_list.append('Have Flyers     {0:5d} (Missing {1})'.format(have_count_list[2], total_machines - have_count_list[2]))
    report_str_list.append('Have Marquees   {0:5d} (Missing {1})'.format(have_count_list[3], total_machines - have_count_list[3]))
    report_str_list.append('Have PCBs       {0:5d} (Missing {1})'.format(have_count_list[4], total_machines - have_count_list[4]))
    report_str_list.append('Have Snaps      {0:5d} (Missing {1})'.format(have_count_list[5], total_machines - have_count_list[5]))
    report_str_list.append('Have Titles     {0:5d} (Missing {1})'.format(have_count_list[6], total_machines - have_count_list[6]))
    report_str_list.append('Have Clearlogos {0:5d} (Missing {1})'.format(have_count_list[7], total_machines - have_count_list[7]))
    report_str_list.append('Have Trailers   {0:5d} (Missing {1})'.format(have_count_list[8], total_machines - have_count_list[8]))
    report_str_list.append('Have Manuals    {0:5d} (Missing {1})'.format(have_count_list[9], total_machines - have_count_list[9]))
    report_str_list.append('')
    table_str_list = text_render_table_str(table_str)
    report_str_list.extend(table_str_list)
    log_info('Opening MAME asset report file "{0}"'.format(PATHS.REPORT_MAME_ASSETS_PATH.getPath()))
    with open(PATHS.REPORT_MAME_ASSETS_PATH.getPath(), 'w') as file:
        file.write('\n'.join(report_str_list).encode('utf-8'))

    # >> Save asset database and control_dic
    kodi_busydialog_ON()
    fs_write_JSON_file(PATHS.MAIN_ASSETS_DB_PATH.getPath(), assets_dic)
    kodi_busydialog_OFF()

def fs_scan_SL_assets(PATHS, SL_catalog_dic, Asset_path_FN):
    # >> Traverse Software List, check if ROM exists, update and save database
    pDialog = xbmcgui.DialogProgress()
    pdialog_line1 = 'Scanning Sofware Lists assets/artwork ...'
    pDialog.create('Advanced MAME Launcher', pdialog_line1)
    pDialog.update(0)
    total_files = len(SL_catalog_dic)
    processed_files = 0
    for SL_name in sorted(SL_catalog_dic):
        # >> Open database
        file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '.json'
        SL_DB_FN = PATHS.SL_DB_DIR.pjoin(file_name)
        # log_debug('Processing "{0}" ({1})'.format(SL_name, SL_catalog_dic[SL_name]['display_name']))
        SL_roms = fs_load_JSON_file(SL_DB_FN.getPath())

        # >> Scan for assets
        assets_file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '_assets.json'
        SL_asset_DB_FN = PATHS.SL_DB_DIR.pjoin(assets_file_name)
        # log_info('Assets JSON "{0}"'.format(SL_asset_DB_FN.getPath()))
        SL_assets_dic = {}
        for rom_key in sorted(SL_roms):
            rom = SL_roms[rom_key]
            SL_assets = fs_new_SL_asset()
            for idx, asset_key in enumerate(ASSET_SL_KEY_LIST):
                full_asset_dir_FN = Asset_path_FN.pjoin(ASSET_SL_PATH_LIST[idx]).pjoin(SL_name)
                if asset_key == 'trailer':
                    asset_FN = full_asset_dir_FN.pjoin(rom_key + '.mp4')
                elif asset_key == 'manual':
                    SL_assets[asset_key] = ''
                    continue
                else:
                    asset_FN = full_asset_dir_FN.pjoin(rom_key + '.png')
                # log_info('Testing P "{0}"'.format(asset_FN.getPath()))
                if asset_FN.exists(): SL_assets[asset_key] = asset_FN.getOriginalPath()
                else:                 SL_assets[asset_key] = ''
            SL_assets_dic[rom_key] = SL_assets

        # >> Save SL asset DB
        fs_write_JSON_file(SL_asset_DB_FN.getPath(), SL_assets_dic)

        # >> Update progress
        processed_files += 1
        update_number = (processed_files*100) // total_files
        pDialog.update(update_number, pdialog_line1, 'Software List {0} ...'.format(SL_name))
    pDialog.close()

    # >> Asset statistics
    
    # >> Save control_dic (with updated statistics)
