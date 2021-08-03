import requests
from flask import request

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
