# -*- coding: utf-8 -*-
import os
import unittest
import tempfile
from datetime import datetime

from flask.ext.sqlalchemy import SQLAlchemy

from app import app, db, Pass, Registration


class PassbookTestCase(unittest.TestCase):

    def setUp(self):
        temp = tempfile.mkstemp()
        self.temp = temp
        self.db_fd = temp[0]
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///%s' % temp[1]
        app.config['TESTING'] = True
        self.app = app.test_client()

        SQLAlchemy.create_all(db)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))

    def test_add_pass_and_registrations(self):
        data = {
            'foo': 57,
            'bar': str(datetime.utcnow()),
            'baz': 'Lorem ipsum dolar sit amet'
        }

        p = Pass('com.company.pass.example', 'ABC123', data)
        db.session.add(p)
        db.session.commit()

        assert Pass.query.get(1)

        r = Registration('123456789', '00000000 00000000 00000000 00000000 \
                         00000000 00000000 00000000 00000000', p)
        db.session.add(r)
        db.session.commit()

        assert Registration.query.get(1)

if __name__ == '__main__':
    unittest.main()
