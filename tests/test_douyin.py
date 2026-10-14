import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from douyin import validate_evidence, media_address, save, transfer, CheckedRedirect

def fixture():
    return {'source_url': 'https://www.douyin.com/video/1234567890123456789',
            'title': 'Synthetic test', 'duration_seconds': 2,
            'media_url': 'https://v.example.douyinvod.com/synthetic?__vid=1234567890123456789',
            'ui_download_status': 'not_observed', 'ui_evidence': 'No reliable UI label observed',
            'access_gate': 'none'}

class DouyinTests(unittest.TestCase):
    def test_valid_observed_evidence(self):
        self.assertEqual(validate_evidence(fixture()), ('1234567890123456789', 2))

    def test_reject_noncanonical_pages(self):
        for url in ['https://evil.test/video/1234567890123456789', 'https://v.douyin.com/abc',
                    'http://www.douyin.com/video/1234567890123456789',
                    'https://www.douyin.com/video/1234567890123456789?cookie=secret']:
            data=fixture(); data['source_url']=url
            with self.subTest(url=url), self.assertRaises(ValueError): validate_evidence(data)

    def test_media_identity_mismatch(self):
        data=fixture(); data['media_url']=data['media_url'].replace('1234567890123456789', '9999999999999999999')
        with self.assertRaisesRegex(ValueError,'ID'): validate_evidence(data)

    def test_cdn_whitelist_and_credentials(self):
        for url in ['https://127.0.0.1/a','http://v.douyinvod.com/a','https://v.douyinvod.com.evil.test/a',
                    'https://user:pass@v.douyinvod.com/a','https://v.douyinvod.com:8080/a']:
            with self.subTest(url=url), self.assertRaises(ValueError): media_address(url, '1234567890123456789')

    def test_unknown_ui_never_becomes_disabled(self):
        data=fixture(); validate_evidence(data)
        self.assertEqual(data['ui_download_status'], 'not_observed')
        data['ui_download_status']='probably_disabled'
        with self.assertRaises(ValueError): validate_evidence(data)

    def test_access_gates_stop_before_io(self):
        for gate in ['login','captcha','paywall','denied',None]:
            data=fixture(); data['access_gate']=gate
            with self.subTest(gate=gate), self.assertRaisesRegex(ValueError,'Stop'): validate_evidence(data)

    def test_finite_duration_and_evidence_required(self):
        for key,value in [('duration_seconds',float('nan')),('duration_seconds',True),('duration_seconds',0),('ui_evidence',''),('title','')]:
            data=fixture(); data[key]=value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError): validate_evidence(data)

    def test_never_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'out.mp4'; target.write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError,'exists'): save(fixture(),target)
            self.assertEqual(target.read_bytes(),b'keep')

    def test_verified_import_preserves_source(self):
        with tempfile.TemporaryDirectory() as temp, patch('douyin.require_tools'), patch('douyin.verify_media',return_value={'audio_tracks':1,'duration_seconds':2}):
            source=Path(temp)/'source.mp4'; source.write_bytes(b'synthetic')
            target=Path(temp)/'out.mp4'; result=save(fixture(),target,source)
            self.assertEqual(source.read_bytes(),target.read_bytes())
            self.assertEqual(result['ui_download_status'],'not_observed')
            self.assertFalse(result['author_permission_inferred'])
            self.assertEqual(list(Path(temp).glob('.wesave-*')),[])

    def test_bad_media_never_published(self):
        for result in [{'audio_tracks':0,'duration_seconds':2},{'audio_tracks':1,'duration_seconds':8}]:
            with self.subTest(result=result), tempfile.TemporaryDirectory() as temp, patch('douyin.require_tools'), patch('douyin.verify_media',return_value=result):
                source=Path(temp)/'source.mp4'; source.write_bytes(b'synthetic'); target=Path(temp)/'out.mp4'
                with self.assertRaises(RuntimeError): save(fixture(),target,source)
                self.assertFalse(target.exists()); self.assertEqual(list(Path(temp).glob('.wesave-*')),[])

    def test_redirect_revalidation(self):
        with self.assertRaises(ValueError):
            CheckedRedirect('1234567890123456789').redirect_request(None,None,302,'',{},'http://127.0.0.1/private')

    def test_bad_content_type_or_short_response(self):
        class Response(io.BytesIO):
            status=200
        for headers,body in [({'Content-Type':'text/html'},b'error'),({'Content-Length':'99'},b'video')]:
            with self.subTest(headers=headers), patch('douyin.urllib.request.build_opener') as opener:
                response=Response(body); response.headers=headers; opener.return_value.open.return_value=response
                with self.assertRaises(RuntimeError): transfer(fixture(),io.BytesIO(),'1234567890123456789')

if __name__ == '__main__': unittest.main()
