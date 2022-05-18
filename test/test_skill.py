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

from copy import deepcopy
from os import mkdir
from os.path import dirname, join, exists
from mock import Mock
from neon_utils.user_utils import get_default_user_config
from ovos_utils.messagebus import FakeBus
from mycroft_bus_client import Message
from neon_utils.configuration_utils import get_neon_local_config, get_neon_user_config
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
        self.skill.speak_dialog.assert_called_once_with("time_format_already_set",
                                                        {"scale": "12"},
                                                        private=True)
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

    def test_handle_transcription(self):
        pass

    def test_handle_speak_speed(self):
        pass


if __name__ == '__main__':
    unittest.main()
