from flask import jsonify


def make_success_response(data=None, message='success', http_code=200):
    return jsonify({
        'code': 0,
        'message': message,
        'data': data or {}
    }), http_code


def make_fail_response(message='fail', http_code=400, data=None):
    return jsonify({
        'code': -1,
        'message': message,
        'data': data or {}
    }), http_code
