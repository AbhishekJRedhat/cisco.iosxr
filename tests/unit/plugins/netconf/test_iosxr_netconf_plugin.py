from __future__ import absolute_import, division, print_function


__metaclass__ = type

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("ncclient")
pytest.importorskip("lxml")

from lxml.etree import Element

from ansible_collections.cisco.iosxr.plugins.netconf.iosxr import Netconf


@pytest.fixture
def netconf_plugin():
    mock_connection = MagicMock()
    mock_manager = MagicMock()
    mock_connection.manager = mock_manager
    plugin = Netconf(mock_connection)
    plugin._connection = mock_connection
    return plugin, mock_manager


class TestEditConfigHugeTree:
    """Tests for huge_tree support in edit_config"""

    def test_edit_config_parses_string_with_huge_tree(self, netconf_plugin):
        """Verify that string config is parsed with huge_tree=True (handles >10MB XML)"""
        plugin, mock_manager = netconf_plugin

        mock_resp = MagicMock()
        mock_resp.data_xml = "<ok/>"
        mock_manager.edit_config.return_value = mock_resp

        large_description = "X" * 100000
        config_xml = (
            f'<config><interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">'
            f"<interface-configuration><active>act</active>"
            f"<interface-name>Loopback9999</interface-name>"
            f"<description>{large_description}</description>"
            f"</interface-configuration></interface-configurations></config>"
        )

        result = plugin.edit_config(config=config_xml)

        assert result == "<ok/>"
        mock_manager.edit_config.assert_called_once()
        call_args = mock_manager.edit_config.call_args
        passed_config = call_args[0][0] if call_args[0] else call_args[1]["config"]
        assert hasattr(passed_config, "tag")

    def test_edit_config_string_parsed_as_element(self, netconf_plugin):
        """Verify string config is converted to lxml Element before passing to ncclient"""
        plugin, mock_manager = netconf_plugin

        mock_resp = MagicMock()
        mock_resp.data_xml = "<ok/>"
        mock_manager.edit_config.return_value = mock_resp

        config_xml = "<config><test>value</test></config>"
        plugin.edit_config(config=config_xml)

        call_args = mock_manager.edit_config.call_args
        passed_config = call_args[0][0] if call_args[0] else call_args[1]["config"]
        assert hasattr(passed_config, "tag")
        assert passed_config.tag == "config"

    def test_edit_config_element_passed_directly(self, netconf_plugin):
        """Verify lxml Element config is passed directly without re-parsing"""
        plugin, mock_manager = netconf_plugin

        mock_resp = MagicMock()
        mock_resp.data_xml = "<ok/>"
        mock_manager.edit_config.return_value = mock_resp

        config_elem = Element("config")
        plugin.edit_config(config=config_elem)

        call_args = mock_manager.edit_config.call_args
        passed_config = call_args[0][0] if call_args[0] else call_args[1]["config"]
        assert passed_config is config_elem

    def test_edit_config_none_raises_value_error(self, netconf_plugin):
        """Verify ValueError is raised when config is None"""
        plugin, mock_manager = netconf_plugin

        with pytest.raises(ValueError, match="config value must be provided"):
            plugin.edit_config(config=None)

    def test_edit_config_rpc_error_raises_exception(self, netconf_plugin):
        """Verify RPCError from ncclient is re-raised as Exception"""
        plugin, mock_manager = netconf_plugin

        from ncclient.operations import RPCError

        rpc_error = MagicMock()
        rpc_error.xml = Element("rpc-error")
        mock_manager.edit_config.side_effect = RPCError(rpc_error)

        with pytest.raises(Exception):
            plugin.edit_config(config="<config/>")

    @patch("ansible_collections.cisco.iosxr.plugins.netconf.iosxr.remove_namespaces")
    def test_edit_config_remove_ns(self, mock_remove_ns, netconf_plugin):
        """Verify remove_ns=True calls remove_namespaces on response"""
        plugin, mock_manager = netconf_plugin

        mock_resp = MagicMock()
        mock_resp.data_xml = "<ok/>"
        mock_manager.edit_config.return_value = mock_resp
        mock_remove_ns.return_value = "<ok/>"

        result = plugin.edit_config(config="<config/>", remove_ns=True)

        mock_remove_ns.assert_called_once_with(mock_resp)
