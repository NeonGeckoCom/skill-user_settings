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
from datetime import datetime
from typing import Optional, Tuple
from adapt.intent import IntentBuilder
from dateutil.tz import gettz
from lingua_franca import load_language
from lingua_franca.time import default_timezone
from mycroft_bus_client import Message
from neon_utils.location_utils import get_timezone
from neon_utils.skills.neon_skill import NeonSkill
from neon_utils.logger import LOG
from neon_utils.user_utils import get_user_prefs
from neon_utils.language_utils import get_supported_languages
from lingua_franca.parse import extract_langcode, get_full_lang_code
from lingua_franca.format import pronounce_lang
from lingua_franca.internal import UnsupportedLanguageError
from ovos_utils.file_utils import read_vocab_file
from ovos_utils.network_utils import is_connected
from mycroft.skills.core import intent_handler, intent_file_handler
from mycroft.util.parse import extract_datetime


class UserSettingsSkill(NeonSkill):
    MAX_SPEECH_SPEED = 1.5
    MIN_SPEECH_SPEED = 0.7

    def __init__(self):
        super(UserSettingsSkill, self).__init__(name="UserSettingsSkill")
        self._languages = None

    def initialize(self):
        if self.settings.get('use_geolocation'):
            LOG.debug(f"Geolocation update enabled")
            if is_connected():
                LOG.debug('Internet connected, request location update')
                self._request_location_update()
            else:
                LOG.debug('Waiting for internet to request location update')
                self.add_event('mycroft.internet.connected',
                               self._request_location_update, once=True)

    def _request_location_update(self, _=None):
        LOG.info(f'Requesting Geolocation update')
        self.add_event('ovos.ipgeo.update.response',
                       self._handle_location_ipgeo_update)
        self.bus.emit(Message('ovos.ipgeo.update', {'overwrite': True}))

    def _handle_location_ipgeo_update(self, message):
        updated_location = message.data.get('location')
        if not updated_location:
            LOG.warning(f"No geolocation returned by plugin")
            return
        from neon_utils.user_utils import apply_local_user_profile_updates
        from neon_utils.configuration_utils import get_neon_user_config
        user_config = get_neon_user_config()
        if not all((user_config['location']['lat'],
                    user_config['location']['lng'])):
            LOG.info(f'Updating default user config from ip geolocation')
            new_loc = {
                    'lat': str(updated_location['coordinate']['latitude']),
                    'lon': str(updated_location['coordinate']['longitude']),
                    'city': updated_location['city']['name'],
                    'state': updated_location['city']['state']['name'],
                    'country': updated_location['city']['state']['country']['name'],
                }
            name, offset = self._get_timezone_from_location(new_loc)
            new_loc['lng'] = new_loc.pop('lon')
            new_loc['tz'] = name
            new_loc['utc'] = str(round(offset, 1))
            apply_local_user_profile_updates({'location': new_loc},
                                             get_neon_user_config())
        else:
            LOG.debug(f'Ignoring IP location for already defined user location')
        # Remove listener after a successful update
        self.remove_event('ovos.ipgeo.update.response')

    @property
    def stt_languages(self) -> Optional[set]:
        self._get_supported_languages()
        if not all((self._languages.skills, self._languages.stt)):
            LOG.warning("Incomplete language support response. "
                        "Assuming all languages are supported")
            return None
        return set((lang for lang in self._languages.stt
                    if lang in self._languages.skills))

    @property
    def tts_languages(self):
        self._get_supported_languages()
        if not all((self._languages.skills, self._languages.tts)):
            LOG.warning("Incomplete language support response. "
                        "Assuming all languages are supported")
            return None
        return set((lang for lang in self._languages.tts
                    if lang in self._languages.skills))

    def _get_supported_languages(self):
        """
        Gather supported languages via the Messagebus API and save the result
        """
        if not self._languages:
            supported_langs = get_supported_languages()
            self._languages = supported_langs

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
            self.speak_dialog("units_changed",
                              {"unit": self.translate(f"word_{new_unit}")},
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
                              {"scale": str(new_setting)}, private=True)
        else:
            updated_prefs = {"units": {"time": new_setting}}
            self.update_profile(updated_prefs, message)
            self.speak_dialog("time_format_changed",
                              {"scale": str(new_setting)}, private=True)

    @intent_handler(IntentBuilder("SetHesitation").one_of("permit", "deny")
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
            self.speak_dialog("hesitation_disabled", private=True)

    @intent_handler(IntentBuilder("Transcription").one_of("permit", "deny")
                    .optionally("audio").optionally("text").require("retention")
                    .build())
    def handle_transcription_retention(self, message: Message):
        """
        Handle a request to permit or deny saving audio recordings
        :param message: Message associated with request
        """
        allow = True if message.data.get("permit") else False
        kind = "save_audio" if message.data.get("audio") else \
            "save_text" if message.data.get("text") else None
        if not kind:
            LOG.warning(f"No transcription type specified, assume text")
            kind = 'save_text'

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
    def handle_speech_speed(self, message: Message):
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

        if speed < self.MIN_SPEECH_SPEED:
            speed = self.MIN_SPEECH_SPEED
        elif speed > self.MAX_SPEECH_SPEED:
            speed = self.MAX_SPEECH_SPEED

        speed = round(speed, 1)
        self.update_profile({"speech": {"speed_multiplier": speed}})

        if speed == current_speed == self.MAX_SPEECH_SPEED:
            self.speak_dialog("speech_speed_limit",
                              {"limit": self.translate("word_faster")},
                              private=True)
        elif speed == current_speed == self.MIN_SPEECH_SPEED:
            self.speak_dialog("speech_speed_limit",
                              {"limit": self.translate("word_slower")},
                              private=True)
        elif speed == 1.0:
            self.speak_dialog("speech_speed_normal", private=True)
        elif speed > current_speed:
            self.speak_dialog("speech_speed_faster", private=True)
        elif speed < current_speed:
            self.speak_dialog("speech_speed_slower", private=True)

    @intent_handler(IntentBuilder("ChangeLocationTimezone").require("change")
                    .one_of("timezone", "location").require("rx_place")
                    .build())
    def handle_change_location_timezone(self, message: Message):
        """
        Handle a request to change user configured location or timezone.
        This will prompt the user to update the non-requested setting too
        :param message: Message associated with request
        """
        requested_place = message.data.get("rx_place")
        resolved_place = self._get_location_from_spoken_location(
            requested_place, self.lang)
        if not resolved_place and message.data.get("timezone"):
            # TODO: Try resolving tz by name DM
            pass
        if not resolved_place:
            self.speak_dialog("location_not_found",
                              {"location": requested_place},
                              private=True)
            return

        tz_name, utc_offset = get_timezone(resolved_place["lat"],
                                           resolved_place["lon"])
        if message.data.get("timezone"):
            do_timezone = True
            do_location = self.ask_yesno(
                "also_change_location_tz",
                {"type": self.translate("word_location"),
                 "new": requested_place}) == "yes"
        elif message.data.get("location"):
            do_location = True
            do_timezone = self.ask_yesno(
                "also_change_location_tz",
                {"type": self.translate("word_timezone"),
                 "new": requested_place}) == "yes"
        else:
            do_location = False
            do_timezone = False

        if do_timezone:
            self.update_profile({"location": {"tz": tz_name,
                                              "utc": utc_offset}})
            self.speak_dialog("change_location_tz",
                              {"type": self.translate("word_timezone"),
                               "location": f"UTC {utc_offset}"},
                              private=True)
        if do_location:
            self.update_profile({'location': {
                'city': resolved_place['address']['city'],
                'state': resolved_place['address'].get('state'),
                'country': resolved_place['address']['country'],
                'lat': float(resolved_place['lat']),
                'lng': float(resolved_place['lon'])}})
            self.speak_dialog("change_location_tz",
                              {"type": self.translate("word_location"),
                               "location": resolved_place['address']['city']},
                              private=True)

    @intent_handler(IntentBuilder("ChangeDialog").one_of("change", "permit")
                    .require("dialog_mode").one_of("random", "limited")
                    .build())
    def handle_change_dialog_mode(self, message: Message):
        """
        Handle a request to switch between normal and limited dialog modes
        :param message: Message associated with request
        """
        new_dialog = "word_random" if message.data.get("random") else \
            "word_limited" if message.data.get("limited") else None
        if not new_dialog:
            raise RuntimeError("Missing required dialog mode")
        new_limit_dialog = new_dialog == "word_limited"
        current_limit_dialog = get_user_prefs(message)["response_mode"].get(
            "limit_dialog", False)

        if new_limit_dialog == current_limit_dialog:
            self.speak_dialog("dialog_mode_already_set",
                              {"response": self.translate(new_dialog)},
                              private=True)
            return

        self.update_profile(
            {"response_mode": {"limit_dialog": new_limit_dialog}})
        self.speak_dialog("dialog_mode_changed",
                          {"response": self.translate(new_dialog)},
                          private=True)

    @intent_handler(IntentBuilder("SayMyName").require("tell_me_my")
                    .require("name").build())
    def handle_say_my_name(self, message: Message):
        """
        Handle a request to read back a user's name
        :param message: Message associated with request
        """
        if not self.neon_in_request(message):
            return
        utterance = message.data.get("utterance")
        profile = get_user_prefs(message)

        if not any((profile["user"]["first_name"],
                    profile["user"]["middle_name"],
                    profile["user"]["last_name"],
                    profile["user"]["preferred_name"],
                    profile["user"]["full_name"],
                    profile["user"]["username"])):
            # TODO: Use get_response to ask for the user's name
            self.speak_dialog(
                "name_not_known",
                {"name_position": self.translate("word_name")},
                private=True)
            return
        if self.voc_match(utterance, "first_name"):
            name = profile["user"]["first_name"]
            request = "word_first_name"
        elif self.voc_match(utterance, "middle_name"):
            name = profile["user"]["middle_name"]
            request = "word_middle_name"
        elif self.voc_match(utterance, "last_name"):
            name = profile["user"]["last_name"]
            request = "word_last_name"
        elif self.voc_match(utterance, "preferred_name"):
            name = profile["user"]["preferred_name"]
            request = "word_preferred_name"
        elif self.voc_match(utterance, "full_name"):
            name = profile["user"]["full_name"]
            request = "word_full_name"
        elif self.voc_match(utterance, "username"):
            name = profile["user"]["username"]
            request = "word_username"
        else:
            name = profile["user"]["preferred_name"] or \
                   profile["user"]["first_name"] or \
                   profile["user"]["username"]
            request = "word_name"

        if not name or name == profile["user"]["username"] == 'local':
            # TODO: Use get_response to ask for the user's name
            self.speak_dialog("name_not_known",
                              {"name_position": self.translate(request)},
                              private=True)
        else:
            self.speak_dialog("name_is",
                              {"name_position": self.translate(request),
                               "name": name}, private=True)

    @intent_handler(IntentBuilder("SayMyEmail").require("tell_me_my")
                    .require("email").build())
    def handle_say_my_email(self, message: Message):
        """
        Handle a request to read back the user's email address
        :param message: Message associated with request
        """
        if not self.neon_in_request(message):
            return
        email_address = get_user_prefs(message)["user"]["email"]
        if not email_address:
            # TODO: Use get_response to ask for the user's email
            self.speak_dialog("email_not_known", private=True)
        else:
            self.speak_dialog("email_is", {"email": email_address},
                              private=True)

    @intent_handler(IntentBuilder("SayMyLocation").require("tell_me_my")
                    .require("location").build())
    @intent_file_handler("where_am_i.intent")
    def handle_say_my_location(self, message: Message):
        """
        Handle a request to read back the user's location
        :param message: Message associated with request
        """
        if not self.neon_in_request(message):
            return
        location_prefs = get_user_prefs(message)["location"]
        if not location_prefs["city"]:
            from neon_utils.net_utils import check_online
            if check_online():
                self.speak_dialog("location_unknown_online",
                                  private=True)
            else:
                self.speak_dialog("location_unknown_offline",
                                  private=True)
        else:
            friendly_location = ", ".join([x for x in
                                           (location_prefs["city"],
                                            location_prefs["state"] or
                                            location_prefs["country"])])
            self.speak_dialog("location_is", {"location": friendly_location},
                              private=True)

    @intent_handler(IntentBuilder("SetMyBirthday").require("my")
                    .require("birthday").build())
    def handle_set_my_birthday(self, message: Message):
        """
        Handle a request to set a user's birthday
        :param message: Message associated with request
        """
        if not self.neon_in_request(message):
            return
        load_language(self.lang)
        user_tz = gettz(self.location_timezone) if self.location_timezone else \
            default_timezone()
        now_time = datetime.now(user_tz)
        try:
            birth_date, _ = extract_datetime(message.data.get("utterance"),
                                             now_time, self.lang)
        except IndexError:
            self.speak_dialog("birthday_not_heard", private=True)
            return

        formatted_birthday = birth_date.strftime("%Y/%m/%d")
        # TODO: Update to use LF when method added for month + date format
        # anchor_date = now_time.replace(year=birth_date.year)
        # speakable_birthday = nice_date(birth_date, now=anchor_date)
        speakable_birthday = birth_date.strftime("%B %-d")

        self.update_profile({"user": {"dob": formatted_birthday}}, message)
        self.speak_dialog("birthday_confirmed",
                          {"birthday": speakable_birthday}, private=True)

        if birth_date.month == now_time.month and \
                birth_date.day == now_time.day:
            self.speak_dialog("happy_birthday", private=True)

    @intent_handler(IntentBuilder("SetMyEmail").optionally("change")
                    .require("my").require("email").require("rx_setting")
                    .build())
    def handle_set_my_email(self, message: Message):
        """
       Handle a request to set a user's email address
       :param message: Message associated with request
       """
        # Parse actual email address from intent
        extracted = message.data.get("rx_setting")
        email_addr: str = extracted.split()[0] + \
            message.data.get("utterance").rsplit(extracted.split()[0])[1]
        dot = read_vocab_file(self.find_resource("dot.voc", 'vocab'))[0][0]
        at = read_vocab_file(self.find_resource("at.voc", 'vocab'))[0][0]
        email_words = email_addr.split()
        if dot in email_words:
            email_words[email_words.index(dot)] = "."
        if at in email_words:
            email_words[email_words.index(at)] = "@"
        email_addr = "".join(email_words)
        LOG.info(email_addr)

        if '@' not in email_addr or '.' not in email_addr.split('@')[1]:
            self.speak_dialog("email_set_error", private=True)
            return

        current_email = get_user_prefs(message)["user"]["email"]
        if current_email and email_addr == current_email:
            self.speak_dialog("email_already_set_same",
                              {"email": current_email}, private=True)
            return
        if current_email:
            if self.ask_yesno("email_overwrite", {"old": current_email,
                                                  "new": email_addr}) == "yes":
                self.update_profile({"user": {"email": email_addr}})
                self.speak_dialog("email_set", {"email": email_addr},
                                  private=True)
            else:
                self.speak_dialog("email_not_changed",
                                  {"email": current_email}, private=True)
            return
        if self.ask_yesno("email_confirmation",
                          {"email": email_addr}) == "yes":
            self.update_profile({"user": {"email": email_addr}})
            self.speak_dialog("email_set", {"email": email_addr},
                              private=True)
        else:
            self.speak_dialog("email_not_confirmed", private=True)

    @intent_handler(IntentBuilder("SetMyName").optionally("change")
                    .require("my").require("name").require("rx_setting")
                    .build())
    @intent_handler(IntentBuilder("MyNameIs").require("my_name_is")
                    .require("rx_name").build())
    def handle_set_my_name(self, message: Message):
        """
        Handle a request to set a user's name
        :param message: Message associated with request
        """
        if not self.neon_in_request(message):
            return
        utterance = message.data.get("utterance")
        name = message.data.get("rx_setting") or message.data.get("rx_name")
        if self.voc_match(utterance, "first_name"):
            request = "first_name"
            name = name.title()
        elif self.voc_match(utterance, "middle_name"):
            name = name.title()
            request = "middle_name"
        elif self.voc_match(utterance, "last_name"):
            name = name.title()
            request = "last_name"
        elif self.voc_match(utterance, "preferred_name"):
            name = name.title()
            request = "preferred_name"
        elif self.voc_match(utterance, "username"):
            self.speak_dialog("error_change_username", private=True)
            return
        else:
            name = name.title()
            request = None

        user_profile = get_user_prefs(message)["user"]

        if request:
            if name == user_profile[request]:
                self.speak_dialog(
                    "name_not_changed",
                    {"position": self.translate(f"word_{request}"),
                     "name": name}, private=True)
            else:
                name_parts = (name if request == n else user_profile.get(n)
                              for n in ("first_name", "middle_name",
                                        "last_name"))
                full_name = " ".join((n for n in name_parts if n))
                self.update_profile({"user": {request: name,
                                              "full_name": full_name}},
                                    message)
                self.speak_dialog(
                    "name_set_part",
                    {"position": self.translate(f"word_{request}"),
                     "name": name}, private=True)
        else:
            preferred_name = user_profile["preferred_name"] or name
            name_parts = self._get_name_parts(name, user_profile)
            if preferred_name == user_profile["first_name"] and \
                    "first_name" in name_parts:
                preferred_name = name_parts["first_name"]
            updated_user_profile = {"preferred_name": preferred_name,
                                    **name_parts}
            if all((user_profile[n] == updated_user_profile.get(n) for n in
                    ("first_name", "middle_name", "last_name"))):
                self.speak_dialog("name_not_changed",
                                  {"position": self.translate(f"word_name"),
                                   "name": name})
            else:
                self.update_profile({"user": updated_user_profile}, message)
                self.speak_dialog("name_set_full",
                                  {"nick": preferred_name,
                                   "name": name_parts["full_name"]},
                                  private=True)

    @intent_handler(IntentBuilder("SayMyLanguageSettings")
                    .require("tell_me_my").require("language_settings")
                    .build())
    @intent_file_handler("language_settings.intent")
    def handle_say_my_language_settings(self, message: Message):
        """
        Handle a request to read back the user's language settings
        :param message: Message associated with request
        """
        load_language(self.lang)
        language_settings = get_user_prefs(message)["speech"]
        primary_lang = pronounce_lang(language_settings["tts_language"])
        second_lang = pronounce_lang(
            language_settings["secondary_tts_language"])
        self.speak_dialog("language_setting",
                          {"primary": self.translate("word_primary"),
                           "language": primary_lang,
                           "gender": self.translate(
                               f'word_{language_settings["tts_gender"]}')},
                          private=True)
        if second_lang and (second_lang != primary_lang or
                            language_settings["tts_gender"] !=
                            language_settings["secondary_tts_gender"]):
            self.speak_dialog(
                "language_setting",
                {"primary": self.translate("word_secondary"),
                 "language": second_lang,
                 "gender": self.translate(
                     f'word_{language_settings["secondary_tts_gender"]}')},
                private=True)

    @intent_handler(IntentBuilder("SetSTTLanguage").require("change")
                    .optionally("my").require("language_stt")
                    .require("language").require("rx_language").build())
    @intent_file_handler("language_stt.intent")
    def handle_set_stt_language(self, message: Message):
        """
        Handle a request to change the language spoken by the user
        :param message: Message associated with request
        """
        requested_lang = message.data.get('rx_language') or \
            message.data.get('request_language')
        lang = self._parse_languages(message.data.get("utterance"))[0] or \
            requested_lang.split()[-1]
        try:
            code, spoken_lang = self._get_lang_code_and_name(lang)
        except UnsupportedLanguageError as e:
            LOG.error(e)
            self.speak_dialog("language_not_recognized", {"lang": lang},
                              private=True)
            return

        LOG.info(f"code={code}")
        if self.stt_languages and code.split('-')[0] not in self.stt_languages:
            LOG.warning(f"{code} not found in: {self.stt_languages}")
            self.speak_dialog("language_not_supported",
                              {"lang": spoken_lang,
                               "io": self.translate('word_understand')},
                              private=True)
            return
        dialog_data = {"io": self.translate("word_stt"),
                       "lang": spoken_lang}
        if code == get_user_prefs(message)["speech"]["stt_language"]:
            self.speak_dialog("language_not_changed", dialog_data,
                              private=True)
            return

        if self.ask_yesno("language_change_confirmation",
                          dialog_data) == "yes":
            self.update_profile({"speech": {"stt_language": code}})
            self.speak_dialog("language_set", dialog_data,
                              private=True)
        else:
            self.speak_dialog("language_not_confirmed", private=True)

    @intent_handler(IntentBuilder("SetTTSLanguage").require("change")
                    .optionally("my").require("language_tts")
                    .require("language").require("rx_language").build())
    @intent_handler(IntentBuilder("TalkToMe").require("speak_to_me")
                    .require("rx_language").build())
    def handle_set_tts_language(self, message: Message):
        """
        Handle a request to change the language spoken to the user
        :param message: Message associated with request
        """
        language = message.data.get("rx_language") or \
            message.data.get("rx_setting")
        primary, secondary = \
            self._parse_languages(message.data.get("utterance"))
        LOG.info(f"primary={primary} | secondary={secondary} | "
                 f"language={language}")
        user_settings = get_user_prefs(message)
        if primary:
            try:
                primary_code, primary_spoken = \
                    self._get_lang_code_and_name(primary)
                LOG.info(f"primary={primary_code}")
                if self.tts_languages and \
                        primary_code.split('-')[0] not in self.tts_languages:
                    LOG.warning(f"{primary_code} not found in:"
                                f" {self.tts_languages}")
                    self.speak_dialog("language_not_supported",
                                      {"lang": primary_spoken,
                                       "io": self.translate('word_speak')},
                                      private=True)
                    return
                gender = self._get_gender(primary) or \
                    user_settings["speech"]["tts_gender"]
                self.update_profile({"speech": {"tts_gender": gender,
                                                "tts_language": primary_code}},
                                    message)
                self.speak_dialog("language_set",
                                  {"io": self.translate("word_primary"),
                                   "lang": primary_spoken}, private=True)
            except UnsupportedLanguageError:
                LOG.warning(f"No language for primary request: {primary}")
                self.speak_dialog("language_not_recognized", {"lang": primary},
                                  private=True)
        if secondary:
            try:
                secondary_code, secondary_spoken = \
                    self._get_lang_code_and_name(secondary)
                LOG.info(f"secondary={secondary_code}")
                if self.tts_languages and \
                        secondary_code.split('-')[0] not in self.tts_languages:
                    LOG.warning(f"{secondary_code} not found in:"
                                f" {self.tts_languages}")
                    self.speak_dialog("language_not_supported",
                                      {"lang": secondary_spoken,
                                       "io": self.translate('word_speak')},
                                      private=True)
                    return
                gender = self._get_gender(secondary) or \
                    user_settings["speech"]["secondary_tts_gender"]
                self.update_profile(
                    {"speech": {"secondary_tts_gender": gender,
                                "secondary_tts_language": secondary_code}},
                    message)
                self.speak_dialog("language_set",
                                  {"io": self.translate("word_secondary"),
                                   "lang": secondary_spoken}, private=True)
            except UnsupportedLanguageError:
                LOG.warning(f"No language for secondary request: {secondary}")
                self.speak_dialog("language_not_recognized",
                                  {"lang": secondary}, private=True)

        if any((primary, secondary)):
            return
        if language:
            try:
                code, spoken = \
                    self._get_lang_code_and_name(language)
                if self.tts_languages and \
                        code.split('-')[0] not in self.tts_languages:
                    LOG.warning(f"{code} not found in: {self.tts_languages}")
                    self.speak_dialog("language_not_supported",
                                      {"lang": spoken,
                                       "io": self.translate('word_speak')},
                                      private=True)
                    return
                gender = self._get_gender(language) or \
                    user_settings["speech"]["tts_gender"]
                self.update_profile({"speech": {"tts_gender": gender,
                                                "tts_language": code}},
                                    message)
                self.speak_dialog("language_set",
                                  {"io": self.translate("word_primary"),
                                   "lang": spoken}, private=True)
            except UnsupportedLanguageError:
                LOG.warning(f"No language for secondary request: {language}")
                self.speak_dialog("language_not_recognized",
                                  {"lang": language}, private=True)
        else:
            LOG.warning("No language parsed")
            self.speak_dialog("language_not_heard", private=True)

    @intent_handler(IntentBuilder("SetPreferredLanguage").require("my")
                    .require("preferred_language").require("rx_setting")
                    .build())
    @intent_handler(IntentBuilder("SetMyLanguage").require("change")
                    .require("my").require("language")
                    .optionally("rx_language").build())
    def handle_set_language(self, message: Message):
        """
        Handle a user request to change languages. Checks for improper parsing
        of STT/TTS keywords and otherwise updates both STT and TTS settings.
        :param message: Message associated with request
        """
        utterance = message.data.get("utterance")
        LOG.info(f"language={message.data.get('language')}")
        LOG.info(f"preferred_language={message.data.get('preferred_language')}")
        LOG.info(f"Ambiguous language change request: {utterance}")
        if self.voc_match(utterance, "language_stt"):
            LOG.warning("STT Intent not matched")
            self.handle_set_stt_language(message)
        elif self.voc_match(utterance, "language_tts"):
            LOG.warning("TTS Intent not matched")
            self.handle_set_tts_language(message)
        else:
            LOG.info("General language change request, handle STT+TTS")
            self.handle_set_tts_language(message)
            try:
                lang = self._get_lang_code_and_name(
                    message.data.get("rx_language", ""))[0]
                if not lang or lang != \
                        get_user_prefs(message)["speech"]["stt_language"]:
                    self.handle_set_stt_language(message)
            except UnsupportedLanguageError:
                pass

    @intent_handler(IntentBuilder("NoSecondaryLanguage")
                    .require("no_secondary_language").build())
    def handle_no_secondary_language(self, message: Message):
        """
        Handle a user request to only hear responses in one language
        :param message: Message associated with request
        """
        self.update_profile({"speech": {"secondary_tts_language": "",
                                        "secondary_neon_voice": ""}},
                            message)
        self.speak_dialog("only_one_language", private=True)

    def _parse_languages(self, utterance: str) -> \
            (Optional[str], Optional[str]):
        """
        Parse a language change request for primary and secondary languages
        :param utterance: raw utterance spoken by the user
        :returns: spoken primary, secondary languages requested
        """
        def _get_rx_patterns(rx_file: str, utt: str):
            with open(rx_file) as f:
                for pat in f.read().splitlines():
                    pat = pat.strip()
                    if pat and pat[0] == "#":
                        continue
                    res = re.search(pat, utt)
                    if res:
                        return res
        utterance = f"{utterance}\n"
        primary_tts = self.find_resource('primary_tts.rx', 'regex')
        secondary_tts = self.find_resource('secondary_tts.rx', 'regex')
        if primary_tts:
            try:
                primary = _get_rx_patterns(primary_tts,
                                           utterance).group("rx_primary").strip()
            except (IndexError, AttributeError):
                primary = None
        else:
            LOG.warning("Could not resolve primary_tts.rx")
            primary = None
        if secondary_tts:
            try:
                secondary = _get_rx_patterns(secondary_tts,
                                             utterance).group("rx_secondary")\
                    .strip()
            except (IndexError, AttributeError):
                secondary = None
        else:
            LOG.warning("Could not resolve secondary_tts.rx")
            secondary = None

        return primary, secondary

    def _get_lang_code_and_name(self, request: str) -> (str, str):
        """
        Extract the lang code and pronounceable name from a requested language
        :param request: user requested language
        :returns: lang code and pronounceable language name if found, else None
        """
        load_language(self.lang)

        code = None
        # Manually specified languages take priority
        request_overrides = self.translate_namedvalues("languages.value")
        for lang, c in request_overrides.items():
            if lang in request.lower().split():
                code = c
                break
        if not code:
            # Ask LF to determine the code
            short_code = extract_langcode(request)[0]
            code = get_full_lang_code(short_code)
            if code.split('-')[0] != short_code:
                LOG.warning(f"Got {code} from {short_code}. No valid code")
                code = None

        if not code:
            # Request is not a language, raise an exception
            raise UnsupportedLanguageError(f"No language found in {request}")
        spoken_lang = pronounce_lang(code)
        return code, spoken_lang

    def _get_gender(self, request: str) -> Optional[str]:
        """
        Extract a requested voice gender
        :param request: Parsed user requested language
        :returns: 'male', 'female', or None
        """
        if self.voc_match(request, "male"):
            return "male"
        if self.voc_match(request, "female"):
            return "female"
        LOG.info(f"no gender in request: {request}")
        return None

    @staticmethod
    def _get_name_parts(name: str, user_profile: dict) -> dict:
        """
        Parse a name string into first/middle/last components
        :param user_profile: user preferences dict with keys:
            ('first_name', 'middle_name', 'last_name')
        :returns: dict of positional names extracted
        """
        name_parts = name.split()
        if len(name_parts) == 1:
            name = {"first_name": name}
        elif len(name_parts) == 2:
            name = {"first_name": name_parts[0],
                    "last_name": name_parts[1]}
        elif len(name_parts) == 3:
            name = {"first_name": name_parts[0],
                    "middle_name": name_parts[1],
                    "last_name": name_parts[2]}
        else:
            LOG.warning(f"Longer name than expected: {name}")
            name = {"first_name": name_parts[0],
                    "middle_name": name_parts[1],
                    "last_name": " ".join(name_parts[2:])}
        name_parts = (name.get(n) or user_profile.get(n)
                      for n in ("first_name", "middle_name", "last_name"))
        name["full_name"] = " ".join((n for n in name_parts if n))
        return name

    @staticmethod
    def _get_timezone_from_location(location: dict) -> \
            Optional[Tuple[str, float]]:
        """
        Get timezone info for the resolved location
        :param location: location data to get timezone for
        :returns: Timezone name, UTC Offset
        """
        try:
            tz_name, tz_offset = get_timezone(location["lat"], location["lon"])
            return tz_name, tz_offset
        except (KeyError, TypeError):
            return None

    @staticmethod
    def _get_location_from_spoken_location(location: str,
                                           lang: Optional[str] = None) -> \
            Optional[dict]:
        """
        Get address information for the requested location
        :param location: spoken location to get data for
        :returns: dict of location data containing at minimum:
            'lat', 'lon', 'address'['city'], address['country']
        """
        from neon_utils.location_utils import get_full_location
        try:
            place = get_full_location(location, lang)
            if not place or not place.get("address"):
                LOG.warning(f"Could not locate: {location}")
                return None
            if not place['address'].get("city") and \
                    place['address'].get("town"):
                place["address"]["city"] = place["address"]["town"]
        except AttributeError:
            LOG.warning(f"Could not locate: {location}")
            return None
        return place

    def stop(self):
        pass


def create_skill():
    return UserSettingsSkill()
