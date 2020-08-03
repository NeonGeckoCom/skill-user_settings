# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2020 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Regina Bloomstine, Elon Gasper, Richard Leeds
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2020: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending

from mycroft.util.parse import extract_number
from adapt.intent import IntentBuilder
# from dateutil.tz import gettz, tzlocal
from NGI.utilities.utilHelper import LookupHelpers
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util import LOG
from datetime import datetime, timedelta
from time import time
import re
import pytz
import tkinter as tk
import tkinter.simpledialog as dialog_box
# from NGI.utilities.chat_user_util import get_chat_nickname_from_filename


class ControlsSkill(MycroftSkill):
    """
    Skill to interact with user-specific settings
    """

    def __init__(self):
        super(ControlsSkill, self)\
            .__init__(name="ControlsSkill")
        # self.clear_wait(True)
        self.new_ww = ""
        self.new_loc = ""
        # Read clap/blink settings
        try:
            self.create_signal("CLAP_active") if self.user_info_available['interface']['clap_commands_enabled'] \
                else self.check_for_signal("CLAP_active")
            self.create_signal("BLINK_active") if self.user_info_available['interface']['blink_commands_enabled'] \
                else self.check_for_signal("BLINK_active")
            self.create_signal("CORE_useHesitation") if self.user_info_available['interface']['use_hesitation'] \
                else self.check_for_signal("CORE_useHesitation")
        except KeyError:
            # self.create_signal("NGI_YAML_user_update")
            self.user_config.update_yaml_file("interface", "clap_commands_enabled", False, final=False)
            self.user_config.update_yaml_file("interface", "use_hesitation", False, final=False)
            self.user_config.update_yaml_file("interface", "blink_commands_enabled", False)
            self.bus.emit(Message('check.yml.updates'), {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"})
            self.check_for_signal("CORE_useHesitation")
            self.check_for_signal("CLAP_active")

    def initialize(self):
        pass
        # self.disable_intent('USC_ConfirmYes')
        # self.disable_intent('USC_ConfirmNo')

    @intent_handler(IntentBuilder("ChangeMeasuring").require("Change").optionally("My").optionally("Time")
                    .require("Units").optionally("To").one_of("American", "Military").build())
    def handle_time_unit_change(self, message=None, confirmed=None):
        # TODO: Move to dialog files DM
        self.user_config.check_for_updates()
        flac_filename = message.context["flac_filename"]
        if message.data.get("Time") or confirmed:
            LOG.info(message.data.get("Military"))
            choice = 24 if message.data.get("Military") else 12 if message.data.get("American") else ""
            if not choice:
                return
            if message.data.get("To"):
                current = self.preference_unit(message)['time']
                if choice == current:
                    self.speak("Time is already set to {}-hour format".format(choice), private=True)
                    return

            self.speak("Okay. Time is set to {} hour format".format(choice), private=True)
            if self.server:
                # flac_filename = message.data.get('flac_filename')
                user_dict = self.build_user_dict(message)
                user_dict['time'] = choice
                LOG.info(user_dict)
                self.socket_io_emit(event="update profile", kind="skill",
                                    flac_filename=flac_filename, message=user_dict)
            else:
                self.user_config.update_yaml_file("units", "time", choice)
                self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))
        else:
            choice = "metric" if message.data.get("Military") else "imperial" \
                if message.data.get("American") else ""
            if not choice:
                return
            if message.data.get("To"):
                current = self.preference_unit(message)['measure']
                if choice == current:
                    self.speak("Units are already " + choice, private=True)
                    return
            self.speak("Okay. Switching my system units to " + choice, private=True)
            if self.server:
                user_dict = self.build_user_dict(message)
                user_dict['measure'] = choice
                LOG.info(user_dict)
                self.socket_io_emit(event="update profile", kind="skill",
                                    flac_filename=flac_filename,  message=user_dict)
            else:
                self.user_config.update_yaml_file("units", "measure", choice)
                self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))
        # self.create_signal("NGI_YAML_user_update")
        # self.user_config._update_yaml_file(header="units", sub_header="time", value=choice)

    @intent_handler(IntentBuilder("PermitTranscription").one_of("Permit", "Deny").one_of("Audio", "Text").
                    require("Transcription").build())
    def handle_permit_transcription(self, message):
        options = "text" if message.data.get("Text") else "audio" if message.data.get("Audio") else None
        user = self.get_utterance_user(message)
        action = "allow" if message.data.get("Permit") else "stop"

        # self.speak("Should I allow text transcription?", True, private=True) if options == "text"\
        #     else self.speak("Should I allow audio transcription?", True, private=True)
        # TODO: Check if currently enabled/disabled and speak different dialog
        #       Add server support DM
        if options == "text":
            if message.data.get("Permit"):
                # self.create_signal('PermitAudioTranscription')
                self.await_confirmation(user, "PermitAudioTranscription")
            else:
                self.await_confirmation(user, "DenyAudioTranscription")
            self.speak_dialog("ConfirmTranscription", {"option": options, "action": action},
                              expect_response=True, private=True)
        elif options == "audio":
            if message.data.get("Permit"):
                self.await_confirmation(user, "PermitAudioRecording")
            else:
                self.await_confirmation(user, "DenyAudioRecording")
            self.speak_dialog("ConfirmTranscription", {"option": options, "action": action},
                              expect_response=True, private=True)

        else:
            # TODO: Speak error DM
            LOG.error(f"No option in: {message.data}")
        # self.create_signal('PermitAudioTranscription') if options == "text" else \
        #     self.create_signal("PermitAudioRecording")
        # self.handle_wait()

        # self.create_signal('WaitingToConfirm')

    @intent_handler(IntentBuilder("EnableGesture").one_of("Permit", "Deny").one_of("Clap", "Blink").
                    require("Settings").optionally("Setup").optionally("OnStartup").build())
    def handle_enable_gesture(self, message):
        self.user_config.check_for_updates()
        if ("change" or "set") in message.data.get('utterance'):
            self.handle_change_clap_blink_set(message)
            return
        if message.data.get("Clap"):
            to_modify = "clap_commands_enabled"
            speakable = "Clap"
        elif message.data.get("Blink"):
            to_modify = "blink_commands_enabled"
            speakable = "Blink"
        else:
            LOG.warning("Invalid command")
            return

        if message.data.get("Deny"):
            state = "disabled"
        elif message.data.get("Permit"):
            state = "enabled"
        else:
            LOG.warning("Invalid state")
            return

        if message.data.get("Setup") and to_modify == "clap_commands_enabled":
            LOG.info("USC - Setup Clapper")
            self.create_signal("CLAP_active")
            self.create_signal("CLAP_calibrate")
        else:
            LOG.info(f"Enabling Gesture {to_modify}")
            if message.data.get("OnStartup"):
                LOG.info("USC - Changing default value")
                self.user_config.update_yaml_file("interface", to_modify, True) \
                    if state == "enabled" else \
                    self.user_config.update_yaml_file("interface", to_modify, False)
                self.speak_dialog("StartupSetting", {"kind": speakable, "enable": state})
                self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))
                # self.speak("Changing the clapper settings to your preference", private=True)
            # else:
            #     self.create_signal("CLAP_active") if message.data.get("Permit") and not \
            #         message.data.get("Deny") else self.check_for_signal("CLAP_active")
            #     self.speak("Clapper is active", private=True) if self.check_for_signal("CLAP_active", -1) else \
            #         self.speak("Clapper is inactive", private=True)
            if state == "disabled":
                if to_modify == "clap_commands_enabled":
                    self.check_for_signal("CLAP_active")
                elif to_modify == "blink_commands_enabled":
                    self.check_for_signal("BLINK_active")
            elif state == "enabled":
                if to_modify == "clap_commands_enabled":
                    self.create_signal("CLAP_active")
                elif to_modify == "blink_commands_enabled":
                    self.create_signal("BLINK_active")
            self.speak_dialog("GestureState", {"kind": speakable, "enable": state})

    @intent_handler(IntentBuilder("CalibrateClaps").require("Setup").require("Clap").optionally("Commands").build())
    def handle_calibrate_clapper(self, message):
        LOG.debug(message.data)
        LOG.info("USC - Setup Clapper")
        if not self.check_for_signal("CLAP_active", -1):
            self.create_signal("CLAP_active")
        self.create_signal("CLAP_calibrate")

    @intent_handler(IntentBuilder("AdjustBlinker").require("Blink").require("Threshold").
                    one_of("Increase", "Decrease", "Adjust").build())
    def handle_blink_sensitivity(self, message):
        import os

        LOG.debug(message.data)
        # blink_scalar should be constrained ~[0.3-1.2]
        current = float(self.user_info_available["interface"].get("blink_scalar", 1.0))
        req_val = extract_number(message.context["cc_data"].get("raw_utterance"))
        min_multiplier, max_multiplier = (0.3, 1.3)
        if req_val:
            LOG.debug(req_val)
            req_val = req_val/0.3
            LOG.debug(req_val)
            if min_multiplier < req_val < max_multiplier:
                new_val = req_val
            else:
                new_val = current
        elif message.data.get("Increase"):
            if current < 0.3:
                new_val = 0.3
            elif current < 0.6:
                new_val = 0.6
            elif current < 1.0:
                new_val = 1.0
            else:
                new_val = 1.2
        elif message.data.get("Decrease"):
            if current > 1.0:
                new_val = 1.0
            elif current > 0.6:
                new_val = 0.6
            else:
                new_val = 0.3
        else:
            new_val = current
        LOG.info(f"Change blink_scalar from {current} to {new_val}")

        if current == new_val:
            if req_val:
                self.speak_dialog("ThresholdOutOfBounds", {"kind": "blink",
                                                           "max": f"{0.3*max_multiplier}",
                                                           "min": f"{0.3*min_multiplier}"})
            elif message.data.get("Increase"):
                self.speak_dialog("BlinkBoundary", {"bound": "maximum"})
                # self.speak("Already at maximum threshold")
            elif message.data.get("Decrease"):
                self.speak_dialog("BlinkBoundary", {"bound": "minimum"})
                # self.speak("Already at minimum threshold")
        else:
            self.speak(f"Adjusting blink threshold to {0.3*new_val}")
            self.user_config.update_yaml_file("interface", "blink_scalar", new_val)
            self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))
            os.system("sudo -H -u " + self.configuration_available['devVars']['installUser'] + ' ' +
                      self.configuration_available['dirVars']['coreDir'] + "/start_neon.sh vision")

    # TODO: Intent to enable/disable blink preview

    @intent_handler(IntentBuilder("CallYou").require("CallYou").build())
    def handle_name_change(self, message):
        self.change_ww(message, ww=message.data.get("utterance").replace(message.data.get("CallYou"), "").strip())

    @intent_handler(IntentBuilder("ChangeWW").optionally("Neon").require("Change").optionally("My").require("WW").
                    require("To").build())
    def change_ww(self, message, ww=None):
        # self.clear_signals("USC")
        user = self.get_utterance_user(message)
        self.new_ww = ww
        if not ww:
            words = message.data.get('utterance').split()
            for word in words:
                if word == 'to':
                    self.new_ww = ' '.join(words[int(words.index(word) + 1):])
                    break
            # self.new_ww = message.data.get("WakeWord")
            # to_change = message.data.get("utterance").replace(message.data.get("WW"), "").replace(
            #     message.data.get("To"), "").replace(message.data.get("Change"), "").strip()
            # to_change = to_change.replace(message.data.get("My"), "").strip() if message.data.get("My") else to_change
            # LOG.info(to_change)
            # self.new_ww = to_change
        LOG.debug(self.new_ww)
        LOG.info(self.new_ww)
        self.new_ww = re.compile("[^a-zA-Z ]").sub('', self.new_ww)
        if len(self.new_ww.split()) < 2:
            # self.speak("Please pick a longer wake word phrase.", private=True)
            self.speak_dialog("NeedLongerWakeWord", private=True)
        # TODO: Check syllables, not words (should be at least 3 syllables) DM
        else:
            # self.speak("Change my wake word to {}?".format(self.new_ww), True, private=True)
            self.speak_dialog("ConfirmNewWakeWord", {"ww": self.new_ww}, True, private=True)
            self.await_confirmation(user, "wwChange")
            # self.create_signal("USC_wwChange")
            # self.handle_wait()

    @intent_handler(IntentBuilder("UpdateTimeZone").optionally("Neon").require("Change").require("My").
                    require("TimeZone").require("To").build())
    def update_timezone(self, message):
        # flac_filename = message.data.get('flac_filename')
        user = self.get_utterance_user(message)
        self.user_config.check_for_updates()
        self.clear_signals("USC")
        old_loc = self.preference_location(message)['city']
        # self.update_location(message, tz_only=True)
        to_change = message.data.get("utterance").replace(message.data.get("TimeZone"), "").replace(
            message.data.get("To"), "", 1).replace(message.data.get("Change"), "").strip()
        to_change = to_change.replace(message.data.get("My"), "", 1).strip() if message.data.get("My") else to_change
        to_change = to_change.replace(message.data.get("Neon"), "", 1).strip() if message.data.get("Neon") \
            else to_change
        to_change = str(to_change).lower()
        LOG.info(to_change)
        utc_opts = ['gmt', 'utc']
        if any(opt in to_change for opt in utc_opts):
            try:
                new_utc = float(re.sub(' ', '', re.sub('[a-z]', '', to_change)))
                LOG.debug(new_utc)
            except Exception as e:
                LOG.debug(e)
                new_utc = 0.0
            utc_offset = timedelta(hours=new_utc)
            now = datetime.now(pytz.utc)
            tz_name = list(tz.zone for tz in map(pytz.timezone, pytz.common_timezones)
                           if now.astimezone(tz).utcoffset() == utc_offset)[1]
            self.speak_dialog('ChangeLocation', {"type": "time zone",
                                                 "location": "UTC " + str(new_utc)}, private=True)
            self.user_config.update_yaml_file(header="location", sub_header="tz", value=tz_name, multiple=True)
            self.user_config.update_yaml_file(header="location", sub_header="utc", value=new_utc, final=True)
            LOG.debug('YML Updates Complete')
            self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))
        # TODO: Handle Timezone Names DM

        elif self.server:
            self.change_location(True, True, message)
        else:
            self.new_loc = to_change  # TODO: Associate with user to allow converse for server too? DM
            self.speak_dialog("AlsoLocation", {"type": "location",
                                               "old": old_loc,
                                               "new": to_change.title()}, True, private=True)
            # self.speak("Would you also like to change your location?", True)
            self.await_confirmation(user, "tzChange")
            # self.create_signal("USC_tzChange")
            # self.handle_wait()

    @intent_handler(IntentBuilder("UpdateLocation").optionally("Neon").require("Change").optionally("My").
                    require("Location").require("To").build())
    def update_location(self, message):
        # flac_filename = message.data.get('flac_filename')
        user = self.get_utterance_user(message)
        self.user_config.check_for_updates()
        self.clear_signals("USC")
        old_tz = str(self.preference_location(message)['tz']).split('/')[1].replace('_', ' ')
        to_change = message.data.get("utterance").replace(message.data.get("Location"), "").replace(
            message.data.get("To"), "", 1).replace(message.data.get("Change"), "").strip()
        to_change = to_change.replace(message.data.get("My"), "", 1).strip() if message.data.get("My") else to_change
        to_change = to_change.replace(message.data.get("Neon"), "", 1).strip() if message.data.get("Neon") \
            else to_change
        LOG.info(to_change)
        self.new_loc = to_change
        if self.server:
            self.change_location(True, True, message)
        else:
            self.speak_dialog("AlsoLocation", {"type": "time",
                                               "old": old_tz + " time",
                                               "new": to_change.title() + " time"}, True)
            # self.speak("Would you also like to change your time zone?", True)
            self.await_confirmation(user, "locChange")
            # self.create_signal("USC_locChange")
            # self.handle_wait()

    def write_ww_change(self):
        import os
        # self.speak("Alright. I'll respond to '{}' from now on".format(self.new_ww), private=True)
        self.speak_dialog("NewWakeWord", {"ww": self.new_ww}, private=True)

        if self.server:
            # TODO: Something in user profile? DM
            pass
        else:
            # self.create_signal("NGI_YAML_user_update")
            self.user_config.update_yaml_file(header="listener", sub_header="wake_word", value=self.new_ww,
                                              multiple=True)
            self.user_config.update_yaml_file(header="listener", sub_header="phonemes",
                                              value=LookupHelpers.get_phonemes(self.new_ww))
            if not self.check_for_signal("CORE_skipWakeWord", -1):
                os.system("sudo -H -u " + self.configuration_available['devVars']['installUser'] + ' ' +
                          self.configuration_available['dirVars']['coreDir'] + "/start_neon.sh voice")
            self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))

    def change_location(self, do_tz=False, do_loc=False, message=None):
        start_time = time()

        # Init Variables (these will only be used if they are overwritten)
        city, state, country, timezone, offset = None, None, None, None, None

        try:
            if self.new_loc in self.long_lat_dict:
                LOG.debug(f"DM: location name cache hit: {self.new_loc}")
                coord = self.long_lat_dict[self.new_loc]
                lat = coord['lat']
                lng = coord['lng']
            else:
                LOG.debug(f"DM: location name lookup")
                lat, lng = LookupHelpers.get_coordinates(self.new_loc)
                LOG.debug(f"DM: location: lat/lng={lat}, {lng}")
                if self.new_loc and not (lat == -1 and lng == -1):
                    self.long_lat_dict[self.new_loc] = {'lat': lat, 'lng': lng}
                    self.bus.emit(Message('neon.update_cache', {'cache': 'coord_cache', 'dict': self.long_lat_dict}))
            LOG.debug(f"DM: lat/lng={lat},{lng}, do_tz/do_loc={do_tz},{do_loc}")

            if do_tz:
                timezone, offset = LookupHelpers.get_timezone(lat, lng)
                LOG.debug(f"timezone={timezone} offset={offset}")
            if do_loc:
                if f"{lat}, {lng}" in self.location_dict:
                    results = self.location_dict[f"{lat}, {lng}"]
                    LOG.debug(f"DM: results={results}")
                    city = results["city"]
                    state = results["state"]
                    country = results["country"]
                    LOG.debug(f"DM: cache time={time() - start_time}")
                else:
                    LOG.debug("DM: Lookup location from coords")
                    city, county, state, country = LookupHelpers.get_location(lat, lng)
                    if not city:
                        city = self.new_loc.split()[0].title()
                    LOG.debug(f"{city}, {county}, {state}, {country}")
                    if city and state and country and not (lat == -1 and lng == -1):
                        self.location_dict[f"{lat}, {lng}"] = {'city': city, 'state': state, 'country': country}
                        self.bus.emit(Message('neon.update_cache', {'cache': 'location_cache',
                                                                    'dict': self.location_dict}))
                    LOG.debug(f"DM: lookup time={time() - start_time}")
        except Exception as e:
            if not do_loc:
                pass
                # TODO: Try to process TZ names/offsets
            LOG.error(e)
            self.speak("It looks like there was a problem with your entered location. Please, try again.", private=True)
            return

        if self.server:
            self.speak("I am updating your user profile.", private=True)
            flac_filename = message.context["flac_filename"]
            user_dict = self.build_user_dict(message)
            user_dict['lat'] = lat
            user_dict['lng'] = lng
            LOG.debug(f"do_loc={do_loc}")
            if do_loc:
                user_dict['city'] = city
                user_dict['state'] = state
                user_dict['country'] = country
            LOG.debug(f"do_tz={do_tz}")
            if do_tz:
                user_dict['tz'] = timezone
                user_dict['utc'] = offset
            LOG.info("user_dict: " + str(user_dict))
            self.socket_io_emit(event="update profile", kind="skill",
                                flac_filename=flac_filename, message=user_dict)
        # self.socket_io_emit(event="location update", message={'lat': lat,
        #                                                       'lng': lng,
        #                                                       'city': city,
        #                                                       'state': state,
        #                                                       'country': country,
        #                                                       'nick': get_chat_nickname_from_filename(flac_filename)
        #                                                       })
        else:
            if do_loc:
                # TODO: Catch null values before error thrown here!! DM
                self.speak_dialog('ChangeLocation', {"type": "location",
                                                     "location": city + ', ' + state + ', ' + country}, private=True)
                self.user_config.update_yaml_file(header="location", sub_header="lat", value=lat, multiple=True)
                self.user_config.update_yaml_file(header="location", sub_header="lng", value=lng, multiple=True)
                self.user_config.update_yaml_file(header="location", sub_header="city", value=city, multiple=True)
                self.user_config.update_yaml_file(header="location", sub_header="state", value=state, multiple=True)
                if not do_tz:
                    self.user_config.update_yaml_file(header="location", sub_header="country",
                                                      value=country, final=True)
                    # LOG.debug('YML Updates Complete')
                else:
                    self.user_config.update_yaml_file(header="location", sub_header="country",
                                                      value=country, multiple=True)

            if do_tz:
                self.speak_dialog('ChangeLocation',
                                  {"type": "time zone",
                                   "location": f'<say-as interpret-as="characters">UTC</say-as> {offset}'},
                                  private=True)
                self.user_config.update_yaml_file(header="location", sub_header="tz", value=timezone, multiple=True)
                self.user_config.update_yaml_file(header="location", sub_header="utc", value=offset, final=True)
                # LOG.debug('YML Updates Complete')
            # self.speak("Changing location to {}".format(to_change))
            # self.create_signal("NGI_YAML_user_update")
            self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))

    @intent_handler(IntentBuilder("NeonBrain").optionally("Permit").optionally("Deny").require("Show").
                    require("Brain").optionally("OnStartup").build())
    def handle_brain(self, message):
        self.user_config.check_for_updates()
        # self.create_signal("NGI_YAML_user_update")
        if message.data.get("Permit") or not message.data.get("Deny"):
            self.speak("Launching Neon Brain.", private=True)
            self.user_config.update_yaml_file(header="interface", sub_header="display_neon_brain", value=True)
        else:
            self.speak("Hiding Neon Brain.", private=True)
            self.user_config.update_yaml_file(header="interface", sub_header="display_neon_brain", value=False)
        self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))

    @intent_handler(IntentBuilder("ConfirmListening").optionally("Permit").optionally("Deny").
                    require("ConfirmListening").optionally("OnStartup").optionally("With").optionally("WW").build())
    def handle_confirm_listening(self, message):
        import os
        self.user_config.check_for_updates()
        # self.create_signal("NGI_YAML_user_update")
        if message.data.get("Permit"):
            self.speak("I will chime when I hear my wake word.", private=True)
            self.user_config.update_yaml_file(header="interface", sub_header="confirm_listening", value=True)
        else:
            self.speak("I will stop making noise when I hear my wake word", private=True)
            self.user_config.update_yaml_file(header="interface", sub_header="confirm_listening", value=False)
        self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))

        if not self.check_for_signal("CORE_skipWakeWord", -1):
            os.system("sudo -H -u " + self.configuration_available['devVars']['installUser'] + ' ' +
                      self.configuration_available['dirVars']['coreDir'] + "/start_neon.sh voice")

    @intent_handler(IntentBuilder("SpeakSpeed").require("Talk").require("Speed").build())
    def handle_speak_faster(self, message):
        self.user_config.check_for_updates()
        if "slower" in message.data.get("Speed"):
            speed = (float(self.user_info_available['speech']['speed_multiplier']) * 0.9)
            if speed < 0.7:
                speed = 0.7
                phrase = "I cannot talk any slower."
            else:
                phrase = "I will talk slower."
        elif "faster" in message.data.get("Speed"):
            speed = (float(self.user_info_available['speech']['speed_multiplier']) / 0.9)
            if speed > 1.5:
                speed = 1.5
                phrase = "I cannot talk any faster."
            else:
                phrase = "I will talk faster."
        else:
            speed = 1.0
            phrase = "I will talk normally."

        # self.create_signal("NGI_YAML_user_update")
        self.user_config.update_yaml_file(header="speech", sub_header="speed_multiplier", value=speed)
        self.create_signal("USC_speak_speed")
        self.speak(phrase, private=True)
        # self.bus.emit(Message('check.yml.updates'))

    # @intent_handler(IntentBuilder("ClapMenu").require("ClapperMenu").build())
    # def handle_tell_me_clap(self, message):
    #     if self.check_for_signal('CLAP_audio', -1):
    #         list_clap = self.user_info_available['clap_sets']['audio']
    #     elif self.check_for_signal('CLAP_home', -1):
    #         list_clap = self.user_info_available['clap_sets']['home']
    #     else:
    #         list_clap = self.user_info_available['clap_sets']['default']
    #     # list_clap = options
    #     LOG.info(list_clap)
    #     if list_clap:
    #         self.speak("Sure. Your clapper options are:", private=True)
    #         for i in range(1, len(list_clap)):
    #             self.speak("{} claps to {}.".format(i, list_clap[i]), private=True) if list_clap[i] \
    #                 else LOG.info("No command")

    @intent_handler(IntentBuilder("ListCommands").require("TellMe").optionally("My").one_of("Clap", "Blink")
                    .require("Commands").build())
    def handle_list_gestures(self, message):
        LOG.info(message.data)
        # TODO: simplify below code DM
        if message.data.get("Clap", None):
            if self.check_for_signal('CLAP_audio', -1):
                list_clap = self.user_info_available['clap_sets']['audio']
            elif self.check_for_signal('CLAP_home', -1):
                list_clap = self.user_info_available['clap_sets']['home']
            else:
                list_clap = self.user_info_available['clap_sets']['default']
            # list_clap = options
            LOG.info(list_clap)
            if list_clap:
                self.speak_dialog("ListGestures", {"gesture": "clap"}, private=True)
                for i in range(1, len(list_clap)):
                    self.speak("{} claps to {}.".format(i, list_clap[i]), private=True) if list_clap[i] \
                        else LOG.info("No command")
        elif message.data.get("Blink", None):
            if self.check_for_signal('BLINK_audio', -1):
                list_blink = self.user_info_available['blink_sets']['audio']
            elif self.check_for_signal('BLINK_home', -1):
                list_blink = self.user_info_available['blink_sets']['home']
            else:
                list_blink = self.user_info_available['blink_sets']['default']
            # list_blink = options
            LOG.info(list_blink)
            if list_blink:
                self.speak_dialog("ListGestures", {"gesture": "blink"}, private=True)
                for i in range(1, len(list_blink)):
                    self.speak("{} blinks to {}.".format(i, list_blink[i]), private=True) if list_blink[i] \
                        else LOG.info("No command")

    @intent_handler(IntentBuilder("ClapSet").require("SetChange").optionally("My").
                    one_of("Clap", "Blink").require("To").require("AudioHome").optionally("Scene").build())
    def handle_change_clap_blink_set(self, message):
        # TODO: Simplify this function DM
        if message.data.get("Clap"):
            self.check_for_signal('CLAP_audio')
            self.check_for_signal('CLAP_home')
            if "audio" in message.data.get("utterance"):
                # self.create_signal("NGI_YAML_user_update")
                # self.user_config._update_yaml_file(header="claps", value=self.audio_set)
                option = "the audio set"
                self.create_signal('CLAP_audio')
            elif "home" in message.data.get("utterance"):
                # self.create_signal("NGI_YAML_user_update")
                # self.user_config._update_yaml_file(header="claps", value=self.home_control_set)
                option = "the home control set"
                self.create_signal('CLAP_home')
            elif "default" in message.data.get("utterance"):
                option = "the default set"
            else:
                self.speak("Clap option not found, switching to default.", private=True)
                return
            self.speak("Updating your clapper settings to {}.".format(option), private=True)
        elif message.data.get("Blink"):
            self.check_for_signal('BLINK_audio')
            self.check_for_signal('BLINK_home')
            if "audio" in message.data.get("utterance"):
                # self.create_signal("NGI_YAML_user_update")
                # self.user_config._update_yaml_file(header="claps", value=self.audio_set)
                option = "the audio set"
                self.create_signal('BLINK_audio')
            elif "home" in message.data.get("utterance"):
                # self.create_signal("NGI_YAML_user_update")
                # self.user_config._update_yaml_file(header="claps", value=self.home_control_set)
                option = "the home control set"
                self.create_signal('BLINK_home')
            elif "default" in message.data.get("utterance"):
                option = "the default set"
            else:
                self.speak("Blink option not found, switching to default.", private=True)
                return
            self.speak("Updating your blinker settings to {}.".format(option), private=True)

    # @intent_handler(IntentBuilder("BlinkMenu").require("BlinkerMenu").build())
    # def handle_tell_me_blink(self, message):
    #     if self.check_for_signal('BLINK_audio', -1):
    #         list_clap = self.user_info_available['clap_sets']['audio']
    #     elif self.check_for_signal('BLINK_home', -1):
    #         list_clap = self.user_info_available['clap_sets']['home']
    #     else:
    #         list_clap = self.user_info_available['clap_sets']['default']
    #     # list_clap = options
    #     LOG.info(list_clap)
    #     if list_clap:
    #         self.speak("Sure. Your blink options are:", private=True)
    #         for i in range(1, len(list_clap)):
    #             self.speak("{} blinks to {}.".format(i, list_clap[i]), private=True) if list_clap[i] \
    #                 else LOG.info("No command")

    # @intent_handler(IntentBuilder("BlinkSet").require("SetChange").optionally("My").
    #                 require("Blink").require("To").require("AudioHome").optionally("Scene").build())
    # def handle_set_blinker_to_set(self, message):
    #     self.check_for_signal('BLINK_audio')
    #     self.check_for_signal('BLINK_home')
    #     if "audio" in message.data.get("utterance"):
    #         # self.create_signal("NGI_YAML_user_update")
    #         # self.user_config._update_yaml_file(header="claps", value=self.audio_set)
    #         option = "the audio set"
    #         self.create_signal('BLINK_audio')
    #     elif "home" in message.data.get("utterance"):
    #         # self.create_signal("NGI_YAML_user_update")
    #         # self.user_config._update_yaml_file(header="claps", value=self.home_control_set)
    #         option = "the home control set"
    #         self.create_signal('BLINK_home')
    #     elif "default" in message.data.get("utterance"):
    #         option = "the default set"
    #     else:
    #         self.speak("Blink option not found, switching to default.", private=True)
    #         return
    #     self.speak("Updating your blinker settings to {}.".format(option), private=True)

    @intent_handler(IntentBuilder("Hesitation").one_of("Permit", "Deny").require("Hesitation").build())
    def handle_speak_hesitation(self, message):
        # LOG.info("In hesitation")
        # TODO: Move to DCC? Is this a device setting or a user setting? DM
        if message.data.get("Permit"):
            self.speak("I will say something when I have to look up a response.", private=True)
            self.create_signal("CORE_useHesitation")
        elif message.data.get("Deny"):
            self.speak("I will only speak when I have a response ready.", private=True)
            self.check_for_signal("CORE_useHesitation")

    # @intent_handler(IntentBuilder("NoHesitation").require("Deny").require("Hesitation").build())
    # def handle_turn_off_hesitation(self, message):
    #     LOG.info("In hesitation")
    #     self.speak("I will only speak when I have a response ready.", private=True)
    #     self.check_for_signal("CORE_useHesitation")

    def converse(self, utterances, lang="en-us", message=None):
        user = self.get_utterance_user(message)
        LOG.debug(self.actions_to_confirm)
        if user in self.actions_to_confirm.keys():
            result = self.check_yes_no_response(message)
            if result == -1:
                # This isn't a response, ignore it
                return False
            elif not result:
                # Filler speech to let the user know we're working on something
                if self.check_for_signal('CORE_useHesitation', -1):
                    self.speak("Okay.", private=True)

                actions_requested = self.actions_to_confirm.pop(user)
                if "wwChange" in actions_requested:
                    self.speak("Please try again or type my new name in the field", private=True)
                    try:
                        parent = tk.Tk()
                        parent.withdraw()
                        self.new_ww = dialog_box.askstring("Wake Words", "Please enter your desired wake words:")
                        parent.quit()
                        LOG.info(self.new_ww)
                    except Exception as e:
                        LOG.info(e)
                    if self.new_ww:
                        self.write_ww_change()
                    else:
                        self.speak("I did not receive any parameters. Please, try again.", private=True)

                    self.new_ww = ""
                elif "tzChange" in actions_requested:
                    # elif self.check_for_signal("USC_tzChange"):
                    self.change_location(do_tz=True, do_loc=False, message=message)
                elif "locChange" in actions_requested:
                    # elif self.check_for_signal("USC_locChange"):
                    self.change_location(do_tz=False, do_loc=True, message=message)
                else:
                    LOG.info(actions_requested)
                    self.speak("Okay. Not doing anything.", False, private=True)
                self.cancel_scheduled_event(f"{user}_{actions_requested[0]}")
                return True
            elif result:
                # Filler speech to let the user know we're working on something
                if self.check_for_signal('CORE_useHesitation', -1):
                    self.speak("Sounds good.", private=True)

                self.user_config.check_for_updates()  # TODO: Is this necessary? DM
                LOG.info(message)
                # 0 index works because this skill only handles one action per confirmation
                action_requested = self.actions_to_confirm.pop(user)[0]
                if action_requested == 'PermitAudioRecording':
                    # self.check_for_signal('CORE_keepAudioPermission', 0)
                    self.create_signal('CORE_keepAudioPermission')
                    self.speak("Audio Recording Enabled.", False, private=True)
                elif action_requested == "DenyAudioRecording":
                    self.check_for_signal('CORE_keepAudioPermission')
                    self.speak("Audio Recording Disabled.", False, private=True)
                elif action_requested == "PermitAudioTranscription":
                    self.create_signal('CORE_transcribeTextPermission')
                    self.speak("Audio Transcription Enabled.", False, private=True)
                elif action_requested == "DenyAudioTranscription":
                    self.check_for_signal('CORE_transcribeTextPermission')
                    self.speak("Audio Transcription Disabled.", False, private=True)
                elif action_requested == "wwChange":
                    self.write_ww_change()
                elif action_requested == "tzChange":
                    self.change_location(do_tz=True, do_loc=True, message=message)
                elif action_requested == "locChange":
                    self.change_location(do_tz=True, do_loc=True, message=message)
                self.cancel_scheduled_event(f"{user}_{action_requested}")
                return True

    def stop(self):
        self.clear_signals("USC")


