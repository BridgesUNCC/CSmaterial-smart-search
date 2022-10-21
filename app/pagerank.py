from flask import Flask, Response, Blueprint, request
#from matplotlib import pyplot as plt
from sklearn.manifold import MDS
import networkx as nx
import time
from flask_cors  import CORS

from app import util
from app import data


pagerank_blueprint = Blueprint('pagerank', __name__)
CORS(pagerank_blueprint)

g = None

def build_graph():
    start = time.time()    
    # declare an empty graph from the NetworkX module
    global g
    g = nx.Graph()

    # add the classification edges (between materials and tags)

    for mid in data.material_lookup:
        mat = data.material_lookup[mid]
        if 'tags' in mat:
            for tags in mat['tags']:
                if tags['id'] in data.all_acm_ids:
                    g.add_edge("m" + str(mat['id']), "t" + str(tags['id']))

    # ontology edges/for all ACM tags tid: add edge between tid and parent tid
    for t in data.all_acm_ids:
        if 'parent' in data.acm_lookup[t]:
            parentid = data.acm_lookup[t]['parent']
            g.add_edge("t" + str(parentid), "t" + str(t))

        # nx.write_edgelist(g, "test.edgelist", data=False)
        # f = plt.figure()
        # nx.draw_spring(g, with_labels=True, ax=f.add_subplot(111))
        # f.savefig('graph.png')
        # return 'empty'
        

    end = time.time()
    print("it took "+str(end - start)+"s to build the graph")
    
def pagerank_feature(tags, matID, matchpool, k, algo):
    if g is None:
        build_graph()

    start = time.time()    

    #init seed
    totalseed = len(matID)+len(tags)

    perso = {}
    for id in matID:
        perso["m"+str(id)] = 1./totalseed

    for id in tags:
        perso["t"+str(id)] = 1./totalseed
        

    #run pagerank

    pr = nx.pagerank(g, alpha=0.85, personalization=perso, max_iter=100,
                     tol=1e-05, nstart=None,
                     weight='weight', dangling=None)

    #format
    res = {}
    
    for e in pr:
        if e[0] == 'm':
            id = int (e[1:])
            if id not in matID:
                val = pr[e]
                res[id] = val
            
    end = time.time()
    print("it took "+str(end - start)+"s to build the compute pagerank")
    
    return res
