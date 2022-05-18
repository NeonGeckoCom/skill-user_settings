# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import pytz

from adapt.intent import IntentBuilder
from mycroft_bus_client import Message
from mycroft.skills.core import intent_handler
from datetime import timedelta
from time import time
from neon_utils.skills.neon_skill import NeonSkill
from neon_utils.logger import LOG
from neon_utils.user_utils import get_user_prefs


class ControlsSkill(NeonSkill):
    def __init__(self):
        super(ControlsSkill, self).__init__(name="UserSettingsSkill")

    @intent_handler(IntentBuilder("ChangeUnits").require("change")
                    .require("units").one_of("imperial", "metric").build())
    def handle_unit_change(self, message: Message):
        """
        Handle a request to set metric or imperial units of measurement
        :param message: Message associated with request
        """
        new_unit = "imperial" if message.data.get("imperial") else \
            "metric" if message.data.get("metric") else None
        if not new_unit:
            raise RuntimeError("Missing required imperial or metric vocab")

        current_unit = get_user_prefs(message)["units"]["measure"]
        if new_unit == current_unit:
            self.speak_dialog("units_already_set", {"unit": new_unit},
                              private=True)
        else:
            updated_prefs = {"units": {"measure": new_unit}}
            self.update_profile(updated_prefs, message)
            self.speak_dialog("units_changed", {"unit": new_unit},
                              private=True)

    @intent_handler(IntentBuilder("ChangeTime").require("change")
                    .require("time").one_of("half", "full").build())
    def handle_time_format_change(self, message: Message):
        """
        Handle a request to set time format to 12 or 24 hour time
        :param message: Message associated with request
        """
        new_setting = 12 if message.data.get("half") else \
            24 if message.data.get("full") else None
        if not new_setting:
            raise RuntimeError("Missing required time scale vocab")

        current_setting = get_user_prefs(message)["units"]["time"]
        if new_setting == current_setting:
            self.speak_dialog("time_format_already_set",
                              {"scale": new_setting}, private=True)
        else:
            updated_prefs = {"units": {"time": new_setting}}
            self.update_profile(updated_prefs, message)
            self.speak_dialog("time_format_changed",
                              {"scale": new_setting}, private=True)

    @intent_handler(IntentBuilder("Transcription").one_of("permit", "deny")
                    .one_of("audio", "text").require("retention").build())
    def handle_transcription(self, message: Message):
        """
        Handle a request to permit or deny saving audio recordings
        :param message: Message associated with request
        """
        allow = True if message.data.get("permit") else False
        kind = "save_audio" if message.data.get("audio") else \
            "save_text" if message.data.get("text") else None
        if not kind:
            raise RuntimeError("Missing required transcription type")

        transcription = "word_audio" if kind == "save_audio" else "word_text"
        enabled = "word_enabled" if allow else "word_disabled"

        current_setting = get_user_prefs(message)["privacy"][kind]
        if current_setting == allow:
            self.speak_dialog("transcription_already_set",
                              {"transcription": self.translate(transcription),
                               "enabled": self.translate(enabled)},
                              private=True)
        else:
            updated_prefs = {"privacy": {kind: allow}}
            self.update_profile(updated_prefs, message)
            self.speak_dialog("transcription_changed",
                              {"transcription": self.translate(transcription),
                               "enabled": self.translate(enabled)},
                              private=True)

    @intent_handler(IntentBuilder("SpeakSpeed").require("speak_to_me")
                    .one_of("faster", "slower", "normally").build())
    def handle_speak_faster(self, message: Message):
        """
        Handle a request to adjust response audio playback speed
        :param message: Message associated with request
        """
        current_speed = float(get_user_prefs(message)["speech"].get(
            "speed_multiplier")) or 1.0
        if message.data.get("faster"):
            speed = current_speed / 0.9
        elif message.data.get("slower"):
            speed = current_speed * 0.9
        elif message.data.get("normally"):
            speed = 1.0
        else:
            raise RuntimeError("Missing speed keyword")

        if speed < 0.7:
            speed = 0.7
        elif speed > 1.5:
            speed = 1.5

        speed = round(speed, 1)
        self.update_profile({"speech": {"speed_multiplier": speed}})

        if speed == current_speed == 1.5:
            self.speak_dialog("speech_speed_limit",
                              {"limit": self.translate("word_faster")},
                              private=True)
        elif speed == current_speed == 0.7:
            self.speak_dialog("speech_speed_limit",
                              {"limit": self.translate("word_slower")},
                              private=True)
        elif speed == 1.0:
            self.speak_dialog("speech_speed_normal", private=True)
        elif speed > current_speed:
            self.speak_dialog("speech_speed_faster", private=True)
        elif speed < current_speed:
            self.speak_dialog("speech_speed_slower", private=True)

    @intent_handler(IntentBuilder("Hesitation").one_of("permit", "deny")
                    .require("hesitation").build())
    def handle_speak_hesitation(self, message: Message):
        """
        Handle a request for Neon to speak something when intent processing
        may take some time
        :param message: Message associated with request
        """
        enabled = True if message.data.get("permit") else False
        self.update_profile({"response_mode": {"hesitation": enabled}})
        if enabled:
            self.speak_dialog("hesitation_enabled", private=True)
        else:
            self.speak_dialog("hesitation_disabled")

