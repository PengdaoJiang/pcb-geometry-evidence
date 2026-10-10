import dataclasses,hashlib,json,warnings

from collections import Counter

from pathlib import Path

from gerbonara.utils import Inch

from gerber_legacy_adapter import parse_legacy

from gerber_geometry import warning_role

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def objects(source):
    assert sha(source['path'])==source['sha256']
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');file,adapter=parse_legacy(Path(source['path']).read_text(encoding='ascii'),filename=source['path'])
    messages=[dict(category=w.category.__name__,message=str(w.message),role=warning_role(w.category.__name__,str(w.message))) for w in caught]
    keys=Counter();ledger={};outer_dark=True;sequence=[];polarities=[]
    with warnings.catch_warnings(record=True) as conversion:
        warnings.simplefilter('always')
        for i,o in enumerate(file.objects):
            outer_dark=outer_dark and o.polarity_dark
            p=[dict(kind=type(p).__name__,fields=dataclasses.asdict(p)) for p in o.to_primitives(unit=Inch)]
            text=json.dumps(dict(outer_dark=o.polarity_dark,ordered_primitives=p),sort_keys=True,separators=(',',':'),allow_nan=False)
            h=hashlib.sha256(text.encode('ascii')).hexdigest();keys[h]+=1;sequence.append(h);polarities.append(bool(o.polarity_dark))
            if h not in ledger:ledger[h]=dict(first_index=i,source_object_kind=type(o).__name__,payload=text)
    assert not conversion,'Unqualified primitive conversion warning'
    assert sha(source['path'])==source['sha256']
    return keys,ledger,sequence,polarities,dict(source=source,objects=len(file.objects),all_outer_positive=bool(outer_dark),adapter=adapter,warnings=messages)

def identity_reason(left_sequence,right_sequence,all_positive):
    if left_sequence==right_sequence:return 'EXACT_ORDERED_OBJECT_PRIMITIVES_EQUAL'
    if all_positive and Counter(left_sequence)==Counter(right_sequence):return 'EXACT_POSITIVE_OBJECT_PRIMITIVE_MULTISET_EQUAL'
    return 'NEEDS_GEOMETRY_COMPARISON'

def polarity_runs(sequence,polarities):
    assert len(sequence)==len(polarities) and all(type(p) is bool for p in polarities)
    runs=[]
    for h,p in zip(sequence,polarities):
        if not runs or runs[-1]['dark']!=p:runs.append(dict(dark=p,objects=Counter()))
        runs[-1]['objects'][h]+=1
    return runs