def create_skill():
    return ControlsSkill()


# @intent_handler(IntentBuilder("StartBlinker").one_of("Permit", "Deny").require("Blink").
#                 require("Settings").optionally("OnStartup").build())
# def handle_blinker_start(self, message):
#     self.user_config.check_for_updates()
#     if ("change" or "set") in message.data.get('utterance'):
#         self.handle_change_clap_blink_set(message)
#         return
#
#     if message.data.get("OnStartup"):
#         LOG.info("USC - Changing default blinker value")
#         self.user_config._update_yaml_file("interface", "blink_commands_enabled", True) \
#             if message.data.get("Permit") and not message.data.get("Deny") else \
#             self.user_config._update_yaml_file("interface", "blink_commands_enabled", False)
#         self.speak("Changing the blinker settings to your preference", private=True)
#     else:
#         self.create_signal("BLINK_active") if message.data.get("Permit") and not \
#             message.data.get("Deny") else self.check_for_signal("BLINK_active")
#         self.speak("Blinker is active", private=True) if self.check_for_signal("BLINK_active", -1) else \
#             self.speak("Blinker is inactive", private=True)

# @intent_handler(IntentBuilder("DenyTranscription").require("Deny").require("Transcription3").
#                 require("Transcription2").build())
# def handle_deny_transcription(self, message):
#     options = message.data.get("Transcription3")
#
#     self.speak("Should I stop audio transcription?", True, private=True) if options == "audio" \
#         else self.speak("Should I stop text transcription?", True, private=True)
#     self.create_signal('DenyAudioTranscription') if options == "text" else
#     self.create_signal("DenyAudioRecording")
#     self.handle_wait()
#
#     self.create_signal('WaitingToConfirm')

