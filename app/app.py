from flask import Flask, request, Response, make_response
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

import json
import sys
import requests


from app import util
from app import data

from app import agreement
from app import similarity
from app import pagerank
from app import search


app = Flask(__name__)
app.register_blueprint(agreement.agreement_blueprint)
app.register_blueprint(similarity.similarity_blueprint)
app.register_blueprint(pagerank.pagerank_blueprint)
app.register_blueprint(search.search_blueprint)

# you'll need to pip3 install networkx


@app.route('/')
def homepage():
    return 'homepage'





    
@app.route('/ontologyCSV')
def ontology_csv():
    ret = ""
    for t in data.all_acm_ids:
        ret += str(t)
        id = t
        li = [ data.acm_lookup[id]['title'] ]
        while 'parent' in data.acm_lookup[id]:
            id = data.acm_lookup[id]['parent']
            li.insert(0, data.acm_lookup[id]['title'])
        for ti in li:
            ret += "\t"+ti
        ret += "\n"

    response = make_response(ret, 200)
    response.mimetype = "text/plain"
    return response
    
        

# query = 154 # KRS - HW - Binary trees
# query = 55 # Bacon Number imdb  bridges
# query = 237 # 3112 module 3 project
# matchpool = list(material_lookup)
# matchpool.remove(query)
# k = 10


# nifty = 264
# erik_ds=178
# kr_ds=185
# kr_3112 = 266
# bk_CS1 = 326


# pdc_mats = all_materials_in_collection(peachy)
# pdc_mats.extend( all_materials_in_collection(erik_parco) )

# similarity_query_tags(all_acm_tags_in_list([ query ]), pdc_mats, k, 'matching')


# function with a new route called SimilarityMatrix
# Takes a set of materials as the request parameter MatID


def tag2(args):
    pass




@app.route('/class_model/<classname>')
def class_model(classname: str):
    if classname == "datastructure":

        erik_ds = 178
        kr_ds = 185

        ds_tags = data.all_acm_tags_in_list(data.all_materials_in_collection(erik_ds)).intersection(
            data.all_acm_tags_in_list(data.all_materials_in_collection(kr_ds)))

        # for t in ds_tags:
        #     print (acm_lookup[t]['title'])

        return util.return_object({
            "datastructure": list(ds_tags)
        })
    else:
        return json.dumps(
            {
                "status": "KO"
            }
        )


@app.route('/sets/allpdc')
def all_pdc():
    # nifty = 264
    peachy = 263
    erik_parco = 179
    # erik_ds=178
    # kr_ds=185
    # kr_3112 = 266
    # bk_CS1 = 326
    pdc_mats = data.all_materials_in_collection(peachy)
    pdc_mats.extend(data.all_materials_in_collection(erik_parco))
    return util.return_object({
        "allpdc": list(pdc_mats)
    })


@app.before_first_request
def init():
    data.update_model()
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=data.update_model, trigger="interval", minutes=60)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    # query = 154 # KRS - HW - Binary trees
    # query = 55 # Bacon Number imdb  bridges
    # query = 237 # 3112 module 3 project
    # matchpool = list(material_lookup)
    # matchpool.remove(query)
    # k = 10

    # similarity_query_tags(all_acm_tags_in_list([ query ]), pdc_mats, k, 'matching')

    # for n in all_materials_in_collection(bk_CS1):
    #     print ("===", n, material_lookup[n]['title'], "===")
    #     similarity_query_tags(all_acm_tags_in_list([ n ]), pdc_mats, k, 'matching')

    # print (all_materials_in_collection(nifty))

    # print (all_acm_tags_in_list(all_materials_in_collection(erik_ds)))
    # print (all_acm_tags_in_list(all_materials_in_collection(kr_ds)))

    # ds_tags = all_acm_tags_in_list(all_materials_in_collection(erik_ds)).intersection(all_acm_tags_in_list(all_materials_in_collection(kr_ds)))

    # print (ds_tags)
    # for t in ds_tags:
    #     print (tags_lookup[t])
