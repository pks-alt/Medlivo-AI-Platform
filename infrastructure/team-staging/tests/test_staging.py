import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

MODULE = Path(__file__).parents[1] / 'staging.py'
spec = importlib.util.spec_from_file_location('staging', MODULE)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def config(enabled=False):
    value = {'project': s.PROJECT, 'region': s.REGION, 'environment': 'staging',
             'images': {'api': f'{s.REGISTRY}/{s.API}@sha256:' + '1' * 64,
                        'web': f'{s.REGISTRY}/{s.WEB}@sha256:' + '2' * 64}}
    if enabled:
        value.update(app_origin=f'https://{s.WEB}-test-uw.a.run.app',
                     api_url=f'https://{s.API}-test-uw.a.run.app',
                     google_client_id='123456-test.apps.googleusercontent.com',
                     secret_versions={key:'1' for key in s.SECRETS},
                     reviewed={key:True for key in ('staging_database_and_grants','oauth_callback_registered',
                                                   'synthetic_users_only','callback_logs_redacted')})
    return value


class ManifestTests(unittest.TestCase):
    def test_bootstrap_is_disabled_private_and_has_no_secret_references(self):
        with patch.object(s.subprocess, 'run', side_effect=AssertionError('No commands during render')):
            specs = s.render(config(), 'bootstrap')
        for kind, service in specs.items():
            self.assertEqual(service['metadata']['annotations']['run.googleapis.com/invoker-iam-disabled'], 'false')
            self.assertEqual(service['metadata']['labels']['environment'], 'staging')
            self.assertEqual(service['spec']['template']['spec']['containers'][0]['env'][0]['value'], 'false')
        self.assertNotIn('secretKeyRef', json.dumps(specs))
        self.assertNotIn('cloudsql-instances', json.dumps(specs))

    def test_configured_still_private_and_only_references_pinned_secrets(self):
        specs = s.render(config(True), 'configured')
        for kind, service in specs.items():
            self.assertEqual(service['metadata']['annotations']['run.googleapis.com/invoker-iam-disabled'], 'false')
            runtime = service['spec']['template']['spec']
            self.assertIn('-staging@', runtime['serviceAccountName'])
            self.assertEqual(runtime['containers'][0]['env'][0]['value'], 'true')
            refs = [v['valueFrom']['secretKeyRef'] for v in runtime['containers'][0]['env'] if 'valueFrom' in v]
            self.assertEqual(len(refs), 1 if kind == 'api' else 3)
            self.assertTrue(all(r['key'] == '1' for r in refs))
        self.assertIn(f'{s.PROJECT}:{s.REGION}:medlivo-ai-postgres', json.dumps(specs))
        self.assertNotIn('DATABASE_URL=postgres', json.dumps(specs))

    def test_production_target_changes_are_rejected(self):
        for key, val in [('project','production'),('region','us-east1'),('environment','production')]:
            value=config(); value[key]=val
            with self.subTest(key=key), self.assertRaises(s.ConfigurationError): s.render(value,'bootstrap')

    def test_raw_credentials_and_unknown_fields_are_rejected(self):
        for key in ('password','client_secret','api_service','database_url'):
            value=config(); value[key]='not-a-secret'
            with self.subTest(key=key), self.assertRaises(s.ConfigurationError): s.render(value,'bootstrap')

    def test_only_digest_pinned_images_from_designated_repository(self):
        for image in ['image:latest',f'{s.REGISTRY}/{s.API}:latest',f'{s.REGISTRY}/medlivo-ai-api@sha256:'+'1'*64,
                      'attacker.example/app@sha256:'+'1'*64]:
            value=config(); value['images']['api']=image
            with self.subTest(image=image), self.assertRaises(s.ConfigurationError): s.render(value,'bootstrap')

    def test_secret_latest_and_numbers_and_values_are_rejected(self):
        for version in ['latest',0,1,'0','abc','raw-password']:
            value=config(True); value['secret_versions']['TEAM_SESSION_KEY']=version
            with self.subTest(version=version), self.assertRaises(s.ConfigurationError): s.render(value,'configured')

    def test_origin_is_staging_https_root_only(self):
        for url in ['http://localhost:8080','https://recruit.medlivo.com',f'https://{s.WEB}-x.run.app/path',
                    f'https://{s.WEB}-x.run.app?key=a',f'https://user:pass@{s.WEB}-x.run.app',
                    f'https://{s.WEB}-x.run.app.attacker.test',f'https://{s.API}-x.run.app']:
            value=config(True); value['app_origin']=url
            with self.subTest(url=url), self.assertRaises(s.ConfigurationError): s.render(value,'configured')

    def test_operator_gates_require_boolean_true(self):
        for entry in config(True)['reviewed']:
            for flag in [False,'true',1]:
                value=config(True); value['reviewed'][entry]=flag
                with self.subTest(entry=entry,flag=flag), self.assertRaises(s.ConfigurationError): s.render(value,'configured')

    def test_explicit_service_identity_cloudsql_and_bounded_settings(self):
        specs=s.render(config(True),'configured')
        for kind,name in [('api',s.API),('web',s.WEB)]:
            service=specs[kind]; runtime=service['spec']['template']['spec']
            self.assertEqual(service['metadata']['name'],name)
            self.assertEqual(runtime['serviceAccountName'],f'{name}@{s.PROJECT}.iam.gserviceaccount.com')
            self.assertEqual(runtime['containerConcurrency'],10)
            self.assertEqual(service['spec']['template']['metadata']['annotations']['autoscaling.knative.dev/maxScale'],'2')
            self.assertEqual(service['spec']['template']['metadata']['annotations']['run.googleapis.com/cloudsql-instances'],f'{s.PROJECT}:{s.REGION}:{s.SQL}')