# @intent_handler(IntentBuilder("USC_ConfirmYes").require("ConfirmYes").build())
# def handle_confirm_yes(self, message):
#     self.user_config.check_for_updates()
#     LOG.info(message)
#     if self.check_for_signal('CORE_useHesitation', -1):
#         self.speak("Sounds good.", private=True)
#
#     if self.check_for_signal('PermitAudioRecording', 0):
#         self.check_for_signal('CORE_keepAudioPermission', 0)
#         self.create_signal('CORE_keepAudioPermission')
#         self.speak("Audio Recording Enabled.", False, private=True)
#
#     elif self.check_for_signal("DenyAudioRecording", 0):
#         self.check_for_signal('CORE_keepAudioPermission', 0)
#         self.speak("Audio Recording Disabled.", False, private=True)
#
#     elif self.check_for_signal('PermitAudioTranscription', 0):
#         self.check_for_signal('CORE_transcribeTextPermission', 0)
#         self.create_signal('CORE_transcribeTextPermission')
#         self.speak("Audio Transcription Enabled.", False, private=True)
#
#     elif self.check_for_signal("DenyAudioTranscription", 0):
#         self.check_for_signal('CORE_transcribeTextPermission', 0)
#         self.speak("Audio Transcription Disabled.", False, private=True)
#
#     elif self.check_for_signal("USC_wwChange"):
#         self.write_ww_change()
#
#     elif self.check_for_signal("USC_tzChange"):
#         self.change_location(do_tz=True, do_loc=True, message=message)
#
#     elif self.check_for_signal("USC_locChange"):
#         self.change_location(do_tz=True, do_loc=True, message=message)
#
#     self.check_for_signal('WaitingToConfirm')
#     self.disable_intent('USC_ConfirmYes')
#     self.disable_intent('USC_ConfirmNo')
#
# @intent_handler(IntentBuilder("USC_ConfirmNo").require("ConfirmNo").build())
# def handle_confirm_no(self, message):
#     self.user_config.check_for_updates()
#     LOG.info(message)
#     if self.check_for_signal('CORE_useHesitation', -1):
#         self.speak("Okay.", private=True)
#
#     if self.check_for_signal("USC_wwChange"):
#         self.speak("Please try again or type my new name in the field", private=True)
#         try:
#             parent = tk.Tk()
#             parent.withdraw()
#             self.new_ww = dialog_box.askstring("Wake Words", "Please enter your desired wake words:")
#             parent.quit()
#             LOG.info(self.new_ww)
#         except Exception as e:
#             LOG.info(e)
#         if self.new_ww:
#             self.write_ww_change()
#         else:
#             self.speak("I did not receive any parameters. Please, try again.", private=True)
#
#         self.new_ww = ""
#
#     elif self.check_for_signal("USC_tzChange"):
#         self.change_location(do_tz=True, do_loc=False, message=message)
#
#     elif self.check_for_signal("USC_locChange"):
#         self.change_location(do_tz=False, do_loc=True, message=message)
#     else:
#         self.speak("Okay. Not doing anything.", False, private=True)
#
#     self.disable_intent('USC_ConfirmYes')
#     self.disable_intent('USC_ConfirmNo')
#     self.clear_wait()

# def handle_wait(self):
#     self.enable_intent('USC_ConfirmYes')
#     self.enable_intent('USC_ConfirmNo')
#     self.request_check_timeout(30, "USC_ConfirmYes")
#     self.request_check_timeout(30, "USC_ConfirmNo")
#     self.clear_wait()

# def clear_wait(self, pass_signal=None):
#     if self.check_for_signal("WaitingToConfirm") or pass_signal:
#         self.check_for_signal("WaitingToConfirm")
#         self.check_for_signal('PermitAudioRecording', 0)
#         self.check_for_signal("DenyAudioRecording", 0)
#         self.check_for_signal('PermitAudioTranscription', 0)
#         self.check_for_signal("DenyAudioTranscription", 0)
#         self.clear_signals("USC")
#         # self.check_for_signal("USC_wwChange")

# @intent_handler(IntentBuilder("MuteMic").require("MuteMic").optionally("time").optionally("Neon").build())
# def handle_mute_request(self, message):
#     LOG.info(message.data)
#     timeout_in_seconds = message.data.get('time')
#     LOG.info(timeout_in_seconds)
