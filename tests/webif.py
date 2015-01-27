import unittest
import urllib2
import shutil
import json
import os

from flask import Flask
from flask.ext.testing import LiveServerTestCase

from lwp.app import app
from lwp.utils import connect_db

class TestWebIf(LiveServerTestCase):

    render_templates = False

    def create_app(self):
        return app

    def test_server_is_up_and_running(self):
        response = urllib2.urlopen(self.get_server_url())
        self.assertEqual(response.code, 200)

    def test_views(self):
        endpoints = ('/home', '/settings/lxc-net', '/about', '/lwp/users',
            '/lwp/tokens', '/action', '/_refresh_info', '/_check_version')

        for link in endpoints:
            response = urllib2.urlopen(self.get_server_url() + link)
            self.assertEqual(response.code, 200)

class TestApi(LiveServerTestCase):

    token = 'myrandomapitestoken'
    db = None
    type_json = {'Content-Type': 'application/json'}

    def create_app(self):
        shutil.copyfile('lwp.db', '/tmp/db.sql')
        self.db = connect_db('/tmp/db.sql')
        self.db.execute('insert into api_tokens(description, token) values(?, ?)', ['test', self.token])
        self.db.commit()
        app.config['DATABASE'] = '/tmp/db.sql'
        return app

    def test_00_get_containers(self):
        shutil.rmtree('/tmp/lxc/', ignore_errors=True)
        request = urllib2.Request(self.get_server_url() + '/api/v1/containers/')
        request.add_header('Private-Token', self.token)
        response = urllib2.urlopen(request)
        self.assertEqual(response.code, 200)
        #assert isinstance(response.read(), list)

    def test_01_put_containers(self):
        data = {'name': 'test_vm_sshd', 'template': 'sshd'}
        request = urllib2.Request(self.get_server_url() + '/api/v1/containers/', json.dumps(data), self.type_json)
        request.add_header('Private-Token', self.token)
        request.get_method = lambda: 'PUT'
        response = urllib2.urlopen(request)
        self.assertEqual(response.code, 200)
        assert data['name'] in os.listdir('/tmp/lxc')

    def test_02_post_containers(self):
        data = {'action': 'start'}
        request = urllib2.Request(self.get_server_url() + '/api/v1/containers/test_vm_sshd', json.dumps(data), self.type_json)
        request.add_header('Private-Token', self.token)
        request.get_method = lambda: 'POST'
        response = urllib2.urlopen(request)
        self.assertEqual(response.code, 200)

    def test_03_delete_containers(self):
        request = urllib2.Request(self.get_server_url() + '/api/v1/containers/test_vm_sshd')
        request.add_header('Private-Token', self.token)
        request.get_method = lambda: 'DELETE'
        response = urllib2.urlopen(request)
        self.assertEqual(response.code, 200)

    def test_04_post_token(self):
        data = {'token': 'test'}
        request = urllib2.Request(self.get_server_url() + '/api/v1/tokens/', json.dumps(data), self.type_json)
        request.add_header('Private-Token', self.token)
        response = urllib2.urlopen(request)
        self.assertEqual(response.code, 200)

    def test_05_delete_token(self):
        request = urllib2.Request(self.get_server_url() + '/api/v1/tokens/test')
        request.add_header('Private-Token', self.token)
        request.get_method = lambda: 'DELETE'
        response = urllib2.urlopen(request)
        self.assertEqual(response.code, 200)

if __name__ == '__main__':
    unittest.main()
