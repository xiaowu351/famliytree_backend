from flask import jsonify


def make_success_response(data=None, message='success', code=200):
    return jsonify({
        'status': 'success',
        'code': code,
        'message': message,
        'data': data or {}
    }), code


def make_fail_response(message='fail', code=400, data=None):
    return jsonify({
        'status': 'fail',
        'code': code,
        'message': message,
        'data': data or {}
    }), code
