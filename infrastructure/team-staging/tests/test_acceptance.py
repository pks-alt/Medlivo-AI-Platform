import json
import unittest
from unittest.mock import patch
import importlib.util
from pathlib import Path

PATH=Path(__file__).resolve().parents[1]/"acceptance.py"
spec=importlib.util.spec_from_file_location("acceptance",PATH)
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class AcceptanceTests(unittest.TestCase):
    def test_base_url_requires_clean_https_origin(self):
        self.assertEqual(a.base_url("https://staging.example/team/"),"https://staging.example/team")
        for value in ("http://x.example","https://u:p@x.example","https://x.example?a=1"):
            with self.assertRaises(ValueError): a.base_url(value)

    @patch.object(a,"fetch")
    def test_read_only_acceptance_contract(self,fetch):
        fetch.side_effect=[
            (200,{"Cache-Control":"no-store"},b"<html>Medlivo Team</html>"),
            (200,{},json.dumps({"ok":True,"workspace_enabled":True,"database_checked":False}).encode()),
            (200,{},json.dumps({"ok":True,"workspace_enabled":True,"database_checked":True,"database_reachable":True}).encode()),
            (401,{},b'{"detail":"Authentication required"}'),
        ]
        result=a.run("https://web.example","https://api.example","server-token")
        self.assertFalse(result["mutations_performed"])
        self.assertFalse(result["jobdiva_write_authorized"])
        self.assertTrue(all(c["status"]=="pass" for c in result["checks"]))
        self.assertEqual(fetch.call_args_list[-1].args,("https://api.example/api/v1/team/me",None))

if __name__=="__main__": unittest.main()
