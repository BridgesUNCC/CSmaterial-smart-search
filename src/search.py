from flask import Flask, Response, Blueprint, request
from matplotlib import pyplot as plt
from sklearn.manifold import MDS
import networkx as nx
import time

import util
import data
import similarity


search_blueprint = Blueprint('search', __name__)


@search_blueprint.route('/search')
def my_search():
    matchpool = []

    matchpoolstr = 'all'

    if request.args.get('matchpool') is not None:
        matchpoolstr = request.args.get('matchpool')

    if matchpoolstr == 'all':
        matchpool = list(data.material_lookup)
    elif matchpoolstr == 'pdc':
        peachy = 263
        erik_parco = 179
        pdc_mats = data.all_materials_in_collection(peachy)
        pdc_mats.extend(data.all_materials_in_collection(erik_parco))
        matchpool = pdc_mats
    else:
        return util.return_error("unknown matchpool parameter")

    tags = util.argument_to_IDlist('tags')
    if tags is not None:
        tags = set(tags)
    else:
        tags= set()
        
    matID = util.argument_to_IDlist('matID')
    if matID is not None:
        for id in matID:
            matchpool.remove(id)
        tags = tags | data.all_acm_tags_in_list(matID)

    k = 10

    if request.args.get('k') is not None:
        k_query = int(request.args.get('k'))
        if k_query > 0 and k_query < 100:
            k = int(k_query)

    algo = 'matching'

    simdata = similarity.similarity_query_tags(tags, matchpool, k, algo)

    simdata['query']['query_matID'] = matID

    return util.return_object(simdata)