class InventoryTests(unittest.TestCase):
    def test_unreadable_resources_are_unknown_not_missing(self):
        r=s.inventory(lambda args:{'readable':False,'reason':'Permission denied'})
        self.assertTrue(all(c['status']=='unknown' for c in r['checks'][:-2]))
        self.assertFalse(r['ready_to_enable']); self.assertFalse(r['secret_values_read'])

    def test_empty_inventory_is_explicit_missing_without_creation(self):
        calls=[]
        def reader(args): calls.append(args); return {'readable':True,'value':[]}
        r=s.inventory(reader)
        self.assertEqual(len(calls),5)
        self.assertTrue(all(c['status']=='missing' for c in r['checks'][:-2]))
        self.assertNotIn('access', ' '.join(' '.join(c) for c in calls))
        self.assertTrue(all('list' in c for c in calls))

    def test_sensitive_metadata_is_not_echoed(self):
        def reader(args):
            if args[0]=='run': return {'readable':True,'value':[{'metadata':{'name':'production'},'private':'raw-private-marker'}]}
            return {'readable':True,'value':[]}
        self.assertNotIn('raw-private-marker',json.dumps(s.inventory(reader)))

    def test_existing_public_service_is_flagged_and_not_modified(self):
        calls=[]
        def reader(args):
            calls.append(args)
            if 'get-iam-policy' in args: return {'readable':True,'value':{'bindings':[{'role':'roles/run.invoker','members':['allUsers']}]}}
            if args[0]=='run':
                return {'readable':True,'value':[{'metadata':{'name':s.API,'annotations':{'run.googleapis.com/invoker-iam-disabled':'true'}},'status':{'url':f'https://{s.API}-x.run.app'}}]}
            return {'readable':True,'value':[]}
        r=s.inventory(reader)
        by={c['name']:c for c in r['checks']}
        self.assertEqual(by[s.API]['status'],'review')
        self.assertTrue(by[s.API+'_iam']['detail']['public_binding_present'])
        self.assertTrue(all('list' in c or 'get-iam-policy' in c for c in calls))

    def test_gcloud_is_no_shell_fixed_project_and_no_raw_errors(self):
        with patch.object(s.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='secret marker')) as run:
            result=s.cloud_json(['services','list','--enabled'])
        self.assertFalse(result['readable']); self.assertNotIn('secret marker',json.dumps(result))
        args,kwargs=run.call_args
        self.assertIn('--project='+s.PROJECT,args[0]); self.assertFalse(kwargs.get('shell',False))

    def test_missing_cli_and_invalid_json_are_sanitized(self):
        with patch.object(s.subprocess,'run',side_effect=FileNotFoundError('secret')):
            self.assertFalse(s.cloud_json(['services','list'])['readable'])
        with patch.object(s.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='broken',stderr='')):
            self.assertFalse(s.cloud_json(['services','list'])['readable'])

    def test_allowlist_does_not_treat_conditional_binding_as_unconditional(self):
        def reader(args):
            if 'get-iam-policy' in args:
                return {'readable':True,'value':{'bindings':[{'role':'roles/run.invoker','members':[f'serviceAccount:{s.WEB}@{s.PROJECT}.iam.gserviceaccount.com'],'condition':{'expression':'false'}}]}}
            if args[0]=='run':
                return {'readable':True,'value':[{'metadata':{'name':s.API},'spec':{'template':{'spec':{}}}}]}
            return {'readable':True,'value':[]}
        r=s.inventory(reader)
        check=next(c for c in r['checks'] if c['name']==s.API+'_iam')
        self.assertFalse(check['detail']['web_to_api_direct_invoker_binding'])


if __name__=='__main__': unittest.main()
