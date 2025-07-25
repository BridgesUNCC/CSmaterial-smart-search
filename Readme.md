##

## Routes

```
$ flask routes
Endpoint                      Methods  Rule
----------------------------  -------  ------------------------
agreement.agreement           GET      /agreement
all_pdc                       GET      /sets/allpdc
class_model                   GET      /class_model/<classname>
homepage                      GET      /
ontology_csv                  GET      /ontologyCSV
search.my_search              GET      /search
similarity.similarity_matrix  GET      /similarity
static                        GET      /static/<path:filename>
```

### /similarity
will compute the similary between multiple materials.

takes parameters ```matID``` a list of materials; must be at least 2 materials.
The similarity is computed using the ```matching``` method

### /search
will perform a search against tags and/or materials.

parameters:
```k``` optional. integer, number of results to return (capped at 100; default 10)

```tags``` list of CS materials tag number

```matID``` list of CS materials material ID

```algo``` specify algorithm to use. Accepting ```jaccard```, ```matching```, and ```pagerank```

```matchpool``` specify the pool of materials to search in (default ```all```)

### /agreement

generate agreement between multiple materials; that is to say how many common tags they use.

parameters:
```matID```  a list of materials; must be at least 2 materials.


### /ontologyCSV

returns the ACM curriculum guidelines formatted as CSV

### /class_model/<classname>

Returns a list of tags that form the model for a class

Currently only support class ```datastructure```

This model is computed by looking at the agreement between a few stereotypical classes.

### /sets/allpdc

return all pdc materaisl in cs materials. The list is not automated and is curated by hand.


## parameters

In general list of materials are comma separated list. where the ID itself is a CS materials ID

```matchpool``` can be ```all``` or ```pdc``` as defined in function ```parse_matchpool()```


## install

Check the python version in runtime.txt. Create a venv with that python install
install packages from requiremsnts.txt using pip.
