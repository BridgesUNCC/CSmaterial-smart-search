from flask import Flask, Response, Blueprint
from flask_cors  import CORS

from app import util
from app import data

agreement_blueprint = Blueprint('agreement', __name__)
CORS(agreement_blueprint)

@agreement_blueprint.route('/agreement')
def agreement():
    matID = util.argument_to_IDlist('matID')

    if (matID == None):
        return util.return_error("matID is a necessary parameter")
    
    if len(matID)<2:
        return util.return_error("need at least 2 materials")

    mapping = {}
    alltags = set()

    #material info
    matinfo = {}
    
    for id in matID:
        mapping[id] = data.all_acm_tags_in_list([id], True)
        alltags = alltags | mapping[id]
        matinfo[id] = data.material_lookup[id]

    
        
    #generate counts
    allcount = {}
        
    for tag in alltags:
        #print (tag)
        count = 0
        for id in mapping:
            if tag in mapping[id]:
                count += 1
        allcount[tag] = count

    #generate histogram
    histogram = [0] * (len(mapping)+1)

    percount = {}
    for i in range(len(matID)+1):
        percount[i] = []
    
    for tag in allcount:
        histogram[allcount[tag]] += 1
        percount[allcount[tag]].append(
            {
                'id': tag,
                'title' : data.tags_lookup[tag]['title']
            })


        
    return util.return_object(
        {
            'materials': matinfo,
            'count' : allcount,
            'histogram' : histogram,
            'percount': percount
        })
