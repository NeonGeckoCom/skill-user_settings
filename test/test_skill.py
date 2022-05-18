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

import unittest

from os import mkdir
from os.path import dirname, join, exists
from typing import Optional

from mock import Mock
from mock.mock import call
from neon_utils.user_utils import get_default_user_config
from ovos_utils.messagebus import FakeBus
from mycroft_bus_client import Message
from neon_utils.configuration_utils import get_neon_local_config,\
    get_neon_user_config
from mycroft.skills.skill_loader import SkillLoader


class TestSkill(unittest.TestCase):
    test_message = Message("test", {}, {"neon_in_request": True})

    @classmethod
    def setUpClass(cls) -> None:
        bus = FakeBus()
        bus.run_in_thread()
        skill_loader = SkillLoader(bus, dirname(dirname(__file__)))
        skill_loader.load()
        cls.skill = skill_loader.instance

        # Define a directory to use for testing
        cls.test_fs = join(dirname(__file__), "skill_fs")
        if not exists(cls.test_fs):
            mkdir(cls.test_fs)

        # Override the configuration and fs paths to use the test directory
        cls.skill._local_config = get_neon_local_config(cls.test_fs)
        cls.skill._user_config = get_neon_user_config(cls.test_fs)
        cls.skill.settings_write_path = cls.test_fs
        cls.skill.file_system.path = cls.test_fs
        cls.skill._init_settings()
        cls.skill.initialize()

        # Override speak and speak_dialog to test passed arguments
        cls.skill.speak = Mock()
        cls.skill.speak_dialog = Mock()

    def setUp(self):
        self.skill.speak.reset_mock()
        self.skill.speak_dialog.reset_mock()

    def test_00_skill_init(self):
        # Test any parameters expected to be set in init or initialize methods
        from neon_utils.skills.neon_skill import NeonSkill

        self.assertIsInstance(self.skill, NeonSkill)

    def test_handle_unit_change(self):
        test_profile = get_default_user_config()
        test_profile["user"]["username"] = "test_user"
        test_profile["units"]["measure"] = "imperial"
        test_message = Message("test", {"imperial": "imperial"},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        # imperial -> imperial
        self.skill.handle_unit_change(test_message)
        self.skill.speak_dialog.assert_called_once_with("units_already_set",
                                                        {"unit": "imperial"},
                                                        private=True)
        self.assertEqual(
            test_message.context["user_profiles"][0]["units"]["measure"],
            "imperial")
        # imperial -> metric
        test_message.data = {"metric": "metric"}
        self.skill.handle_unit_change(test_message)
        self.skill.speak_dialog.assert_called_with("units_changed",
                                                   {"unit": "metric"},
                                                   private=True)
        self.assertEqual(
            test_message.context["user_profiles"][0]["units"]["measure"],
            "metric")
        # metric -> metric
        self.skill.handle_unit_change(test_message)
        self.skill.speak_dialog.assert_called_with("units_already_set",
                                                   {"unit": "metric"},
                                                   private=True)
        self.assertEqual(
            test_message.context["user_profiles"][0]["units"]["measure"],
            "metric")
        # metric -> imperial
        test_message.data = {"imperial": "imperial"}
        self.skill.handle_unit_change(test_message)
        self.skill.speak_dialog.assert_called_with("units_changed",
                                                   {"unit": "imperial"},
                                                   private=True)
        self.assertEqual(
            test_message.context["user_profiles"][0]["units"]["measure"],
            "imperial")

    def test_handle_time_format_change(self):
        test_profile = get_default_user_config()
        test_profile["user"]["username"] = "test_user"
        test_profile["units"]["time"] = 12
        test_message = Message("test", {"half": "12 hour"},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        # 12 -> 12
        self.skill.handle_time_format_change(test_message)
        self.skill.speak_dialog.assert_called_once_with(
            "time_format_already_set", {"scale": "12"},  private=True)
        self.assertEqual(
            test_message.context["user_profiles"][0]["units"]["time"], 12)
        # 12 -> 24
        test_message.data = {"full": "24 hour"}
        self.skill.handle_time_format_change(test_message)
        self.skill.speak_dialog.assert_called_with("time_format_changed",
                                                   {"scale": "24"},
                                                   private=True)
        self.assertEqual(
            test_message.context["user_profiles"][0]["units"]["time"], 24)
        # 24 -> 24
        self.skill.handle_time_format_change(test_message)
        self.skill.speak_dialog.assert_called_with("time_format_already_set",
                                                   {"scale": "24"},
                                                   private=True)
        self.assertEqual(
            test_message.context["user_profiles"][0]["units"]["time"], 24)
        # 24 -> 12
        test_message.data = {"half": "half scale"}
        self.skill.handle_time_format_change(test_message)
        self.skill.speak_dialog.assert_called_with("time_format_changed",
                                                   {"scale": "12"},
                                                   private=True)
        self.assertEqual(
            test_message.context["user_profiles"][0]["units"]["time"], 12)

    def test_handle_speech_hesitation(self):
        test_profile = get_default_user_config()
        test_profile["user"]["username"] = "test_user"
        test_profile["response_mode"]["hesitation"] = True
        test_message = Message("test", {"permit": "enable"},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        # True -> True
        self.skill.handle_speak_hesitation(test_message)
        self.skill.speak_dialog.assert_called_once_with("hesitation_enabled",
                                                        private=True)
        self.assertTrue(test_message.context["user_profiles"][0]
                        ["response_mode"]["hesitation"])
        # True -> False
        test_message.data = {"deny": "disable"}
        self.skill.handle_speak_hesitation(test_message)
        self.skill.speak_dialog.assert_called_with("hesitation_disabled",
                                                   private=True)
        self.assertFalse(test_message.context["user_profiles"][0]
                         ["response_mode"]["hesitation"])
        # False -> False
        self.skill.handle_speak_hesitation(test_message)
        self.skill.speak_dialog.assert_called_with("hesitation_disabled",
                                                   private=True)
        self.assertFalse(test_message.context["user_profiles"][0]
                         ["response_mode"]["hesitation"])
        # False -> True
        test_message.data = {"permit": "enable"}
        self.skill.handle_speak_hesitation(test_message)
        self.skill.speak_dialog.assert_called_with("hesitation_enabled",
                                                   private=True)
        self.assertTrue(test_message.context["user_profiles"][0]
                        ["response_mode"]["hesitation"])

    def test_handle_transcription_retention(self):
        test_profile = get_default_user_config()
        test_profile["user"]["username"] = "test_user"
        test_profile["privacy"]["save_audio"] = True
        test_profile["privacy"]["save_text"] = True
        test_message = Message("test", {"permit": "enable",
                                        "audio": "recordings"},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        # Audio Recordings
        # Enable -> Enable
        self.skill.handle_transcription_retention(test_message)
        self.skill.speak_dialog.assert_called_with("transcription_already_set",
                                                   {"transcription": "audio",
                                                    "enabled": "enabled"},
                                                   private=True)
        self.assertTrue(test_message.context["user_profiles"][0]
                        ["privacy"]["save_audio"])
        # Enable -> Disable
        test_message.data = {"deny": "disable", "audio": "recording"}
        self.skill.handle_transcription_retention(test_message)
        self.skill.speak_dialog.assert_called_with("transcription_changed",
                                                   {"transcription": "audio",
                                                    "enabled": "disabled"},
                                                   private=True)
        self.assertFalse(test_message.context["user_profiles"][0]
                         ["privacy"]["save_audio"])
        # Disable -> Disable
        self.skill.handle_transcription_retention(test_message)
        self.skill.speak_dialog.assert_called_with("transcription_already_set",
                                                   {"transcription": "audio",
                                                    "enabled": "disabled"},
                                                   private=True)
        self.assertFalse(test_message.context["user_profiles"][0]
                         ["privacy"]["save_audio"])
        # Disable -> Enable
        test_message.data = {"permit": "enable", "audio": "recording"}
        self.skill.handle_transcription_retention(test_message)
        self.skill.speak_dialog.assert_called_with("transcription_changed",
                                                   {"transcription": "audio",
                                                    "enabled": "enabled"},
                                                   private=True)
        self.assertTrue(test_message.context["user_profiles"][0]
                        ["privacy"]["save_audio"])
        # Text Transcriptions
        # Enable -> Disable
        test_message.data = {"deny": "disable", "text": "transcription"}
        self.skill.handle_transcription_retention(test_message)
        self.skill.speak_dialog.assert_called_with("transcription_changed",
                                                   {"transcription": "text",
                                                    "enabled": "disabled"},
                                                   private=True)
        self.assertFalse(test_message.context["user_profiles"][0]
                         ["privacy"]["save_text"])
        # Disable -> Disable
        self.skill.handle_transcription_retention(test_message)
        self.skill.speak_dialog.assert_called_with("transcription_already_set",
                                                   {"transcription": "text",
                                                    "enabled": "disabled"},
                                                   private=True)
        self.assertFalse(test_message.context["user_profiles"][0]
                         ["privacy"]["save_text"])
        # Disable -> Enable
        test_message.data = {"permit": "allow", "text": "transcription"}
        self.skill.handle_transcription_retention(test_message)
        self.skill.speak_dialog.assert_called_with("transcription_changed",
                                                   {"transcription": "text",
                                                    "enabled": "enabled"},
                                                   private=True)
        self.assertTrue(test_message.context["user_profiles"][0]
                        ["privacy"]["save_text"])
        # Enable -> Enable
        self.skill.handle_transcription_retention(test_message)
        self.skill.speak_dialog.assert_called_with("transcription_already_set",
                                                   {"transcription": "text",
                                                    "enabled": "enabled"},
                                                   private=True)
        self.assertTrue(test_message.context["user_profiles"][0]
                        ["privacy"]["save_text"])

    def test_handle_speak_speed(self):
        test_profile = get_default_user_config()
        test_profile["user"]["username"] = "test_user"
        test_message = Message("test", {"faster": "faster"},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        self.assertEqual(test_profile["speech"]["speed_multiplier"], 1.0)

        # Speak faster
        self.skill.handle_speech_speed(test_message)
        self.skill.speak_dialog.assert_called_once_with("speech_speed_faster",
                                                        private=True)
        self.assertGreater(test_message.context["user_profiles"][0]
                           ["speech"]["speed_multiplier"], 1.0)
        # Speak max speed
        test_message.context["user_profiles"][0]["speech"][
            "speed_multiplier"] = self.skill.MAX_SPEECH_SPEED
        self.skill.handle_speech_speed(test_message)
        self.skill.speak_dialog.assert_called_with("speech_speed_limit",
                                                   {"limit": "faster"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["speech"]["speed_multiplier"],
                         self.skill.MAX_SPEECH_SPEED)
        # Speak normally
        test_message.data = {"normally": "normally"}
        self.skill.handle_speech_speed(test_message)
        self.skill.speak_dialog.assert_called_with("speech_speed_normal",
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["speech"]["speed_multiplier"], 1.0)
        # Speak slower
        test_message.data = {"slower": "slower"}
        self.skill.handle_speech_speed(test_message)
        self.skill.speak_dialog.assert_called_with("speech_speed_slower",
                                                   private=True)
        self.assertLess(test_message.context["user_profiles"][0]
                        ["speech"]["speed_multiplier"], 1.0)
        # Speak min speed
        test_message.context["user_profiles"][0]["speech"][
            "speed_multiplier"] = self.skill.MIN_SPEECH_SPEED
        self.skill.handle_speech_speed(test_message)
        self.skill.speak_dialog.assert_called_with("speech_speed_limit",
                                                   {"limit": "slower"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["speech"]["speed_multiplier"],
                         self.skill.MIN_SPEECH_SPEED)

    def test_handle_change_location_timezone(self):
        real_ask_yesno = self.skill.ask_yesno
        self.skill.ask_yesno = Mock(return_value="no")

        test_profile = get_default_user_config()
        test_profile["user"]["username"] = "test_user"
        test_message: Optional[Message] = None

        def _init_test_message(voc, location):
            nonlocal test_message
            test_message = Message("test", {voc: voc,
                                            "Place": location},
                                   {"username": "test_user",
                                    "user_profiles": [test_profile]})

        # Change location same tz
        _init_test_message("location", "new york")
        self.skill.handle_change_location_timezone(test_message)
        self.skill.ask_yesno.assert_called_once_with(
            "also_change_location_tz", {"type": "timezone", "new": "new york"})
        self.skill.speak_dialog.assert_called_once_with(
            "change_location_tz", {"type": "location", "location": "New York"},
            private=True)
        profile = test_message.context["user_profiles"][0]
        unchanged = ("tz", "utc", "country")
        for setting in unchanged:
            self.assertEqual(profile["location"][setting],
                             test_profile["location"][setting])
        self.assertEqual(profile["location"]["city"], "New York")
        self.assertEqual(profile["location"]["state"], "New York")
        self.assertEqual(profile["location"]["lat"], 40.7127281)
        self.assertEqual(profile["location"]["lng"], -74.0060152)
        self.skill.ask_yesno.reset_mock()
        self.skill.speak_dialog.reset_mock()

        # Change tz same location
        _init_test_message("timezone", "phoenix")
        self.skill.handle_change_location_timezone(test_message)
        self.skill.ask_yesno.assert_called_once_with(
            "also_change_location_tz", {"type": "location", "new": "phoenix"})
        self.skill.speak_dialog.assert_called_once_with(
            "change_location_tz", {"type": "timezone", "location": "UTC -7.0"},
            private=True)
        profile = test_message.context["user_profiles"][0]
        unchanged = ("city", "state", "country", "lat", "lng")
        for setting in unchanged:
            self.assertEqual(profile["location"][setting],
                             test_profile["location"][setting])
        self.assertEqual(profile["location"]["tz"], "America/Phoenix")
        self.assertEqual(profile["location"]["utc"], -7.0)
        self.skill.speak_dialog.reset_mock()
        self.skill.ask_yesno = Mock(return_value="yes")

        # Change location and tz
        _init_test_message("location", "honolulu")
        self.skill.handle_change_location_timezone(test_message)
        self.skill.ask_yesno.assert_called_once_with(
            "also_change_location_tz", {"type": "timezone", "new": "honolulu"})
        self.skill.speak_dialog.assert_has_calls((
            call("change_location_tz",
                 {"type": "location", "location": "Honolulu"}, private=True),
            call("change_location_tz",
                 {"type": "timezone", "location": "UTC -10.0"}, private=True)),
            True)

        profile = test_message.context["user_profiles"][0]
        unchanged = ("country",)
        for setting in unchanged:
            self.assertEqual(profile["location"][setting],
                             test_profile["location"][setting])
        self.assertEqual(profile["location"]["city"], "Honolulu")
        self.assertEqual(profile["location"]["state"], "Hawaii")
        self.assertEqual(profile["location"]["lat"], 21.2890997)
        self.assertEqual(profile["location"]["lng"], -157.717299)
        self.assertEqual(profile["location"]["tz"], "Pacific/Honolulu")
        self.assertEqual(profile["location"]["utc"], -10.0)

        self.skill.speak_dialog.reset_mock()
        self.skill.ask_yesno.reset_mock()

        # Change tz and location
        _init_test_message("timezone", "phoenix")
        self.skill.handle_change_location_timezone(test_message)
        self.skill.ask_yesno.assert_called_once_with(
            "also_change_location_tz", {"type": "location", "new": "phoenix"})

        self.skill.speak_dialog.assert_has_calls((
            call("change_location_tz",
                 {"type": "location", "location": "Phoenix"}, private=True),
            call("change_location_tz",
                 {"type": "timezone", "location": "UTC -7.0"}, private=True)),
            True)

        profile = test_message.context["user_profiles"][0]
        unchanged = ("country",)
        for setting in unchanged:
            self.assertEqual(profile["location"][setting],
                             test_profile["location"][setting])

        self.assertEqual(profile["location"]["city"], "Phoenix")
        self.assertEqual(profile["location"]["state"], "Arizona")
        self.assertEqual(profile["location"]["lat"], 33.4484367)
        self.assertEqual(profile["location"]["lng"], -112.074141)
        self.assertEqual(profile["location"]["tz"], "America/Phoenix")
        self.assertEqual(profile["location"]["utc"], -7.0)

        self.skill.ask_yesno = real_ask_yesno

    def test_handle_change_dialog_option(self):
        test_profile = get_default_user_config()
        test_profile["user"]["username"] = "test_user"
        test_message = Message("test", {"limited": "limited"},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        test_profile["response_mode"]["limit_dialog"] = False

        # random -> limited
        self.skill.handle_change_dialog_mode(test_message)
        self.assertTrue(test_message.context["user_profiles"][0]
                        ["response_mode"]["limit_dialog"])
        self.skill.speak_dialog.assert_called_with("dialog_mode_changed",
                                                   {"response": "limited"},
                                                   private=True)
        # limited -> limited
        self.skill.handle_change_dialog_mode(test_message)
        self.assertTrue(test_message.context["user_profiles"][0]
                        ["response_mode"]["limit_dialog"])
        self.skill.speak_dialog.assert_called_with("dialog_mode_already_set",
                                                   {"response": "limited"},
                                                   private=True)
        test_message.data = {"random": "standard"}
        # limited -> random
        self.skill.handle_change_dialog_mode(test_message)
        self.assertFalse(test_message.context["user_profiles"][0]
                         ["response_mode"]["limit_dialog"])
        self.skill.speak_dialog.assert_called_with("dialog_mode_changed",
                                                   {"response": "random"},
                                                   private=True)
        # random -> random
        self.skill.handle_change_dialog_mode(test_message)
        self.assertFalse(test_message.context["user_profiles"][0]
                         ["response_mode"]["limit_dialog"])
        self.skill.speak_dialog.assert_called_with("dialog_mode_already_set",
                                                   {"response": "random"},
                                                   private=True)

    def test_get_timezone_from_location(self):
        name, offset = \
            self.skill._get_timezone_from_location(
                self.skill._get_location_from_spoken_location("seattle"))
        self.assertEqual(name, "America/Los_Angeles")
        self.assertIsInstance(offset, float)

        timezone = \
            self.skill._get_timezone_from_location(
                self.skill._get_location_from_spoken_location(
                    "non-existent place"))
        self.assertIsNone(timezone)

    def test_get_location_from_spoken_location(self):
        address = self.skill._get_location_from_spoken_location("seattle")
        self.assertEqual(address['address']['city'], "Seattle")
        self.assertEqual(address['address']['state'], "Washington")
        self.assertEqual(address['address']['country'], "United States")
        self.assertIsInstance(address['lat'], str)
        self.assertIsInstance(address['lon'], str)

        address = self.skill._get_location_from_spoken_location("kyiv",
                                                                "en-us")
        self.assertEqual(address['address']['city'], "Kyiv")
        self.assertEqual(address['address']['country'], "Ukraine")
        self.assertIsInstance(address['lat'], str)
        self.assertIsInstance(address['lon'], str)

        address = self.skill._get_location_from_spoken_location(
            "kirkland washington")
        self.assertEqual(address['address']['city'], "Kirkland")
        self.assertEqual(address['address']['state'], "Washington")
        self.assertEqual(address['address']['country'], "United States")
        self.assertIsInstance(address['lat'], str)
        self.assertIsInstance(address['lon'], str)


if __name__ == '__main__':
    unittest.main()
