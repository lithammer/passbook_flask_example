# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
try:
    # Python 2
    from urlparse import urlparse
except ImportError:
    # Python 3
    from urllib.parse import urlparse

from flask import Flask, request, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates

try:
    url = urlparse(os.environ['DATABASE_URL'])
    DATABASE = 'postgresql://{user}:{pwd}@{host}:{port}/{db}'.format(
        user=url.username,
        pwd=url.password,
        host=url.hostname,
        port=url.port,
        db=url.path[1:])
except KeyError:
    path = os.path.abspath(os.path.dirname(__file__))
    DATABASE = 'sqlite:////{path}/dev.db'.format(path=path)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE
db = SQLAlchemy(app)


class Pass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pass_type_identifier = db.Column(db.String(255), unique=True)
    serial_number = db.Column(db.String(255), unique=True)
    data = db.Column(db.PickleType)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

    @validates
    def validate_pass_type_identifier(self, key, ident):
        assert re.match(r'([\w\d]\.?)+', ident)
        return ident

    def __init__(self, pass_type_identifier, serial_number, data):
        self.pass_type_identifier = pass_type_identifier
        self.serial_number = serial_number
        self.data = data
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def __repr__(self):
        return '<Pass %s>' % self.pass_type_identifier


class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_library_identifier = db.Column(db.String(255), unique=True)
    push_token = db.Column(db.String(255))
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    pass_id = db.Column(db.Integer, db.ForeignKey('pass.id'))
    p = db.relationship('Pass', backref=db.backref('registrations',
                                                   lazy='dynamic'))

    def __init__(self, device_library_identifier, push_token, p):
        self.device_library_identifier = device_library_identifier
        self.push_token = push_token
        self.p = p
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def __repr__(self):
        return '<Registration %s>' % self.device_library_identifier


@app.route('/passes/<pass_type_identifier>/<serial_number>')
def show(pass_type_identifier, serial_number):
    """
    Getting the latest version of a Pass

    Keyword arguments:
    pass_type_identifier -- The pass’s type, as specified in the pass
    serial_number -- The unique pass identifier, as specified in the pass
    """
    p = Pass.query.filter_by(pass_type_identifier=pass_type_identifier,
                             serial_number=serial_number).first_or_404()

    return jsonify(p.data)


@app.route('/devices/<device_library_identifier>/registrations/<pass_type_identifier>')
def index(device_library_identifier, pass_type_identifier):
    """
    Getting the serial numbers for passes associated with a device

    Keyword arguments:
    device_library_identifier -- A unique identifier that is used to identify
                                 and authenticate the device
    pass_type_identifier      -- The pass’s type, as specified in the pass

    If the passes_updated_since parameter is present, return only the passes
    that have been updated since the time indicated by tag. Otherwise, return
    all passes.
    """
    p = Pass.query.filter_by(
            pass_type_identifier=pass_type_identifier).first_or_404()

    r = p.registrations.filter_by(
            device_library_identifier=device_library_identifier)
    if 'passesUpdatedSince' in request.args:
        r = r.filter(Registration.updated_at >= request.args['passesUpdatedSince'])

    if r:
        # XXX: Is this the correct return value for serial number?
        return jsonify({
            'lastUpdated': p.updated_at,
            'serialNumbers': [p.serial_number]
        })
    else:
        return ('No Content', 204)


@app.route('/devices/<device_library_identifier>/registrations/<pass_type_identifier>/<serial_number>')
def create(device_library_identifier, pass_type_identifier, serial_number, methods=['POST']):
    """
    Registering a device to receive push notifications for a pass

    Keyword arguments:
    device_library_identifier -- A unique identifier that is used to identify
                                 and authenticate the device
    pass_type_identifier      -- The pass’s type, as specified in the pass
    serial_number             -- The unique pass identifier, as specified in
                                 the pass
    """
    p = Pass.query.filter_by(pass_type_identifier=pass_type_identifier,
                             serial_number=serial_number).first_or_404()

    registrations = p.registrations.filter_by(
        device_library_identifier=device_library_identifier)
    registrations.push_token = request.form['push_token']

    db.session.add(registrations)
    db.session.commit()

    return ('Created', 201)


@app.route('/devices/<device_library_identifier>/registrations/<pass_type_identifier>')
def destroy(device_library_identifier, pass_type_identifier, methods=['DELETE']):
    """
    Unregistering a device

    Keyword arguments:
    device_library_identifier -- A unique identifier that is used to identify
                                 and authenticate the device
    pass_type_identifier      -- The pass’s type, as specified in the pass
    serial_number             -- The unique pass identifier, as specified in
                                 the pass
    """
    p = Pass.query.filter_by(
        pass_type_identifier=pass_type_identifier).first_or_404()
    registrations = p.registrations.filter_by(
        device_library_identifier=device_library_identifier).first_or_404()

    db.session.delete(registrations)
    db.session.commit()

    return ('OK', 200)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
