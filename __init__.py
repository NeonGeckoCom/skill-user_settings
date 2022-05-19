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

from datetime import datetime
from typing import Optional, Tuple
from adapt.intent import IntentBuilder
from dateutil.tz import gettz
from lingua_franca.format import nice_date
from mycroft_bus_client import Message
from neon_utils.location_utils import get_timezone
from neon_utils.skills.neon_skill import NeonSkill
from neon_utils.logger import LOG
from neon_utils.user_utils import get_user_prefs

from mycroft.skills.core import intent_handler, intent_file_handler
from mycroft.util.parse import extract_datetime
from ovos_utils.file_utils import read_vocab_file


class ControlsSkill(NeonSkill):
    MAX_SPEECH_SPEED = 1.5
    MIN_SPEECH_SPEED = 0.7

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
                    .one_of("audio", "text").require("retention").build())
    def handle_transcription_retention(self, message: Message):
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
                    .one_of("timezone", "location").require("Place").build())
    def handle_change_location_timezone(self, message: Message):
        """
        Handle a request to change user configured location or timezone.
        This will prompt the user to update the non-requested setting too
        :param message: Message associated with request
        """
        requested_place = message.data.get("Place")
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

    @intent_handler(IntentBuilder("change_dialog").require("change")
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
                    profile["user"]["full_name"])):
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

        if not name:
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
        friendly_location = ", ".join([x for x in
                                       (location_prefs["city"],
                                        location_prefs["state"],
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

        user_tz = gettz(self.preference_location(message)['tz']) or self.sys_tz
        now_time = datetime.now(user_tz)
        try:
            birth_date, _ = extract_datetime(message.data.get("utterance"),
                                             lang=self.lang)
        except IndexError:
            self.speak_dialog("birthday_not_heard", private=True)
            return

        formatted_birthday = birth_date.strftime("%Y/%m/%d")
        anchor_date = now_time.replace(year=birth_date.year)
        speakable_birthday = nice_date(birth_date, now=anchor_date)

        self.update_profile({"user": {"dob": formatted_birthday}}, message)
        self.speak_dialog("birthday_confirmed",
                          {"birthday": speakable_birthday}, private=True)

        if birth_date.month == now_time.month and \
                birth_date.day == now_time.day:
            self.speak_dialog("happy_birthday", private=True)

    @intent_handler(IntentBuilder("SetMyEmail").optionally("change")
                    .require("my").require("email").require("Setting")
                    .build())
    def handle_set_my_email(self, message: Message):
        """
       Handle a request to set a user's email address
       :param message: Message associated with request
       """
        # Parse actual email address from intent
        extracted = message.data.get("Setting")
        email_addr: str = extracted.split()[0] + \
            message.data.get("utterance").rsplit(extracted.split()[0])[1]
        dot = read_vocab_file(self.find_resource("dot" + '.voc', 'vocab',
                                                 lang=self.lang))[0][0]
        at = read_vocab_file(self.find_resource("at" + '.voc', 'vocab',
                                                lang=self.lang))[0][0]
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

    def profile_intent(self, message):
        # TODO: Refactor this intent into handle_set_my_name
        """Intent to change profile information"""
        if self.neon_in_request(message):
            preference_user = self.preference_user(message)
            name = message.data.get("profile", "").title()
            name_count = name.split(" ")

            # Catch intent match with no name
            if len(name_count) == 0 or not name_count:
                self.speak("I did not catch what you were trying to say. Please try again", private=True)
            else:
                user_dict = self.build_user_dict(message)
                # self.create_signal("NGI_YAML_user_update")
                position = message.data.get("First")

                # User specified "First/Middle/Last" Name
                if position:
                    LOG.debug(f"DM: Name position parameter given - {position}")
                    LOG.debug(f'DM: old= {user_dict["first_name"]} {user_dict["middle_name"]} {user_dict["last_name"]}')
                    if position == "first":
                        user_dict["first_name"] = name

                        if not self.server:
                            self.user_config.update_yaml_file("user", "first_name", name, True)
                    elif position in ['middle', 'second']:
                        user_dict["middle_name"] = name
                        if not self.server:
                            self.user_config.update_yaml_file("user", "middle_name", name, True)
                    elif position == "last":
                        user_dict["last_name"] = name
                        if not self.server:
                            self.user_config.update_yaml_file("user", "last_name", name, True)
                    elif position == "preferred":
                        user_dict["preferred_name"] = name
                        if not self.server:
                            self.user_config.update_yaml_file("user", "preferred_name", name, False)

                    # Put together full name
                    if isinstance(user_dict['first_name'], str) and \
                            isinstance(user_dict['middle_name'], str) and isinstance(user_dict['last_name'], str):
                        user_dict["full_name"] = ' '.join([user_dict["first_name"],
                                                          user_dict["middle_name"],
                                                          user_dict["last_name"]])
                    elif isinstance(user_dict['first_name'], str) and isinstance(user_dict['last_name'], str):
                        user_dict["full_name"] = ' '.join([user_dict["first_name"],
                                                           user_dict["last_name"]])
                    elif isinstance(user_dict['first_name'], str):
                        user_dict["full_name"] = user_dict["first_name"]
                    else:
                        user_dict["full_name"] = ""
                        LOG.warning(f"Error with name! {user_dict['first_name']} {user_dict['middle_name']} "
                                    f"{user_dict['last_name']}")

                    if self.server:
                        LOG.info(user_dict)
                        self.socket_emit_to_server("update profile", ["skill", user_dict,
                                                                      message.context["klat_data"]["request_id"]])
                    elif user_dict["full_name"]:
                        self.user_config.update_yaml_file("user", "full_name", user_dict["full_name"], False)

                # Handle a full name that can't be parsed into First/Middle/Last
                elif len(name_count) > 3:
                    if self.server:
                        # TODO: Maybe parse this better to use all name_count fields DM
                        user_dict['full_name'] = name
                        user_dict['first_name'] = name_count[1]
                        user_dict['middle_name'] = name_count[2]
                        user_dict['last_name'] = name_count[3]
                        LOG.info(user_dict)
                        self.socket_emit_to_server("update profile", ["skill", user_dict,
                                                                      message.context["klat_data"]["request_id"]])
                    else:
                        # TODO: Better way to handle this without a self param (or use a dict)
                        self.speak("If I understood correctly, your name is a little longer "
                                   "than I was expecting. I will save "
                                   "your full name in the settings and will address you as "
                                   + name_count[0] + ". Is that okay?", private=True)
                        self.full_name = name
                        self.create_signal("PS_longerFullName")
                        self.await_confirmation(self.get_utterance_user(message), "longerFullName")
                        return

                # Handle a full name (First/Middle/Last)
                elif len(name_count) == 3:
                    if self.server:
                        user_dict['middle_name'] = name_count[1]
                        user_dict['last_name'] = name_count[2]
                        user_dict['full_name'] = name
                        LOG.info(user_dict)
                        self.socket_emit_to_server("update profile", ["skill", user_dict,
                                                                      message.context["klat_data"]["request_id"]])
                    else:
                        self.user_config.update_yaml_file("user", "middle_name", name_count[1], True)
                        self.user_config.update_yaml_file("user", "last_name", name_count[2], True)
                        LOG.info(name)
                        self.user_config.update_yaml_file("user", "full_name", name)
                # Handle a First/Last Full Name
                elif len(name_count) == 2:
                    if self.server:
                        user_dict['middle_name'] = ""
                        user_dict['last_name'] = name_count[1]
                        user_dict['full_name'] = name
                        LOG.info(user_dict)
                        self.socket_emit_to_server("update profile", ["skill", user_dict,
                                                                      message.context["klat_data"]["request_id"]])
                    else:
                        self.user_config.update_yaml_file("user", "last_name", name_count[1], True)
                        self.user_config.update_yaml_file("user", "middle_name", '', True)
                        self.user_config.update_yaml_file("user", "full_name", name)

                # First name doesn't match existing (possibly empty) profile value
                if (name_count[0] != preference_user["first_name"] or not preference_user["first_name"]) and \
                        not position:
                    if self.server:
                        user_dict['first_name'] = name_count[0]
                        user_dict['preferred_name'] = name_count[0]
                        LOG.info(user_dict)
                        nick = self.get_utterance_user(message)
                        message.context["nick_profiles"][nick] = user_dict
                        self.socket_emit_to_server("update profile", ["skill", user_dict,
                                                                      message.context["klat_data"]["request_id"]])
                    else:
                        self.user_config.update_yaml_file("user", "first_name", name_count[0], True)
                        full_name = name_count[0] + ' ' + \
                            preference_user['middle_name'] + ' ' + \
                            preference_user['last_name']

                        if not preference_user["preferred_name"] or preference_user["preferred_name"] != name_count[0]:
                            self.user_config.update_yaml_file("user", "preferred_name", name_count[0], True)

                        self.user_config.update_yaml_file("user", "full_name", full_name)

                    new_name = name_count[0]
                    LOG.debug(">>> Profile Intent Server End")
                    self.speak_dialog("new.name", {'name': new_name}, private=True)
                else:
                    if position:
                        self.speak_dialog("position.name", {"position": position, "name": name}, private=True)
                    elif len(name_count) > 1:
                        self.speak("I noted the information, " + name_count[0], private=True)
                    else:
                        self.speak("Don't worry, " + name_count[0] + ". I remember. Always pleased to assist you.",
                                   private=True)
                if not self.server:
                    self.bus.emit(Message('check.yml.updates',
                                          {"modified": ["ngi_user_info"]}, {"origin": "personal.neon"}))

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
            if not place['address'].get("city") and \
                    place['address'].get("town"):
                place["address"]["city"] = place["address"]["town"]
        except AttributeError:
            LOG.warning(f"Could not locate: {location}")
            place = None
        return place

    def stop(self):
        pass


def create_skill():
    return ControlsSkill()
