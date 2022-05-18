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

from typing import Optional, Tuple
from adapt.intent import IntentBuilder
from mycroft_bus_client import Message
from neon_utils.location_utils import get_timezone
from neon_utils.skills.neon_skill import NeonSkill
from neon_utils.logger import LOG
from neon_utils.user_utils import get_user_prefs

from mycroft.skills.core import intent_handler


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
        except AttributeError:
            LOG.warning(f"Could not locate: {location}")
            place = None
        return place

    def stop(self):
        pass


def create_skill():
    return ControlsSkill()
