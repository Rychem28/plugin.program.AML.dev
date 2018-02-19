# -*- coding: utf-8 -*-
#
# Advanced MAME Launcher main script file
#

# Copyright (c) 2016-2018 Wintermute0110 <wintermute0110@gmail.com>
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
# Division operator: https://www.python.org/dev/peps/pep-0238/
from __future__ import unicode_literals
from __future__ import division
import os
import urlparse
import subprocess
import copy

# --- Kodi stuff ---
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

# --- Modules/packages in this plugin ---
from constants import *
from utils import *
from utils_kodi import *
from assets import *
from disk_IO import *

# --- Addon object (used to access settings) ---
__addon_obj__     = xbmcaddon.Addon()
__addon_id__      = __addon_obj__.getAddonInfo('id').decode('utf-8')
__addon_name__    = __addon_obj__.getAddonInfo('name').decode('utf-8')
__addon_version__ = __addon_obj__.getAddonInfo('version').decode('utf-8')
__addon_author__  = __addon_obj__.getAddonInfo('author').decode('utf-8')
__addon_profile__ = __addon_obj__.getAddonInfo('profile').decode('utf-8')
__addon_type__    = __addon_obj__.getAddonInfo('type').decode('utf-8')

# --- Addon paths and constant definition ---
# _PATH is a filename | _DIR is a directory
ADDONS_DATA_DIR = FileName('special://profile/addon_data')
PLUGIN_DATA_DIR = ADDONS_DATA_DIR.pjoin(__addon_id__)
BASE_DIR        = FileName('special://profile')
HOME_DIR        = FileName('special://home')
KODI_FAV_PATH   = FileName('special://profile/favourites.xml')
ADDONS_DIR      = HOME_DIR.pjoin('addons')
AML_ADDON_DIR   = ADDONS_DIR.pjoin(__addon_id__)

# --- Used in the addon URLs so mark the location of machines/ROMs ---
LOCATION_STANDARD  = 'STANDARD'
LOCATION_MAME_FAVS = 'MAME_FAVS'
LOCATION_SL_FAVS   = 'SL_FAVS'

# --- Plugin database indices ---
class AML_Paths:
    def __init__(self):
        # >> MAME stdout/strderr files
        self.MAME_STDOUT_PATH     = PLUGIN_DATA_DIR.pjoin('log_stdout.log')
        self.MAME_STDERR_PATH     = PLUGIN_DATA_DIR.pjoin('log_stderr.log')
        self.MAME_STDOUT_VER_PATH = PLUGIN_DATA_DIR.pjoin('log_version_stdout.log')
        self.MAME_STDERR_VER_PATH = PLUGIN_DATA_DIR.pjoin('log_version_stderr.log')
        self.MAME_OUTPUT_PATH     = PLUGIN_DATA_DIR.pjoin('log_output.log')

        # >> MAME XML, main database and main PClone list.
        self.MAME_XML_PATH        = PLUGIN_DATA_DIR.pjoin('MAME.xml')
        self.MAIN_ASSETS_DB_PATH  = PLUGIN_DATA_DIR.pjoin('MAME_assets.json')
        self.MAIN_CONTROL_PATH    = PLUGIN_DATA_DIR.pjoin('MAME_control_dic.json')
        self.DEVICES_DB_PATH      = PLUGIN_DATA_DIR.pjoin('MAME_DB_devices.json')
        self.MAIN_DB_PATH         = PLUGIN_DATA_DIR.pjoin('MAME_DB_main.json')
        self.RENDER_DB_PATH       = PLUGIN_DATA_DIR.pjoin('MAME_DB_render.json')
        self.ROMS_DB_PATH         = PLUGIN_DATA_DIR.pjoin('MAME_DB_roms.json')
        self.MAIN_PCLONE_DIC_PATH = PLUGIN_DATA_DIR.pjoin('MAME_DB_pclone_dic.json')

        # >> ROM set databases
        self.ROM_AUDIT_ROMS_DB_PATH     = PLUGIN_DATA_DIR.pjoin('ROM_Audit_DB_ROMs.json')
        self.ROM_AUDIT_CHDS_DB_PATH     = PLUGIN_DATA_DIR.pjoin('ROM_Audit_DB_CHDs.json')
        self.ROM_SET_MACHINES_DB_PATH   = PLUGIN_DATA_DIR.pjoin('ROM_Set_machines.json')
        self.ROM_SET_ARCHIVES_R_DB_PATH = PLUGIN_DATA_DIR.pjoin('ROM_Set_archives_ROM.json')
        self.ROM_SET_ARCHIVES_C_DB_PATH = PLUGIN_DATA_DIR.pjoin('ROM_Set_archives_CHD.json')

        # >> DAT indices and databases.
        self.HISTORY_IDX_PATH     = PLUGIN_DATA_DIR.pjoin('DAT_History_index.json')
        self.HISTORY_DB_PATH      = PLUGIN_DATA_DIR.pjoin('DAT_History_DB.json')
        self.MAMEINFO_IDX_PATH    = PLUGIN_DATA_DIR.pjoin('DAT_MAMEInfo_index.json')
        self.MAMEINFO_DB_PATH     = PLUGIN_DATA_DIR.pjoin('DAT_MAMEInfo_DB.json')
        self.GAMEINIT_IDX_PATH    = PLUGIN_DATA_DIR.pjoin('DAT_GameInit_index.json')
        self.GAMEINIT_DB_PATH     = PLUGIN_DATA_DIR.pjoin('DAT_GameInit_DB.json')
        self.COMMAND_IDX_PATH     = PLUGIN_DATA_DIR.pjoin('DAT_Command_index.json')
        self.COMMAND_DB_PATH      = PLUGIN_DATA_DIR.pjoin('DAT_Command_DB.json')

        # >> Disabled. There are global properties for this.
        # self.MAIN_PROPERTIES_PATH = PLUGIN_DATA_DIR.pjoin('MAME_properties.json')

        # >> Catalogs
        self.CATALOG_DIR                        = PLUGIN_DATA_DIR.pjoin('catalogs')
        self.CATALOG_NONE_PARENT_PATH           = self.CATALOG_DIR.pjoin('catalog_none_parents.json')
        self.CATALOG_NONE_ALL_PATH              = self.CATALOG_DIR.pjoin('catalog_none_all.json')
        self.CATALOG_CATVER_PARENT_PATH         = self.CATALOG_DIR.pjoin('catalog_catver_parents.json')
        self.CATALOG_CATVER_ALL_PATH            = self.CATALOG_DIR.pjoin('catalog_catver_all.json')
        self.CATALOG_CATLIST_PARENT_PATH        = self.CATALOG_DIR.pjoin('catalog_catlist_parents.json')
        self.CATALOG_CATLIST_ALL_PATH           = self.CATALOG_DIR.pjoin('catalog_catlist_all.json')
        self.CATALOG_GENRE_PARENT_PATH          = self.CATALOG_DIR.pjoin('catalog_genre_parents.json')
        self.CATALOG_GENRE_ALL_PATH             = self.CATALOG_DIR.pjoin('catalog_genre_all.json')
        self.CATALOG_NPLAYERS_PARENT_PATH       = self.CATALOG_DIR.pjoin('catalog_nplayers_parents.json')
        self.CATALOG_NPLAYERS_ALL_PATH          = self.CATALOG_DIR.pjoin('catalog_nplayers_all.json')
        self.CATALOG_BESTGAMES_PARENT_PATH      = self.CATALOG_DIR.pjoin('catalog_bestgames_parents.json')
        self.CATALOG_BESTGAMES_ALL_PATH         = self.CATALOG_DIR.pjoin('catalog_bestgames_all.json')
        self.CATALOG_SERIES_PARENT_PATH         = self.CATALOG_DIR.pjoin('catalog_series_parents.json')
        self.CATALOG_SERIES_ALL_PATH            = self.CATALOG_DIR.pjoin('catalog_series_all.json')
        self.CATALOG_MANUFACTURER_PARENT_PATH   = self.CATALOG_DIR.pjoin('catalog_manufacturer_parents.json')
        self.CATALOG_MANUFACTURER_ALL_PATH      = self.CATALOG_DIR.pjoin('catalog_manufacturer_all.json')
        self.CATALOG_YEAR_PARENT_PATH           = self.CATALOG_DIR.pjoin('catalog_year_parents.json')
        self.CATALOG_YEAR_ALL_PATH              = self.CATALOG_DIR.pjoin('catalog_year_all.json')
        self.CATALOG_DRIVER_PARENT_PATH         = self.CATALOG_DIR.pjoin('catalog_driver_parents.json')
        self.CATALOG_DRIVER_ALL_PATH            = self.CATALOG_DIR.pjoin('catalog_driver_all.json')
        self.CATALOG_CONTROL_PARENT_PATH        = self.CATALOG_DIR.pjoin('catalog_control_parents.json')
        self.CATALOG_CONTROL_ALL_PATH           = self.CATALOG_DIR.pjoin('catalog_control_all.json')
        self.CATALOG_DISPLAY_TAG_PARENT_PATH    = self.CATALOG_DIR.pjoin('catalog_display_tag_parents.json')
        self.CATALOG_DISPLAY_TAG_ALL_PATH       = self.CATALOG_DIR.pjoin('catalog_display_tag_all.json')
        self.CATALOG_DISPLAY_TYPE_PARENT_PATH   = self.CATALOG_DIR.pjoin('catalog_display_type_parents.json')
        self.CATALOG_DISPLAY_TYPE_ALL_PATH      = self.CATALOG_DIR.pjoin('catalog_display_type_all.json')
        self.CATALOG_DISPLAY_ROTATE_PARENT_PATH = self.CATALOG_DIR.pjoin('catalog_display_rotate_parents.json')
        self.CATALOG_DISPLAY_ROTATE_ALL_PATH    = self.CATALOG_DIR.pjoin('catalog_display_rotate_all.json')
        self.CATALOG_DEVICE_LIST_PARENT_PATH    = self.CATALOG_DIR.pjoin('catalog_device_list_parents.json')
        self.CATALOG_DEVICE_LIST_ALL_PATH       = self.CATALOG_DIR.pjoin('catalog_device_list_all.json')
        self.CATALOG_SL_PARENT_PATH             = self.CATALOG_DIR.pjoin('catalog_SL_parents.json')
        self.CATALOG_SL_ALL_PATH                = self.CATALOG_DIR.pjoin('catalog_SL_all.json')

        # >> Distributed hashed database
        self.MAIN_DB_HASH_DIR                   = PLUGIN_DATA_DIR.pjoin('db_main_hash')
        self.ROMS_DB_HASH_DIR                   = PLUGIN_DATA_DIR.pjoin('db_ROMs_hash')

        # >> Software Lists
        self.SL_DB_DIR                   = PLUGIN_DATA_DIR.pjoin('db_SoftwareLists')
        self.SL_INDEX_PATH               = PLUGIN_DATA_DIR.pjoin('SoftwareLists_index.json')
        self.SL_MACHINES_PATH            = PLUGIN_DATA_DIR.pjoin('SoftwareLists_machines.json')
        self.SL_PCLONE_DIC_PATH          = PLUGIN_DATA_DIR.pjoin('SoftwareLists_pclone_dic.json')
        # >> Disabled. There are global properties
        # self.SL_MACHINES_PROP_PATH       = PLUGIN_DATA_DIR.pjoin('SoftwareLists_properties.json')

        # >> Favourites
        self.FAV_MACHINES_PATH           = PLUGIN_DATA_DIR.pjoin('Favourite_Machines.json')
        self.FAV_SL_ROMS_PATH            = PLUGIN_DATA_DIR.pjoin('Favourite_SL_ROMs.json')

        # >> Reports
        self.REPORTS_DIR                        = PLUGIN_DATA_DIR.pjoin('reports')
        self.REPORT_MAME_SCAN_ROM_MACHINES_PATH = self.REPORTS_DIR.pjoin('Report_ROM_machine_scanner.txt')
        self.REPORT_MAME_SCAN_ROM_ARCHIVES_PATH = self.REPORTS_DIR.pjoin('Report_ROM_archives_scanner.txt')
        self.REPORT_MAME_SCAN_CHD_MACHINES_PATH = self.REPORTS_DIR.pjoin('Report_CHD_machine_scanner.txt')
        self.REPORT_MAME_SCAN_CHD_ARCHIVES_PATH = self.REPORTS_DIR.pjoin('Report_CHD_archives_scanner.txt')
        self.REPORT_MAME_SCAN_SAMP_PATH         = self.REPORTS_DIR.pjoin('Report_Samples_scanner.txt')
        self.REPORT_SL_SCAN_ROMS_PATH           = self.REPORTS_DIR.pjoin('Report_SL_ROM_scanner.txt')
        self.REPORT_SL_SCAN_CHDS_PATH           = self.REPORTS_DIR.pjoin('Report_SL_CHD_scanner.txt')
        # >> Audit report
        self.REPORT_MAME_ROM_AUDIT_PATH         = self.REPORTS_DIR.pjoin('Report_MAME_ROM_audit.txt')
PATHS = AML_Paths()

# --- ROM flags used by skins to display status icons ---
AEL_INFAV_BOOL_LABEL  = 'AEL_InFav'
AEL_PCLONE_STAT_LABEL = 'AEL_PClone_stat'

AEL_INFAV_BOOL_VALUE_TRUE    = 'InFav_True'
AEL_INFAV_BOOL_VALUE_FALSE   = 'InFav_False'
AEL_PCLONE_STAT_VALUE_PARENT = 'PClone_Parent'
AEL_PCLONE_STAT_VALUE_CLONE  = 'PClone_Clone'
AEL_PCLONE_STAT_VALUE_NONE   = 'PClone_None'

