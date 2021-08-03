import requests
from flask import request, Response
import json

def argument_to_IDlist(argname :str) -> list :
    if request.args.get(argname) is None:
        return None

    try:
        matID = []
        for id in request.args.get(argname).split(','):
            matID.append(int(id))

        return matID
    except:
        raise ValueError("Should be a comma separated list of integers")


def add_response_headers(resp):
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp


def return_object(obj):
    resp = Response(json.dumps({
        "data": obj,
        "status": "OK"
    }
    ), mimetype='application/json')
    return add_response_headers(resp)


def return_error(str):
    resp = Response(json.dumps({
        "status": "KO",
        "reason": str
    }
    ), mimetype='application/json')
    return add_response_headers(resp)

