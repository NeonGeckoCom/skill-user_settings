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

import os
import shutil
import unittest

from copy import deepcopy
from datetime import datetime
from os import mkdir
from os.path import dirname, join, exists
from typing import Optional

import mock
from dateutil.tz import gettz
from mock import Mock
from mock.mock import call
from neon_utils.user_utils import get_user_prefs
from neon_utils.language_utils import SupportedLanguages
from ovos_utils.messagebus import FakeBus
from mycroft_bus_client import Message

from mycroft.skills.skill_loader import SkillLoader


class TestSkill(unittest.TestCase):
    test_message = Message("test", {}, {"neon_in_request": True})
    default_config = deepcopy(get_user_prefs())

    @classmethod
    @mock.patch('neon_utils.language_utils.get_supported_languages')
    def setUpClass(cls, get_langs) -> None:
        get_langs.return_value = SupportedLanguages({'en'}, {'en'}, {'en'})
        # Define a directory to use for testing
        cls.test_fs = join(dirname(__file__), "skill_fs")
        if not exists(cls.test_fs):
            mkdir(cls.test_fs)
        os.environ["NEON_CONFIG_PATH"] = cls.test_fs

        bus = FakeBus()
        bus.run_in_thread()
        skill_loader = SkillLoader(bus, dirname(dirname(__file__)))
        skill_loader.load()
        cls.skill = skill_loader.instance

        # Override the configuration and fs paths to use the test directory
        cls.skill.settings_write_path = cls.test_fs
        cls.skill.file_system.path = cls.test_fs
        cls.skill._init_settings()
        cls.skill.initialize()

        # Override speak and speak_dialog to test passed arguments
        cls.skill.speak = Mock()
        cls.skill.speak_dialog = Mock()

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.test_fs)

    def setUp(self):
        self.skill.speak.reset_mock()
        self.skill.speak_dialog.reset_mock()
        self.user_config = deepcopy(self.default_config)

    def test_00_skill_init(self):
        # Test any parameters expected to be set in init or initialize methods
        from neon_utils.skills.neon_skill import NeonSkill

        self.assertIsInstance(self.skill, NeonSkill)

    def test_stt_languages(self):
        real_languages = self.skill._languages
        # Languages Specified
        self.skill._languages = SupportedLanguages({'en', 'es', 'uk'},
                                                   {}, {'en', 'uk', 'pl'})
        self.assertEqual(self.skill.stt_languages, {'en', 'uk'})

        # Languages not Specified
        self.skill._languages = SupportedLanguages({}, {}, {'en', 'uk', 'pl'})
        self.assertIsNone(self.skill.stt_languages)

        self.skill._languages = real_languages

    def test_tts_languages(self):
        real_languages = self.skill._languages
        # Languages Specified
        self.skill._languages = SupportedLanguages({}, {'en', 'es', 'uk'},
                                                   {'en', 'uk', 'pl'})
        self.assertEqual(self.skill.tts_languages, {'en', 'uk'})

        # Languages not Specified
        self.skill._languages = SupportedLanguages({}, {'en', 'es', 'uk'}, {})
        self.assertIsNone(self.skill.tts_languages)

        self.skill._languages = real_languages

    def test_handle_unit_change(self):
        test_profile = self.user_config
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
        test_profile = self.user_config
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
        test_profile = self.user_config
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
        test_profile = self.user_config
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
        test_profile = self.user_config
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

        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_message: Optional[Message] = None

        def _init_test_message(voc, location):
            nonlocal test_message
            test_message = Message("test", {voc: voc,
                                            "rx_place": location},
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
        self.assertAlmostEqual(profile["location"]["lat"], 21.2890997, 0)
        self.assertAlmostEqual(profile["location"]["lng"], -157.717299, 0)
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
        test_profile = self.user_config
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

    def test_handle_say_my_name(self):
        test_profile = self.user_config
        test_message = Message("test", {},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})

        # No name set
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with("name_not_known",
                                                   {"name_position": "name"},
                                                   private=True)

        test_message.context["user_profiles"][0]["user"]["username"] = \
            "test_user"
        # first name not known
        test_message.data['utterance'] = "tell me my first name"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_not_known", {"name_position": "first name"}, private=True)
        # middle name not known
        test_message.data['utterance'] = "tell me my middle name"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_not_known", {"name_position": "middle name"}, private=True)
        # last name not known
        test_message.data['utterance'] = "tell me my last name"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_not_known", {"name_position": "last name"}, private=True)
        # preferred name not known
        test_message.data['utterance'] = "tell me my nick name"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_not_known", {"name_position": "preferred name"}, private=True)

        # name username set
        test_message.data['utterance'] = "tell me my name"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_is", {"name_position": "name",
                        "name": "test_user"}, private=True)

        # name first name set
        test_message.context["user_profiles"][0]["user"]["first_name"] = \
            "First"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_is", {"name_position": "name",
                        "name": "First"}, private=True)

        # name preferred name set
        test_message.context["user_profiles"][0]["user"]["preferred_name"] = \
            "Preferred"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_is", {"name_position": "name",
                        "name": "Preferred"}, private=True)

        test_message.context["user_profiles"][0]["user"]["middle_name"] = \
            "Middle"
        test_message.context["user_profiles"][0]["user"]["last_name"] = \
            "Last"

        # request first name
        test_message.data['utterance'] = "tell me my first name"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_is", {"name_position": "first name",
                        "name": "First"}, private=True)
        # request middle name
        test_message.data['utterance'] = "tell me my middle name"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_is", {"name_position": "middle name",
                        "name": "Middle"}, private=True)
        # request last name
        test_message.data['utterance'] = "tell me my last name"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_is", {"name_position": "last name",
                        "name": "Last"}, private=True)

        # request preferred name
        test_message.data['utterance'] = "tell me my preferred name"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_is", {"name_position": "preferred name",
                        "name": "Preferred"}, private=True)

        # request username
        test_message.data['utterance'] = "tell me my username"
        self.skill.handle_say_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_is", {"name_position": "username",
                        "name": "test_user"}, private=True)

    def test_handle_say_my_email(self):
        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_message = Message("test", {},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        self.assertFalse(test_profile["user"]["email"])
        self.skill.handle_say_my_email(test_message)
        self.skill.speak_dialog.assert_called_with("email_not_known",
                                                   private=True)
        test_message.context["user_profiles"][0]["user"]["email"] = \
            "test@neon.ai"
        self.skill.handle_say_my_email(test_message)
        self.skill.speak_dialog.assert_called_with("email_is",
                                                   {"email": "test@neon.ai"},
                                                   private=True)

    def test_handle_say_my_location(self):
        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_message = Message("test", {},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        self.skill.handle_say_my_location(test_message)
        self.skill.speak_dialog.assert_called_with(
            "location_is", {"location": "Renton, Washington"}, private=True)

        test_message.context['user_profiles'][0]['location']['city'] = "Kyiv"
        test_message.context['user_profiles'][0]['location']['state'] = ""
        test_message.context['user_profiles'][0]['location']['country'] = \
            "Ukraine"
        self.skill.handle_say_my_location(test_message)
        self.skill.speak_dialog.assert_called_with(
            "location_is", {"location": "Kyiv, Ukraine"}, private=True)

    def test_handle_set_my_birthday(self):
        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_message = Message("test", {"utterance": "my birthday is today"},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        self.skill.handle_set_my_birthday(test_message)
        today = datetime.now(gettz(test_profile["location"]["tz"]))
        self.skill.speak_dialog.assert_has_calls((
            call("birthday_confirmed", {"birthday": today.strftime("%B %-d")},
                 private=True),
            call("happy_birthday", private=True)
        ), True)

        test_message.data['utterance'] = "my birthday is september 9"
        self.skill.handle_set_my_birthday(test_message)
        self.skill.speak_dialog.assert_called_with("birthday_confirmed",
                                                   {"birthday": "September 9"},
                                                   private=True)

    def test_handle_set_my_email(self):
        real_ask_yesno = self.skill.ask_yesno
        self.skill.ask_yesno = Mock(return_value="no")
        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_message = Message("test", {},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})

        def _check_not_confirmed(msg):
            self.skill.handle_set_my_email(msg)
            self.skill.ask_yesno.assert_called_once_with(
                "email_confirmation", {"email": "test@neon.ai"})
            self.skill.speak_dialog.assert_called_once_with(
                "email_not_confirmed", private=True)
            self.skill.ask_yesno.reset_mock()
            self.skill.speak_dialog.reset_mock()

        # Typed input
        test_message.data["utterance"] = "my email address is test@neon.ai"
        test_message.data["rx_setting"] = "test@neon . "
        _check_not_confirmed(test_message)

        # Spoken input recognized domain
        test_message.data["utterance"] = "my email address is test at neon.ai"
        test_message.data["rx_setting"] = "test at neon ."
        _check_not_confirmed(test_message)

        # Spoken input unrecognized domain
        test_message.data["utterance"] = "my email is test at neon dot ai"
        test_message.data["rx_setting"] = "test at neon dot ai"
        _check_not_confirmed(test_message)

        # Invalid address
        test_message.data["utterance"] = "my email address is test at neon ai"
        test_message.data["rx_setting"] = "test at neon ai"
        self.skill.handle_set_my_email(test_message)
        self.skill.speak_dialog.assert_called_once_with(
            "email_set_error", private=True)
        self.skill.speak_dialog.reset_mock()

        # Set Email Confirmed
        test_message.data["utterance"] = "my email is test at neon dot ai"
        test_message.data["rx_setting"] = "test at neon dot ai"
        self.skill.ask_yesno = Mock(return_value="yes")
        self.skill.handle_set_my_email(test_message)
        self.skill.ask_yesno.assert_called_with("email_confirmation",
                                                {"email": "test@neon.ai"})
        self.skill.speak_dialog.assert_called_with("email_set",
                                                   {"email": "test@neon.ai"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["email"], "test@neon.ai")
        # Set Email No Change
        self.skill.handle_set_my_email(test_message)
        self.skill.speak_dialog.assert_called_with("email_already_set_same",
                                                   {"email": "test@neon.ai"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["email"], "test@neon.ai")
        # Change Email Not Confirmed
        self.skill.ask_yesno = Mock(return_value="no")
        test_message.data["utterance"] = "my email is demo at neon dot ai"
        test_message.data["rx_setting"] = "demo at neon dot ai"
        self.skill.handle_set_my_email(test_message)
        self.skill.ask_yesno.assert_called_with("email_overwrite",
                                                {"old": "test@neon.ai",
                                                 "new": "demo@neon.ai"})
        self.skill.speak_dialog.assert_called_with("email_not_changed",
                                                   {"email": "test@neon.ai"},
                                                   private=True)
        # Change Email Confirmed
        self.skill.ask_yesno = Mock(return_value="yes")
        self.skill.handle_set_my_email(test_message)
        self.skill.ask_yesno.assert_called_with("email_overwrite",
                                                {"old": "test@neon.ai",
                                                 "new": "demo@neon.ai"})
        self.skill.speak_dialog.assert_called_with("email_set",
                                                   {"email": "demo@neon.ai"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["email"], "demo@neon.ai")

        self.skill.ask_yesno = real_ask_yesno

    def test_handle_set_my_name(self):
        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_message = Message("test", {},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})

        # Set first name
        test_message.data["utterance"] = "my first name is daniel"
        test_message.data["rx_setting"] = "daniel"
        self.skill.handle_set_my_name(test_message)
        self.skill.speak_dialog.assert_called_with("name_set_part",
                                                   {"position": "first name",
                                                    "name": "Daniel"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["first_name"], "Daniel")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["full_name"], "Daniel")
        # Set middle name
        test_message.data["utterance"] = "my middle name is james"
        test_message.data["rx_setting"] = "james"
        self.skill.handle_set_my_name(test_message)
        self.skill.speak_dialog.assert_called_with("name_set_part",
                                                   {"position": "middle name",
                                                    "name": "James"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["middle_name"], "James")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["full_name"], "Daniel James")
        # Set last name
        test_message.data["utterance"] = "my last name is McKnight"
        test_message.data["rx_setting"] = "McKnight"
        self.skill.handle_set_my_name(test_message)
        self.skill.speak_dialog.assert_called_with("name_set_part",
                                                   {"position": "last name",
                                                    "name": "Mcknight"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["last_name"], "Mcknight")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["full_name"], "Daniel James Mcknight")
        # Set preferred name
        test_message.data["utterance"] = "my preferred name is Dan"
        test_message.data["rx_setting"] = "Dan"
        self.skill.handle_set_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_set_part",
            {"position": "preferred name", "name": "Dan"}, private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["preferred_name"], "Dan")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["full_name"], "Daniel James Mcknight")
        # Set preferred name unchanged
        self.skill.handle_set_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_not_changed",
            {"position": "preferred name", "name": "Dan"}, private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["preferred_name"], "Dan")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["full_name"], "Daniel James Mcknight")
        # Set full name no change
        test_message.data["utterance"] = "my name is Daniel James McKnight"
        test_message.data["rx_setting"] = "Daniel James McKnight"
        self.skill.handle_set_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_not_changed", {"position": "name",
                                 "name": "Daniel James Mcknight"})
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["full_name"], "Daniel James Mcknight")
        # Set full name 1 first changed
        test_message.data["utterance"] = "my name is test"
        test_message.data["rx_setting"] = "test"
        self.skill.handle_set_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_set_full", {"nick": "Dan", "name": "Test James Mcknight"},
            private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["full_name"], "Test James Mcknight")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["first_name"], "Test")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["preferred_name"], "Dan")
        # Set full name 2 last changed
        test_message.data["utterance"] = "my name is test this user"
        test_message.data["rx_setting"] = "test this user"
        self.skill.handle_set_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_set_full", {"nick": "Dan", "name": "Test This User"},
            private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["full_name"], "Test This User")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["middle_name"], "This")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["last_name"], "User")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["preferred_name"], "Dan")
        # Set full name 4
        test_message.data["utterance"] = "my name is test this user again"
        test_message.data["rx_setting"] = "test this user again"
        self.skill.handle_set_my_name(test_message)
        self.skill.speak_dialog.assert_called_with(
            "name_set_full", {"nick": "Dan", "name": "Test This User Again"},
            private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["full_name"], "Test This User Again")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["middle_name"], "This")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["last_name"], "User Again")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["user"]["preferred_name"], "Dan")

    def test_handle_say_my_language_settings(self):
        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_profile["speech"]["tts_language"] = "en-us"
        test_profile["speech"]["tts_gender"] = "female"
        test_message = Message("test", {},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        # Only one lang
        self.skill.handle_say_my_language_settings(test_message)
        self.skill.speak_dialog.assert_called_once_with(
            "language_setting", {"primary": "primary",
                                 "language": "American English",
                                 "gender": "female"}, private=True)
        # Two diff langs
        test_message.context["user_profiles"][0][
            "speech"]["secondary_tts_language"] = "uk-ua"
        self.skill.speak_dialog.reset_mock()
        self.skill.handle_say_my_language_settings(test_message)
        self.skill.speak_dialog.assert_has_calls((
            call("language_setting", {"primary": "primary",
                                      "language": "American English",
                                      "gender": "female"}, private=True),
            call("language_setting", {"primary": "secondary",
                                      "language": "Ukrainian",
                                      "gender": "male"}, private=True)
        ))
        # Two langs same gender
        test_message.context["user_profiles"][0][
            "speech"]["secondary_tts_gender"] = "female"
        self.skill.speak_dialog.reset_mock()
        self.skill.handle_say_my_language_settings(test_message)
        self.skill.speak_dialog.assert_has_calls((
            call("language_setting", {"primary": "primary",
                                      "language": "American English",
                                      "gender": "female"}, private=True),
            call("language_setting", {"primary": "secondary",
                                      "language": "Ukrainian",
                                      "gender": "female"}, private=True)
        ))
        # One lang diff gender
        test_message.context["user_profiles"][0][
            "speech"]["secondary_tts_gender"] = "male"
        test_message.context["user_profiles"][0][
            "speech"]["secondary_tts_language"] = "en-us"
        self.skill.speak_dialog.reset_mock()
        self.skill.handle_say_my_language_settings(test_message)
        self.skill.speak_dialog.assert_has_calls((
            call("language_setting", {"primary": "primary",
                                      "language": "American English",
                                      "gender": "female"}, private=True),
            call("language_setting", {"primary": "secondary",
                                      "language": "American English",
                                      "gender": "male"}, private=True)
        ))

    def test_handle_set_stt_language(self):
        real_ask_yesno = self.skill.ask_yesno
        real_supported_languages = self.skill._languages
        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_profile["speech"]["stt_language"] = "en-us"
        test_message = Message("test", {"rx_language": "something"},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        # Invalid lang
        self.skill.handle_set_stt_language(test_message)
        self.skill.speak_dialog.assert_called_with("language_not_recognized",
                                                   {"lang": "something"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["speech"]["stt_language"], "en-us")

        # Same lang
        test_message.data["rx_language"] = "english"
        self.skill.handle_set_stt_language(test_message)
        self.skill.speak_dialog.assert_called_with(
            "language_not_changed", {"io": "speech to text",
                                     "lang": "American English"},
            private=True)

        # Change lang unsupported
        test_message.data["rx_language"] = "ukrainian"
        self.skill.handle_set_stt_language(test_message)
        self.skill.speak_dialog.assert_called_with("language_not_supported",
                                                   {"io": "understand",
                                                    "lang": "Ukrainian"},
                                                   private=True)

        # Mock supported STT langs
        self.skill._languages = SupportedLanguages({'uk'}, {}, {'uk'})

        # Change lang unconfirmed
        self.skill.ask_yesno = Mock(return_value=False)
        self.skill.handle_set_stt_language(test_message)
        self.skill.ask_yesno.assert_called_once_with(
            "language_change_confirmation", {"io": "speech to text",
                                             "lang": "Ukrainian"})
        self.skill.speak_dialog.assert_called_with("language_not_confirmed",
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["speech"]["stt_language"], "en-us")

        # Change lang confirmed
        self.skill.ask_yesno = Mock(return_value="yes")
        self.skill.handle_set_stt_language(test_message)
        self.skill.ask_yesno.assert_called_once_with(
            "language_change_confirmation", {"io": "speech to text",
                                             "lang": "Ukrainian"})
        self.skill.speak_dialog.assert_called_with("language_set",
                                                   {"io": "speech to text",
                                                    "lang": "Ukrainian"},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["speech"]["stt_language"], "uk-ua")

        self.skill.ask_yesno = real_ask_yesno
        self.skill._languages = real_supported_languages

    def test_handle_set_tts_language(self):
        real_supported_languages = self.skill._languages
        self.skill._languages = SupportedLanguages({}, {'it', 'ja', 'de', 'uk',
                                                        'pl', 'fr', 'es', 'bg',
                                                        'en'},
                                                   {'it', 'ja', 'de', 'uk',
                                                        'pl', 'fr', 'es',
                                                        'en'})

        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_message = Message("test", {},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        # Change TTS language
        test_message.data = {"utterance": "Change my TTS language to spanish",
                             "rx_language": "spanish"}
        self.skill.handle_set_tts_language(test_message)
        self.skill.speak_dialog.assert_called_with(
            "language_set", {"io": "primary", "lang": "Spanish"}, private=True)
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_language"], "es-es")
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_gender"], test_profile["speech"]["tts_gender"])
        # Change Primary TTS language
        test_message.data = {"utterance": "Change my Primary TTS language "
                                          "to french",
                             "rx_language": "french"}
        self.skill.handle_set_tts_language(test_message)
        self.skill.speak_dialog.assert_called_with(
            "language_set", {"io": "primary", "lang": "French"}, private=True)
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_language"], "fr-fr")
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_gender"], test_profile["speech"]["tts_gender"])
        # Change Secondary TTS language
        test_message.data = {"utterance": "Change my secondary TTS language "
                                          "to female Polish"}
        self.skill.handle_set_tts_language(test_message)
        self.skill.speak_dialog.assert_called_with(
            "language_set", {"io": "secondary", "lang": "Polish"},
            private=True)
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["secondary_tts_language"], "pl-pl")
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["secondary_tts_gender"], "female")
        # Talk to me
        test_message.data = {"utterance": "Talk to me in Ukrainian",
                             "rx_language": "Ukrainian"}
        self.skill.handle_set_tts_language(test_message)
        self.skill.speak_dialog.assert_called_with(
            "language_set", {"io": "primary", "lang": "Ukrainian"},
            private=True)
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_language"], "uk-ua")
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_gender"], test_profile["speech"]["tts_gender"])
        # Change primary and secondary
        test_message.data = {"utterance": "Change my primary language to "
                                          "English and my secondary language "
                                          "to German"}
        self.skill.speak_dialog.reset_mock()
        self.skill.handle_set_tts_language(test_message)
        self.skill.speak_dialog.assert_has_calls((
            call("language_set",
                 {"io": "primary", "lang": "American English"}, private=True),
            call("language_set",
                 {"io": "secondary", "lang": "German"}, private=True)
        ))
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_language"], "en-us")
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["secondary_tts_language"], "de-de")
        # Change primary language invalid and secondary language valid
        test_message.data = {"utterance": "Change my primary language to "
                                          "nothing and my second language "
                                          "to Italian"}
        self.skill.speak_dialog.reset_mock()
        self.skill.handle_set_tts_language(test_message)
        self.skill.speak_dialog.assert_has_calls((
            call("language_not_recognized",
                 {"lang": "nothing"}, private=True),
            call("language_set",
                 {"io": "secondary", "lang": "Italian"}, private=True)
        ))
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_language"], "en-us")
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["secondary_tts_language"], "it-it")

        # Change primary language valid and second language invalid
        test_message.data = {"utterance": "Change my primary language to "
                                          "Japanese and my second language "
                                          "to something"}
        self.skill.speak_dialog.reset_mock()
        self.skill.handle_set_tts_language(test_message)
        self.skill.speak_dialog.assert_has_calls((
            call("language_set",
                 {"io": "primary", "lang": "Japanese"}, private=True),
            call("language_not_recognized",
                 {"lang": "something"}, private=True)

        ))
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_language"], "ja-jp")
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["secondary_tts_language"], "it-it")

        # Change TTS language invalid
        test_message.data = {"utterance": "Change my text to speech language"}
        self.skill.handle_set_tts_language(test_message)
        self.skill.speak_dialog.assert_called_with("language_not_heard",
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_language"], "ja-jp")
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["secondary_tts_language"], "it-it")

        # Change TTS language unsupported
        test_message.data = {"utterance": "Change my text to speech language"
                                          "to bulgarian",
                             'rx_language': 'bulgarian'}
        self.skill.handle_set_tts_language(test_message)
        self.skill.speak_dialog.assert_called_with("language_not_supported",
                                                   {'io': 'speak',
                                                    'lang': 'Bulgarian'},
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["tts_language"], "ja-jp")
        self.assertEqual(test_message.context["user_profiles"][0]["speech"]
                         ["secondary_tts_language"], "it-it")

        self.skill._languages = real_supported_languages

    def test_handle_set_language(self):
        real_set_stt_language = self.skill.handle_set_stt_language
        real_set_tts_language = self.skill.handle_set_tts_language
        self.skill.handle_set_stt_language = Mock()
        self.skill.handle_set_tts_language = Mock()

        # stt request
        stt_message = Message("test",
                              {"utterance": "set my language speech to text"})
        self.skill.handle_set_language(stt_message)
        self.skill.handle_set_stt_language.assert_called_once_with(stt_message)
        # tts request
        tts_message = Message("test",
                              {"utterance": "set my language text to speech"})
        self.skill.handle_set_language(tts_message)
        self.skill.handle_set_tts_language.assert_called_once_with(tts_message)

        # Unspecified request
        test_message = Message("test",
                               {"utterance": "set my language to spanish",
                                "rx_language": "spanish"})
        self.skill.handle_set_language(test_message)
        self.skill.handle_set_stt_language.assert_called_with(test_message)
        self.skill.handle_set_tts_language.assert_called_with(test_message)

        # Unspecified STT not changed
        self.skill.handle_set_stt_language.reset_mock()
        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_profile["speech"]["stt_language"] = "en-us"
        test_message = Message("test", {"Language": "American English"},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        self.skill.handle_set_language(test_message)
        self.skill.handle_set_tts_language.assert_called_with(test_message)
        self.skill.handle_set_stt_language.assert_not_called()

        self.skill.handle_set_stt_language = real_set_stt_language
        self.skill.handle_set_tts_language = real_set_tts_language

    def test_handle_no_secondary_language(self):
        test_profile = self.user_config
        test_profile["user"]["username"] = "test_user"
        test_profile["speech"]["secondary_tts_language"] = "es-es"
        test_message = Message("test", {},
                               {"username": "test_user",
                                "user_profiles": [test_profile]})
        self.skill.handle_no_secondary_language(test_message)
        self.skill.speak_dialog.assert_called_once_with("only_one_language",
                                                        private=True)
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["speech"]["secondary_tts_language"], "")
        self.assertEqual(test_message.context["user_profiles"][0]
                         ["speech"]["secondary_neon_voice"], "")
        profile = deepcopy(test_message.context["user_profiles"][0])

        self.skill.handle_no_secondary_language(test_message)
        self.skill.speak_dialog.assert_called_with("only_one_language",
                                                   private=True)
        self.assertEqual(test_message.context["user_profiles"][0], profile)

    def test_get_name_parts(self):
        user_profile = self.user_config
        # First none existing
        name = self.skill._get_name_parts("first", user_profile["user"])
        self.assertEqual(name, {"first_name": "first",
                                "full_name": "first"})

        # First and Last override First, existing Middle
        user_profile["user"]["first_name"] = "old"
        user_profile["user"]["middle_name"] = "middle"
        name = self.skill._get_name_parts("first last", user_profile["user"])
        self.assertEqual(name, {"first_name": "first",
                                "last_name": "last",
                                "full_name": "first middle last"})
        # First Middle Last override existing
        user_profile["user"]["first_name"] = "old"
        user_profile["user"]["middle_name"] = "old"
        user_profile["user"]["last_name"] = "old"
        name = self.skill._get_name_parts("first middle last",
                                          user_profile["user"])
        self.assertEqual(name, {"first_name": "first",
                                "middle_name": "middle",
                                "last_name": "last",
                                "full_name": "first middle last"})
        # Longer name override existing
        name = self.skill._get_name_parts("first-name middle last senior",
                                          user_profile["user"])
        self.assertEqual(name, {"first_name": "first-name",
                                "middle_name": "middle",
                                "last_name": "last senior",
                                "full_name": "first-name middle last senior"})

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

    def test_parse_languages(self):
        self.assertEqual((None, None),
                         self.skill._parse_languages(
                             "change my language to french"))
        self.assertEqual(("australian english", None),
                         self.skill._parse_languages(
                             "change my primary language to australian "
                             "english"))
        self.assertEqual(("australian english", "mexican spanish"),
                         self.skill._parse_languages(
                             "change my primary language to australian "
                             "english and my second language to "
                             "mexican spanish"))

    def test_get_lang_name_and_code(self):
        from lingua_franca.internal import UnsupportedLanguageError
        # Check all the Coqui TTS Supported Languages
        self.assertEqual(("en-us", "American English"),
                         self.skill._get_lang_code_and_name("english"))
        self.assertEqual(("es-es", "Spanish"),
                         self.skill._get_lang_code_and_name("spanish"))
        self.assertEqual(("fr-fr", "French"),
                         self.skill._get_lang_code_and_name("french"))
        self.assertEqual(("de-de", "German"),
                         self.skill._get_lang_code_and_name("german"))
        self.assertEqual(("it-it", "Italian"),
                         self.skill._get_lang_code_and_name("italian"))
        self.assertEqual(("pl-pl", "Polish"),
                         self.skill._get_lang_code_and_name("polish"))
        self.assertEqual(("uk-ua", "Ukrainian"),
                         self.skill._get_lang_code_and_name("ukrainian"))
        self.assertEqual(("ro-ro", "Romanian"),
                         self.skill._get_lang_code_and_name("romanian"))
        self.assertEqual(("hu-hu", "Hungarian"),
                         self.skill._get_lang_code_and_name("hungarian"))
        self.assertEqual(("el-gr", "Greek"),
                         self.skill._get_lang_code_and_name("greek"))
        self.assertEqual(("sv-se", "Swedish"),
                         self.skill._get_lang_code_and_name("swedish"))
        self.assertEqual(("bg-bg", "Bulgarian"),
                         self.skill._get_lang_code_and_name("bulgarian"))
        self.assertEqual(("nl-nl", "Dutch"),
                         self.skill._get_lang_code_and_name("dutch"))
        self.assertEqual(("fi-fi", "Finnish"),
                         self.skill._get_lang_code_and_name("finnish"))
        self.assertEqual(("sl-si", "Slovenian"),
                         self.skill._get_lang_code_and_name("slovenian"))
        self.assertEqual(("lv-lv", "Latvian"),
                         self.skill._get_lang_code_and_name("latvian"))
        self.assertEqual(("et-ee", "Estonian"),
                         self.skill._get_lang_code_and_name("estonian"))
        self.assertEqual(("ga-ie", "Irish"),
                         self.skill._get_lang_code_and_name("irish"))

        # Check LibreTranslate supported languages
        self.assertEqual(("ar-sa", "Arabic"),
                         self.skill._get_lang_code_and_name("arabic"))
        self.assertEqual(("az-az", "Azerbaijani"),
                         self.skill._get_lang_code_and_name("azerbaijani"))
        self.assertEqual(("zh-zh", "Chinese"),
                         self.skill._get_lang_code_and_name("chinese"))
        self.assertEqual(("cs-cz", "Czech"),
                         self.skill._get_lang_code_and_name("czech"))
        self.assertEqual(("da-dk", "Danish"),
                         self.skill._get_lang_code_and_name("danish"))
        # self.assertEqual(("eo", "Esperanto"),
        #                  self.skill._get_lang_code_and_name("esperanto"))
        # self.assertEqual(("he-il", "Hebrew"),
        #                  self.skill._get_lang_code_and_name("hebrew"))
        self.assertEqual(("hi-in", "Hindi"),
                         self.skill._get_lang_code_and_name("hindi"))
        self.assertEqual(("id-id", "Indonesian"),
                         self.skill._get_lang_code_and_name("indonesian"))
        self.assertEqual(("ja-jp", "Japanese"),
                         self.skill._get_lang_code_and_name("japanese"))
        self.assertEqual(("ko-kr", "Korean"),
                         self.skill._get_lang_code_and_name("korean"))
        self.assertEqual(("fa-ir", "Persian"),
                         self.skill._get_lang_code_and_name("persian"))
        self.assertEqual(("pt-pt", "Portuguese"),
                         self.skill._get_lang_code_and_name("portuguese"))
        self.assertEqual(("ru-ru", "Russian"),
                         self.skill._get_lang_code_and_name("russian"))
        self.assertEqual(("sk-sk", "Slovak"),
                         self.skill._get_lang_code_and_name("slovak"))
        self.assertEqual(("tr-tr", "Turkish"),
                         self.skill._get_lang_code_and_name("turkish"))
        # Check manually specified alternative language requests
        self.assertEqual(("ga-ie", "Irish"),
                         self.skill._get_lang_code_and_name("gaelic"))
        self.assertEqual(("en-au", "English"),
                         self.skill._get_lang_code_and_name(
                             "australian english"))
        self.assertEqual(("fa-ir", "Persian"),
                         self.skill._get_lang_code_and_name("farsi"))
        with self.assertRaises(UnsupportedLanguageError):
            self.skill._get_lang_code_and_name("nothing")


if __name__ == '__main__':
    unittest.main()