class Main:
    # --- Object variables ---
    settings = {}

    # ---------------------------------------------------------------------------------------------
    # This is the plugin entry point.
    # ---------------------------------------------------------------------------------------------
    def run_plugin(self):
        # --- Initialise log system ---
        # >> Force DEBUG log level for development.
        # >> Place it before setting loading so settings can be dumped during debugging.
        # set_log_level(LOG_DEBUG)

        # --- Fill in settings dictionary using addon_obj.getSetting() ---
        self._get_settings()
        set_log_level(self.settings['log_level'])

        # --- Some debug stuff for development ---
        log_debug('---------- Called AML Main::run_plugin() constructor ----------')
        log_debug('sys.platform {0}'.format(sys.platform))
        log_debug('Python version ' + sys.version.replace('\n', ''))
        log_debug('__addon_version__ {0}'.format(__addon_version__))
        for i in range(len(sys.argv)): log_debug('sys.argv[{0}] = "{1}"'.format(i, sys.argv[i]))

        # --- Addon data paths creation ---
        if not PLUGIN_DATA_DIR.exists():        PLUGIN_DATA_DIR.makedirs()
        if not PATHS.MAIN_DB_HASH_DIR.exists(): PATHS.MAIN_DB_HASH_DIR.makedirs()
        # if not PATHS.ROMS_DB_HASH_DIR.exists(): PATHS.ROMS_DB_HASH_DIR.makedirs()
        if not PATHS.SL_DB_DIR.exists():        PATHS.SL_DB_DIR.makedirs()
        if not PATHS.CATALOG_DIR.exists():      PATHS.CATALOG_DIR.makedirs()
        if not PATHS.REPORTS_DIR.exists():      PATHS.REPORTS_DIR.makedirs()

        # --- Process URL ---
        self.base_url     = sys.argv[0]
        self.addon_handle = int(sys.argv[1])
        args              = urlparse.parse_qs(sys.argv[2][1:])
        log_debug('args = {0}'.format(args))
        # Interestingly, if plugin is called as type executable then args is empty.
        # However, if plugin is called as type video then Kodi adds the following
        # even for the first call: 'content_type': ['video']
        self.content_type = args['content_type'] if 'content_type' in args else None
        log_debug('content_type = {0}'.format(self.content_type))

        # --- URL routing -------------------------------------------------------------------------
        args_size = len(args)
        if args_size == 0:
            self._render_root_list()
            log_debug('Advanced MAME Launcher exit (addon root)')
            return

        elif 'catalog' in args and not 'command' in args:
            catalog_name = args['catalog'][0]
            # --- Software list is a special case ---
            if catalog_name == 'SL' or catalog_name == 'SL_ROM' or \
               catalog_name == 'SL_CHD' or catalog_name == 'SL_ROM_CHD':
                SL_name     = args['category'][0] if 'category' in args else ''
                parent_name = args['parent'][0] if 'parent' in args else ''
                if SL_name and parent_name:
                    self._render_SL_pclone_set(SL_name, parent_name)
                elif SL_name and not parent_name:
                    self._render_SL_ROMs(SL_name)
                else:
                    self._render_SL_list(catalog_name)
            # --- DAT browsing ---
            elif catalog_name == 'History' or catalog_name == 'MAMEINFO' or \
                 catalog_name == 'Gameinit' or catalog_name == 'Command':
                category_name = args['category'][0] if 'category' in args else ''
                machine_name = args['machine'][0] if 'machine' in args else ''
                if category_name and machine_name:
                    self._render_DAT_machine_info(catalog_name, category_name, machine_name)
                elif category_name and not machine_name:
                    self._render_DAT_category(catalog_name, category_name)
                else:
                    self._render_DAT_list(catalog_name)
            else:
                category_name = args['category'][0] if 'category' in args else ''
                parent_name   = args['parent'][0] if 'parent' in args else ''
                if category_name and parent_name:
                    self._render_catalog_clone_list(catalog_name, category_name, parent_name)
                elif category_name and not parent_name:
                    self._render_catalog_parent_list(catalog_name, category_name)
                else:
                    self._render_catalog_list(catalog_name)

        elif 'command' in args:
            command = args['command'][0]

            # >> Commands used by skins to render items of the addon root menu.
            if   command == 'SKIN_SHOW_FAV_SLOTS':       self._render_skin_fav_slots()
            elif command == 'SKIN_SHOW_MAIN_FILTERS':    self._render_skin_main_filters()
            elif command == 'SKIN_SHOW_BINARY_FILTERS':  self._render_skin_binary_filters()
            elif command == 'SKIN_SHOW_CATALOG_FILTERS': self._render_skin_catalog_filters()
            elif command == 'SKIN_SHOW_DAT_SLOTS':       self._render_skin_dat_slots()
            elif command == 'SKIN_SHOW_SL_FILTERS':      self._render_skin_SL_filters()

            # >> Auxiliar commands from parent machine context menu
            # >> Not sure if this will cause problems with the concurrent protected code once it's
            #    implemented.
            elif command == 'EXEC_SHOW_MAME_CLONES':
                catalog_name  = args['catalog'][0] if 'catalog' in args else ''
                category_name = args['category'][0] if 'category' in args else ''
                machine_name  = args['parent'][0] if 'parent' in args else ''
                url = self._misc_url_3_arg('catalog', catalog_name, 'category', category_name, 'parent', machine_name)
                xbmc.executebuiltin('Container.Update({0})'.format(url))

            elif command == 'EXEC_SHOW_SL_CLONES':
                catalog_name  = args['catalog'][0] if 'catalog' in args else ''
                category_name = args['category'][0] if 'category' in args else ''
                machine_name  = args['parent'][0] if 'parent' in args else ''
                url = self._misc_url_3_arg('catalog', 'SL', 'category', category_name, 'parent', machine_name)
                xbmc.executebuiltin('Container.Update({0})'.format(url))

            elif command == 'LAUNCH':
                machine  = args['machine'][0]
                location = args['location'][0] if 'location' in args else ''
                log_info('Launching MAME machine "{0}"'.format(machine, location))
                self._run_machine(machine, location)
            elif command == 'LAUNCH_SL':
                SL_name  = args['SL'][0]
                ROM_name = args['ROM'][0]
                location = args['location'][0] if 'location' in args else LOCATION_STANDARD
                log_info('Launching SL machine "{0}" (ROM "{1}")'.format(SL_name, ROM_name))
                self._run_SL_machine(SL_name, ROM_name, location)

            elif command == 'SETUP_PLUGIN':
                self._command_context_setup_plugin()

            #
            # Not used at the moment.
            # Instead of per-catalog, per-category display mode there are global settings.
            #
            elif command == 'DISPLAY_SETTINGS_MAME':
                catalog_name = args['catalog'][0]
                category_name = args['category'][0] if 'category' in args else ''
                self._command_context_display_settings(catalog_name, category_name)
            elif command == 'DISPLAY_SETTINGS_SL':
                self._command_context_display_settings_SL(args['category'][0])
            elif command == 'VIEW_DAT':
                machine  = args['machine'][0]  if 'machine'  in args else ''
                SL       = args['SL'][0]       if 'SL'       in args else ''
                ROM      = args['ROM'][0]      if 'ROM'      in args else ''
                location = args['location'][0] if 'location' in args else LOCATION_STANDARD
                self._command_context_view_DAT(machine, SL, ROM, location)
            elif command == 'VIEW':
                machine  = args['machine'][0]  if 'machine'  in args else ''
                SL       = args['SL'][0]       if 'SL'       in args else ''
                ROM      = args['ROM'][0]      if 'ROM'      in args else ''
                location = args['location'][0] if 'location' in args else LOCATION_STANDARD
                self._command_context_view(machine, SL, ROM, location)

            # >> MAME Favourites
            elif command == 'ADD_MAME_FAV':
                self._command_context_add_mame_fav(args['machine'][0])
            elif command == 'MANAGE_MAME_FAV':
                self._command_context_manage_mame_fav(args['machine'][0])
            elif command == 'SHOW_MAME_FAVS':
                self._command_show_mame_fav()

            # >> SL Favourites
            elif command == 'ADD_SL_FAV':
                self._command_context_add_sl_fav(args['SL'][0], args['ROM'][0])
            elif command == 'MANAGE_SL_FAV':
                self._command_context_manage_sl_fav(args['SL'][0], args['ROM'][0])
            elif command == 'SHOW_SL_FAVS':
                self._command_show_sl_fav()

            else:
                log_error('Unknown command "{0}"'.format(command))

        else:
            log_error('Error in URL routing')

        # --- So Long, and Thanks for All the Fish ---
        log_debug('Advanced MAME Launcher exit')

    #
    # Get Addon Settings
    #
    def _get_settings(self):
        # --- Paths ---
        self.settings['mame_prog']      = __addon_obj__.getSetting('mame_prog').decode('utf-8')
        self.settings['rom_path']       = __addon_obj__.getSetting('rom_path').decode('utf-8')

        self.settings['assets_path']    = __addon_obj__.getSetting('assets_path').decode('utf-8')
        self.settings['chd_path']       = __addon_obj__.getSetting('chd_path').decode('utf-8')        
        self.settings['SL_hash_path']   = __addon_obj__.getSetting('SL_hash_path').decode('utf-8')
        self.settings['SL_rom_path']    = __addon_obj__.getSetting('SL_rom_path').decode('utf-8')
        self.settings['SL_chd_path']    = __addon_obj__.getSetting('SL_chd_path').decode('utf-8')
        self.settings['samples_path']   = __addon_obj__.getSetting('samples_path').decode('utf-8')

        # --- DAT Paths ---
        self.settings['catver_path']    = __addon_obj__.getSetting('catver_path').decode('utf-8')
        self.settings['catlist_path']   = __addon_obj__.getSetting('catlist_path').decode('utf-8')
        self.settings['genre_path']     = __addon_obj__.getSetting('genre_path').decode('utf-8')
        self.settings['nplayers_path']  = __addon_obj__.getSetting('nplayers_path').decode('utf-8')
        self.settings['bestgames_path'] = __addon_obj__.getSetting('bestgames_path').decode('utf-8')
        self.settings['series_path']    = __addon_obj__.getSetting('series_path').decode('utf-8')
        self.settings['history_path']   = __addon_obj__.getSetting('history_path').decode('utf-8')
        self.settings['mameinfo_path']  = __addon_obj__.getSetting('mameinfo_path').decode('utf-8')
        self.settings['gameinit_path']  = __addon_obj__.getSetting('gameinit_path').decode('utf-8')
        self.settings['command_path']   = __addon_obj__.getSetting('command_path').decode('utf-8')

        # --- ROM sets ---
        self.settings['mame_rom_set']      = int(__addon_obj__.getSetting('mame_rom_set'))
        self.settings['mame_chd_set']      = int(__addon_obj__.getSetting('mame_chd_set'))
        self.settings['audit_only_errors'] = True if __addon_obj__.getSetting('audit_only_errors') == 'true' else False

        # --- Display ---
        self.settings['mame_view_mode']          = int(__addon_obj__.getSetting('mame_view_mode'))
        self.settings['sl_view_mode']            = int(__addon_obj__.getSetting('sl_view_mode'))
        self.settings['display_hide_BIOS']       = True if __addon_obj__.getSetting('display_hide_BIOS') == 'true' else False
        self.settings['display_hide_nonworking'] = True if __addon_obj__.getSetting('display_hide_nonworking') == 'true' else False
        self.settings['display_hide_imperfect']  = True if __addon_obj__.getSetting('display_hide_imperfect') == 'true' else False
        self.settings['display_rom_available']   = True if __addon_obj__.getSetting('display_rom_available') == 'true' else False
        self.settings['display_chd_available']   = True if __addon_obj__.getSetting('display_chd_available') == 'true' else False

        # --- Display ---
        self.settings['artwork_mame_icon']   = int(__addon_obj__.getSetting('artwork_mame_icon'))
        self.settings['artwork_mame_fanart'] = int(__addon_obj__.getSetting('artwork_mame_fanart'))
        self.settings['artwork_SL_icon']     = int(__addon_obj__.getSetting('artwork_SL_icon'))
        self.settings['artwork_SL_fanart']   = int(__addon_obj__.getSetting('artwork_SL_fanart'))
        self.settings['display_hide_trailers']   = True if __addon_obj__.getSetting('display_hide_trailers') == 'true' else False

        # --- Advanced ---
        self.settings['log_level'] = int(__addon_obj__.getSetting('log_level'))

        # --- Transform settings data ---
        self.mame_icon   = assets_get_asset_key_MAME_icon(self.settings['artwork_mame_icon'])
        self.mame_fanart = assets_get_asset_key_MAME_fanart(self.settings['artwork_mame_fanart'])
        self.SL_icon     = assets_get_asset_key_SL_icon(self.settings['artwork_SL_icon'])
        self.SL_fanart   = assets_get_asset_key_SL_fanart(self.settings['artwork_SL_fanart'])

        # --- Dump settings for DEBUG ---
        # log_debug('Settings dump BEGIN')
        # for key in sorted(self.settings):
        #     log_debug('{0} --> {1:10s} {2}'.format(key.rjust(21), str(self.settings[key]), type(self.settings[key])))
        # log_debug('Settings dump END')

    # ---------------------------------------------------------------------------------------------
    # Root menu rendering
    # ---------------------------------------------------------------------------------------------
    def _render_root_list(self):
        mame_view_mode = self.settings['mame_view_mode']

        # >> Count number of ROMs in binary filters
        if mame_view_mode == VIEW_MODE_FLAT:
            c_dic = fs_get_cataloged_dic_all(PATHS, 'None')
        elif mame_view_mode == VIEW_MODE_PCLONE or mame_view_mode == VIEW_MODE_PARENTS_ONLY:
            c_dic = fs_get_cataloged_dic_parents(PATHS, 'None')

        if not c_dic:
            machines_n_str = 'Machines with coin slot (Normal)'
            machines_u_str = 'Machines with coin slot (Unusual)'
            nocoin_str     = 'Machines with no coin slot'
            mecha_str      = 'Mechanical machines'
            dead_str       = 'Dead machines'
            devices_str    = 'Device machines'
            norom_str      = 'Machines [with no ROMs]'
            chd_str        = 'Machines [with CHDs]'
            samples_str    = 'Machines [with Samples]'
            bios_str       = 'Machines [BIOS]'
        else:
            if mame_view_mode == VIEW_MODE_FLAT:
                machines_n_str = 'Machines with coin slot (Normal) [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['Normal']['num_machines'])
                machines_u_str = 'Machines with coin slot (Unusual) [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['Unusual']['num_machines'])
                nocoin_str = 'Machines with no coin slot [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['NoCoin']['num_machines'])
                mecha_str = 'Mechanical machines [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['Mechanical']['num_machines'])
                dead_str = 'Dead machines [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['Dead']['num_machines'])
                devices_str = 'Device machines [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['Devices']['num_machines'])
                norom_str = 'Machines [with no ROMs] [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['NoROM']['num_machines'])
                chd_str = 'Machines [with CHDs] [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['CHD']['num_machines'])
                samples_str = 'Machines [with Samples] [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['Samples']['num_machines'])
                bios_str = 'Machines [BIOS] [COLOR orange]({0} machines)[/COLOR]'.format(c_dic['BIOS']['num_machines'])
            elif mame_view_mode == VIEW_MODE_PCLONE or mame_view_mode == VIEW_MODE_PARENTS_ONLY:
                machines_n_str = 'Machines with coin slot (Normal) [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['Normal']['num_parents'])
                machines_u_str = 'Machines with coin slot (Unusual) [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['Unusual']['num_parents'])
                nocoin_str = 'Machines with no coin slot [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['NoCoin']['num_parents'])
                mecha_str = 'Mechanical machines [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['Mechanical']['num_parents'])
                dead_str = 'Dead machines [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['Dead']['num_parents'])
                devices_str = 'Device machines [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['Devices']['num_parents'])
                norom_str = 'Machines [with no ROMs] [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['NoROM']['num_parents'])
                chd_str = 'Machines [with CHDs] [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['CHD']['num_parents'])
                samples_str = 'Machines [with Samples] [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['Samples']['num_parents'])
                bios_str = 'Machines [BIOS] [COLOR orange]({0} parents)[/COLOR]'.format(c_dic['BIOS']['num_parents'])

        # >> Main filters (Virtual catalog 'None')
        self._render_root_list_row(machines_n_str, self._misc_url_2_arg('catalog', 'None', 'category', 'Normal'))
        self._render_root_list_row(machines_u_str, self._misc_url_2_arg('catalog', 'None', 'category', 'Unusual'))
        self._render_root_list_row(nocoin_str,     self._misc_url_2_arg('catalog', 'None', 'category', 'NoCoin'))
        self._render_root_list_row(mecha_str,      self._misc_url_2_arg('catalog', 'None', 'category', 'Mechanical'))
        self._render_root_list_row(dead_str,       self._misc_url_2_arg('catalog', 'None', 'category', 'Dead'))
        self._render_root_list_row(devices_str,    self._misc_url_2_arg('catalog', 'None', 'category', 'Devices'))

        # >> Binary filters (Virtual catalog 'None')
        self._render_root_list_row(norom_str,      self._misc_url_2_arg('catalog', 'None', 'category', 'NoROM'))
        self._render_root_list_row(chd_str,        self._misc_url_2_arg('catalog', 'None', 'category', 'CHD'))
        self._render_root_list_row(samples_str,    self._misc_url_2_arg('catalog', 'None', 'category', 'Samples'))
        self._render_root_list_row(bios_str,       self._misc_url_2_arg('catalog', 'None', 'category', 'BIOS'))

        # >> Cataloged filters
        if self.settings['catver_path']:
            self._render_root_list_row('Machines by Category (Catver)', self._misc_url_1_arg('catalog', 'Catver'))
        if self.settings['catlist_path']:
            self._render_root_list_row('Machines by Category (Catlist)', self._misc_url_1_arg('catalog', 'Catlist'))
        if self.settings['genre_path']:
            self._render_root_list_row('Machines by Category (Genre)', self._misc_url_1_arg('catalog', 'Genre'))
        if self.settings['nplayers_path']:
            self._render_root_list_row('Machines by Number of players', self._misc_url_1_arg('catalog', 'NPlayers'))
        if self.settings['bestgames_path']:
            self._render_root_list_row('Machines by Score', self._misc_url_1_arg('catalog', 'Bestgames'))
        if self.settings['series_path']:
            self._render_root_list_row('Machines by Series', self._misc_url_1_arg('catalog', 'Series'))

        self._render_root_list_row('Machines by Manufacturer',        self._misc_url_1_arg('catalog', 'Manufacturer'))
        self._render_root_list_row('Machines by Year',                self._misc_url_1_arg('catalog', 'Year'))
        self._render_root_list_row('Machines by Driver',              self._misc_url_1_arg('catalog', 'Driver'))
        self._render_root_list_row('Machines by Control Type',        self._misc_url_1_arg('catalog', 'Controls'))
        self._render_root_list_row('Machines by Display Tag',         self._misc_url_1_arg('catalog', 'Display_Tag'))
        self._render_root_list_row('Machines by Display Type',        self._misc_url_1_arg('catalog', 'Display_Type'))
        self._render_root_list_row('Machines by Display Rotation',    self._misc_url_1_arg('catalog', 'Display_Rotate'))
        self._render_root_list_row('Machines by Device',              self._misc_url_1_arg('catalog', 'Devices'))
        self._render_root_list_row('Machines by Software List',       self._misc_url_1_arg('catalog', 'BySL'))

        # >> history.dat, mameinfo.dat, gameinit.dat, command.dat
        self._render_root_list_row('History DAT',  self._misc_url_1_arg('catalog', 'History'))
        self._render_root_list_row('MAMEINFO DAT', self._misc_url_1_arg('catalog', 'MAMEINFO'))
        self._render_root_list_row('Gameinit DAT', self._misc_url_1_arg('catalog', 'Gameinit'))
        self._render_root_list_row('Command DAT',  self._misc_url_1_arg('catalog', 'Command'))

        # >> Software lists
        if self.settings['SL_hash_path']:
            self._render_root_list_row('Software Lists (with ROMs)', self._misc_url_1_arg('catalog', 'SL_ROM'))
            self._render_root_list_row('Software Lists (with CHDs)', self._misc_url_1_arg('catalog', 'SL_CHD'))
            self._render_root_list_row('Software Lists (with ROMs and CHDs)', self._misc_url_1_arg('catalog', 'SL_ROM_CHD'))

        # >> Special launchers
        self._render_root_list_row('<Favourite MAME machines>',       self._misc_url_1_arg('command', 'SHOW_MAME_FAVS'))
        self._render_root_list_row('<Favourite Software Lists ROMs>', self._misc_url_1_arg('command', 'SHOW_SL_FAVS'))
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    #
    # These _render_skin_* functions used by skins only for widgets.
    #
    def _render_skin_fav_slots(self):
        self._render_root_list_row('Favourite MAME machines', self._misc_url_1_arg('command', 'SHOW_MAME_FAVS'))
        self._render_root_list_row('Favourite Software Lists ROMs', self._misc_url_1_arg('command', 'SHOW_SL_FAVS'))
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_skin_main_filters(self):
        machines_n_str = 'Machines with coin slot (Normal)'
        machines_u_str = 'Machines with coin slot (Unusual)'
        nocoin_str = 'Machines with no coin slot'
        mecha_str = 'Mechanical machines'
        dead_str = 'Dead machines'
        devices_str = 'Device machines'

        self._render_root_list_row(machines_n_str, self._misc_url_2_arg('catalog', 'None', 'category', 'Normal'))
        self._render_root_list_row(machines_u_str, self._misc_url_2_arg('catalog', 'None', 'category', 'Unusual'))
        self._render_root_list_row(nocoin_str,     self._misc_url_2_arg('catalog', 'None', 'category', 'NoCoin'))
        self._render_root_list_row(mecha_str,      self._misc_url_2_arg('catalog', 'None', 'category', 'Mechanical'))
        self._render_root_list_row(dead_str,       self._misc_url_2_arg('catalog', 'None', 'category', 'Dead'))
        self._render_root_list_row(devices_str,    self._misc_url_2_arg('catalog', 'None', 'category', 'Devices'))
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_skin_binary_filters(self):
        norom_str = 'Machines [with no ROMs]'
        chd_str = 'Machines [with CHDs]'
        samples_str = 'Machines [with Samples]'
        bios_str = 'Machines [BIOS]'

        self._render_root_list_row(norom_str,      self._misc_url_2_arg('catalog', 'None', 'category', 'NoROM'))
        self._render_root_list_row(chd_str,        self._misc_url_2_arg('catalog', 'None', 'category', 'CHD'))
        self._render_root_list_row(samples_str,    self._misc_url_2_arg('catalog', 'None', 'category', 'Samples'))
        self._render_root_list_row(bios_str,       self._misc_url_2_arg('catalog', 'None', 'category', 'BIOS'))
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_skin_catalog_filters(self):
        if self.settings['catver_path']:
            self._render_root_list_row('Machines by Category (Catver)',  self._misc_url_1_arg('catalog', 'Catver'))
        if self.settings['catlist_path']:
            self._render_root_list_row('Machines by Category (Catlist)', self._misc_url_1_arg('catalog', 'Catlist'))
        if self.settings['genre_path']:
            self._render_root_list_row('Machines by Category (Genre)',   self._misc_url_1_arg('catalog', 'Genre'))
        if self.settings['nplayers_path']:
            self._render_root_list_row('Machines by Number of players',  self._misc_url_1_arg('catalog', 'NPlayers'))
        if self.settings['bestgames_path']:
            self._render_root_list_row('Machines by Score',              self._misc_url_1_arg('catalog', 'Bestgames'))
        if self.settings['series_path']:
            self._render_root_list_row('Machines by Series',             self._misc_url_1_arg('catalog', 'Series'))

        self._render_root_list_row('Machines by Manufacturer',        self._misc_url_1_arg('catalog', 'Manufacturer'))
        self._render_root_list_row('Machines by Year',                self._misc_url_1_arg('catalog', 'Year'))
        self._render_root_list_row('Machines by Driver',              self._misc_url_1_arg('catalog', 'Driver'))
        self._render_root_list_row('Machines by Control Type',        self._misc_url_1_arg('catalog', 'Controls'))
        self._render_root_list_row('Machines by Display Tag',         self._misc_url_1_arg('catalog', 'Display_Tag'))
        self._render_root_list_row('Machines by Display Type',        self._misc_url_1_arg('catalog', 'Display_Type'))
        self._render_root_list_row('Machines by Display Rotation',    self._misc_url_1_arg('catalog', 'Display_Rotate'))
        self._render_root_list_row('Machines by Device',              self._misc_url_1_arg('catalog', 'Devices'))
        self._render_root_list_row('Machines by Software List',       self._misc_url_1_arg('catalog', 'BySL'))
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_skin_dat_slots(self):
        self._render_root_list_row('History DAT',  self._misc_url_1_arg('catalog', 'History'))
        self._render_root_list_row('MAMEINFO DAT', self._misc_url_1_arg('catalog', 'MAMEINFO'))
        self._render_root_list_row('Gameinit DAT', self._misc_url_1_arg('catalog', 'Gameinit'))
        self._render_root_list_row('Command DAT',  self._misc_url_1_arg('catalog', 'Command'))
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_skin_SL_filters(self):
        if self.settings['SL_hash_path']:
            self._render_root_list_row('Software Lists (with ROMs)', self._misc_url_1_arg('catalog', 'SL_ROM'))
            self._render_root_list_row('Software Lists (with CHDs)', self._misc_url_1_arg('catalog', 'SL_CHD'))
            self._render_root_list_row('Software Lists (with ROMs and CHDs)', self._misc_url_1_arg('catalog', 'SL_ROM_CHD'))
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_root_list_row(self, root_name, root_URL):
        # --- Create listitem row ---
        ICON_OVERLAY = 6
        listitem = xbmcgui.ListItem(root_name)
        listitem.setInfo('video', {'title' : root_name, 'overlay' : ICON_OVERLAY})

        # --- Create context menu ---
        commands = []
        commands.append(('View', self._misc_url_1_arg_RunPlugin('command', 'VIEW'), ))
        commands.append(('Setup plugin', self._misc_url_1_arg_RunPlugin('command', 'SETUP_PLUGIN'), ))
        commands.append(('Kodi File Manager', 'ActivateWindow(filemanager)', ))
        commands.append(('Add-on Settings', 'Addon.OpenSettings({0})'.format(__addon_id__), ))
        listitem.addContextMenuItems(commands, replaceItems = True)

        # --- Add row ---
        xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = root_URL, listitem = listitem, isFolder = True)

    #----------------------------------------------------------------------------------------------
    # Cataloged machines
    #----------------------------------------------------------------------------------------------
    def _render_catalog_list(self, catalog_name):
        log_debug('_render_catalog_list() Starting ...')
        log_debug('_render_catalog_list() catalog_name = "{0}"'.format(catalog_name))

        # >> Render categories in catalog index
        self._set_Kodi_all_sorting_methods_and_size()
        mame_view_mode = self.settings['mame_view_mode']
        loading_ticks_start = time.time()
        if mame_view_mode == VIEW_MODE_FLAT:
            catalog_dic = fs_get_cataloged_dic_all(PATHS, catalog_name)
        elif mame_view_mode == VIEW_MODE_PCLONE:
            catalog_dic = fs_get_cataloged_dic_parents(PATHS, catalog_name)
        elif mame_view_mode == VIEW_MODE_PARENTS_ONLY:
            catalog_dic = fs_get_cataloged_dic_parents(PATHS, catalog_name)
        if not catalog_dic:
            kodi_dialog_OK('Catalog is empty. Check out "Setup plugin" context menu.')
            xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
            return

        loading_ticks_end = time.time()
        rendering_ticks_start = time.time()
        for catalog_key in sorted(catalog_dic):
            if mame_view_mode == VIEW_MODE_FLAT:
                num_machines = catalog_dic[catalog_key]['num_machines']
                if num_machines == 1: machine_str = 'machine'
                else:                 machine_str = 'machines'
            elif mame_view_mode == VIEW_MODE_PCLONE or mame_view_mode == VIEW_MODE_PARENTS_ONLY:
                num_machines = catalog_dic[catalog_key]['num_parents']
                if num_machines == 1: machine_str = 'parent'
                else:                 machine_str = 'parents'
            self._render_catalog_list_row(catalog_name, catalog_key, num_machines, machine_str)
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
        rendering_ticks_end = time.time()

        # --- DEBUG Data loading/rendering statistics ---
        log_debug('Loading seconds   {0}'.format(loading_ticks_end - loading_ticks_start))
        log_debug('Rendering seconds {0}'.format(rendering_ticks_end - rendering_ticks_start))

    #
    # Renders a Parent list knowing the catalog name and the category.
    # Display mode: a) parents only b) all machines
    #
    def _render_catalog_parent_list(self, catalog_name, category_name):
        # When using threads the performance gain is small: from 0.76 to 0.71, just 20 ms.
        # It's not worth it.
        USE_THREADED_JSON_LOADER = False

        log_debug('_render_catalog_parent_list() catalog_name  = {0}'.format(catalog_name))
        log_debug('_render_catalog_parent_list() category_name = {0}'.format(category_name))
        display_hide_BIOS       = self.settings['display_hide_BIOS']
        if catalog_name == 'None' and category_name == 'BIOS': display_hide_BIOS = False
        display_hide_nonworking = self.settings['display_hide_nonworking']
        display_hide_imperfect  = self.settings['display_hide_imperfect']

        # >> Load ListItem properties (Not used at the moment)
        # prop_key = '{0} - {1}'.format(catalog_name, category_name)
        # log_debug('_render_catalog_parent_list() Loading props with key "{0}"'.format(prop_key))
        # mame_properties_dic = fs_load_JSON_file(PATHS.MAIN_PROPERTIES_PATH.getPath())
        # prop_dic = mame_properties_dic[prop_key]
        # view_mode_property = prop_dic['vm']
        # >> Global properties
        view_mode_property = self.settings['mame_view_mode']
        log_debug('_render_catalog_parent_list() view_mode_property = {0}'.format(view_mode_property))

        # >> Check id main DB exists
        if not PATHS.RENDER_DB_PATH.exists():
            kodi_dialog_OK('MAME database not found. Check out "Setup plugin" context menu.')
            xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
            return

        # >> Load main MAME info DB and catalog
        if USE_THREADED_JSON_LOADER:
            total_time_start = time.time()
            # --- Create thread objects  and run ---
            render_thread = Threaded_Load_JSON(PATHS.RENDER_DB_PATH.getPath())
            assets_thread = Threaded_Load_JSON(PATHS.MAIN_ASSETS_DB_PATH.getPath())
            pclone_thread = Threaded_Load_JSON(PATHS.MAIN_PCLONE_DIC_PATH.getPath())
            render_thread.start()
            assets_thread.start()
            pclone_thread.start()

            # --- Do not use a thread for the catalog. Loads very fast ---
            l_cataloged_dic_start = time.time()
            if view_mode_property == VIEW_MODE_PCLONE or view_mode_property == VIEW_MODE_PARENTS_ONLY:
                catalog_dic = fs_get_cataloged_dic_parents(PATHS, catalog_name)
            elif view_mode_property == VIEW_MODE_FLAT:
                catalog_dic = fs_get_cataloged_dic_all(PATHS, catalog_name)
            else:
                kodi_dialog_OK('Wrong vm = "{0}". This is a bug, please report it.'.format(prop_dic['vm']))
                return
            l_cataloged_dic_end = time.time()

            # --- Wait for everybody to finish execution ---
            pclone_thread.join() # Should finish first
            render_thread.join()
            assets_thread.join()

            # --- Get data ---
            MAME_db_dic     = render_thread.output_dic
            MAME_assets_dic = assets_thread.output_dic
            main_pclone_dic = pclone_thread.output_dic
            total_time_end = time.time()

            render_t = assets_t = pclone_t = 0
            catalog_t = l_cataloged_dic_end - l_cataloged_dic_start
            loading_time = total_time_end - total_time_start
        else:
            l_render_db_start = time.time()
            MAME_db_dic = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
            l_render_db_end = time.time()
            l_assets_db_start = time.time()
            MAME_assets_dic = fs_load_JSON_file(PATHS.MAIN_ASSETS_DB_PATH.getPath())
            l_assets_db_end = time.time()
            l_pclone_dic_start = time.time()
            main_pclone_dic = fs_load_JSON_file(PATHS.MAIN_PCLONE_DIC_PATH.getPath())
            l_pclone_dic_end = time.time()
            l_cataloged_dic_start = time.time()
            if view_mode_property == VIEW_MODE_PCLONE or view_mode_property == VIEW_MODE_PARENTS_ONLY:
                catalog_dic = fs_get_cataloged_dic_parents(PATHS, catalog_name)
            elif view_mode_property == VIEW_MODE_FLAT:
                catalog_dic = fs_get_cataloged_dic_all(PATHS, catalog_name)
            else:
                kodi_dialog_OK('Wrong vm = "{0}". This is a bug, please report it.'.format(prop_dic['vm']))
                return
            l_cataloged_dic_end = time.time()
            render_t     = l_render_db_end - l_render_db_start
            assets_t     = l_assets_db_end - l_assets_db_start
            pclone_t     = l_pclone_dic_end - l_pclone_dic_start
            catalog_t    = l_cataloged_dic_end - l_cataloged_dic_start
            loading_time = render_t + assets_t + pclone_t + catalog_t

        # >> Check if catalog is empty
        if not catalog_dic:
            kodi_dialog_OK('Catalog is empty. Check out "Setup plugin" context menu.')
            xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
            return

        # >> Render parent main list
        rendering_ticks_start = time.time()
        self._set_Kodi_all_sorting_methods()
        if view_mode_property == VIEW_MODE_PCLONE or view_mode_property == VIEW_MODE_PARENTS_ONLY:
            # >> Parent/Clone mode render parents only
            machine_list = catalog_dic[category_name]['parents']
            for machine_name in machine_list:
                machine = MAME_db_dic[machine_name]
                if display_hide_BIOS and machine['isBIOS']: continue
                if display_hide_nonworking and machine['driver_status'] == 'preliminary': continue
                if display_hide_imperfect and machine['driver_status'] == 'imperfect': continue
                assets  = MAME_assets_dic[machine_name]
                num_clones = len(main_pclone_dic[machine_name])
                self._render_catalog_machine_row(machine_name, machine, assets, True, view_mode_property,
                                                 catalog_name, category_name, num_clones)
        else:
            # >> Flat mode renders all machines
            machine_list = catalog_dic[category_name]['machines']
            for machine_name in machine_list:
                machine = MAME_db_dic[machine_name]
                if display_hide_BIOS and machine['isBIOS']: continue
                if display_hide_nonworking and machine['driver_status'] == 'preliminary': continue
                if display_hide_imperfect and machine['driver_status'] == 'imperfect': continue
                assets  = MAME_assets_dic[machine_name]
                self._render_catalog_machine_row(machine_name, machine, assets, False, view_mode_property,
                                                 catalog_name, category_name)
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
        rendering_ticks_end = time.time()

        # --- DEBUG Data loading/rendering statistics ---
        log_debug('Loading render db     {0:.4f} s'.format(render_t))
        log_debug('Loading assets db     {0:.4f} s'.format(assets_t))
        log_debug('Loading pclone dic    {0:.4f} s'.format(pclone_t))
        log_debug('Loading cataloged dic {0:.4f} s'.format(catalog_t))
        log_debug('Loading               {0:.4f} s'.format(loading_time))
        log_debug('Rendering             {0:.4f} s'.format(rendering_ticks_end - rendering_ticks_start))

    #
    # No need to check for DB existance here. If this function is called is because parents and
    # hence all ROMs databases exist.
    #
    def _render_catalog_clone_list(self, catalog_name, category_name, parent_name):
        log_debug('_render_catalog_clone_list() Starting ...')
        display_hide_nonworking = self.settings['display_hide_nonworking']
        display_hide_imperfect  = self.settings['display_hide_imperfect']

        # >> Load main MAME info DB
        loading_ticks_start = time.time()
        MAME_db_dic     = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
        MAME_assets_dic = fs_load_JSON_file(PATHS.MAIN_ASSETS_DB_PATH.getPath())
        main_pclone_dic = fs_load_JSON_file(PATHS.MAIN_PCLONE_DIC_PATH.getPath())
        view_mode_property = self.settings['mame_view_mode']
        log_debug('_render_catalog_clone_list() view_mode_property = {0}'.format(view_mode_property))

        # >> Render parent first
        loading_ticks_end = time.time()
        rendering_ticks_start = time.time()
        self._set_Kodi_all_sorting_methods()
        machine = MAME_db_dic[parent_name]
        assets  = MAME_assets_dic[parent_name]
        self._render_catalog_machine_row(parent_name, machine, assets, False, view_mode_property, 
                                         catalog_name, category_name)

        # >> Render clones belonging to parent in this category
        for p_name in main_pclone_dic[parent_name]:
            machine = MAME_db_dic[p_name]
            assets  = MAME_assets_dic[p_name]
            if display_hide_nonworking and machine['driver_status'] == 'preliminary': continue
            if display_hide_imperfect and machine['driver_status'] == 'imperfect': continue
            self._render_catalog_machine_row(p_name, machine, assets, False, view_mode_property,
                                             catalog_name, category_name)
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
        rendering_ticks_end = time.time()

        # --- DEBUG Data loading/rendering statistics ---
        log_debug('Loading seconds   {0}'.format(loading_ticks_end - loading_ticks_start))
        log_debug('Rendering seconds {0}'.format(rendering_ticks_end - rendering_ticks_start))

    def _render_catalog_list_row(self, catalog_name, catalog_key, num_machines, machine_str):
        # --- Create listitem row ---
        ICON_OVERLAY = 6
        title_str = '{0} [COLOR orange]({1} {2})[/COLOR]'.format(catalog_key, num_machines, machine_str)
        listitem = xbmcgui.ListItem(title_str)
        listitem.setInfo('video', {'Title'   : title_str, 'Overlay' : ICON_OVERLAY, 'size' : num_machines})

        # --- Create context menu ---
        commands = []
        URL_view = self._misc_url_1_arg_RunPlugin('command', 'VIEW')
        commands.append(('View', URL_view ))
        commands.append(('Kodi File Manager', 'ActivateWindow(filemanager)' ))
        commands.append(('Add-on Settings', 'Addon.OpenSettings({0})'.format(__addon_id__) ))
        listitem.addContextMenuItems(commands, replaceItems = True)

        # --- Add row ---
        URL = self._misc_url_2_arg('catalog', catalog_name, 'category', catalog_key)
        xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = True)

    def _render_catalog_machine_row(self, machine_name, machine, machine_assets, flag_parent_list, view_mode_property,
                                    catalog_name, category_name, num_clones = 0):
        # --- Default values for flags ---
        AEL_PClone_stat_value = AEL_PCLONE_STAT_VALUE_NONE

        # --- Render a Parent only list ---
        display_name = machine['description']
        if flag_parent_list and num_clones > 0:
            # NOTE all machines here are parents
            # --- Mark number of clones ---
            display_name += ' [COLOR orange] ({0} clones)[/COLOR]'.format(num_clones)

            # --- Mark Flags, BIOS, Devices, BIOS, Parent/Clone and Driver status ---
            display_name += ' [COLOR skyblue]{0}[/COLOR]'.format(machine['flags'])
            if machine['isBIOS']:   display_name += ' [COLOR cyan][BIOS][/COLOR]'
            if machine['isDevice']: display_name += ' [COLOR violet][Dev][/COLOR]'
            if   machine['driver_status'] == 'imperfect':   display_name += ' [COLOR yellow][Imp][/COLOR]'
            elif machine['driver_status'] == 'preliminary': display_name += ' [COLOR red][Pre][/COLOR]'

            # --- Skin flags ---
            AEL_PClone_stat_value = AEL_PCLONE_STAT_VALUE_PARENT
        else:
            # --- Mark Flags, BIOS, Devices, BIOS, Parent/Clone and Driver status ---
            display_name += ' [COLOR skyblue]{0}[/COLOR]'.format(machine['flags'])            
            if machine['isBIOS']:   display_name += ' [COLOR cyan][BIOS][/COLOR]'
            if machine['isDevice']: display_name += ' [COLOR violet][Dev][/COLOR]'
            if machine['cloneof']:  display_name += ' [COLOR orange][Clo][/COLOR]'
            if   machine['driver_status'] == 'imperfect':   display_name += ' [COLOR yellow][Imp][/COLOR]'
            elif machine['driver_status'] == 'preliminary': display_name += ' [COLOR red][Pre][/COLOR]'

            # --- Skin flags ---
            if machine['cloneof']: AEL_PClone_stat_value = AEL_PCLONE_STAT_VALUE_CLONE
            else:                  AEL_PClone_stat_value = AEL_PCLONE_STAT_VALUE_PARENT

        # --- Assets/artwork ---
        icon_path      = machine_assets[self.mame_icon] if machine_assets[self.mame_icon] else 'DefaultProgram.png'
        fanart_path    = machine_assets[self.mame_fanart]
        banner_path    = machine_assets['marquee']
        clearlogo_path = machine_assets['clearlogo']
        poster_path    = machine_assets['flyer']

        # --- Create listitem row ---
        ICON_OVERLAY = 6
        listitem = xbmcgui.ListItem(display_name)
        # >> Make all the infolabels compatible with Advanced Emulator Launcher
        if self.settings['display_hide_trailers']:
            listitem.setInfo('video', {'title'   : display_name,     'year'    : machine['year'],
                                       'genre'   : machine['genre'], 'studio'  : machine['manufacturer'],
                                       'plot'    : machine['plot'],
                                       'overlay' : ICON_OVERLAY})
        else:
            listitem.setInfo('video', {'title'   : display_name,     'year'    : machine['year'],
                                       'genre'   : machine['genre'], 'studio'  : machine['manufacturer'],
                                       'plot'    : machine['plot'],  'trailer' : machine_assets['trailer'],
                                       'overlay' : ICON_OVERLAY})
        listitem.setProperty('nplayers', machine['nplayers'])
        listitem.setProperty('platform', 'MAME')

        # --- Assets ---
        # >> AEL/AML custom artwork fields
        listitem.setArt({'title'     : machine_assets['title'],   'snap'    : machine_assets['snap'],
                         'boxfront'  : machine_assets['cabinet'], 'boxback' : machine_assets['cpanel'],
                         'cartridge' : machine_assets['PCB'],     'flyer'   : machine_assets['flyer'] })
        # >> Kodi official artwork fields
        listitem.setArt({'icon'   : icon_path,   'fanart'    : fanart_path,
                         'banner' : banner_path, 'clearlogo' : clearlogo_path, 'poster' : poster_path })

        # --- ROM flags (Skins will use these flags to render icons) ---
        listitem.setProperty(AEL_PCLONE_STAT_LABEL, AEL_PClone_stat_value)

        # --- Create context menu ---
        URL_view_DAT    = self._misc_url_2_arg_RunPlugin('command', 'VIEW_DAT', 'machine', machine_name)
        URL_view        = self._misc_url_2_arg_RunPlugin('command', 'VIEW', 'machine', machine_name)
        URL_show_clones = self._misc_url_4_arg_RunPlugin('command', 'EXEC_SHOW_MAME_CLONES', 
                                                         'catalog', catalog_name, 'category', category_name, 'parent', machine_name)
        # URL_display     = self._misc_url_4_arg_RunPlugin('command', 'DISPLAY_SETTINGS_MAME',
        #                                                  'catalog', catalog_name, 'category', category_name, 'machine', machine_name)
        URL_fav         = self._misc_url_2_arg_RunPlugin('command', 'ADD_MAME_FAV', 'machine', machine_name)
        commands = []
        commands.append(('Info / Utils',  URL_view_DAT))
        commands.append(('View / Audit',  URL_view))
        if flag_parent_list and num_clones > 0 and view_mode_property == VIEW_MODE_PARENTS_ONLY:
            commands.append(('Show clones',  URL_show_clones))
        # commands.append(('Display settings', URL_display))
        commands.append(('Add to MAME Favourites', URL_fav))
        commands.append(('Kodi File Manager', 'ActivateWindow(filemanager)'))
        commands.append(('Add-on Settings', 'Addon.OpenSettings({0})'.format(__addon_id__)))
        listitem.addContextMenuItems(commands, replaceItems = True)

        # --- Add row ---
        if flag_parent_list and num_clones > 0 and view_mode_property == VIEW_MODE_PCLONE:
            URL = self._misc_url_3_arg('catalog', catalog_name, 'category', category_name, 'parent', machine_name)
            xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = True)
        else:
            URL = self._misc_url_2_arg('command', 'LAUNCH', 'machine', machine_name)
            xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = False)

    #
    # Not used at the moment -> There are global display settings.
    #
    def _command_context_display_settings(self, catalog_name, category_name):
        # >> Load ListItem properties
        log_debug('_command_display_settings() catalog_name  "{0}"'.format(catalog_name))
        log_debug('_command_display_settings() category_name "{0}"'.format(category_name))
        prop_key = '{0} - {1}'.format(catalog_name, category_name)
        log_debug('_command_display_settings() Loading props with key "{0}"'.format(prop_key))
        mame_properties_dic = fs_load_JSON_file(PATHS.MAIN_PROPERTIES_PATH.getPath())
        prop_dic = mame_properties_dic[prop_key]
        if prop_dic['vm'] == VIEW_MODE_NORMAL: dmode_str = 'Parents only'
        else:                                  dmode_str = 'Parents and clones'

        # --- Select menu ---
        dialog = xbmcgui.Dialog()
        menu_item = dialog.select('Display settings',
                                 ['Display mode (currently {0})'.format(dmode_str),
                                  'Default Icon',   'Default Fanart',
                                  'Default Banner', 'Default Poster',
                                  'Default Clearlogo'])
        if menu_item < 0: return
        
        # --- Display settings ---
        if menu_item == 0:
            # >> Krypton feature: preselect the current item.
            # >> NOTE Preselect must be called with named parameter, otherwise it does not work well.
            # See http://forum.kodi.tv/showthread.php?tid=250936&pid=2327011#pid2327011
            if prop_dic['vm'] == VIEW_MODE_NORMAL: p_idx = 0
            else:                                  p_idx = 1
            log_debug('_command_display_settings() p_idx = "{0}"'.format(p_idx))
            idx = dialog.select('Display mode', ['Parents only', 'Parents and clones'], preselect = p_idx)
            log_debug('_command_display_settings() idx = "{0}"'.format(idx))
            if idx < 0: return
            if idx == 0:   prop_dic['vm'] = VIEW_MODE_NORMAL
            elif idx == 1: prop_dic['vm'] = VIEW_MODE_ALL

        # --- Change default icon ---
        elif menu_item == 1:
            kodi_dialog_OK('Not coded yet. Sorry')

        # >> Changes made. Refreash container
        fs_write_JSON_file(PATHS.MAIN_PROPERTIES_PATH.getPath(), mame_properties_dic)
        kodi_refresh_container()

    #----------------------------------------------------------------------------------------------
    # Software Lists
    #----------------------------------------------------------------------------------------------
    def _render_SL_list(self, catalog_name):
        log_debug('_render_SL_list() catalog_name = {0}\n'.format(catalog_name))
        # >> Load Software List catalog
        SL_main_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
        if not SL_main_catalog_dic:
            kodi_dialog_OK('Software Lists database not found. Check out "Setup plugin" context menu.')
            xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
            return

        # >> Build SL
        SL_catalog_dic = {}
        if catalog_name == 'SL_ROM':
            for SL_name, SL_dic in SL_main_catalog_dic.iteritems():
                if SL_dic['rom_count'] > 0:
                    SL_catalog_dic[SL_name] = SL_dic
        elif catalog_name == 'SL_CHD':
            for SL_name, SL_dic in SL_main_catalog_dic.iteritems():
                if SL_dic['chd_count'] > 0:
                    SL_catalog_dic[SL_name] = SL_dic
        elif catalog_name == 'SL_ROM_CHD':
            for SL_name, SL_dic in SL_main_catalog_dic.iteritems():
                if SL_dic['rom_count'] > 0 and SL_dic['chd_count'] > 0:
                    SL_catalog_dic[SL_name] = SL_dic
        else:
            kodi_dialog_OK('Wrong catalog_name {0}'.format(catalog_name))
            return
        log_debug('_render_SL_list() len(catalog_name) = {0}\n'.format(len(SL_catalog_dic)))

        self._set_Kodi_all_sorting_methods()
        for SL_name in SL_catalog_dic:
            SL = SL_catalog_dic[SL_name]
            self._render_SL_list_row(SL_name, SL)
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_SL_ROMs(self, SL_name):
        log_debug('_render_SL_ROMs() SL_name "{0}"'.format(SL_name))

        # >> Load ListItem properties (Not used at the moment)
        # SL_properties_dic = fs_load_JSON_file(PATHS.SL_MACHINES_PROP_PATH.getPath()) 
        # prop_dic = SL_properties_dic[SL_name]
        # >> Global properties
        view_mode_property = self.settings['sl_view_mode']
        log_debug('_render_SL_ROMs() view_mode_property = {0}'.format(view_mode_property))

        # >> Load Software List ROMs
        SL_PClone_dic = fs_load_JSON_file(PATHS.SL_PCLONE_DIC_PATH.getPath())
        SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
        file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '.json'
        SL_DB_FN = PATHS.SL_DB_DIR.pjoin(file_name)
        # log_debug('_render_SL_ROMs() SL ROMs JSON "{0}"'.format(SL_DB_FN.getPath()))
        SL_roms = fs_load_JSON_file(SL_DB_FN.getPath())

        assets_file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '_assets.json'
        SL_asset_DB_FN = PATHS.SL_DB_DIR.pjoin(assets_file_name)
        SL_asset_dic = fs_load_JSON_file(SL_asset_DB_FN.getPath())

        self._set_Kodi_all_sorting_methods()
        SL_proper_name = SL_catalog_dic[SL_name]['display_name']
        if view_mode_property == VIEW_MODE_PCLONE or view_mode_property == VIEW_MODE_PARENTS_ONLY:
            log_debug('_render_SL_ROMs() Rendering Parent/Clone launcher')
            # >> Get list of parents
            parent_list = []
            for parent_name in sorted(SL_PClone_dic[SL_name]): parent_list.append(parent_name)
            for parent_name in parent_list:
                ROM        = SL_roms[parent_name]
                assets     = SL_asset_dic[parent_name] if parent_name in SL_asset_dic else fs_new_SL_asset()
                num_clones = len(SL_PClone_dic[SL_name][parent_name])
                ROM['genre'] = SL_proper_name # >> Add the SL name as 'genre'
                self._render_SL_ROM_row(SL_name, parent_name, ROM, assets, True, view_mode_property, num_clones)
        elif view_mode_property == VIEW_MODE_FLAT:
            log_debug('_render_SL_ROMs() Rendering Flat launcher')
            for rom_name in SL_roms:
                ROM    = SL_roms[rom_name]
                assets = SL_asset_dic[rom_name] if rom_name in SL_asset_dic else fs_new_SL_asset()
                ROM['genre'] = SL_proper_name # >> Add the SL name as 'genre'
                self._render_SL_ROM_row(SL_name, rom_name, ROM, assets, False, view_mode_property)
        else:
            kodi_dialog_OK('Wrong vm = "{0}". This is a bug, please report it.'.format(prop_dic['vm']))
            return
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_SL_pclone_set(self, SL_name, parent_name):
        log_debug('_render_SL_pclone_set() SL_name     "{0}"'.format(SL_name))
        log_debug('_render_SL_pclone_set() parent_name "{0}"'.format(parent_name))
        view_mode_property = self.settings['sl_view_mode']
        log_debug('_render_SL_pclone_set() view_mode_property = {0}'.format(view_mode_property))

        # >> Load Software List ROMs
        SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
        SL_PClone_dic = fs_load_JSON_file(PATHS.SL_PCLONE_DIC_PATH.getPath())
        file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '.json'
        SL_DB_FN = PATHS.SL_DB_DIR.pjoin(file_name)
        log_debug('_render_SL_pclone_set() ROMs JSON "{0}"'.format(SL_DB_FN.getPath()))
        SL_roms = fs_load_JSON_file(SL_DB_FN.getPath())

        assets_file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '_assets.json'
        SL_asset_DB_FN = PATHS.SL_DB_DIR.pjoin(assets_file_name)
        SL_asset_dic = fs_load_JSON_file(SL_asset_DB_FN.getPath())

        # >> Render parent first
        SL_proper_name = SL_catalog_dic[SL_name]['display_name']
        self._set_Kodi_all_sorting_methods()
        ROM = SL_roms[parent_name]
        assets = SL_asset_dic[parent_name] if parent_name in SL_asset_dic else fs_new_SL_asset()
        ROM['genre'] = SL_proper_name # >> Add the SL name as 'genre'
        self._render_SL_ROM_row(SL_name, parent_name, ROM, assets, False, view_mode_property)

        # >> Render clones belonging to parent in this category
        for clone_name in sorted(SL_PClone_dic[SL_name][parent_name]):
            ROM = SL_roms[clone_name]
            assets = SL_asset_dic[clone_name] if clone_name in SL_asset_dic else fs_new_SL_asset()
            ROM['genre'] = SL_proper_name # >> Add the SL name as 'genre'
            log_debug(unicode(ROM))
            self._render_SL_ROM_row(SL_name, clone_name, ROM, assets, False, view_mode_property)
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_SL_list_row(self, SL_name, SL):
        if SL['chd_count'] == 0:
            if SL['rom_count'] == 1: display_name = '{0}  [COLOR orange]({1} ROM)[/COLOR]'.format(SL['display_name'], SL['rom_count'])
            else:                    display_name = '{0}  [COLOR orange]({1} ROMs)[/COLOR]'.format(SL['display_name'], SL['rom_count'])
        elif SL['rom_count'] == 0:
            if SL['chd_count'] == 1: display_name = '{0}  [COLOR orange]({1} CHD)[/COLOR]'.format(SL['display_name'], SL['chd_count'])
            else:                    display_name = '{0}  [COLOR orange]({1} CHDs)[/COLOR]'.format(SL['display_name'], SL['chd_count'])
        else:
            display_name = '{0}  [COLOR orange]({1} ROMs and {2} CHDs)[/COLOR]'.format(SL['display_name'], SL['rom_count'], SL['chd_count'])

        # --- Create listitem row ---
        ICON_OVERLAY = 6
        listitem = xbmcgui.ListItem(display_name)
        listitem.setInfo('video', {'title' : display_name, 'overlay' : ICON_OVERLAY } )

        # --- Create context menu ---
        commands = []
        URL_view = self._misc_url_1_arg_RunPlugin('command', 'VIEW')
        commands.append(('View', URL_view ))
        commands.append(('Kodi File Manager', 'ActivateWindow(filemanager)' ))
        commands.append(('Add-on Settings', 'Addon.OpenSettings({0})'.format(__addon_id__) ))
        listitem.addContextMenuItems(commands, replaceItems = True)

        # --- Add row ---
        URL = self._misc_url_2_arg('catalog', 'SL', 'category', SL_name)
        xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = True)

    def _render_SL_ROM_row(self, SL_name, rom_name, ROM, assets, flag_parent_list, view_mode_property, num_clones = 0):
        display_name = ROM['description']
        if flag_parent_list and num_clones > 0:
            display_name += ' [COLOR orange] ({0} clones)[/COLOR]'.format(num_clones)
            status = '{0}{1}'.format(ROM['status_ROM'], ROM['status_CHD'])
            display_name += ' [COLOR skyblue]{0}[/COLOR]'.format(status)
        else:
            # --- Mark flags and status ---
            status = '{0}{1}'.format(ROM['status_ROM'], ROM['status_CHD'])
            display_name += ' [COLOR skyblue]{0}[/COLOR]'.format(status)
            if ROM['cloneof']: display_name += ' [COLOR orange][Clo][/COLOR]'

        # --- Assets/artwork ---
        icon_path   = assets[self.SL_icon] if assets[self.SL_icon] else 'DefaultProgram.png'
        fanart_path = assets[self.SL_fanart]
        poster_path = assets['boxfront']

        # --- Create listitem row ---
        ICON_OVERLAY = 6
        listitem = xbmcgui.ListItem(display_name)
        # >> Make all the infolabels compatible with Advanced Emulator Launcher
        listitem.setInfo('video', {'title'   : display_name,      'year'    : ROM['year'],
                                   'genre'   : ROM['genre'],      'studio'  : ROM['publisher'],
                                   'trailer' : assets['trailer'], 'overlay' : ICON_OVERLAY })
        listitem.setProperty('platform', 'MAME Software List')

        # --- Assets ---
        # >> AEL custom artwork fields
        listitem.setArt({'title' : assets['title'], 'snap' : assets['snap'], 'boxfront' : assets['boxfront']})
        # >> Kodi official artwork fields
        listitem.setArt({'icon' : icon_path, 'fanart' : fanart_path, 'poster' : poster_path})

        # --- Create context menu ---
        URL_view = self._misc_url_3_arg_RunPlugin('command', 'VIEW', 'SL', SL_name, 'ROM', rom_name)
        URL_show_clones = self._misc_url_4_arg_RunPlugin('command', 'EXEC_SHOW_SL_CLONES', 
                                                         'catalog', 'SL', 'category', SL_name, 'parent', rom_name)
        # URL_display = self._misc_url_4_arg_RunPlugin('command', 'DISPLAY_SETTINGS_SL', 
        #                                              'catalog', 'SL', 'category', SL_name, 'machine', rom_name)
        URL_fav = self._misc_url_3_arg_RunPlugin('command', 'ADD_SL_FAV', 'SL', SL_name, 'ROM', rom_name)
        commands = []
        commands.append(('View / Audit', URL_view))
        if flag_parent_list and num_clones > 0 and view_mode_property == VIEW_MODE_PARENTS_ONLY:
            commands.append(('Show clones',  URL_show_clones))
        # commands.append(('Display settings', URL_display))
        commands.append(('Add ROM to SL Favourites', URL_fav))
        commands.append(('Kodi File Manager', 'ActivateWindow(filemanager)'))
        commands.append(('Add-on Settings', 'Addon.OpenSettings({0})'.format(__addon_id__)))
        listitem.addContextMenuItems(commands, replaceItems = True)

        # --- Add row ---
        if flag_parent_list and num_clones > 0 and view_mode_property == VIEW_MODE_PCLONE:
            URL = self._misc_url_3_arg('catalog', 'SL', 'category', SL_name, 'parent', rom_name)
            xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = True)
        else:
            URL = self._misc_url_3_arg('command', 'LAUNCH_SL', 'SL', SL_name, 'ROM', rom_name)
            xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = False)

    #----------------------------------------------------------------------------------------------
    # DATs
    #
    # catalog = 'History'  / category = '32x' / machine = 'sonic'
    # catalog = 'MAMEINFO' / category = '32x' / machine = 'sonic'
    # catalog = 'Gameinit' / category = 'None' / machine = 'sonic'
    # catalog = 'Command'  / category = 'None' / machine = 'sonic'
    #----------------------------------------------------------------------------------------------
    def _render_DAT_list(self, catalog_name):
        # --- Create context menu ---
        commands = []
        URL_view = self._misc_url_1_arg_RunPlugin('command', 'VIEW')
        commands.append(('View', URL_view ))
        commands.append(('Kodi File Manager', 'ActivateWindow(filemanager)' ))
        commands.append(('Add-on Settings', 'Addon.OpenSettings({0})'.format(__addon_id__) ))
        # --- Unrolled variables ---
        ICON_OVERLAY = 6

        # >> Load Software List catalog
        if catalog_name == 'History':
            DAT_idx_dic = fs_load_JSON_file(PATHS.HISTORY_IDX_PATH.getPath())
            if not DAT_idx_dic:
                kodi_dialog_OK('DAT database file "{0}" empty.'.format(catalog_name))
                xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
                return
            self._set_Kodi_all_sorting_methods()
            for key in DAT_idx_dic:
                category_name = '{0} [COLOR lightgray]({1})[/COLOR]'.format(DAT_idx_dic[key]['name'], key)
                listitem = xbmcgui.ListItem(category_name)
                listitem.setInfo('video', {'title' : category_name, 'overlay' : ICON_OVERLAY } )
                listitem.addContextMenuItems(commands, replaceItems = True)
                URL = self._misc_url_2_arg('catalog', catalog_name, 'category', key)
                xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = True)
        elif catalog_name == 'MAMEINFO':
            DAT_idx_dic = fs_load_JSON_file(PATHS.MAMEINFO_IDX_PATH.getPath())
            if not DAT_idx_dic:
                kodi_dialog_OK('DAT database file "{0}" empty.'.format(catalog_name))
                xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
                return
            self._set_Kodi_all_sorting_methods()
            for key in DAT_idx_dic:
                category_name = '{0}'.format(key)
                listitem = xbmcgui.ListItem(category_name)
                listitem.setInfo('video', {'title' : category_name, 'overlay' : ICON_OVERLAY } )
                listitem.addContextMenuItems(commands, replaceItems = True)
                URL = self._misc_url_2_arg('catalog', catalog_name, 'category', key)
                xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = True)
        elif catalog_name == 'Gameinit':
            DAT_idx_list = fs_load_JSON_file(PATHS.GAMEINIT_IDX_PATH.getPath())
            if not DAT_idx_list:
                kodi_dialog_OK('DAT database file "{0}" empty.'.format(catalog_name))
                xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
                return
            self._set_Kodi_all_sorting_methods()
            for machine_name_list in DAT_idx_list:
                machine_name = '{0} [COLOR lightgray]({1})[/COLOR]'.format(machine_name_list[1], machine_name_list[0])
                listitem = xbmcgui.ListItem(machine_name)
                listitem.setInfo('video', {'title' : machine_name, 'overlay' : ICON_OVERLAY } )
                listitem.addContextMenuItems(commands, replaceItems = True)
                URL = self._misc_url_3_arg('catalog', catalog_name, 'category', 'None', 'machine', machine_name_list[0])
                xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = False)
        elif catalog_name == 'Command':
            DAT_idx_list = fs_load_JSON_file(PATHS.COMMAND_IDX_PATH.getPath())
            if not DAT_idx_list:
                kodi_dialog_OK('DAT database file "{0}" empty.'.format(catalog_name))
                xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
                return
            self._set_Kodi_all_sorting_methods()
            for machine_name_list in DAT_idx_list:
                machine_name = '{0} [COLOR lightgray]({1})[/COLOR]'.format(machine_name_list[1], machine_name_list[0])
                listitem = xbmcgui.ListItem(machine_name)
                listitem.setInfo('video', {'title' : machine_name, 'overlay' : ICON_OVERLAY } )
                listitem.addContextMenuItems(commands, replaceItems = True)
                URL = self._misc_url_3_arg('catalog', catalog_name, 'category', 'None', 'machine', machine_name_list[0])
                xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = False)
        else:
            kodi_dialog_OK('DAT database file "{0}" not found. Check out "Setup plugin" context menu.'.format(catalog_name))
            xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
            return
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_DAT_category(self, catalog_name, category_name):
        # >> Load Software List catalog
        if catalog_name == 'History':
            DAT_catalog_dic = fs_load_JSON_file(PATHS.HISTORY_IDX_PATH.getPath())
        elif catalog_name == 'MAMEINFO':
            DAT_catalog_dic = fs_load_JSON_file(PATHS.MAMEINFO_IDX_PATH.getPath())
        else:
            kodi_dialog_OK('DAT database file "{0}" not found. Check out "Setup plugin" context menu.'.format(catalog_name))
            xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
            return
        if not DAT_catalog_dic:
            kodi_dialog_OK('DAT database file "{0}" empty.'.format(catalog_name))
            xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
            return
        self._set_Kodi_all_sorting_methods()
        if catalog_name == 'History':
            category_machine_list = DAT_catalog_dic[category_name]['machines']
            for machine_tuple in category_machine_list:
                self._render_DAT_category_row(catalog_name, category_name, machine_tuple)
        elif catalog_name == 'MAMEINFO':
            category_machine_list = DAT_catalog_dic[category_name]
            for machine_tuple in category_machine_list:
                self._render_DAT_category_row(catalog_name, category_name, machine_tuple)
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_DAT_category_row(self, catalog_name, category_name, machine_tuple):
        display_name = '{0} [COLOR lightgray]({1})[/COLOR]'.format(machine_tuple[1], machine_tuple[0])

        # --- Create listitem row ---
        ICON_OVERLAY = 6
        listitem = xbmcgui.ListItem(display_name)
        listitem.setInfo('video', {'title' : display_name, 'overlay' : ICON_OVERLAY } )

        # --- Create context menu ---
        commands = []
        URL_view = self._misc_url_1_arg_RunPlugin('command', 'VIEW')
        commands.append(('View', URL_view ))
        commands.append(('Kodi File Manager', 'ActivateWindow(filemanager)' ))
        commands.append(('Add-on Settings', 'Addon.OpenSettings({0})'.format(__addon_id__) ))
        listitem.addContextMenuItems(commands, replaceItems = True)

        # --- Add row ---
        URL = self._misc_url_3_arg('catalog', catalog_name, 'category', category_name, 'machine', machine_tuple[0])
        xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = False)

    def _render_DAT_machine_info(self, catalog_name, category_name, machine_name):
        log_debug('_render_DAT_machine_info() catalog_name "{0}"'.format(catalog_name))
        log_debug('_render_DAT_machine_info() category_name "{0}"'.format(category_name))
        log_debug('_render_DAT_machine_info() machine_name "{0}"'.format(machine_name))

        # >> Load Software List catalog
        if catalog_name == 'History':
            DAT_dic = fs_load_JSON_file(PATHS.HISTORY_DB_PATH.getPath())
            info_str = DAT_dic[category_name][machine_name]
            info_text = info_str
        elif catalog_name == 'MAMEINFO':
            DAT_dic = fs_load_JSON_file(PATHS.MAMEINFO_DB_PATH.getPath())
            info_str = DAT_dic[category_name][machine_name]
            info_text = info_str
        elif catalog_name == 'Gameinit':
            DAT_dic = fs_load_JSON_file(PATHS.GAMEINIT_DB_PATH.getPath())
            info_str = DAT_dic[machine_name]
            info_text = info_str
        elif catalog_name == 'Command':
            DAT_dic = fs_load_JSON_file(PATHS.COMMAND_DB_PATH.getPath())
            info_str = DAT_dic[machine_name]
            info_text = info_str
        else:
            kodi_dialog_OK('Wrong catalog_name "{0}". '.format(catalog_name) +
                           'This is a bug, please report it.')
            return

        # --- Show information window ---
        window_title = '{0} information'.format(catalog_name)
        self._display_text_window(window_title, info_text)

    #
    # Not used at the moment -> There are global display settings.
    #
    def _command_context_display_settings_SL(self, SL_name):
        log_debug('_command_display_settings_SL() SL_name "{0}"'.format(SL_name))

        # --- Load properties DB ---
        SL_properties_dic = fs_load_JSON_file(PATHS.SL_MACHINES_PROP_PATH.getPath())
        prop_dic = SL_properties_dic[SL_name]

        # --- Show menu ---
        if prop_dic['vm'] == VIEW_MODE_NORMAL: dmode_str = 'Parents only'
        else:                                  dmode_str = 'Parents and clones'
        dialog = xbmcgui.Dialog()
        menu_item = dialog.select('Display settings',
                                 ['Display mode (currently {0})'.format(dmode_str),
                                  'Default Icon', 'Default Fanart', 
                                  'Default Banner', 'Default Poster', 'Default Clearlogo'])
        if menu_item < 0: return

        # --- Change display mode ---
        if menu_item == 0:
            if prop_dic['vm'] == VIEW_MODE_NORMAL: p_idx = 0
            else:                                  p_idx = 1
            log_debug('_command_display_settings() p_idx = "{0}"'.format(p_idx))
            idx = dialog.select('Display mode', ['Parents only', 'Parents and clones'], preselect = p_idx)
            log_debug('_command_display_settings() idx = "{0}"'.format(idx))
            if idx < 0: return
            if idx == 0:   prop_dic['vm'] = VIEW_MODE_NORMAL
            elif idx == 1: prop_dic['vm'] = VIEW_MODE_ALL

        # --- Change default icon ---
        elif menu_item == 1:
            kodi_dialog_OK('Not coded yet. Sorry')

        # --- Save display settings ---
        fs_write_JSON_file(PATHS.SL_MACHINES_PROP_PATH.getPath(), SL_properties_dic)
        kodi_refresh_container()

    # ---------------------------------------------------------------------------------------------
    # Information display / Utilities
    # ---------------------------------------------------------------------------------------------
    def _command_context_view_DAT(self, machine_name, SL_name, SL_ROM, location):
        # --- Determine if we are in a category, launcher or ROM ---
        log_debug('_command_context_view_DAT() machine_name "{0}"'.format(machine_name))
        log_debug('_command_context_view_DAT() SL_name      "{0}"'.format(SL_name))
        log_debug('_command_context_view_DAT() SL_ROM       "{0}"'.format(SL_ROM))
        log_debug('_command_context_view_DAT() location     "{0}"'.format(location))

        # >> Load DAT indices
        History_idx_dic   = fs_load_JSON_file(PATHS.HISTORY_IDX_PATH.getPath())
        Mameinfo_idx_dic  = fs_load_JSON_file(PATHS.MAMEINFO_IDX_PATH.getPath())
        Gameinit_idx_list = fs_load_JSON_file(PATHS.GAMEINIT_IDX_PATH.getPath())
        Command_idx_list  = fs_load_JSON_file(PATHS.COMMAND_IDX_PATH.getPath())

        # >> Check if DAT information is available for this machine
        if location == 'STANDARD':
            if History_idx_dic:
                History_MAME_set = set([ machine[0] for machine in History_idx_dic['mame']['machines'] ])
                if machine_name in History_MAME_set: History_str = 'Found'
                else:                                History_str = 'Not found'
            else:
                History_str = 'Not configured'
            if Mameinfo_idx_dic:
                Mameinfo_MAME_set = set([ machine[0] for machine in Mameinfo_idx_dic['mame'] ])
                if machine_name in Mameinfo_MAME_set: Mameinfo_str = 'Found'
                else:                                 Mameinfo_str = 'Not found'
            else:
                Mameinfo_str = 'Not configured'
            if Gameinit_idx_list:
                Gameinit_MAME_set = set([ machine[0] for machine in Gameinit_idx_list ])
                if machine_name in Gameinit_MAME_set: Gameinit_str = 'Found'
                else:                                 Gameinit_str = 'Not found'
            else:
                Gameinit_str = 'Not configured'
            if Command_idx_list:
                Command_MAME_set = set([ machine[0] for machine in Command_idx_list ])
                if machine_name in Command_MAME_set: Command_str = 'Found'
                else:                                Command_str = 'Not found'
            else:
                Command_str = 'Not configured'
        else:
            kodi_dialog_OK('Location {0} not supported. This is a bug, please report it.'.format(location))
            return

        # >> Menu
        d_list = [
          'View History DAT ({0})'.format(History_str),
          'View MAMEinfo DAT ({0})'.format(Mameinfo_str),
          'View Gameinit DAT ({0})'.format(Gameinit_str),
          'View Command DAT ({0})'.format(Command_str),
          'Display brother machines',
        ]
        s_value = xbmcgui.Dialog().select('View', d_list)
        if s_value < 0: return

        if s_value == 0:
            if machine_name not in History_MAME_set:
                kodi_dialog_OK('Machine {0} not in History DAT'.format(machine_name))
                return
            DAT_dic = fs_load_JSON_file(PATHS.HISTORY_DB_PATH.getPath())
            window_title = 'History DAT for machine {0}'.format(machine_name)
            info_text = DAT_dic['mame'][machine_name]
            self._display_text_window(window_title, info_text)
        elif s_value == 1:
            if machine_name not in Mameinfo_MAME_set:
                kodi_dialog_OK('Machine {0} not in Mameinfo DAT'.format(machine_name))
                return
            DAT_dic = fs_load_JSON_file(PATHS.MAMEINFO_DB_PATH.getPath())
            info_text = DAT_dic['mame'][machine_name]

            window_title = 'MAMEinfo DAT for machine {0}'.format(machine_name)
            self._display_text_window(window_title, info_text)
        elif s_value == 2:
            if machine_name not in Gameinit_MAME_set:
                kodi_dialog_OK('Machine {0} not in Gameinit DAT'.format(machine_name))
                return
            DAT_dic = fs_load_JSON_file(PATHS.GAMEINIT_DB_PATH.getPath())
            window_title = 'Gameinit DAT for machine {0}'.format(machine_name)
            info_text = DAT_dic[machine_name]
            self._display_text_window(window_title, info_text)
        elif s_value == 3:
            if machine_name not in Command_MAME_set:
                kodi_dialog_OK('Machine {0} not in Command DAT'.format(machine_name))
                return
            DAT_dic = fs_load_JSON_file(PATHS.COMMAND_DB_PATH.getPath())
            window_title = 'Command DAT for machine {0}'.format(machine_name)
            info_text = DAT_dic[machine_name]
            self._display_text_window(window_title, info_text)
        # --- Display brother machines (same driver) ---
        # catalog = 'Driver', 
        elif s_value == 4:
            kodi_dialog_OK('"Display brother machines" not coded yet, sorry.')

    # ---------------------------------------------------------------------------------------------
    # Information display
    # ---------------------------------------------------------------------------------------------
    def _command_context_view(self, machine_name, SL_name, SL_ROM, location):
        VIEW_SIMPLE       = 100
        VIEW_MAME_MACHINE = 200
        VIEW_SL_ROM       = 300

        ACTION_VIEW_MACHINE_DATA       = 100
        ACTION_VIEW_MACHINE_ROMS       = 200
        ACTION_VIEW_MACHINE_AUDIT_ROMS = 300
        ACTION_VIEW_SL_ROM_DATA        = 400
        ACTION_VIEW_SL_ROM_ROMS        = 500
        ACTION_VIEW_SL_ROM_AUDIT_ROMS  = 600
        ACTION_VIEW_DB_STATS           = 700
        ACTION_VIEW_EXEC_OUTPUT        = 800
        ACTION_VIEW_REPORT_SCANNER     = 900
        ACTION_VIEW_REPORT_ASSETS      = 1000
        ACTION_VIEW_REPORT_AUDIT       = 1100
        ACTION_AUDIT_MAME_MACHINE      = 1200
        ACTION_AUDIT_SL_MACHINE        = 1300

        # --- Determine if we are in a category, launcher or ROM ---
        log_debug('_command_context_view() machine_name "{0}"'.format(machine_name))
        log_debug('_command_context_view() SL_name      "{0}"'.format(SL_name))
        log_debug('_command_context_view() SL_ROM       "{0}"'.format(SL_ROM))
        log_debug('_command_context_view() location     "{0}"'.format(location))
        if not machine_name and not SL_name:
            view_type = VIEW_SIMPLE
        elif machine_name:
            view_type = VIEW_MAME_MACHINE
        elif SL_name:
            view_type = VIEW_SL_ROM
        log_debug('_command_context_view() view_type = {0}'.format(view_type))

        # --- Build menu base on view_type ---
        if PATHS.MAME_OUTPUT_PATH.exists():
            filesize = PATHS.MAME_OUTPUT_PATH.fileSize()
            STD_status = '{0} bytes'.format(filesize)
        else:
            STD_status = 'not found'

        if view_type == VIEW_SIMPLE:
            d_list = [
              'View database statistics',
              'View scanner reports ...',
              'View asset/artwork reports ...',
              'View audit reports ...',
              'View MAME last execution output ({0})'.format(STD_status),
            ]
        elif view_type == VIEW_MAME_MACHINE:
            d_list = [
              'View MAME machine data',
              'View MAME machine ROMs (ROMs DB)',
              'View MAME machine ROMs (Audit DB)',
              'Audit MAME machine ROMs',
              'View database statistics',
              'View scanner reports ...',
              'View asset/artwork reports ...',
              'View audit reports ...',
              'View MAME last execution output ({0})'.format(STD_status),
            ]
        elif view_type == VIEW_SL_ROM:
            d_list = [
              'View Software List item data',
              'View Software List ROMs (ROMs DB)',
              'View Software List ROMs (Audit DB)',
              'Audit Software List ROMs',
              'View database statistics',
              'View scanner reports ...',
              'View asset/artwork reports ...',
              'View audit reports ...',
              'View MAME last execution output ({0})'.format(STD_status),
            ]
        else:
            kodi_dialog_OK('Wrong view_type = {0}. This is a bug, please report it.'.format(view_type))
            return
        selected_value = xbmcgui.Dialog().select('View', d_list)
        if selected_value < 0: return

        # --- Polymorphic menu. Determine action to do. ---
        if view_type == VIEW_SIMPLE:
            if   selected_value == 0: action = ACTION_VIEW_DB_STATS
            elif selected_value == 1: action = ACTION_VIEW_REPORT_SCANNER
            elif selected_value == 2: action = ACTION_VIEW_REPORT_ASSETS
            elif selected_value == 3: action = ACTION_VIEW_REPORT_AUDIT
            elif selected_value == 4: action = ACTION_VIEW_EXEC_OUTPUT
            else:
                kodi_dialog_OK('view_type == VIEW_SIMPLE and selected_value = {0}. '.format(selected_value) +
                               'This is a bug, please report it.')
                return
        elif view_type == VIEW_MAME_MACHINE:
            if   selected_value == 0: action = ACTION_VIEW_MACHINE_DATA
            elif selected_value == 1: action = ACTION_VIEW_MACHINE_ROMS
            elif selected_value == 2: action = ACTION_VIEW_MACHINE_AUDIT_ROMS
            elif selected_value == 3: action = ACTION_AUDIT_MAME_MACHINE
            elif selected_value == 4: action = ACTION_VIEW_DB_STATS
            elif selected_value == 5: action = ACTION_VIEW_REPORT_SCANNER
            elif selected_value == 6: action = ACTION_VIEW_REPORT_ASSETS
            elif selected_value == 7: action = ACTION_VIEW_REPORT_AUDIT
            elif selected_value == 8: action = ACTION_VIEW_EXEC_OUTPUT
            else:
                kodi_dialog_OK('view_type == VIEW_MAME_MACHINE and selected_value = {0}. '.format(selected_value) +
                               'This is a bug, please report it.')
                return
        elif view_type == VIEW_SL_ROM:
            if   selected_value == 0: action = ACTION_VIEW_SL_ROM_DATA
            elif selected_value == 1: action = ACTION_VIEW_SL_ROM_ROMS
            elif selected_value == 2: action = ACTION_VIEW_SL_ROM_AUDIT_ROMS
            elif selected_value == 3: action = ACTION_AUDIT_SL_MACHINE
            elif selected_value == 4: action = ACTION_VIEW_DB_STATS
            elif selected_value == 5: action = ACTION_VIEW_REPORT_SCANNER
            elif selected_value == 6: action = ACTION_VIEW_REPORT_ASSETS
            elif selected_value == 7: action = ACTION_VIEW_REPORT_AUDIT
            elif selected_value == 8: action = ACTION_VIEW_EXEC_OUTPUT
            else:
                kodi_dialog_OK('view_type == VIEW_SL_ROM and selected_value = {0}. '.format(selected_value) +
                               'This is a bug, please report it.')
                return
        else:
            kodi_dialog_OK('Wrong view_type = {0}. '.format(view_type) +
                           'This is a bug, please report it.')
            return
        log_debug('_command_context_view() action = {0}'.format(action))

        # --- Execute action ---
        if action == ACTION_VIEW_MACHINE_DATA:
            if location == LOCATION_STANDARD:
                # >> Read MAME machine information
                kodi_busydialog_ON()
                machine    = fs_get_machine_main_db_hash(PATHS, machine_name)
                assets_dic = fs_load_JSON_file(PATHS.MAIN_ASSETS_DB_PATH.getPath())
                kodi_busydialog_OFF()
                assets  = assets_dic[machine_name]
                window_title = 'MAME Machine Information'
            elif location == LOCATION_MAME_FAVS:
                machines = fs_load_JSON_file(PATHS.FAV_MACHINES_PATH.getPath())
                machine = machines[machine_name]
                assets = machine['assets']
                window_title = 'Favourite MAME Machine Information'

            # --- Make information string ---
            info_text  = '[COLOR orange]Machine {0} / Render data[/COLOR]\n'.format(machine_name)
            if location == LOCATION_MAME_FAVS:
                if 'ver_mame' in machine:
                    info_text += "[COLOR slateblue]ver_mame[/COLOR]: {0}\n".format(machine['ver_mame'])
                else:
                    info_text += "[COLOR slateblue]ver_mame[/COLOR]: not available\n"
                if 'ver_mame_str' in machine:
                    info_text += "[COLOR slateblue]ver_mame_str[/COLOR]: {0}\n".format(machine['ver_mame_str'])
                else:
                    info_text += "[COLOR slateblue]ver_mame_str[/COLOR]: not available\n"
            info_text += "[COLOR violet]cloneof[/COLOR]: '{0}'\n".format(machine['cloneof'])
            info_text += "[COLOR violet]description[/COLOR]: '{0}'\n".format(machine['description'])
            info_text += "[COLOR violet]driver_status[/COLOR]: '{0}'\n".format(machine['driver_status'])
            info_text += "[COLOR violet]flags[/COLOR]: '{0}'\n".format(machine['flags'])
            info_text += "[COLOR violet]genre[/COLOR]: '{0}'\n".format(machine['genre'])
            info_text += "[COLOR skyblue]isBIOS[/COLOR]: {0}\n".format(machine['isBIOS'])
            info_text += "[COLOR skyblue]isDevice[/COLOR]: {0}\n".format(machine['isDevice'])
            info_text += "[COLOR violet]manufacturer[/COLOR]: '{0}'\n".format(machine['manufacturer'])
            info_text += "[COLOR violet]nplayers[/COLOR]: '{0}'\n".format(machine['nplayers'])
            info_text += "[COLOR violet]year[/COLOR]: '{0}'\n".format(machine['year'])

            info_text += '\n[COLOR orange]Machine data[/COLOR]\n'.format(machine_name)
            info_text += "[COLOR violet]bestgames[/COLOR]: '{0}'\n".format(machine['bestgames'])
            info_text += "[COLOR violet]catlist[/COLOR]: '{0}'\n".format(machine['catlist'])
            info_text += "[COLOR violet]catver[/COLOR]: '{0}'\n".format(machine['catver'])
            info_text += "[COLOR skyblue]coins[/COLOR]: {0}\n".format(machine['coins'])
            info_text += "[COLOR skyblue]control_type[/COLOR]: {0}\n".format(unicode(machine['control_type']))
            # Devices list is a special case.
            if machine['devices']:
                for i, device in enumerate(machine['devices']):
                    info_text += "[COLOR lime]devices[/COLOR][{0}]:\n".format(i)
                    info_text += "  [COLOR violet]att_type[/COLOR]: {0}\n".format(device['att_type'])
                    info_text += "  [COLOR violet]att_tag[/COLOR]: {0}\n".format(device['att_tag'])
                    info_text += "  [COLOR skyblue]att_mandatory[/COLOR]: {0}\n".format(unicode(device['att_mandatory']))
                    info_text += "  [COLOR violet]att_interface[/COLOR]: {0}\n".format(device['att_interface'])
                    info_text += "  [COLOR skyblue]instance[/COLOR]: {0}\n".format(unicode(device['instance']))
                    info_text += "  [COLOR skyblue]ext_names[/COLOR]: {0}\n".format(unicode(device['ext_names']))
            else:
                info_text += "[COLOR lime]devices[/COLOR]: []\n"
            info_text += "[COLOR skyblue]display_rotate[/COLOR]: {0}\n".format(unicode(machine['display_rotate']))
            info_text += "[COLOR skyblue]display_tag[/COLOR]: {0}\n".format(unicode(machine['display_tag']))
            info_text += "[COLOR skyblue]display_type[/COLOR]: {0}\n".format(unicode(machine['display_type']))
            info_text += "[COLOR violet]genre[/COLOR]: '{0}'\n".format(machine['genre'])
            info_text += "[COLOR skyblue]isDead[/COLOR]: {0}\n".format(unicode(machine['isDead']))
            info_text += "[COLOR skyblue]isMechanical[/COLOR]: {0}\n".format(unicode(machine['isMechanical']))
            info_text += "[COLOR violet]nplayers[/COLOR]: '{0}'\n".format(machine['nplayers'])
            info_text += "[COLOR violet]romof[/COLOR]: '{0}'\n".format(machine['romof'])
            info_text += "[COLOR violet]sampleof[/COLOR]: '{0}'\n".format(machine['sampleof'])
            info_text += "[COLOR violet]series[/COLOR]: '{0}'\n".format(machine['series'])
            info_text += "[COLOR skyblue]softwarelists[/COLOR]: {0}\n".format(unicode(machine['softwarelists']))
            info_text += "[COLOR violet]sourcefile[/COLOR]: '{0}'\n".format(machine['sourcefile'])

            info_text += '\n[COLOR orange]Asset/artwork data[/COLOR]\n'
            info_text += "[COLOR violet]cabinet[/COLOR]: '{0}'\n".format(assets['cabinet'])
            info_text += "[COLOR violet]cpanel[/COLOR]: '{0}'\n".format(assets['cpanel'])
            info_text += "[COLOR violet]flyer[/COLOR]: '{0}'\n".format(assets['flyer'])
            info_text += "[COLOR violet]marquee[/COLOR]: '{0}'\n".format(assets['marquee'])
            info_text += "[COLOR violet]PCB[/COLOR]: '{0}'\n".format(assets['PCB'])
            info_text += "[COLOR violet]snap[/COLOR]: '{0}'\n".format(assets['snap'])
            info_text += "[COLOR violet]title[/COLOR]: '{0}'\n".format(assets['title'])
            info_text += "[COLOR violet]clearlogo[/COLOR]: '{0}'\n".format(assets['clearlogo'])
            info_text += "[COLOR violet]trailer[/COLOR]: '{0}'\n".format(assets['trailer'])
            info_text += "[COLOR violet]manual[/COLOR]: '{0}'\n".format(assets['manual'])

            # --- Show information window ---
            self._display_text_window(window_title, info_text)

        # --- View Software List ROM Machine data ---
        elif action == ACTION_VIEW_SL_ROM_DATA:
            if location == LOCATION_STANDARD:
                SL_DB_FN = PATHS.SL_DB_DIR.pjoin(SL_name + '.json')
                kodi_busydialog_ON()
                SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
                SL_machines_dic = fs_load_JSON_file(PATHS.SL_MACHINES_PATH.getPath())
                assets_file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '_assets.json'
                SL_asset_DB_FN = PATHS.SL_DB_DIR.pjoin(assets_file_name)
                SL_asset_dic = fs_load_JSON_file(SL_asset_DB_FN.getPath())
                kodi_busydialog_OFF()
                SL_dic = SL_catalog_dic[SL_name]
                SL_machine_list = SL_machines_dic[SL_name]
                roms = fs_load_JSON_file(SL_DB_FN.getPath())
                rom = roms[SL_ROM]
                assets = SL_asset_dic[SL_ROM] if SL_ROM in SL_asset_dic else fs_new_SL_asset()
                window_title = 'Software List ROM Information'

                # >> Build information string
                info_text  = '[COLOR orange]ROM {0}[/COLOR]\n'.format(SL_ROM)
                info_text += "[COLOR violet]cloneof[/COLOR]: '{0}'\n".format(rom['cloneof'])
                info_text += "[COLOR violet]description[/COLOR]: '{0}'\n".format(rom['description'])
                info_text += "[COLOR skyblue]num_disks[/COLOR]: {0}\n".format(rom['num_disks'])
                info_text += "[COLOR skyblue]num_roms[/COLOR]: {0}\n".format(rom['num_roms'])
                if rom['parts']:
                    for i, part in enumerate(rom['parts']):
                        info_text += "[COLOR lime]parts[/COLOR][{0}]:\n".format(i)
                        info_text += "  [COLOR violet]interface[/COLOR]: '{0}'\n".format(part['interface'])
                        info_text += "  [COLOR violet]name[/COLOR]: '{0}'\n".format(part['name'])
                else:
                    info_text += '[COLOR lime]parts[/COLOR]: []\n'
                info_text += "[COLOR violet]publisher[/COLOR]: '{0}'\n".format(rom['publisher'])
                info_text += "[COLOR violet]status_CHD[/COLOR]: '{0}'\n".format(rom['status_CHD'])
                info_text += "[COLOR violet]status_ROM[/COLOR]: '{0}'\n".format(rom['status_ROM'])
                info_text += "[COLOR violet]year[/COLOR]: '{0}'\n".format(rom['year'])

                info_text += '\n[COLOR orange]Software List assets[/COLOR]\n'
                info_text += "[COLOR violet]title[/COLOR]: '{0}'\n".format(assets['title'])
                info_text += "[COLOR violet]snap[/COLOR]: '{0}'\n".format(assets['snap'])
                info_text += "[COLOR violet]boxfront[/COLOR]: '{0}'\n".format(assets['boxfront'])
                info_text += "[COLOR violet]trailer[/COLOR]: '{0}'\n".format(assets['trailer'])
                info_text += "[COLOR violet]manual[/COLOR]: '{0}'\n".format(assets['manual'])

                info_text += '\n[COLOR orange]Software List {0}[/COLOR]\n'.format(SL_name)
                info_text += "[COLOR skyblue]chd_count[/COLOR]: {0}\n".format(SL_dic['chd_count'])
                info_text += "[COLOR violet]display_name[/COLOR]: '{0}'\n".format(SL_dic['display_name'])
                info_text += "[COLOR violet]rom_DB_noext[/COLOR]: '{0}'\n".format(SL_dic['rom_DB_noext'])
                info_text += "[COLOR violet]rom_count[/COLOR]: '{0}'\n".format(SL_dic['rom_count'])

                info_text += '\n[COLOR orange]Runnable by[/COLOR]\n'
                for machine_dic in sorted(SL_machine_list):
                    t = "[COLOR violet]machine[/COLOR]: '{0}' [COLOR slateblue]({1})[/COLOR]\n"
                    info_text += t.format(machine_dic['description'], machine_dic['machine'])

            elif location == LOCATION_SL_FAVS:
                fav_SL_roms = fs_load_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath())
                fav_key = SL_name + '-' + SL_ROM
                rom = fav_SL_roms[fav_key]
                window_title = 'Favourite Software List ROM Information'

                # >> Build information string
                info_text = '[COLOR orange]ROM {0}[/COLOR]\n'.format(fav_key)
                if 'ver_mame' in rom:
                    info_text += "[COLOR slateblue]ver_mame[/COLOR]: {0}\n".format(rom['ver_mame'])
                else:
                    info_text += "[COLOR slateblue]ver_mame[/COLOR]: not available\n"
                if 'ver_mame_str' in rom:
                    info_text += "[COLOR slateblue]ver_mame_str[/COLOR]: {0}\n".format(rom['ver_mame_str'])
                else:
                    info_text += "[COLOR slateblue]ver_mame_str[/COLOR]: not available\n"
                info_text += "[COLOR violet]ROM_name[/COLOR]: '{0}'\n".format(rom['ROM_name'])
                info_text += "[COLOR violet]SL_name[/COLOR]: '{0}'\n".format(rom['SL_name'])
                info_text += "[COLOR violet]cloneof[/COLOR]: '{0}'\n".format(rom['cloneof'])
                info_text += "[COLOR violet]description[/COLOR]: '{0}'\n".format(rom['description'])
                info_text += "[COLOR violet]launch_machine[/COLOR]: '{0}'\n".format(rom['launch_machine'])
                info_text += "[COLOR skyblue]num_disks[/COLOR]: {0}\n".format(unicode(rom['num_disks']))
                info_text += "[COLOR skyblue]num_roms[/COLOR]: {0}\n".format(unicode(rom['num_roms']))
                if rom['parts']:
                    for i, part in enumerate(rom['parts']):
                        info_text += "[COLOR lime]parts[/COLOR][{0}]:\n".format(i)
                        info_text += "  [COLOR violet]interface[/COLOR]: '{0}'\n".format(part['interface'])
                        info_text += "  [COLOR violet]name[/COLOR]: '{0}'\n".format(part['name'])
                else:
                    info_text += '[COLOR lime]parts[/COLOR]: []\n'
                info_text += "[COLOR violet]publisher[/COLOR]: '{0}'\n".format(rom['publisher'])
                info_text += "[COLOR violet]status_CHD[/COLOR]: '{0}'\n".format(rom['status_CHD'])
                info_text += "[COLOR violet]status_ROM[/COLOR]: '{0}'\n".format(rom['status_ROM'])
                info_text += "[COLOR violet]year[/COLOR]: '{0}'\n".format(rom['year'])

                info_text += '\n[COLOR orange]Software List assets[/COLOR]\n'
                info_text += "[COLOR violet]title[/COLOR]: '{0}'\n".format(rom['assets']['title'])
                info_text += "[COLOR violet]snap[/COLOR]: '{0}'\n".format(rom['assets']['snap'])
                info_text += "[COLOR violet]boxfront[/COLOR]: '{0}'\n".format(rom['assets']['boxfront'])
            self._display_text_window(window_title, info_text)

        # --- View database information and statistics stored in control dictionary ---
        elif action == ACTION_VIEW_DB_STATS:
            # --- Warn user if error ---
            if not PATHS.MAIN_CONTROL_PATH.exists():
                kodi_dialog_OK('MAME database not found. Please setup the addon first.')
                return

            # --- Load control dic ---
            control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
            window_title = 'Database information and statistics'

            # --- Main stuff ---
            info_text  = '[COLOR orange]Main information[/COLOR]\n'
            info_text += "AML version            {0}\n".format(__addon_version__)
            info_text += "MAME version string    {0}\n".format(control_dic['ver_mame_str'])
            info_text += "MAME version numerical {0}\n".format(control_dic['ver_mame'])
            info_text += "catver.ini version     {0}\n".format(control_dic['ver_catver'])
            info_text += "catlist.ini version    {0}\n".format(control_dic['ver_catlist'])
            info_text += "genre.ini version      {0}\n".format(control_dic['ver_genre'])
            info_text += "nplayers.ini version   {0}\n".format(control_dic['ver_nplayers'])
            info_text += "bestgames.ini version  {0}\n".format(control_dic['ver_bestgames'])
            info_text += "series.ini version     {0}\n".format(control_dic['ver_series'])

            info_text += '\n[COLOR orange]MAME machine count[/COLOR]\n'
            t = "Machines   {0:5d}  ({1:5d} Parents / {2:5d} Clones)\n"
            info_text += t.format(control_dic['stats_processed_machines'],
                                  control_dic['stats_parents'], 
                                  control_dic['stats_clones'])
            t = "Devices    {0:5d}  ({1:5d} Parents / {2:5d} Clones)\n"
            info_text += t.format(control_dic['stats_devices'],
                                  control_dic['stats_devices_parents'], 
                                  control_dic['stats_devices_clones'])
            t = "Runnable   {0:5d}  ({1:5d} Parents / {2:5d} Clones)\n"
            info_text += t.format(control_dic['stats_runnable'],
                                  control_dic['stats_runnable_parents'], 
                                  control_dic['stats_runnable_clones'])
            t = "Samples    {0:5d}  ({1:5d} Parents / {2:5d} Clones)\n"
            info_text += t.format(control_dic['stats_samples'],
                                  control_dic['stats_samples_parents'], 
                                  control_dic['stats_samples_clones'])

            t = "BIOS       {0:5d}  ({1:5d} Parents / {2:5d} Clones)\n"
            info_text += t.format(control_dic['stats_BIOS'],
                                  control_dic['stats_BIOS_parents'], 
                                  control_dic['stats_BIOS_clones'])
            t = "Coin       {0:5d}  ({1:5d} Parents / {2:5d} Clones)\n"
            info_text += t.format(control_dic['stats_coin'],
                                  control_dic['stats_coin_parents'], 
                                  control_dic['stats_coin_clones'])
            t = "Nocoin     {0:5d}  ({1:5d} Parents / {2:5d} Clones)\n"
            info_text += t.format(control_dic['stats_nocoin'],
                                  control_dic['stats_nocoin_parents'],
                                  control_dic['stats_nocoin_clones'])
            t = "Mechanical {0:5d}  ({1:5d} Parents / {2:5d} Clones)\n"
            info_text += t.format(control_dic['stats_mechanical'],
                                  control_dic['stats_mechanical_parents'],
                                  control_dic['stats_mechanical_clones'])
            t = "Dead       {0:5d}  ({1:5d} Parents / {2:5d} Clones)\n"
            info_text += t.format(control_dic['stats_dead'],
                                  control_dic['stats_dead_parents'], 
                                  control_dic['stats_dead_clones'])

            rom_set = ['Merged', 'Split', 'Non-merged'][self.settings['mame_rom_set']]
            chd_set = ['Merged', 'Split', 'Non-merged'][self.settings['mame_chd_set']]
            info_text += '\n[COLOR orange]ROM/CHD/SL files count[/COLOR]\n'
            info_text += "Number of ROM ZIPs    {0:5d} in the {1} set\n".format(control_dic['MAME_ZIP_files'], rom_set)
            info_text += "Number of CHDs        {0:5d} in the {1} set\n".format(control_dic['MAME_CHD_files'], chd_set)
            info_text += "Number of SL files    {0:5d}\n".format(control_dic['SL_files'])
            info_text += "Total ROMs in all SLs {0:5d}\n".format(control_dic['SL_ROMs'])
            info_text += "Total CHDs in all SLs {0:5d}\n".format(control_dic['SL_CHDs'])

            info_text += '\n[COLOR orange]ROM audit information[/COLOR]\n'
            t = "You have {0:5d} ZIP files out of    {1:5d} ({2:5d} missing)\n"
            info_text += t.format(control_dic['scan_ZIP_files_have'],
                                  control_dic['scan_ZIP_files_total'],
                                  control_dic['scan_ZIP_files_missing'])
            t = "You have {0:5d} CHDs out of         {1:5d} ({2:5d} missing)\n"
            info_text += t.format(control_dic['scan_CHD_files_have'],
                                  control_dic['scan_CHD_files_total'],
                                  control_dic['scan_CHD_files_missing'])

            t = "Can run  {0:5d} ROM machines out of {1:5d} ({2:5d} unrunnable machines)\n"
            info_text += t.format(control_dic['scan_ROM_machines_have'],
                                  control_dic['scan_ROM_machines_total'],
                                  control_dic['scan_ROM_machines_missing'])
            t = "Can run  {0:5d} CHD machines out of {1:5d} ({2:5d} unrunnable machines)\n"
            info_text += t.format(control_dic['scan_CHD_machines_have'],
                                  control_dic['scan_CHD_machines_total'],
                                  control_dic['scan_CHD_machines_missing'])
            info_text += '\n'

            t = "You have {0:5d} Samples out of {1:5d} ({2:5d} missing)\n"
            info_text += t.format(control_dic['scan_Samples_have'],
                                  control_dic['scan_Samples_total'],
                                  control_dic['scan_Samples_missing'])
            t = "You have {0:5d} SL ROMs out of {1:5d} ({2:5d} missing)\n"
            info_text += t.format(control_dic['scan_SL_ROMs_have'],
                                  control_dic['scan_SL_ROMs_total'],
                                  control_dic['scan_SL_ROMs_missing'])
            t = "You have {0:5d} SL CHDs out of {1:5d} ({2:5d} missing)\n"
            info_text += t.format(control_dic['scan_SL_CHDs_have'],
                                  control_dic['scan_SL_CHDs_total'],
                                  control_dic['scan_SL_CHDs_missing'])
            self._display_text_window(window_title, info_text)

        # --- View MAME machine ROMs (ROMs database) ---
        elif action == ACTION_VIEW_MACHINE_ROMS:
            # >> Load machine dictionary, ROM database and Devices database.
            pDialog = xbmcgui.DialogProgress()
            pDialog.create('Advanced MAME Launcher', 'Loading databases ... ')
            pDialog.update(0)
            machine = fs_get_machine_main_db_hash(PATHS, machine_name)
            pDialog.update(33)
            roms_db_dic = fs_load_JSON_file(PATHS.ROMS_DB_PATH.getPath())
            pDialog.update(66)
            devices_db_dic = fs_load_JSON_file(PATHS.DEVICES_DB_PATH.getPath())
            pDialog.update(100)
            pDialog.close()

            # --- Make a dictionary with device ROMs ---
            device_roms_list = []
            for device in devices_db_dic[machine_name]:
                device_roms_dic = roms_db_dic[device]
                for rom in device_roms_dic['roms']:
                    rom['device_name'] = device
                    device_roms_list.append(copy.deepcopy(rom))

            # --- ROM info ---
            info_text = []
            info_text.append('[COLOR violet]cloneof[/COLOR] {0} / '.format(machine['cloneof']) +
                             '[COLOR violet]romof[/COLOR] {0}\n'.format(machine['romof']))
            info_text.append('[COLOR skyblue]isBIOS[/COLOR] {0} / '.format(unicode(machine['isBIOS'])) +
                             '[COLOR skyblue]isDevice[/COLOR] {0}\n'.format(unicode(machine['isDevice'])))
            info_text.append('\n')

            # --- Table header ---
            # Table cell padding: left, right
            # Table columns: Type - ROM name - Size - CRC/SHA1 - Merge - BIOS - Location
            table_str = []
            table_str.append(['right', 'left',     'right', 'left',     'left',  'left'])
            table_str.append(['Type',  'ROM name', 'Size',  'CRC/SHA1', 'Merge', 'BIOS/Device'])

            # --- Table: Machine ROMs ---
            roms_dic = roms_db_dic[machine_name]
            if roms_dic['roms']:
                for rom in roms_dic['roms']:
                    if       rom['bios'] and     rom['merge']: r_type = 'BROM'
                    elif     rom['bios'] and not rom['merge']: r_type = 'XROM'
                    elif not rom['bios'] and     rom['merge']: r_type = 'MROM'
                    elif not rom['bios'] and not rom['merge']: r_type = 'ROM'
                    else:                                      r_type = 'ERROR'
                    table_row = [r_type, str(rom['name']), str(rom['size']),
                                 str(rom['crc']), str(rom['merge']), str(rom['bios'])]
                    table_str.append(table_row)

            # --- Table: device ROMs ---
            if device_roms_list:
                for rom in device_roms_list:
                    table_row = ['DROM', str(rom['name']), str(rom['size']),
                                 str(rom['crc']), str(rom['merge']), str(rom['device_name'])]
                    table_str.append(table_row)

            # --- Table: machine CHDs ---
            if roms_dic['disks']:
                for disk in roms_dic['disks']:
                    table_row = ['DISK', str(disk['name']), '',
                                 str(disk['sha1'])[0:8], str(disk['merge']), '']
                    table_str.append(table_row)

            # --- Table: BIOSes ---
            if roms_dic['bios']:
                bios_table_str = []
                bios_table_str.append(['right',     'left'])
                bios_table_str.append(['BIOS name', 'Description'])
                for bios in roms_dic['bios']:
                    table_row = [str(bios['name']), str(bios['description'])]
                    bios_table_str.append(table_row)

            # --- Render text information window ---
            table_str_list = text_render_table_str(table_str)
            info_text.extend(table_str_list)
            if roms_dic['bios']:
                bios_table_str_list = text_render_table_str(bios_table_str)
                info_text.extend('\n')
                info_text.extend(bios_table_str_list)
            window_title = 'Machine {0} ROMs'.format(machine_name)
            self._display_text_window(window_title, ''.join(info_text))

        # --- View MAME machine ROMs (Audit ROM database) ---
        elif action == ACTION_VIEW_MACHINE_AUDIT_ROMS:
            # --- Load machine dictionary and ROM database ---
            rom_set = ['MERGED', 'SPLIT', 'NONMERGED'][self.settings['mame_rom_set']]
            log_debug('_command_context_view() View Machine ROMs (Audit database)\n')
            log_debug('_command_context_view() rom_set {0}\n'.format(rom_set))

            pDialog = xbmcgui.DialogProgress()
            pDialog.create('Advanced MAME Launcher', 'Loading databases ... ')
            pDialog.update(0)
            machine = fs_get_machine_main_db_hash(PATHS, machine_name)
            pDialog.update(33)
            roms_db_dic = fs_load_JSON_file(PATHS.ROM_AUDIT_ROMS_DB_PATH.getPath())
            pDialog.update(66)
            chds_db_dic = fs_load_JSON_file(PATHS.ROM_AUDIT_CHDS_DB_PATH.getPath())
            pDialog.update(100)
            pDialog.close()

            # --- Grab data and settings ---
            roms_dic = roms_db_dic[machine_name]
            chds_dic = chds_db_dic[machine_name]
            cloneof = machine['cloneof']
            romof = machine['romof']
            log_debug('_command_context_view() machine {0}\n'.format(machine_name))
            log_debug('_command_context_view() cloneof {0}\n'.format(cloneof))
            log_debug('_command_context_view() romof   {0}\n'.format(romof))

            # --- Generate report ---
            info_text = []
            info_text.append('[COLOR violet]cloneof[/COLOR] {0} / '.format(machine['cloneof']) +
                             '[COLOR violet]romof[/COLOR] {0}\n'.format(machine['romof']))
            info_text.append('[COLOR skyblue]isBIOS[/COLOR] {0} / '.format(unicode(machine['isBIOS'])) +
                             '[COLOR skyblue]isDevice[/COLOR] {0}\n'.format(unicode(machine['isDevice'])))
            info_text.append('\n')

            # --- Table header ---
            # Table cell padding: left, right
            # Table columns: Type - ROM name - Size - CRC/SHA1 - Merge - BIOS - Location
            table_str = []
            table_str.append(['right', 'left',     'right', 'left',     'left'])
            table_str.append(['Type',  'ROM name', 'Size',  'CRC/SHA1', 'Location'])

            # --- Table rows ---
            for m_rom in roms_dic:
                table_row = [str(m_rom['type']), str(m_rom['name']), str(m_rom['size']),
                             str(m_rom['crc']), str(m_rom['location'])]
                table_str.append(table_row)
            for m_disk in chds_dic:
                loc = str(m_disk['location']) + '.chd'
                table_row = [str(m_disk['type']), str(m_disk['name']), '',
                             str(m_disk['sha1'])[0:8], loc]
                table_str.append(table_row)
            table_str_list = text_render_table_str(table_str)
            info_text.extend(table_str_list)
            window_title = 'Machine {0} ROM audit'.format(machine_name)
            self._display_text_window(window_title, ''.join(info_text))

        # --- View SL ROMs ---
        elif action == ACTION_VIEW_SL_ROM_ROMS:
            SL_DB_FN = PATHS.SL_DB_DIR.pjoin(SL_name + '.json')
            SL_ROMS_DB_FN = PATHS.SL_DB_DIR.pjoin(SL_name + '_roms.json')
            # kodi_busydialog_ON()
            # SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
            # SL_machines_dic = fs_load_JSON_file(PATHS.SL_MACHINES_PATH.getPath())
            # assets_file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '_assets.json'
            # SL_asset_DB_FN = PATHS.SL_DB_DIR.pjoin(assets_file_name)
            # SL_asset_dic = fs_load_JSON_file(SL_asset_DB_FN.getPath())
            # kodi_busydialog_OFF()
            # SL_dic = SL_catalog_dic[SL_name]
            # SL_machine_list = SL_machines_dic[SL_name]
            # assets = SL_asset_dic[SL_ROM] if SL_ROM in SL_asset_dic else fs_new_SL_asset()
            roms = fs_load_JSON_file(SL_DB_FN.getPath())
            rom = roms[SL_ROM]
            roms_db = fs_load_JSON_file(SL_ROMS_DB_FN.getPath())
            rom_db_list = roms_db[SL_ROM]

            info_text = []
            info_text.append('[COLOR violet]SL_name[/COLOR] {0}\n'.format(SL_name))
            info_text.append('[COLOR violet]SL_ROM[/COLOR] {0}\n'.format(SL_ROM))
            info_text.append('[COLOR violet]description[/COLOR] {0}\n'.format(rom['description']))
            info_text.append('\n')

            table_str = []
            table_str.append(['left',      'left',       'left',      'left',      'left', 'left', 'left'])
            table_str.append(['Part name', 'Part iface', 'Area type', 'A name', 'ROM/CHD name', 'Size', 'CRC/SHA1'])
            # >> Iterate Parts
            for part_dic in rom_db_list:
                part_name = part_dic['part_name']
                part_interface = part_dic['part_interface']
                if 'dataarea' in part_dic:
                    # >> Iterate Dataareas
                    for dataarea_dic in part_dic['dataarea']:
                        dataarea_name = dataarea_dic['name']
                        # >> Interate ROMs in dataarea
                        for rom_dic in dataarea_dic['roms']:
                            table_row = [part_name, part_interface,
                                         'dataarea', dataarea_name,
                                         rom_dic['name'], rom_dic['size'], rom_dic['crc']]
                            table_str.append(table_row)
                if 'diskarea' in part_dic:
                    # >> Iterate Diskareas
                    for diskarea_dic in part_dic['diskarea']:
                        diskarea_name = diskarea_dic['name']
                        # >> Iterate DISKs in diskarea
                        for rom_dic in diskarea_dic['disks']:
                            table_row = [part_name, part_interface,
                                         'diskarea', diskarea_name,
                                         rom_dic['name'], '', rom_dic['sha1'][0:8]]
                            table_str.append(table_row)
            table_str_list = text_render_table_str(table_str)
            info_text.extend(table_str_list)
            window_title = 'Software List ROM List (ROMs DB)'
            self._display_text_window(window_title, ''.join(info_text))

        # --- View SL ROM Audit ROMs ---
        elif action == ACTION_VIEW_SL_ROM_AUDIT_ROMS:
            SL_DB_FN = PATHS.SL_DB_DIR.pjoin(SL_name + '.json')
            # SL_ROMs_DB_FN = PATHS.SL_DB_DIR.pjoin(SL_name + '_roms.json')
            SL_ROM_Audit_DB_FN = PATHS.SL_DB_DIR.pjoin(SL_name + '_audit_ROMs.json')
            SL_CHD_Audit_DB_FN = PATHS.SL_DB_DIR.pjoin(SL_name + '_audit_CHDs.json')

            roms = fs_load_JSON_file(SL_DB_FN.getPath())
            roms_audit_db = fs_load_JSON_file(SL_ROM_Audit_DB_FN.getPath())
            chds_audit_db = fs_load_JSON_file(SL_CHD_Audit_DB_FN.getPath())
            rom = roms[SL_ROM]
            rom_db_list = roms_audit_db[SL_ROM]
            chd_db_list = chds_audit_db[SL_ROM]

            info_text = []
            log_debug(unicode(rom))
            info_text.append('[COLOR violet]SL_name[/COLOR] {0}\n'.format(SL_name))
            info_text.append('[COLOR violet]SL_ROM[/COLOR] {0}\n'.format(SL_ROM))
            info_text.append('[COLOR violet]description[/COLOR] {0}\n'.format(rom['description']))
            info_text.append('\n')

            table_str = []
            table_str.append(['left', 'left',         'left', 'left',     'left'])
            table_str.append(['Type', 'ROM/CHD name', 'Size', 'CRC/SHA1', 'Location'])
            # >> Iterate ROMs
            for rom_dic in rom_db_list:
                table_row = [rom_dic['type'], rom_dic['name'], rom_dic['size'],
                             rom_dic['crc'], rom_dic['location']]
                table_str.append(table_row)
            # >> Iterate CHDs
            for chd_dic in chd_db_list:
                sha1_srt = chd_dic['sha1'][0:8]
                table_row = [chd_dic['type'], chd_dic['name'], '', sha1_srt, chd_dic['location']]
                table_str.append(table_row)

            table_str_list = text_render_table_str(table_str)
            info_text.extend(table_str_list)
            window_title = 'Software List ROM List (Audit DB)'
            self._display_text_window(window_title, ''.join(info_text))

        # --- View MAME stdout/stderr ---
        elif action == ACTION_VIEW_EXEC_OUTPUT:
            if not PATHS.MAME_OUTPUT_PATH.exists():
                kodi_dialog_OK('MAME output file not found. Execute MAME and try again.')
                return

            # --- Read stdout and put into a string ---
            window_title = 'MAME last execution output'
            info_text = ''
            with open(PATHS.MAME_OUTPUT_PATH.getPath(), 'r') as myfile:
                info_text = myfile.read()
            self._display_text_window(window_title, info_text)

        # --- Audit ROMs of a single machine ---
        elif action == ACTION_AUDIT_MAME_MACHINE:
            # --- Load machine dictionary and ROM database ---
            rom_set = ['MERGED', 'SPLIT', 'NONMERGED'][self.settings['mame_rom_set']]
            log_debug('_command_context_view() Auditing Machine ROMs\n')
            log_debug('_command_context_view() rom_set {0}\n'.format(rom_set))

            pDialog = xbmcgui.DialogProgress()
            pDialog.create('Advanced MAME Launcher', 'Loading databases ... ')
            pDialog.update(0)
            machine = fs_get_machine_main_db_hash(PATHS, machine_name)
            pDialog.update(33)
            roms_db_dic = fs_load_JSON_file(PATHS.ROM_SET_ROMS_DB_PATH.getPath())
            pDialog.update(66)
            chds_db_dic = fs_load_JSON_file(PATHS.ROM_SET_CHDS_DB_PATH.getPath())
            pDialog.update(100)
            pDialog.close()

            # --- Grab data and settings ---
            roms_dic = roms_db_dic[machine_name]
            chds_dic = roms_db_dic[machine_name]
            cloneof = machine['cloneof']
            romof = machine['romof']
            log_debug('_command_context_view() machine {0}\n'.format(machine_name))
            log_debug('_command_context_view() cloneof {0}\n'.format(cloneof))
            log_debug('_command_context_view() romof   {0}\n'.format(romof))

            # --- Open ZIP file and check CRC32 ---
            mame_audit_machine_roms(self.settings, roms_dic)
            # mame_audit_machine_chds(self.settings, chds_dic)

            # --- Generate report ---
            info_text = []
            info_text.append('[COLOR violet]cloneof[/COLOR] {0} / '.format(machine['cloneof']) +
                             '[COLOR violet]romof[/COLOR] {0}\n'.format(machine['romof']))
            info_text.append('[COLOR skyblue]isBIOS[/COLOR] {0} / '.format(unicode(machine['isBIOS'])) +
                             '[COLOR skyblue]isDevice[/COLOR] {0}\n'.format(unicode(machine['isDevice'])))
            info_text.append('\n')

            # --- Table header ---
            # Table cell padding: left, right
            # Table columns: Type - ROM name - Size - CRC/SHA1 - Merge - BIOS - Location
            table_str = []
            table_str.append(['right', 'left',     'right', 'left',     'left',  'left', 'left',     'left'])
            table_str.append(['Type',  'ROM name', 'Size',  'CRC/SHA1', 'Merge', 'BIOS', 'Location', 'Status'])

            # --- Table rows ---
            for m_rom in roms_dic:
                table_row = ['ROM', str(m_rom['name']), str(m_rom['size']), str(m_rom['crc']),
                             '', '', m_rom['location'], m_rom['status_colour']]
                table_str.append(table_row)
            table_str_list = text_render_table_str(table_str)
            info_text.extend(table_str_list)
            window_title = 'Machine {0} ROM audit'.format(machine_name)
            self._display_text_window(window_title, ''.join(info_text))

        # --- Audit ROMs of SL item ---
        elif action == ACTION_AUDIT_SL_MACHINE:
            kodi_dialog_OK('ACTION_AUDIT_SL_MACHINE not coded yet. Sorry.')

        # --- View ROM scanner reports ---
        elif action == ACTION_VIEW_REPORT_SCANNER:
            d = xbmcgui.Dialog()
            type_sub = d.select('View scanner reports',
                                ['View MAME machine ROM scanner report',
                                 'View MAME ROM archive scanner report',
                                 'View MAME machine CHD scanner report',
                                 'View MAME CHD archive scanner report',
                                 'View MAME Samples scanner report',
                                 'View Software Lists ROM scanner report',
                                 'View Software Lists CHD scanner report'])
            if type_sub < 0: return

            # --- View MAME machine ROM scanner report ---
            if type_sub == 0:
                if not PATHS.REPORT_MAME_SCAN_ROM_MACHINES_PATH.exists():
                    kodi_dialog_OK('MAME machine ROM scanner report not found. Please scan MAME ROMs and try again.')
                    return

                # --- Read stdout and put into a string ---
                window_title = 'MAME machine ROM scanner report'
                info_text = ''
                with open(PATHS.REPORT_MAME_SCAN_ROM_MACHINES_PATH.getPath(), "r") as myfile:
                    info_text = myfile.read()
                    self._display_text_window(window_title, info_text)

            # --- View MAME ROM archive scanner report ---
            elif type_sub == 1:
                if not PATHS.REPORT_MAME_SCAN_ROM_ARCHIVES_PATH.exists():
                    kodi_dialog_OK('MAME ROM archive scanner report not found. Please scan MAME ROMs and try again.')
                    return

                # --- Read stdout and put into a string ---
                window_title = 'MAME ROM archive scanner report'
                info_text = ''
                with open(PATHS.REPORT_MAME_SCAN_ROM_ARCHIVES_PATH.getPath(), "r") as myfile:
                    info_text = myfile.read()
                    self._display_text_window(window_title, info_text)

            # --- View MAME machine CHD scanner report ---
            elif type_sub == 2:
                if not PATHS.REPORT_MAME_SCAN_CHD_MACHINES_PATH.exists():
                    kodi_dialog_OK('MAME machine CHD scanner report not found. Please scan MAME ROMs and try again.')
                    return

                # --- Read stdout and put into a string ---
                window_title = 'MAME machine CHD scanner report'
                info_text = ''
                with open(PATHS.REPORT_MAME_SCAN_CHD_MACHINES_PATH.getPath(), "r") as myfile:
                    info_text = myfile.read()
                    self._display_text_window(window_title, info_text)

            # --- View MAME CHD archive scanner report ---
            elif type_sub == 3:
                if not PATHS.REPORT_MAME_SCAN_CHD_ARCHIVES_PATH.exists():
                    kodi_dialog_OK('MAME CHD archive scanner report not found. Please scan MAME ROMs and try again.')
                    return

                # --- Read stdout and put into a string ---
                window_title = 'MAME CHD archive scanner report'
                info_text = ''
                with open(PATHS.REPORT_MAME_SCAN_CHD_ARCHIVES_PATH.getPath(), "r") as myfile:
                    info_text = myfile.read()
                    self._display_text_window(window_title, info_text)

            # --- View MAME Samples scanner report ---
            elif type_sub == 4:
                if not PATHS.REPORT_MAME_SCAN_SAMP_PATH.exists():
                    kodi_dialog_OK('MAME Samples scanner report not found. Please scan MAME ROMs and try again.')
                    return

                # --- Read stdout and put into a string ---
                window_title = 'MAME samples scanner report'
                info_text = ''
                with open(PATHS.REPORT_MAME_SCAN_SAMP_PATH.getPath(), 'r') as myfile:
                    info_text = myfile.read()
                    self._display_text_window(window_title, info_text)

            # --- View Software Lists ROM scanner report ---
            elif type_sub == 5:
                if not PATHS.REPORT_SL_SCAN_ROMS_PATH.exists():
                    kodi_dialog_OK('SL ROM scanner report not found. Please scan MAME ROMs and try again.')
                    return

                # --- Read stdout and put into a string ---
                window_title = 'SL ROM scanner report'
                info_text = ''
                with open(PATHS.REPORT_SL_SCAN_ROMS_PATH.getPath(), 'r') as myfile:
                    info_text = myfile.read()
                    self._display_text_window(window_title, info_text)

            # --- View Software Lists CHD scanner report ---
            elif type_sub == 6:
                if not PATHS.REPORT_SL_SCAN_CHDS_PATH.exists():
                    kodi_dialog_OK('SL CHD scanner report not found. Please scan MAME ROMs and try again.')
                    return

                # --- Read stdout and put into a string ---
                window_title = 'SL CHD scanner report'
                info_text = ''
                with open(PATHS.REPORT_SL_SCAN_CHDS_PATH.getPath(), 'r') as myfile:
                    info_text = myfile.read()
                    self._display_text_window(window_title, info_text)

        # --- View asset/artwork scanner reports ---
        elif action == ACTION_VIEW_REPORT_ASSETS:
            d = xbmcgui.Dialog()
            type_sub = d.select('View asset/artwork reports',
                                ['View MAME asset statistics',
                                 'View MAME asset report',
                                 'View Software Lists statistics',
                                 'View Software Lists asset report'])
            if type_sub < 0: return

            # --- View MAME asset statistics ---
            if type_sub == 0:
                kodi_dialog_OK('MAME asset statistics not coded yet. Sorry.')

            # --- View MAME asset report ---
            elif type_sub == 1:
                kodi_dialog_OK('View MAME asset report not coded yet. Sorry.')

            # --- View Software Lists statistics ---
            elif type_sub == 2:
                kodi_dialog_OK('View Software Lists statistics not coded yet. Sorry.')

            # --- View Software Lists asset report ---
            elif type_sub == 3:
                kodi_dialog_OK('View Software Lists asset report not coded yet. Sorry.')

        # --- View audit reports ---
        elif action == ACTION_VIEW_REPORT_AUDIT:
            d = xbmcgui.Dialog()
            type_sub = d.select('View audit reports',
                                ['View MAME audit report', 'View SL audit report'])
            if type_sub < 0: return

            if type_sub == 0:
                if not PATHS.REPORT_MAME_ROM_AUDIT_PATH.exists():
                    kodi_dialog_OK('MAME ROM audit report not found. Please audit your MAME ROMs and try again.')
                    return
                with open(PATHS.REPORT_MAME_ROM_AUDIT_PATH.getPath(), 'r') as myfile:
                    info_text = myfile.read()
                    self._display_text_window('SL CHD scanner report', info_text)

            elif type_sub == 1:
                kodi_dialog_OK('View Software Lists audit report not coded yet. Sorry.')

        else:
            kodi_dialog_OK('Wrong action == {0}. This is a bug, please report it.'.format(action))

    # ---------------------------------------------------------------------------------------------
    # Favourites
    # ---------------------------------------------------------------------------------------------
    # >> Favourites use the main hashed database, not the main and render databases.
    def _command_context_add_mame_fav(self, machine_name):
        log_debug('_command_add_mame_fav() Machine_name "{0}"'.format(machine_name))

        # >> Get Machine database entry
        kodi_busydialog_ON()
        control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
        machine = fs_get_machine_main_db_hash(PATHS, machine_name)
        assets_dic = fs_load_JSON_file(PATHS.MAIN_ASSETS_DB_PATH.getPath())
        kodi_busydialog_OFF()

        # >> Open Favourite Machines dictionary
        fav_machines = fs_load_JSON_file(PATHS.FAV_MACHINES_PATH.getPath())
        
        # >> If machine already in Favourites ask user if overwrite.
        if machine_name in fav_machines:
            ret = kodi_dialog_yesno('Machine {0} ({1}) '.format(machine['description'], machine_name) +
                                    'already in MAME Favourites. Overwrite?')
            if ret < 1: return

        # >> Add machine. Add database version to Favourite.
        assets = assets_dic[machine_name]
        machine['assets'] = assets
        machine['ver_mame'] = control_dic['ver_mame']
        machine['ver_mame_str'] = control_dic['ver_mame_str']
        fav_machines[machine_name] = machine
        log_info('_command_add_mame_fav() Added machine "{0}"'.format(machine_name))

        # >> Save Favourites
        fs_write_JSON_file(PATHS.FAV_MACHINES_PATH.getPath(), fav_machines)
        kodi_notify('Machine {0} added to MAME Favourites'.format(machine_name))


    #
    # Context menu "Manage Favourite machines"
    #   * 'Scan all ROMs/CHDs/Samples'
    #      Scan Favourite machines ROM ZIPs and CHDs and update flags of the Favourites 
    #      database JSON.
    #
    #   * 'Scan all assets/artwork'
    #      Scan Favourite machines assets/artwork and update MAME Favourites database JSON.
    #
    #   * 'Check/Update all MAME Favourites'
    #      Checks that all MAME Favourite machines exist in current database. If the ROM exists,
    #      then update information from current MAME database. If the machine doesn't exist, then
    #      delete it from MAME Favourites (prompt the user about this).
    #
    #   * 'Delete machine from MAME Favourites'
    #
    def _command_context_manage_mame_fav(self, machine_name):
        dialog = xbmcgui.Dialog()
        idx = dialog.select('Manage MAME Favourites', 
                           ['Scan all ROMs/CHDs/Samples',
                            'Scan all assets/artwork',
                            'Check/Update all MAME Favourites',
                            'Delete machine from MAME Favourites'])
        if idx < 0: return

        # --- Scan ROMs/CHDs/Samples ---
        if idx == 0:
            kodi_dialog_OK('Check this code. It is not working properly.')

            # >> Check paths
            if not self.settings['rom_path']:
                kodi_dialog_OK('ROM directory not configured. Aborting.')
                return
            ROM_path_FN = FileName(self.settings['rom_path'])
            if not ROM_path_FN.isdir():
                kodi_dialog_OK('ROM directory does not exist. Aborting.')
                return

            scan_CHDs = False
            if self.settings['chd_path']:
                CHD_path_FN = FileName(self.settings['chd_path'])
                if not CHD_path_FN.isdir():
                    kodi_dialog_OK('CHD directory does not exist. CHD scanning disabled.')
                else:
                    scan_CHDs = True
            else:
                kodi_dialog_OK('CHD directory not configured. CHD scanning disabled.')
                CHD_path_FN = FileName('')

            scan_Samples = False
            if self.settings['samples_path']:
                Samples_path_FN = FileName(self.settings['samples_path'])
                if not Samples_path_FN.isdir():
                    kodi_dialog_OK('Samples directory does not exist. Samples scanning disabled.')
                else:
                    scan_Samples = True
            else:
                kodi_dialog_OK('Samples directory not configured. Samples scanning disabled.')
                Samples_path_FN = FileName('')

            # >> Load database
            # >> Create a fake control_dic for the FAV MAME ROMs
            fav_machines = fs_load_JSON_file(PATHS.FAV_MACHINES_PATH.getPath())
            control_dic = fs_new_control_dic()
            fs_scan_MAME_ROMs(PATHS, fav_machines, control_dic, ROM_path_FN, CHD_path_FN, Samples_path_FN, scan_CHDs, scan_Samples)

            # >> Save updated database
            fs_write_JSON_file(PATHS.FAV_MACHINES_PATH.getPath(), fav_machines)
            kodi_refresh_container()
            kodi_notify('Scanning of MAME Favourites finished')

        # --- Scan assets/artwork ---
        elif idx == 1:
            kodi_dialog_OK('Check this code. I think is wrong. Data must be in machine["assets"]')

            # >> Get assets directory. Abort if not configured/found.
            if not self.settings['assets_path']:
                kodi_dialog_OK('Asset directory not configured. Aborting.')
                return
            Asset_path_FN = FileName(self.settings['assets_path'])
            if not Asset_path_FN.isdir():
                kodi_dialog_OK('Asset directory does not exist. Aborting.')
                return

            fav_machines = fs_load_JSON_file(PATHS.FAV_MACHINES_PATH.getPath())
            pDialog = xbmcgui.DialogProgress()
            pDialog_canceled = False
            pDialog.create('Advanced MAME Launcher', 'Scanning MAME assets/artwork...')
            total_machines = len(fav_machines)
            processed_machines = 0
            assets_dic = {}
            for key in sorted(fav_machines):
                machine = fav_machines[key]
                for idx, asset_key in enumerate(ASSET_MAME_KEY_LIST):
                    asset_FN = Asset_path_FN.pjoin(ASSET_MAME_PATH_LIST[idx]).pjoin(key + '.png')
                    if asset_FN.exists(): machine[asset_key] = asset_FN.getOriginalPath()
                    else:                 machine[asset_key] = ''
                processed_machines = processed_machines + 1
                pDialog.update(100 * processed_machines / total_machines)
            pDialog.close()
            fs_write_JSON_file(PATHS.FAV_MACHINES_PATH.getPath(), fav_machines)
            kodi_notify('Scanning of MAME Favourite Assets finished')

        # --- Check/Update all MAME Favourites ---
        # >> Check if Favourites can be found in current MAME main database. It may happen that
        # >> a machine is renamed between MAME version although I think this is very unlikely.
        # >> MAME Favs can not be relinked. If the machine is not found in current database it must
        # >> be deleted by the user and a new Favourite created.
        # >> If the machine is found in the main database, then update the Favourite database
        # >> with data from the main database.
        elif idx == 2:
            # >> Load databases.
            pDialog = xbmcgui.DialogProgress()
            pDialog.create('Advanced MAME Launcher')
            pDialog.update(0, 'Loading databases (Control DB) ... ')
            control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
            pDialog.update(20, 'Loading databases (MAME Favourites DB) ... ')
            fav_machines = fs_load_JSON_file(PATHS.FAV_MACHINES_PATH.getPath())
            pDialog.update(40, 'Loading databases (Main machines DB) ... ')
            machines = fs_load_JSON_file(PATHS.MAIN_DB_PATH.getPath())
            pDialog.update(60, 'Loading databases (Render machines DB) ... ')
            machines_render = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
            pDialog.update(80, 'Loading databases (Machine assets DB) ... ')
            assets_dic = fs_load_JSON_file(PATHS.MAIN_ASSETS_DB_PATH.getPath())
            pDialog.update(100)
            pDialog.close()

            # >> Check/Update MAME Favourite machines.
            for fav_key in sorted(fav_machines):
                log_debug('Checking Favourite "{0}"'.format(fav_key))
                if fav_key in machines:
                    # >> Update Favourite database (info + assets)
                    new_fav = machines[fav_key].copy()
                    new_fav.update(machines_render[fav_key])
                    new_fav['assets'] = assets_dic[fav_key]
                    new_fav['ver_mame'] = control_dic['ver_mame']
                    new_fav['ver_mame_str'] = control_dic['ver_mame_str']
                    fav_machines[fav_key] = new_fav
                    log_debug('Updated machine "{0}"'.format(fav_key))
                else:
                    log_debug('Machine "{0}" not found in MAME main DB'.format(fav_key))
                    t = 'Favourite machine "{0}" not found in database'.format(fav_key)
                    kodi_dialog_OK(t)

            # >> Save MAME Favourites DB
            fs_write_JSON_file(PATHS.FAV_MACHINES_PATH.getPath(), fav_machines)
            kodi_refresh_container()
            kodi_notify('MAME Favourite checked and updated')

        # --- Delete machine from MAME Favourites ---
        elif idx == 3:
            log_debug('_command_context_manage_mame_fav() Delete MAME Favourite machine')
            log_debug('_command_context_manage_mame_fav() Machine_name "{0}"'.format(machine_name))

            # >> Open Favourite Machines dictionary
            fav_machines = fs_load_JSON_file(PATHS.FAV_MACHINES_PATH.getPath())
            
            # >> Ask user for confirmation.
            ret = kodi_dialog_yesno('Delete Machine {0} ({1})?'.format(fav_machines[machine_name]['description'], machine_name))
            if ret < 1: return
            
            # >> Delete machine
            del fav_machines[machine_name]
            log_info('_command_context_manage_mame_fav() Deleted machine "{0}"'.format(machine_name))

            # >> Save Favourites
            fs_write_JSON_file(PATHS.FAV_MACHINES_PATH.getPath(), fav_machines)
            kodi_refresh_container()
            kodi_notify('Machine {0} deleted from MAME Favourites'.format(machine_name))


    def _command_show_mame_fav(self):
        log_debug('_command_show_mame_fav() Starting ...')

        # >> Open Favourite Machines dictionary
        fav_machines = fs_load_JSON_file(PATHS.FAV_MACHINES_PATH.getPath())
        if not fav_machines:
            kodi_dialog_OK('No Favourite MAME machines. Add some machines to MAME Favourites first.')
            xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
            return

        # >> Render Favourites
        self._set_Kodi_all_sorting_methods()
        for m_name in fav_machines:
            machine = fav_machines[m_name]
            assets  = machine['assets']
            self._render_fav_machine_row(m_name, machine, assets)
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_fav_machine_row(self, machine_name, machine, machine_assets):
        # --- Default values for flags ---
        AEL_PClone_stat_value    = AEL_PCLONE_STAT_VALUE_NONE

        # --- Mark Flags, BIOS, Devices, BIOS, Parent/Clone and Driver status ---
        display_name = machine['description']
        display_name += ' [COLOR skyblue]{0}[/COLOR]'.format(machine['flags'])            
        if machine['isBIOS']:   display_name += ' [COLOR cyan][BIOS][/COLOR]'
        if machine['isDevice']: display_name += ' [COLOR violet][Dev][/COLOR]'
        if machine['cloneof']:  display_name += ' [COLOR orange][Clo][/COLOR]'
        if   machine['driver_status'] == 'imperfect':   display_name += ' [COLOR yellow][Imp][/COLOR]'
        elif machine['driver_status'] == 'preliminary': display_name += ' [COLOR red][Pre][/COLOR]'

        # --- Skin flags ---
        if machine['cloneof']: AEL_PClone_stat_value = AEL_PCLONE_STAT_VALUE_CLONE
        else:                  AEL_PClone_stat_value = AEL_PCLONE_STAT_VALUE_PARENT

        # --- Assets/artwork ---
        icon_path      = machine_assets[self.mame_icon] if machine_assets[self.mame_icon] else 'DefaultProgram.png'
        fanart_path    = machine_assets[self.mame_fanart]
        banner_path    = machine_assets['marquee']
        clearlogo_path = machine_assets['clearlogo']
        poster_path    = machine_assets['flyer']

        # --- Create listitem row ---
        ICON_OVERLAY = 6
        listitem = xbmcgui.ListItem(display_name)

        # --- Metadata ---
        # >> Make all the infotables compatible with Advanced Emulator Launcher
        listitem.setInfo('video', {'title'   : display_name,     'year'    : machine['year'],
                                   'genre'   : machine['genre'], 'studio'  : machine['manufacturer'],
                                   'plot'    : '',               'overlay' : ICON_OVERLAY})
        listitem.setProperty('nplayers', machine['nplayers'])
        listitem.setProperty('platform', 'MAME')

        # --- Assets ---
        # >> AEL custom artwork fields
        listitem.setArt({'title'     : machine_assets['title'],   'snap'    : machine_assets['snap'],
                         'boxfront'  : machine_assets['cabinet'], 'boxback' : machine_assets['cpanel'],
                         'cartridge' : machine_assets['PCB'],     'flyer'   : machine_assets['flyer'] })
        # >> Kodi official artwork fields
        listitem.setArt({'icon'   : icon_path,   'fanart'    : fanart_path,
                         'banner' : banner_path, 'clearlogo' : clearlogo_path, 'poster' : poster_path })

        # --- ROM flags (Skins will use these flags to render icons) ---
        listitem.setProperty(AEL_PCLONE_STAT_LABEL, AEL_PClone_stat_value)

        # --- Create context menu ---
        URL_view_DAT = self._misc_url_2_arg_RunPlugin('command', 'VIEW_DAT', 'machine', machine_name)
        URL_view = self._misc_url_3_arg_RunPlugin('command', 'VIEW', 'machine', machine_name, 'location', LOCATION_MAME_FAVS)
        URL_manage = self._misc_url_2_arg_RunPlugin('command', 'MANAGE_MAME_FAV', 'machine', machine_name)
        commands = []
        commands.append(('Info / Utils',  URL_view_DAT))
        commands.append(('View / Audit',  URL_view ))
        commands.append(('Manage Favourite machines',  URL_manage ))
        commands.append(('Kodi File Manager', 'ActivateWindow(filemanager)' ))
        commands.append(('Add-on Settings', 'Addon.OpenSettings({0})'.format(__addon_id__) ))
        listitem.addContextMenuItems(commands, replaceItems = True)

        # --- Add row ---
        URL = self._misc_url_3_arg('command', 'LAUNCH', 'machine', machine_name, 'location', 'MAME_FAV')
        xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = False)

    def _command_context_add_sl_fav(self, SL_name, ROM_name):
        log_debug('_command_add_sl_fav() SL_name  "{0}"'.format(SL_name))
        log_debug('_command_add_sl_fav() ROM_name "{0}"'.format(ROM_name))

        # >> Get Machine database entry
        kodi_busydialog_ON()
        control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
        SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
        # >> Load SL ROMs
        file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '.json'
        SL_DB_FN = PATHS.SL_DB_DIR.pjoin(file_name)
        SL_roms = fs_load_JSON_file(SL_DB_FN.getPath())
        # >> Load SL assets
        assets_file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '_assets.json'
        SL_asset_DB_FN = PATHS.SL_DB_DIR.pjoin(assets_file_name)
        SL_assets_dic = fs_load_JSON_file(SL_asset_DB_FN.getPath())
        kodi_busydialog_OFF()

        # >> Open Favourite Machines dictionary
        fav_SL_roms = fs_load_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath())
        SL_fav_key = SL_name + '-' + ROM_name
        log_debug('_command_add_sl_fav() SL_fav_key "{0}"'.format(SL_fav_key))
        
        # >> If machine already in Favourites ask user if overwrite.
        if SL_fav_key in fav_SL_roms:
            ret = kodi_dialog_yesno('Machine {0} ({1}) '.format(ROM_name, SL_name) +
                                    'already in SL Favourites. Overwrite?')
            if ret < 1: return

        # >> Add machine to SL Favourites
        ROM = SL_roms[ROM_name]
        assets = SL_assets_dic[ROM_name] if ROM_name in SL_assets_dic else fs_new_SL_asset()
        ROM['ROM_name']       = ROM_name
        ROM['SL_name']        = SL_name
        ROM['ver_mame']       = control_dic['ver_mame']
        ROM['ver_mame_str']   = control_dic['ver_mame_str']
        ROM['launch_machine'] = ''
        ROM['assets']         = assets
        fav_SL_roms[SL_fav_key] = ROM
        log_info('_command_add_sl_fav() Added machine "{0}" ("{1}")'.format(ROM_name, SL_name))

        # >> Save Favourites
        fs_write_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath(), fav_SL_roms)
        kodi_notify('ROM {0} added to SL Favourite ROMs'.format(ROM_name))

    #
    # Context menu "Manage SL Favourite ROMs"
    #   * 'Choose default machine for SL ROM'
    #      Allows to set the default machine to launch each SL ROM.
    #
    #   * 'Scan all SL Favourite ROMs/CHDs'
    #      Scan SL ROM ZIPs and CHDs and update flags of the SL Favourites database JSON.
    #
    #   * 'Scan all SL Favourite assets/artwork'
    #      Scan SL ROMs assets/artwork and update SL Favourites database JSON.
    #
    #   * 'Check/Update all SL Favourites ROMs'
    #      Checks that all SL Favourite ROMs exist in current database. If the ROM exists,
    #      then update information from current SL database. If the ROM doesn't exist, then
    #      delete it from SL Favourites (prompt the user about this).
    #
    #   * 'Delete ROM from SL Favourites'
    #
    def _command_context_manage_sl_fav(self, SL_name, ROM_name):
        dialog = xbmcgui.Dialog()
        idx = dialog.select('Manage Software Lists Favourites', 
                           ['Choose default machine for SL ROM',
                            'Scan all SL Favourite ROMs/CHDs',
                            'Scan all SL Favourite assets/artwork',
                            'Check/Update all SL Favourites ROMs',
                            'Delete ROM from SL Favourites'])
        if idx < 0: return

        # --- Choose default machine for SL ROM ---
        if idx == 0:
            # >> Load Favs
            fav_SL_roms = fs_load_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath())
            SL_fav_key = SL_name + '-' + ROM_name

            # >> Get a list of machines that can launch this SL ROM. User chooses.
            SL_machines_dic = fs_load_JSON_file(PATHS.SL_MACHINES_PATH.getPath())
            SL_machine_list = SL_machines_dic[SL_name]
            SL_machine_names_list = []
            SL_machine_desc_list = []
            SL_machine_names_list.append('')
            SL_machine_desc_list.append('[ Not set ]')
            for SL_machine in SL_machine_list: 
                SL_machine_names_list.append(SL_machine['machine'])
                SL_machine_desc_list.append(SL_machine['description'])
            # >> Krypton feature: preselect current machine
            pre_idx = SL_machine_names_list.index(fav_SL_roms[SL_fav_key]['launch_machine'])
            if pre_idx < 0: pre_idx = 0
            dialog = xbmcgui.Dialog()
            m_index = dialog.select('Select machine', SL_machine_desc_list, preselect = pre_idx)
            if m_index < 0 or m_index == pre_idx: return
            machine_name = SL_machine_names_list[m_index]
            machine_desc = SL_machine_desc_list[m_index]

            # >> Edit and save
            fav_SL_roms[SL_fav_key]['launch_machine'] = machine_name
            fs_write_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath(), fav_SL_roms)
            kodi_notify('Deafult machine set to {0} ({1})'.format(machine_name, machine_desc))

        # --- Scan ROMs/CHDs ---
        # Reuse SL scanner for Favourites
        elif idx == 1:
            kodi_dialog_OK('SL Favourites scanner not coded yet. Sorry.')

        # --- Scan assets/artwork ---
        # Reuse SL scanner for Favourites
        elif idx == 2:
            kodi_dialog_OK('SL Favourites asset scanner not coded yet. Sorry.')

        # --- Check/Update SL Favourites ---
        elif idx == 3:
            # --- Load databases ---
            control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
            SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
            fav_SL_roms = fs_load_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath())

            # --- Check/Update SL Favourite ROMs ---
            num_SL_favs = len(fav_SL_roms)
            num_iteration = 0
            pDialog = xbmcgui.DialogProgress()
            pDialog.create('Advanced MAME Launcher')
            for fav_SL_key in sorted(fav_SL_roms):
                fav_ROM_name = fav_SL_roms[fav_SL_key]['ROM_name']
                fav_SL_name = fav_SL_roms[fav_SL_key]['SL_name']
                log_debug('Checking Favourite "{0}" / "{1}"'.format(fav_ROM_name, fav_SL_name))

                # >> Update progress dialog (BEGIN)
                update_number = (num_iteration * 100) // num_SL_favs
                pDialog.update(update_number, 'Checking SL Favourites (ROM "{0}") ...'.format(fav_ROM_name))

                # >> Load SL ROMs DB and assets
                file_name =  SL_catalog_dic[fav_SL_name]['rom_DB_noext'] + '.json'
                SL_DB_FN = PATHS.SL_DB_DIR.pjoin(file_name)
                SL_roms = fs_load_JSON_file(SL_DB_FN.getPath())
                assets_file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '_assets.json'
                SL_asset_DB_FN = PATHS.SL_DB_DIR.pjoin(assets_file_name)
                SL_assets_dic = fs_load_JSON_file(SL_asset_DB_FN.getPath())

                if fav_ROM_name in SL_roms:
                    # >> Update Favourite DB
                    new_Fav_ROM = SL_roms[fav_ROM_name]
                    new_assets = SL_assets_dic[fav_ROM_name] if fav_ROM_name in SL_assets_dic else fs_new_SL_asset()
                    new_Fav_ROM['ROM_name']       = fav_ROM_name
                    new_Fav_ROM['SL_name']        = fav_SL_name
                    new_Fav_ROM['ver_mame']       = control_dic['ver_mame']
                    new_Fav_ROM['ver_mame_str']   = control_dic['ver_mame_str']
                    new_Fav_ROM['launch_machine'] = ''
                    new_Fav_ROM['assets']         = new_assets
                    fav_SL_roms[fav_SL_key] = new_Fav_ROM
                    log_debug('Updated SL Fav ROM "{0}" / "{1}"'.format(fav_ROM_name, fav_SL_name))

                else:
                    # >> Delete Favourite ROM from Favourite DB
                    log_debug('Machine "{0}" / "{1}" not found in MAME main DB'.format(fav_ROM_name, fav_SL_name))
                    t = 'Favourite machine "{0}" in SL "{1}" not found in database'.format(fav_ROM_name, fav_SL_name)
                    kodi_dialog_OK(t)

                # >> Update progress dialog (END)
                num_iteration += 1
            pDialog.update(100)
            pDialog.close()

            # --- Save SL Favourite ROMs DB ---
            fs_write_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath(), fav_SL_roms)
            kodi_refresh_container()
            kodi_notify('SL Favourite ROMs checked and updated')

        # --- Delete ROM from SL Favourites ---
        elif idx == 4:
            log_debug('_command_context_manage_sl_fav() Delete SL Favourite ROM')
            log_debug('_command_context_manage_sl_fav() SL_name  "{0}"'.format(SL_name))
            log_debug('_command_context_manage_sl_fav() ROM_name "{0}"'.format(ROM_name))

            # >> Get Machine database row
            kodi_busydialog_ON()
            SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
            file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '.json'
            SL_DB_FN = PATHS.SL_DB_DIR.pjoin(file_name)
            SL_roms = fs_load_JSON_file(SL_DB_FN.getPath())
            kodi_busydialog_OFF()
            ROM = SL_roms[ROM_name]
            
            # >> Open Favourite Machines dictionary
            fav_SL_roms = fs_load_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath())
            SL_fav_key = SL_name + '-' + ROM_name
            log_debug('_command_delete_sl_fav() SL_fav_key "{0}"'.format(SL_fav_key))
            
            # >> Ask user for confirmation.
            ret = kodi_dialog_yesno('Delete Machine {0} ({1})?'.format(ROM_name, SL_name))
            if ret < 1: return

            # >> Delete machine
            del fav_SL_roms[SL_fav_key]
            log_info('_command_delete_sl_fav() Deleted machine {0} ({1})'.format(ROM_name, SL_name))

            # >> Save Favourites
            fs_write_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath(), fav_SL_roms)
            kodi_refresh_container()
            kodi_notify('ROM {0} deleted from SL Favourites'.format(ROM_name))


    def _command_show_sl_fav(self):
        log_debug('_command_show_sl_fav() Starting ...')

        # >> Load Software List ROMs
        SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())

        # >> Open Favourite Machines dictionary
        fav_SL_roms = fs_load_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath())
        if not fav_SL_roms:
            kodi_dialog_OK('No Favourite Software Lists ROMs. Add some ROMs to SL Favourites first.')
            xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)
            return

        # >> Render Favourites
        self._set_Kodi_all_sorting_methods()
        for SL_fav_key in fav_SL_roms:
            SL_fav_ROM = fav_SL_roms[SL_fav_key]
            assets = SL_fav_ROM['assets']
            # >> Add the SL name as 'genre'
            SL_name = SL_fav_ROM['SL_name']
            SL_fav_ROM['genre'] = SL_catalog_dic[SL_name]['display_name']
            self._render_sl_fav_machine_row(SL_fav_key, SL_fav_ROM, assets)
        xbmcplugin.endOfDirectory(handle = self.addon_handle, succeeded = True, cacheToDisc = False)

    def _render_sl_fav_machine_row(self, SL_fav_key, ROM, assets):
        SL_name  = ROM['SL_name']
        ROM_name = ROM['ROM_name']
        display_name = ROM['description']

        # --- Mark Status and Clones ---
        status = '{0}{1}'.format(ROM['status_ROM'], ROM['status_CHD'])
        display_name += ' [COLOR skyblue]{0}[/COLOR]'.format(status)
        if ROM['cloneof']:  display_name += ' [COLOR orange][Clo][/COLOR]'

        # --- Assets/artwork ---
        icon_path   = assets[self.SL_icon] if assets[self.SL_icon] else 'DefaultProgram.png'
        fanart_path = assets[self.SL_fanart]
        poster_path = assets['boxfront']

        # --- Create listitem row ---
        ICON_OVERLAY = 6
        listitem = xbmcgui.ListItem(display_name)
        # >> Make all the infolabels compatible with Advanced Emulator Launcher
        listitem.setInfo('video', {'title' : display_name, 'year'    : ROM['year'],
                                   'genre' : ROM['genre'], 'studio'  : ROM['publisher'],
                                   'overlay' : ICON_OVERLAY })
        listitem.setProperty('platform', 'MAME Software List')

        # --- Assets ---
        # >> AEL custom artwork fields
        listitem.setArt({'title' : assets['title'], 'snap' : assets['snap'], 'boxfront' : assets['boxfront']})
        # >> Kodi official artwork fields
        listitem.setArt({'icon' : icon_path, 'fanart' : fanart_path, 'poster' : poster_path})

        # --- Create context menu ---
        URL_view = self._misc_url_4_arg_RunPlugin('command', 'VIEW', 'SL', SL_name, 'ROM', ROM_name, 'location', LOCATION_SL_FAVS)
        URL_manage = self._misc_url_3_arg_RunPlugin('command', 'MANAGE_SL_FAV', 'SL', SL_name, 'ROM', ROM_name)
        commands = []
        commands.append(('View / Audit', URL_view))
        commands.append(('Manage SL Favourite ROMs',  URL_manage))
        commands.append(('Kodi File Manager', 'ActivateWindow(filemanager)'))
        commands.append(('Add-on Settings', 'Addon.OpenSettings({0})'.format(__addon_id__)))
        listitem.addContextMenuItems(commands, replaceItems = True)

        # --- Add row ---
        URL = self._misc_url_4_arg('command', 'LAUNCH_SL', 'SL', SL_name, 'ROM', ROM_name, 'location', LOCATION_SL_FAVS)
        xbmcplugin.addDirectoryItem(handle = self.addon_handle, url = URL, listitem = listitem, isFolder = False)

    # ---------------------------------------------------------------------------------------------
    # Setup plugin databases
    # ---------------------------------------------------------------------------------------------
    def _command_context_setup_plugin(self):
        dialog = xbmcgui.Dialog()
        menu_item = dialog.select('Setup plugin',
                                 ['Check MAME version',
                                  'Extract MAME.xml',
                                  'Build all databases',
                                  'Scan everything',
                                  'Audit MAME machine ROMs/CHDs',
                                  'Audit SL ROMs/CHDs',
                                  'Step by step ...'])
        if menu_item < 0: return

        # --- Check MAME version ---
        # >> Run 'mame -?' and extract version from stdout
        if menu_item == 0:
            if not self.settings['mame_prog']:
                kodi_dialog_OK('MAME executable is not set.')
                return
            mame_prog_FN = FileName(self.settings['mame_prog'])
            mame_version_str = fs_extract_MAME_version(PATHS, mame_prog_FN)
            kodi_dialog_OK('MAME version is {0}'.format(mame_version_str))

        # --- Extract MAME.xml ---
        elif menu_item == 1:
            if not self.settings['mame_prog']:
                kodi_dialog_OK('MAME executable is not set.')
                return
            mame_prog_FN = FileName(self.settings['mame_prog'])

            # --- Extract MAME XML ---
            (filesize, total_machines) = fs_extract_MAME_XML(PATHS, mame_prog_FN)
            kodi_dialog_OK('Extracted MAME XML database. '
                           'Size is {0} MB and there are {1} machines.'.format(filesize / 1000000, total_machines))

        # --- Build everything ---
        elif menu_item == 2:
            if not PATHS.MAME_XML_PATH.exists():
                kodi_dialog_OK('MAME XML not found. Execute "Extract MAME.xml" first.')
                return

            # --- Build all databases ---
            control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
            fs_build_MAME_main_database(PATHS, self.settings, control_dic)

            # >> Load databases
            pDialog = xbmcgui.DialogProgress()
            pDialog.create('Advanced MAME Launcher', 'Loading databases ... ')
            machines = fs_load_JSON_file(PATHS.MAIN_DB_PATH.getPath())
            pDialog.update(20)
            machines_render = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
            pDialog.update(40)
            devices_db_dic = fs_load_JSON_file(PATHS.DEVICES_DB_PATH.getPath())
            pDialog.update(60)
            machine_roms = fs_load_JSON_file(PATHS.ROMS_DB_PATH.getPath())
            pDialog.update(80)
            main_pclone_dic = fs_load_JSON_file(PATHS.MAIN_PCLONE_DIC_PATH.getPath())
            pDialog.update(100)
            pDialog.close()

            # >> Build everything
            fs_build_ROM_databases(PATHS, self.settings, control_dic, machines, machines_render, devices_db_dic, machine_roms)
            fs_build_MAME_catalogs(PATHS, machines, machines_render, machine_roms, main_pclone_dic)
            fs_build_SoftwareLists_index(PATHS, self.settings, machines, machines_render, main_pclone_dic, control_dic)
            kodi_notify('All databases built')

        # --- Scan everything ---
        elif menu_item == 3:
            log_info('_command_setup_plugin() Scanning everything ...')

            # --- MAME Machines -------------------------------------------------------------------
            # NOTE Here only check for abort conditions. Optinal conditions must be check
            #      inside the function.
            # >> Get paths and check they exist
            if not self.settings['rom_path']:
                kodi_dialog_OK('ROM directory not configured. Aborting.')
                return
            ROM_path_FN = FileName(self.settings['rom_path'])
            if not ROM_path_FN.isdir():
                kodi_dialog_OK('ROM directory does not exist. Aborting.')
                return

            scan_CHDs = False
            if self.settings['chd_path']:
                CHD_path_FN = FileName(self.settings['chd_path'])
                if not CHD_path_FN.isdir():
                    kodi_dialog_OK('CHD directory does not exist. CHD scanning disabled.')
                else:
                    scan_CHDs = True
            else:
                kodi_dialog_OK('CHD directory not configured. CHD scanning disabled.')
                CHD_path_FN = FileName('')

            scan_Samples = False
            if self.settings['samples_path']:
                Samples_path_FN = FileName(self.settings['samples_path'])
                if not Samples_path_FN.isdir():
                    kodi_dialog_OK('Samples directory does not exist. Samples scanning disabled.')
                else:
                    scan_Samples = True
            else:
                kodi_dialog_OK('Samples directory not configured. Samples scanning disabled.')
                Samples_path_FN = FileName('')

            # >> Load machine database and control_dic
            pDialog = xbmcgui.DialogProgress()
            pDialog.create('Advanced MAME Launcher', 'Loading databases ... ')
            pDialog.update(0)
            control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
            pDialog.update(16)
            machines = fs_load_JSON_file(PATHS.MAIN_DB_PATH.getPath())
            pDialog.update(33)
            machines_render = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
            pDialog.update(50)
            machine_rom_sets = fs_load_JSON_file(PATHS.ROM_SET_MACHINES_DB_PATH.getPath())
            pDialog.update(66)
            main_rom_list = fs_load_JSON_file(PATHS.ROM_SET_ARCHIVES_R_DB_PATH.getPath())
            pDialog.update(83)
            main_chd_list = fs_load_JSON_file(PATHS.ROM_SET_ARCHIVES_C_DB_PATH.getPath())
            pDialog.update(100)
            pDialog.close()

            fs_scan_MAME_ROMs(PATHS, self.settings,
                              control_dic, machines, machines_render, machine_rom_sets, main_rom_list, main_chd_list,
                              ROM_path_FN, CHD_path_FN, Samples_path_FN,
                              scan_CHDs, scan_Samples)

            # >> Get assets directory. Abort if not configured/found.
            do_MAME_asset_scan = True
            if not self.settings['assets_path']:
                kodi_dialog_OK('Asset directory not configured. Aborting.')
                do_MAME_asset_scan = False
            Asset_path_FN = FileName(self.settings['assets_path'])
            if not Asset_path_FN.isdir():
                kodi_dialog_OK('Asset directory does not exist. Aborting.')
                do_MAME_asset_scan = False

            if do_MAME_asset_scan: fs_scan_MAME_assets(PATHS, machines_render, Asset_path_FN)

            pDialog.create('Advanced MAME Launcher', 'Saving databases ... ')
            pDialog.update(0)
            fs_write_JSON_file(PATHS.RENDER_DB_PATH.getPath(), machines_render)
            pDialog.update(50)
            fs_write_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath(), control_dic)
            pDialog.update(100)
            pDialog.close()

            # --- Software Lists ------------------------------------------------------------------
            # >> Abort if SL hash path not configured.
            do_SL_ROM_scan = True
            if not self.settings['SL_hash_path']:
                kodi_dialog_OK('Software Lists hash path not set. Scanning aborted.')
                do_SL_ROM_scan = False
            SL_hash_dir_FN = PATHS.SL_DB_DIR
            log_info('_command_setup_plugin() SL hash dir OP {0}'.format(SL_hash_dir_FN.getOriginalPath()))
            log_info('_command_setup_plugin() SL hash dir  P {0}'.format(SL_hash_dir_FN.getPath()))

            # >> Abort if SL ROM dir not configured.
            if not self.settings['SL_rom_path']:
                kodi_dialog_OK('Software Lists ROM path not set. Scanning aborted.')
                do_SL_ROM_scan = False
            SL_ROM_dir_FN = FileName(self.settings['SL_rom_path'])
            log_info('_command_setup_plugin() SL ROM dir OP {0}'.format(SL_ROM_dir_FN.getOriginalPath()))
            log_info('_command_setup_plugin() SL ROM dir  P {0}'.format(SL_ROM_dir_FN.getPath()))

            # >> Load SL catalog
            SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())            
            control_dic    = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
            if do_SL_ROM_scan: fs_scan_SL_ROMs(PATHS, SL_catalog_dic, control_dic, SL_hash_dir_FN, SL_ROM_dir_FN)

            # >> Get assets directory. Abort if not configured/found.
            do_SL_asset_scan = True
            if not self.settings['assets_path']:
                kodi_dialog_OK('Asset directory not configured. Aborting.')
                do_SL_asset_scan = False
            Asset_path_FN = FileName(self.settings['assets_path'])
            if not Asset_path_FN.isdir():
                kodi_dialog_OK('Asset directory does not exist. Aborting.')
                do_SL_asset_scan = False

            if do_SL_asset_scan: fs_scan_SL_assets(PATHS, SL_catalog_dic, Asset_path_FN)

            # --- All operations finished ---
            kodi_notify('All ROM/asset scanning finished')

        # --- Audit MAME machine ROMs/CHDs ---
        # NOTE It is likekely that this function will take a looong time. It is important that the
        #      audit process can be canceled and a partial report is written.
        elif menu_item == 4:
            # >> Load machines, ROMs and CHDs databases.
            pDialog = xbmcgui.DialogProgress()
            pDialog.create('Advanced MAME Launcher', 'Loading databases ... ')
            pDialog.update(0)
            control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
            pDialog.update(5)
            machines = fs_load_JSON_file(PATHS.MAIN_DB_PATH.getPath())
            pDialog.update(25)
            machines_render = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
            pDialog.update(50)
            roms_db_dic = fs_load_JSON_file(PATHS.ROM_SET_ROMS_DB_PATH.getPath())
            pDialog.update(75)
            chds_db_dic = fs_load_JSON_file(PATHS.ROM_SET_CHDS_DB_PATH.getPath())
            pDialog.update(100)
            pDialog.close()

            # >> Go machine by machine and audit ZIPs
            # >> Adds new column 'status' to each ROM.
            pDialog.create('Advanced MAME Launcher', 'Auditing MAME ROMs and CHDs ... ')
            total_machines = control_dic['total_machines']
            processed_machines = 0
            for machine in sorted(machines_render):
                # >> Machine has ROMs
                if machine in roms_db_dic:
                    roms_dic = roms_db_dic[machine]
                    # >> roms_dic is mutable and edited inside the function
                    mame_audit_machine_roms(self.settings, roms_dic)

                # >> Machine has CHDs
                if machine in chds_db_dic:
                    chds_dic = chds_db_dic[machine]
                    mame_audit_machine_chds(self.settings, chds_dic)

                # >> Update progress dialog. Check if user run out of patience.
                processed_machines += 1
                pDialog.update((processed_machines * 100) // total_machines)
                if pDialog.iscanceled(): break

            # >> Generate report.
            # >> 1292apvs, 1392apvs have no ROMs (in 0.190)
            report_list = []
            report_only_errors = self.settings['audit_only_errors']
            for machine in sorted(machines_render):
                # --- ROMs report ---
                if machine in roms_db_dic:
                    roms_list = roms_db_dic[machine]
                    if roms_list:
                        # >> Check if audit was canceled.
                        if 'status' not in roms_list[0]:
                            report_list.append('Audit was canceled at machine {0}'.format(machine))
                            break
                        # >> Check if machine has ROM errors.
                        if report_only_errors:
                            machine_has_errors = False
                            for m_rom in roms_list:
                                if m_rom['status'] != 'OK' and m_rom['status'] != 'OK (invalid ROM)':
                                    machine_has_errors = True
                                    break
                        # >> Print report.
                        if report_only_errors and machine_has_errors:
                            description = machines_render[machine]['description']
                            cloneof = machines_render[machine]['cloneof']
                            if cloneof:
                                report_list.append('Machine {0} "{1}" (cloneof {2})'.format(machine, description, cloneof))
                            else:
                                report_list.append('Machine {0} "{1}"'.format(machine, description))
                            for m_rom in roms_list:
                                if m_rom['status'] != 'OK' and m_rom['status'] != 'OK (invalid ROM)':
                                    report_list.append('{0}  {1}  {2}  {3}  {4}'.format(
                                        m_rom['name'], m_rom['size'], m_rom['crc'], m_rom['location'], m_rom['status']))
                            report_list.append('')
                        elif not report_only_errors:
                            cloneof = machines_render[machine]['cloneof']
                            if cloneof:
                                report_list.append('Machine {0} (cloneof {1})'.format(machine, cloneof))
                            else:
                                report_list.append('Machine {0}'.format(machine))
                            for m_rom in roms_list:
                                report_list.append('{0}  {1}  {2}  {3}  {4}'.format(
                                    m_rom['name'], m_rom['size'], m_rom['crc'], m_rom['location'], m_rom['status']))
                            report_list.append('')
                    else:
                        if not report_only_errors:
                            report_list.append('Machine {0} has no ROMs'.format(machine))
                            report_list.append('')

                # --- CHDs report ---
                if machine in chds_db_dic:
                    chds_list = chds_db_dic[machine]
                    if chds_list:
                        # >> Check if machine has ROM errors.
                        if report_only_errors:
                            machine_has_errors = False
                            for m_chd in chds_list:
                                if m_chd['status'] != 'OK' and m_chd['status'] != 'OK (invalid CHD)':
                                    machine_has_errors = True
                                    break
                        # >> Print report.
                        if report_only_errors and machine_has_errors:
                            report_list.append('Machine {0} has CHDs'.format(machine))
                            for m_chd in chds_list:
                                if m_chd['status'] != 'OK' and m_chd['status'] != 'OK (invalid CHD)':
                                    report_list.append('{0}  {1}  {2}'.format(
                                        m_chd['name'], m_chd['sha1'][0:6], m_chd['status']))
                            report_list.append('')
                        elif not report_only_errors:
                            report_list.append('Machine {0} has CHDs'.format(machine))
                            for m_chd in chds_list:
                                report_list.append('{0}  {1}  {2}'.format(
                                    m_chd['name'], m_chd['sha1'][0:6], m_chd['status']))
                            report_list.append('')
                    else:
                        if not report_only_errors:
                            report_list.append('Machine {0} has no CHDs'.format(machine))
                            report_list.append('')
            else:
                report_list.append('Audited all MAME machines')

            # >> Write report
            with open(PATHS.REPORT_MAME_ROM_AUDIT_PATH.getPath(), 'w') as file:
                out_str = '\n'.join(report_list)
                file.write(out_str.encode('utf-8'))

        # --- Audit SL ROMs/CHDs ---
        elif menu_item == 5:
            log_info('_command_setup_plugin() Audit SL ROMs/CHDs ...')
            kodi_dialog_OK('Audit SL ROMs/CHDs not implemented yet.')

        # --- Build Step by Step ---
        elif menu_item == 6:
            submenu = dialog.select('Setup plugin (step by step)',
                                   ['Build MAME databases ...',
                                    'Build ROM Audit databases ...',
                                    'Build MAME catalogs ...',
                                    'Build Software Lists databases and catalogs ...',
                                    'Scan MAME ROMs/CHDs/Samples ...',
                                    'Scan MAME assets/artwork ...',
                                    'Scan Software Lists ROMs/CHDs ...',
                                    'Scan Software Lists assets/artwork ...' ])
            if submenu < 0: return

            # --- Build main MAME database, PClone list and hashed database ---
            if submenu == 0:
                # --- Error checks ---
                # >> Check that MAME_XML_PATH exists
                if not PATHS.MAME_XML_PATH.exists():
                    kodi_dialog_OK('MAME XML not found. Execute "Extract MAME.xml" first.')
                    return

                # --- Parse MAME XML and generate main database and PClone list ---
                control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
                log_info('_command_setup_plugin() Generating MAME main database and PClone list ...')
                try:
                    fs_build_MAME_main_database(PATHS, self.settings, control_dic)
                except GeneralError as e:
                    log_error(e.msg)
                    raise SystemExit
                kodi_notify('Main MAME databases built')

            # --- Build ROM databases ---
            elif submenu == 1:
                # --- Error checks ---
                # >> Check that MAME_XML_PATH exists
                # if not PATHS.MAME_XML_PATH.exists():
                #     kodi_dialog_OK('MAME XML not found. Execute "Extract MAME.xml" first.')
                #     return
                log_info('_command_setup_plugin() Generating ROM databases ...')
                pDialog = xbmcgui.DialogProgress()
                pDialog.create('Advanced MAME Launcher', 'Loading databases ...')
                control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
                pDialog.update(5)
                machines = fs_load_JSON_file(PATHS.MAIN_DB_PATH.getPath())
                pDialog.update(25)
                machines_render = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
                pDialog.update(50)
                devices_db_dic = fs_load_JSON_file(PATHS.DEVICES_DB_PATH.getPath())
                pDialog.update(75)
                machine_roms = fs_load_JSON_file(PATHS.ROMS_DB_PATH.getPath())
                pDialog.update(100)
                pDialog.close()

                # >> Generate ROM databases
                fs_build_ROM_databases(PATHS, self.settings,
                                       control_dic, machines, machines_render, devices_db_dic, machine_roms)
                kodi_notify('ROM databases built')

            # --- Build MAME catalogs ---
            elif submenu == 2:
                # --- Error checks ---
                # >> Check that main MAME database exists

                # --- Read main database and control dic ---
                kodi_busydialog_ON()
                machines        = fs_load_JSON_file(PATHS.MAIN_DB_PATH.getPath())
                machines_render = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
                machine_roms    = fs_load_JSON_file(PATHS.ROMS_DB_PATH.getPath())
                main_pclone_dic = fs_load_JSON_file(PATHS.MAIN_PCLONE_DIC_PATH.getPath())
                kodi_busydialog_OFF()
                fs_build_MAME_catalogs(PATHS, machines, machines_render, machine_roms, main_pclone_dic)
                kodi_notify('Indices and catalogs built')

            # --- Build Software Lists ROM/CHD databases, SL indices and SL catalogs ---
            elif submenu == 3:
                # --- Error checks ---
                if not self.settings['SL_hash_path']:
                    kodi_dialog_OK('Software Lists hash path not set.')
                    return

                # --- Read main database and control dic ---
                kodi_busydialog_ON()
                machines        = fs_load_JSON_file(PATHS.MAIN_DB_PATH.getPath())
                machines_render = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
                main_pclone_dic = fs_load_JSON_file(PATHS.MAIN_PCLONE_DIC_PATH.getPath())
                control_dic     = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
                kodi_busydialog_OFF()
                fs_build_SoftwareLists_index(PATHS, self.settings, machines, machines_render, main_pclone_dic, control_dic)
                kodi_notify('Software Lists indices and catalogs built')

            # --- Scan ROMs/CHDs/Samples and updates ROM status ---
            elif submenu == 4:
                log_info('_command_setup_plugin() Scanning MAME ROMs/CHDs/Samples ...')

                # >> Get paths and check they exist
                if not self.settings['rom_path']:
                    kodi_dialog_OK('ROM directory not configured. Aborting.')
                    return
                ROM_path_FN = FileName(self.settings['rom_path'])
                if not ROM_path_FN.isdir():
                    kodi_dialog_OK('ROM directory does not exist. Aborting.')
                    return

                scan_CHDs = False
                if self.settings['chd_path']:
                    CHD_path_FN = FileName(self.settings['chd_path'])
                    if not CHD_path_FN.isdir():
                        kodi_dialog_OK('CHD directory does not exist. CHD scanning disabled.')
                    else:
                        scan_CHDs = True
                else:
                    kodi_dialog_OK('CHD directory not configured. CHD scanning disabled.')
                    CHD_path_FN = FileName('')

                scan_Samples = False
                if self.settings['samples_path']:
                    Samples_path_FN = FileName(self.settings['samples_path'])
                    if not Samples_path_FN.isdir():
                        kodi_dialog_OK('Samples directory does not exist. Samples scanning disabled.')
                    else:
                        scan_Samples = True
                else:
                    kodi_dialog_OK('Samples directory not configured. Samples scanning disabled.')
                    Samples_path_FN = FileName('')

                # >> Load machine database and control_dic and scan
                pDialog = xbmcgui.DialogProgress()
                pDialog.create('Advanced MAME Launcher', 'Loading databases ... ')
                pDialog.update(0)
                control_dic = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
                pDialog.update(16)
                machines = fs_load_JSON_file(PATHS.MAIN_DB_PATH.getPath())
                pDialog.update(33)
                machines_render = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
                pDialog.update(50)
                machine_rom_sets = fs_load_JSON_file(PATHS.ROM_SET_MACHINES_DB_PATH.getPath())
                pDialog.update(66)
                main_rom_list = fs_load_JSON_file(PATHS.ROM_SET_ARCHIVES_R_DB_PATH.getPath())
                pDialog.update(83)
                main_chd_list = fs_load_JSON_file(PATHS.ROM_SET_ARCHIVES_C_DB_PATH.getPath())
                pDialog.update(100)
                pDialog.close()

                fs_scan_MAME_ROMs(PATHS, self.settings,
                                  control_dic, machines, machines_render, machine_rom_sets, main_rom_list, main_chd_list,
                                  ROM_path_FN, CHD_path_FN, Samples_path_FN,
                                  scan_CHDs, scan_Samples)
                kodi_busydialog_ON()
                fs_write_JSON_file(PATHS.RENDER_DB_PATH.getPath(), machines_render)
                fs_write_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath(), control_dic)
                kodi_busydialog_OFF()
                kodi_notify('Scanning of ROMs, CHDs and Samples finished')

            # --- Scans MAME assets/artwork ---
            elif submenu == 5:
                log_info('_command_setup_plugin() Scanning MAME assets/artwork ...')

                # >> Get assets directory. Abort if not configured/found.
                if not self.settings['assets_path']:
                    kodi_dialog_OK('Asset directory not configured. Aborting.')
                    return
                Asset_path_FN = FileName(self.settings['assets_path'])
                if not Asset_path_FN.isdir():
                    kodi_dialog_OK('Asset directory does not exist. Aborting.')
                    return

                # >> Load machine database and scan
                kodi_busydialog_ON()
                machines_render = fs_load_JSON_file(PATHS.RENDER_DB_PATH.getPath())
                kodi_busydialog_OFF()
                fs_scan_MAME_assets(PATHS, machines_render, Asset_path_FN)
                kodi_notify('Scanning of assets/artwork finished')

            # --- Scan SL ROMs ---
            elif submenu == 6:
                log_info('_command_setup_plugin() Scanning SL ROMs/CHDs ...')

                # >> Abort if SL hash path not configured.
                if not self.settings['SL_hash_path']:
                    kodi_dialog_OK('Software Lists hash path not set. Scanning aborted.')
                    return
                SL_hash_dir_FN = PATHS.SL_DB_DIR
                log_info('_command_setup_plugin() SL hash dir OP {0}'.format(SL_hash_dir_FN.getOriginalPath()))
                log_info('_command_setup_plugin() SL hash dir  P {0}'.format(SL_hash_dir_FN.getPath()))

                # >> Abort if SL ROM dir not configured.
                if not self.settings['SL_rom_path']:
                    kodi_dialog_OK('Software Lists ROM path not set. Scanning aborted.')
                    return
                SL_ROM_dir_FN = FileName(self.settings['SL_rom_path'])
                log_info('_command_setup_plugin() SL ROM dir OP {0}'.format(SL_ROM_dir_FN.getOriginalPath()))
                log_info('_command_setup_plugin() SL ROM dir  P {0}'.format(SL_ROM_dir_FN.getPath()))

                # >> Load SL and scan
                SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())            
                control_dic    = fs_load_JSON_file(PATHS.MAIN_CONTROL_PATH.getPath())
                fs_scan_SL_ROMs(PATHS, SL_catalog_dic, control_dic, SL_hash_dir_FN, SL_ROM_dir_FN)
                kodi_notify('Scanning of SL ROMs finished')

            # --- Scan SL assets/artwork ---
            # >> Database format: ADDON_DATA_DIR/db_SoftwareLists/32x_assets.json
            # >> { 'ROM_name' : {'asset1' : 'path', 'asset2' : 'path', ... }, ... }
            elif submenu == 7:
                log_info('_command_setup_plugin() Scanning SL assets/artwork ...')

                # >> Get assets directory. Abort if not configured/found.
                if not self.settings['assets_path']:
                    kodi_dialog_OK('Asset directory not configured. Aborting.')
                    return
                Asset_path_FN = FileName(self.settings['assets_path'])
                if not Asset_path_FN.isdir():
                    kodi_dialog_OK('Asset directory does not exist. Aborting.')
                    return

                # >> Load SL database and scan
                kodi_busydialog_ON()
                SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
                kodi_busydialog_OFF()
                fs_scan_SL_assets(PATHS, SL_catalog_dic, Asset_path_FN)
                kodi_notify('Scanning of SL assets finished')

    #
    # Launch MAME machine. Syntax: $ mame <machine_name> [options]
    # Example: $ mame dino
    #
    def _run_machine(self, machine_name, location):
        log_info('_run_machine() Launching MAME machine  "{0}"'.format(machine_name))
        log_info('_run_machine() Launching MAME location "{0}"'.format(location))

        # >> If launching from Favourites read ROM from Fav database
        if location and location == 'MAME_FAV':
            fav_machines = fs_load_JSON_file(PATHS.FAV_MACHINES_PATH.getPath())
            machine = fav_machines[machine_name]
            assets  = machine['assets']

        # >> Get paths
        mame_prog_FN = FileName(self.settings['mame_prog'])

        # >> Check if ROM exist
        if not self.settings['rom_path']:
            kodi_dialog_OK('ROM directory not configured.')
            return
        ROM_path_FN = FileName(self.settings['rom_path'])
        if not ROM_path_FN.isdir():
            kodi_dialog_OK('ROM directory does not exist.')
            return
        ROM_FN = ROM_path_FN.pjoin(machine_name + '.zip')
        # if not ROM_FN.exists():
        #     kodi_dialog_OK('ROM "{0}" not found.'.format(ROM_FN.getBase()))
        #     return

        # >> Choose BIOS (only available for Favourite Machines)
        # Not implemented at the moment
        # if location and location == 'MAME_FAV' and len(machine['bios_name']) > 1:
        #     dialog = xbmcgui.Dialog()
        #     m_index = dialog.select('Select BIOS', machine['bios_desc'])
        #     if m_index < 0: return
        #     BIOS_name = machine['bios_name'][m_index]
        # else:
        #     BIOS_name = ''
        BIOS_name = ''

        # >> Launch machine using subprocess module
        (mame_dir, mame_exec) = os.path.split(mame_prog_FN.getPath())
        log_info('_run_machine() mame_prog_FN "{0}"'.format(mame_prog_FN.getPath()))    
        log_info('_run_machine() mame_dir     "{0}"'.format(mame_dir))
        log_info('_run_machine() mame_exec    "{0}"'.format(mame_exec))
        log_info('_run_machine() machine_name "{0}"'.format(machine_name))
        log_info('_run_machine() BIOS_name    "{0}"'.format(BIOS_name))

        # >> Prevent a console window to be shown in Windows. Not working yet!
        if sys.platform == 'win32':
            log_info('_run_machine() Platform is win32. Creating _info structure')
            _info = subprocess.STARTUPINFO()
            _info.dwFlags = subprocess.STARTF_USESHOWWINDOW
            # See https://msdn.microsoft.com/en-us/library/ms633548(v=vs.85).aspx
            # See https://docs.python.org/2/library/subprocess.html#subprocess.STARTUPINFO
            # >> SW_HIDE = 0
            # >> Does not work: MAME console window is not shown, graphical window not shonw either,
            # >> process run in background.
            # _info.wShowWindow = subprocess.SW_HIDE
            # >> SW_SHOWMINIMIZED = 2
            # >> Both MAME console and graphical window minimized.
            # _info.wShowWindow = 2
            # >> SW_SHOWNORMAL = 1
            # >> MAME console window is shown, MAME graphical window on top, Kodi on bottom.
            _info.wShowWindow = 1
        else:
            log_info('_run_machine() _info is None')
            _info = None

        # >> Launch MAME
        # arg_list = [mame_prog_FN.getPath(), '-window', machine_name]
        if BIOS_name: arg_list = [mame_prog_FN.getPath(), machine_name, '-bios', BIOS_name]
        else:         arg_list = [mame_prog_FN.getPath(), machine_name]
        log_info('arg_list = {0}'.format(arg_list))
        log_info('_run_machine() Calling subprocess.Popen()...')
        with open(PATHS.MAME_OUTPUT_PATH.getPath(), 'wb') as f:
            p = subprocess.Popen(arg_list, cwd = mame_dir, startupinfo = _info, stdout = f, stderr = subprocess.STDOUT)
        p.wait()
        log_info('_run_machine() Exiting function')

    #
    # Launch a SL machine. See http://docs.mamedev.org/usingmame/usingmame.html
    # Complex syntax: $ mame <system> <media> <software> [options]
    # Easy syntax: $ mame <system> <software> [options]
    # Valid example: $ mame smspal -cart sonic
    #
    # Software list <part> tag has an 'interface' attribute that tells how to virtually plug the
    # cartridge/cassete/disk/etc. into the MAME <device> with same 'interface' attribute. The
    # <media> argument in the command line is the <device> <instance> 'name' attribute.
    #
    # Launching cases:
    #   A) Machine has only one device (defined by a <device> tag) with a valid <instance> and
    #      SL ROM has only one part (defined by a <part> tag).
    #      Valid examples:$ mame smspal -cart sonic
    #      Launch as: $ mame machine_name -part_attrib_name SL_ROM_name
    #
    # <device type="cartridge" tag="slot" interface="sms_cart">
    #   <instance name="cartridge" briefname="cart"/>
    #   <extension name="bin"/>
    #   <extension name="sms"/>
    # </device>
    # <software name="sonic">
    #   <part name="cart" interface="sms_cart">
    #     <!-- PCB info based on SMS Power -->
    #     <feature name="pcb" value="171-5507" />
    #     <feature name="ic1" value="MPR-14271-F" />
    #     <dataarea name="rom" size="262144">
    #       <rom name="mpr-14271-f.ic1" size="262144" crc="b519e833" sha1="6b9..." offset="000000" />
    #     </dataarea>
    #   </part>
    # </software>
    #
    #   B) Machine has only one device with a valid <instance> and SL ROM has multiple parts.
    #      In this case, user should choose which part to plug.
    #      Currently not implemented and launch using easy syntax.
    #      Valid examples: 
    #      Launch as: $ mame machine_name -part_attrib_name SL_ROM_name
    #
    #   C) Machine has two or more devices with a valid <instance> and SL ROM has only one part.
    #      Traverse the machine devices until there is a match of the <part> interface attribute 
    #      with the <machine> interface attribute. After the match is found, check also that
    #      SL ROM <part> name attribute matches with machine <device> <intance> briefname attribute.
    #      Valid examples:
    #        MSX2 cartridge vampkill (in msx2_cart.xml) with MSX machine.
    #        vampkill is also in msx_flop SL.xml. MSX2 machines always have two or more interfaces.
    #        $ mame hbf700p -cart vampkill
    #      Launch as: $ mame machine_name -part_attrib_name SL_ROM_name
    #
    #   D) Machine has two or more devices with a valid <instance> and SL ROM has two or more parts.
    #      In this case it is not clear how to launch the machine.
    #      Not implemented and launch using easy syntax.
    #
    # Most common cases are A) and C).
    #
    def _run_SL_machine(self, SL_name, ROM_name, location):
        SL_LAUNCH_WITH_MEDIA = 100
        SL_LAUNCH_NO_MEDIA   = 200
        log_info('_run_SL_machine() Launching SL machine (location = {0}) ...'.format(location))
        log_info('_run_SL_machine() SL_name  "{0}"'.format(SL_name))
        log_info('_run_SL_machine() ROM_name "{0}"'.format(ROM_name))

        # --- Get paths ---
        mame_prog_FN = FileName(self.settings['mame_prog'])

        # --- Get a list of machine <devices> and SL ROM <parts>
        if location == LOCATION_SL_FAVS:
            log_info('_run_SL_machine() SL ROM is in Favourites')
            fav_SL_roms = fs_load_JSON_file(PATHS.FAV_SL_ROMS_PATH.getPath())
            SL_fav_key = SL_name + '-' + ROM_name
            machine_name = fav_SL_roms[SL_fav_key]['launch_machine']
            machine_desc = '[ Not available ]'
            log_info('_run_SL_machine() launch_machine = "{0}"'.format(machine_name))
        else:
            machine_name = ''
            machine_desc = ''

        # >> Load SL machines
        SL_machines_dic = fs_load_JSON_file(PATHS.SL_MACHINES_PATH.getPath())
        SL_machine_list = SL_machines_dic[SL_name]
        if not machine_name:
            # >> Get a list of machines that can launch this SL ROM. User chooses in a select dialog
            log_info('_run_SL_machine() Selecting SL run machine ...')
            SL_machine_names_list      = []
            SL_machine_desc_list       = []
            for SL_machine in sorted(SL_machine_list):
                SL_machine_names_list.append(SL_machine['machine'])
                SL_machine_desc_list.append(SL_machine['description'])
            dialog = xbmcgui.Dialog()
            m_index = dialog.select('Select machine', SL_machine_desc_list)
            if m_index < 0: return
            machine_name    = SL_machine_names_list[m_index]
            machine_desc    = SL_machine_desc_list[m_index]
            machine_devices = SL_machine_list[m_index]['devices']
        else:
            # >> User selected a machine to launch this SL. Find the machine in the list
            log_info('_run_SL_machine() Finding SL run machine ...')
            machine_found = False
            for SL_machine in SL_machine_list:
                if SL_machine['machine'] == machine_name:
                    selected_SL_machine = SL_machine
                    machine_found = True
                    break
            if machine_found:
                log_info('_run_SL_machine() Found machine "{0}"'.format(machine_name))
                machine_desc       = SL_machine['description']
                machine_interfaces = SL_machine['device_tags']
            else:
                log_error('_run_SL_machine() Machine "{0}" not found'.format(machine_name))
                log_error('_run_SL_machine() Aborting launch')
                kodi_dialog_OK('Machine "{0}" not found. Aborting launch.'.format(machine_name))
                return

        # --- Get SL ROM list of <part> tags ---
        if location == LOCATION_SL_FAVS:
            part_list = fav_SL_roms[SL_fav_key]['parts']
        else:
            # >> Open SL ROM database and get information
            SL_catalog_dic = fs_load_JSON_file(PATHS.SL_INDEX_PATH.getPath())
            file_name =  SL_catalog_dic[SL_name]['rom_DB_noext'] + '.json'
            SL_DB_FN = PATHS.SL_DB_DIR.pjoin(file_name)
            log_info('_run_SL_machine() SL ROMs JSON "{0}"'.format(SL_DB_FN.getPath()))
            SL_roms = fs_load_JSON_file(SL_DB_FN.getPath())
            SL_rom = SL_roms[ROM_name]
            part_list = SL_rom['parts']

        # --- Select media depending on SL launching case ---
        num_machine_interfaces = len(machine_devices)
        num_SL_ROM_parts = len(part_list)
        log_info('_run_SL_machine() Machine "{0}" has {1} interfaces'.format(machine_name, num_machine_interfaces))
        log_info('_run_SL_machine() SL ROM  "{0}" has {1} parts'.format(ROM_name, num_SL_ROM_parts))

        # >> Error
        if num_machine_interfaces == 0:
            kodi_dialog_OK('Machine has no inferfaces! Aborting launch.')
            return
        elif num_SL_ROM_parts == 0:
            kodi_dialog_OK('SL ROM has no parts! Aborting launch.')
            return

        # >> Case A
        elif num_machine_interfaces == 1 and num_SL_ROM_parts == 1:
            log_info('_run_SL_machine() Launch case A)')
            launch_case = SL_LAUNCH_CASE_A
            media_name = machine_devices[0]['instance']['name']
            sl_launch_mode = SL_LAUNCH_WITH_MEDIA

        # >> Case B
        #    User chooses media to launch?
        elif num_machine_interfaces == 1 and num_SL_ROM_parts > 1:
            log_info('_run_SL_machine() Launch case B)')
            launch_case = SL_LAUNCH_CASE_B
            media_name = ''
            sl_launch_mode = SL_LAUNCH_NO_MEDIA

        # >> Case C
        elif num_machine_interfaces > 1 and num_SL_ROM_parts == 1:
            log_info('_run_SL_machine() Launch case C)')
            launch_case = SL_LAUNCH_CASE_C
            m_interface_found = False
            for device in machine_devices:
                if device['att_interface'] == part_list[0]['interface']:
                    media_name = device['instance']['name']
                    m_interface_found = True
                    break
            if not m_interface_found:
                kodi_dialog_OK('SL launch case C), not machine interface found! Aborting launch.')
                return
            log_info('_run_SL_machine() Matched machine device interface "{0}" '.format(device['att_interface']) +
                     'to SL ROM part "{0}"'.format(part_list[0]['interface']))
            sl_launch_mode = SL_LAUNCH_WITH_MEDIA

        # >> Case D.
        # >> User chooses media to launch?
        elif num_machine_interfaces > 1 and num_SL_ROM_parts > 1:
            log_info('_run_SL_machine() Launch case D)')
            launch_case = SL_LAUNCH_CASE_D
            media_name = ''
            sl_launch_mode = SL_LAUNCH_NO_MEDIA

        else:
            log_info(unicode(machine_interfaces))
            log_warning('_run_SL_machine() Logical error in SL launch case.')
            launch_case = SL_LAUNCH_CASE_ERROR
            kodi_dialog_OK('Logical error in SL launch case. This is a bug, please report it.')
            media_name = ''
            sl_launch_mode = SL_LAUNCH_NO_MEDIA

        # >> Display some DEBUG information.
        kodi_dialog_OK('Launch case {0}. '.format(launch_case) +
                       'Machine has {0} device interfaces and '.format(num_machine_interfaces) +
                       'SL ROM has {0} parts.'.format(num_SL_ROM_parts))

        # >> Launch machine using subprocess module
        (mame_dir, mame_exec) = os.path.split(mame_prog_FN.getPath())
        log_info('_run_SL_machine() mame_prog_FN "{0}"'.format(mame_prog_FN.getPath()))    
        log_info('_run_SL_machine() mame_dir     "{0}"'.format(mame_dir))
        log_info('_run_SL_machine() mame_exec    "{0}"'.format(mame_exec))
        log_info('_run_SL_machine() machine_name "{0}"'.format(machine_name))
        log_info('_run_SL_machine() machine_desc "{0}"'.format(machine_desc))
        log_info('_run_SL_machine() media_name   "{0}"'.format(media_name))

        # >> Build MAME arguments
        if sl_launch_mode == SL_LAUNCH_WITH_MEDIA:
            arg_list = [mame_prog_FN.getPath(), machine_name, '-{0}'.format(media_name), ROM_name]
        elif sl_launch_mode == SL_LAUNCH_NO_MEDIA:
            arg_list = [mame_prog_FN.getPath(), machine_name, '{0}:{1}'.format(SL_name, ROM_name)]
        else:
            kodi_dialog_OK('Unknown sl_launch_mode = {0}. This is a bug, please report it.'.format(sl_launch_mode))
            return
        log_info('arg_list = {0}'.format(arg_list))

        # >> Prevent a console window to be shown in Windows. Not working yet!
        if sys.platform == 'win32':
            log_info('_run_SL_machine() Platform is win32. Creating _info structure')
            _info = subprocess.STARTUPINFO()
            _info.dwFlags = subprocess.STARTF_USESHOWWINDOW
            _info.wShowWindow = 1
        else:
            log_info('_run_SL_machine() _info is None')
            _info = None

        # --- Launch MAME ---
        log_info('_run_SL_machine() Calling subprocess.Popen()...')
        with open(PATHS.MAME_OUTPUT_PATH.getPath(), 'wb') as f:
            p = subprocess.Popen(arg_list, cwd = mame_dir, startupinfo = _info, stdout = f, stderr = subprocess.STDOUT)
        p.wait()
        log_info('_run_SL_machine() Exiting function')

    # ---------------------------------------------------------------------------------------------
    # Misc functions
    # ---------------------------------------------------------------------------------------------
    def _display_text_window(self, window_title, info_text):
        xbmcgui.Window(10000).setProperty('FontWidth', 'monospaced')
        dialog = xbmcgui.Dialog()
        dialog.textviewer(window_title, info_text)
        xbmcgui.Window(10000).setProperty('FontWidth', 'proportional')

    # List of sorting methods here http://mirrors.xbmc.org/docs/python-docs/16.x-jarvis/xbmcplugin.html#-setSetting
    def _set_Kodi_all_sorting_methods(self):
        if self.addon_handle < 0: return
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS)
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_STUDIO)
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_GENRE)
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_UNSORTED)

    def _set_Kodi_all_sorting_methods_and_size(self):
        if self.addon_handle < 0: return
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS)
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_STUDIO)
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_GENRE)
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_SIZE)
        xbmcplugin.addSortMethod(handle=self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_UNSORTED)

    # ---------------------------------------------------------------------------------------------
    # Misc URL building functions
    # ---------------------------------------------------------------------------------------------
    #
    # Used in xbmcplugin.addDirectoryItem()
    #
    def _misc_url_1_arg(self, arg_name, arg_value):
        arg_value_escaped = arg_value.replace('&', '%26')

        return '{0}?{1}={2}'.format(self.base_url, arg_name, arg_value_escaped)

    def _misc_url_2_arg(self, arg_name_1, arg_value_1, arg_name_2, arg_value_2):
        # >> Escape '&' in URLs
        arg_value_1_escaped = arg_value_1.replace('&', '%26')
        arg_value_2_escaped = arg_value_2.replace('&', '%26')

        return '{0}?{1}={2}&{3}={4}'.format(self.base_url, 
                                            arg_name_1, arg_value_1_escaped,
                                            arg_name_2, arg_value_2_escaped)

    def _misc_url_3_arg(self, arg_name_1, arg_value_1, arg_name_2, arg_value_2, 
                              arg_name_3, arg_value_3):
        arg_value_1_escaped = arg_value_1.replace('&', '%26')
        arg_value_2_escaped = arg_value_2.replace('&', '%26')
        arg_value_3_escaped = arg_value_3.replace('&', '%26')

        return '{0}?{1}={2}&{3}={4}&{5}={6}'.format(self.base_url,
                                                    arg_name_1, arg_value_1_escaped,
                                                    arg_name_2, arg_value_2_escaped,
                                                    arg_name_3, arg_value_3_escaped)

    def _misc_url_4_arg(self, arg_name_1, arg_value_1, arg_name_2, arg_value_2, 
                              arg_name_3, arg_value_3, arg_name_4, arg_value_4):
        arg_value_1_escaped = arg_value_1.replace('&', '%26')
        arg_value_2_escaped = arg_value_2.replace('&', '%26')
        arg_value_3_escaped = arg_value_3.replace('&', '%26')
        arg_value_4_escaped = arg_value_4.replace('&', '%26')

        return '{0}?{1}={2}&{3}={4}&{5}={6}&{7}={8}'.format(self.base_url,
                                                            arg_name_1, arg_value_1_escaped,
                                                            arg_name_2, arg_value_2_escaped,
                                                            arg_name_3, arg_value_3_escaped,
                                                            arg_name_4, arg_value_4_escaped)

    #
    # Used in context menus
    #
    def _misc_url_1_arg_RunPlugin(self, arg_name_1, arg_value_1):
        return 'XBMC.RunPlugin({0}?{1}={2})'.format(self.base_url, 
                                                    arg_name_1, arg_value_1)

    def _misc_url_2_arg_RunPlugin(self, arg_name_1, arg_value_1, arg_name_2, arg_value_2):
        return 'XBMC.RunPlugin({0}?{1}={2}&{3}={4})'.format(self.base_url,
                                                            arg_name_1, arg_value_1,
                                                            arg_name_2, arg_value_2)

    def _misc_url_3_arg_RunPlugin(self, arg_name_1, arg_value_1, arg_name_2, arg_value_2, 
                                  arg_name_3, arg_value_3):
        return 'XBMC.RunPlugin({0}?{1}={2}&{3}={4}&{5}={6})'.format(self.base_url,
                                                                    arg_name_1, arg_value_1,
                                                                    arg_name_2, arg_value_2,
                                                                    arg_name_3, arg_value_3)

    def _misc_url_4_arg_RunPlugin(self, arg_name_1, arg_value_1, arg_name_2, arg_value_2, 
                                  arg_name_3, arg_value_3, arg_name_4, arg_value_4):
        return 'XBMC.RunPlugin({0}?{1}={2}&{3}={4}&{5}={6}&{7}={8})'.format(self.base_url,
                                                                            arg_name_1, arg_value_1,
                                                                            arg_name_2, arg_value_2,
                                                                            arg_name_3, arg_value_3, 
                                                                            arg_name_4, arg_value_4)
