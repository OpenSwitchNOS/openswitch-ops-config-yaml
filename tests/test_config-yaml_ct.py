#!/usr/bin/python
#
# Copyright (C) 2015 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

import os
import sys
import time
import subprocess
import pytest

from halonvsi.docker import *
from halonvsi.halon import *

SRC_PATH = "./src/ops-config-yaml/"
TEST_PRG_PATH = SRC_PATH + "build/unit_test/cfg_yaml_ut"
TEST_FILES_PATH = SRC_PATH + "unit_test/yaml_files"

# Test case configuration.

def short_sleep(tm=.5):
    time.sleep(tm)

def get_ip(s):
    out = s.cmd("ifconfig eth0 | grep inet")
    ip = out.split()[1].split(':')[1]
    return ip

def cfgy_tests_passed(out):
    num_tests = 0
    passed_tests = 0

    lines = out.splitlines()

    for line in lines:
        # Looking for "[==========] Running xxx test"
        if "[==========] Running " in line:
            num_tests = int(line.split()[2])
    if num_tests <= 0:
        return False
    for line in lines:
        # Looking for "[  PASSED  ] xxx"
        if "[  PASSED  ]" in line:
            passed_tests = int(line.split()[3])
    if passed_tests == num_tests:
        return True
    return False

# Create a topology with only one switch
class mySingleSwitchTopo( Topo ):
    """Single switch, no hosts
    """

    def build(self, hsts=0, sws=1, n_links=0, **_opts):
        self.hsts = hsts
        self.sws = sws

        "Add the switches to the topology."
        for s in irange(1, sws):
            switch = self.addSwitch('s%s' %s)

class configyamlTest(HalonTest):

    def setupNet(self):

        # Create a topology with one Halon switch
        host_opts = self.getHostOpts()
        switch_opts = self.getSwitchOpts()
        configyaml_topo = mySingleSwitchTopo(sws=1, hopts=host_opts, sopts=switch_opts)

        self.net = Mininet(configyaml_topo, switch=HalonSwitch,
                           host=Host, link=HalonLink,
                           controller=None, build=True)

    # Pre-test setup
    def test_pre_setup(self):
        s1 = self.net.switches[0]

        ip = get_ip(s1)

        info("ip is [%s]" % ip)

        s1.cmd("mkdir /tmp/yaml_files")
        os.system("scp -oStrictHostKeyChecking=no " + TEST_PRG_PATH + " root@" + ip + ":/tmp")
        os.system("scp -r " + TEST_FILES_PATH + " root@" + ip + ":/tmp")

    # Post-test cleanup
    def test_post_cleanup(self):
        s1 = self.net.switches[0]
        s1.cmd("rm -rf /tmp/unit_test /tmp/cfg_yaml_ut")

    def test_001_config_yaml(self):

        info("\n============= test_001_config_yaml =============\n")

        # Copy the test program and test files to the switch
        self.test_pre_setup()

        s1 = self.net.switches[0]

        # Run the tests on the switch
        out = s1.cmd("/tmp/cfg_yaml_ut")

        assert cfgy_tests_passed(out) == True, "Tests failed, test output is...\n\n%s" % out

        # Cleanup
        self.test_post_cleanup()

class Test_configyaml:

    def setup(self):
        pass

    def teardown(self):
        pass

    def setup_class(cls):
        # Create the Mininet topology based on Mininet.
        Test_configyaml.test = configyamlTest()

        # Stop system daemons
        Test_configyaml.test.net.switches[0].cmd("/bin/systemctl stop pmd")

    def teardown_class(cls):

        # Stop the Docker containers and mininet topology
        Test_configyaml.test.net.stop()

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def __del__(self):
        del self.test

    def test_configyaml(self):
        self.test.test_001_config_yaml()