#### TODO: Test above handlers and then continue DM

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
        # import os
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
                                              value=get_phonemes(self.new_ww, "en"))
            # if not self.check_for_signal("CORE_skipWakeWord", -1):
            #     # TODO: Better method to restart voice DM
            #     os.system("sudo -H -u " + self.configuration_available['devVars']['installUser'] + ' ' +
            #               self.configuration_available['dirVars']['coreDir'] + "/start_neon.sh voice")
            # self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))

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
                lat, lng = get_coordinates(self.new_loc)
                LOG.debug(f"DM: location: lat/lng={lat}, {lng}")
                if self.new_loc and not (lat == -1 and lng == -1):
                    self.long_lat_dict[self.new_loc] = {'lat': lat, 'lng': lng}
                    self.bus.emit(Message('neon.update_cache', {'cache': 'coord_cache', 'dict': self.long_lat_dict}))
            LOG.debug(f"DM: lat/lng={lat},{lng}, do_tz/do_loc={do_tz},{do_loc}")

            if do_tz:
                timezone, offset = get_timezone(lat, lng)
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
                    city, county, state, country = get_location(lat, lng)
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
            # flac_filename = message.context["flac_filename"]
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
            self.socket_emit_to_server("update profile", ["skill", user_dict,
                                                          message.context["klat_data"]["request_id"]])
            # self.socket_io_emit(event="update profile", kind="skill",
            #                     flac_filename=flac_filename, message=user_dict)
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
            # self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))

    # TODO: Move to device_controls DM
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

    # TODO: Move to device_controls DM
    @intent_handler(IntentBuilder("ConfirmListening").optionally("Permit").optionally("Deny").
                    require("ConfirmListening").optionally("OnStartup").optionally("With").optionally("WW").build())
    def handle_confirm_listening(self, message):
        # import os
        # self.user_config.check_for_updates()
        # self.create_signal("NGI_YAML_user_update")
        if message.data.get("Permit"):
            self.speak("I will chime when I hear my wake word.", private=True)
            self.local_config.update_yaml_file(header="interface", sub_header="confirm_listening", value=True)
        else:
            self.speak("I will stop making noise when I hear my wake word", private=True)
            self.local_config.update_yaml_file(header="interface", sub_header="confirm_listening", value=False)
        # self.bus.emit(Message('check.yml.updates', {"modified": ["ngi_user_info"]}, {"origin": "controls.neon"}))

        # TODO: Restart voice/update config DM
        # if not self.check_for_signal("CORE_skipWakeWord", -1):
        #     os.system("sudo -H -u " + self.configuration_available['devVars']['installUser'] + ' ' +
        #               self.configuration_available['dirVars']['coreDir'] + "/start_neon.sh voice")

    def stop(self):
        pass


def create_skill():
    return ControlsSkill()
