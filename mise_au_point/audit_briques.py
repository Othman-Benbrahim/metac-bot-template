import json,re,sys,datetime as dt,math,functools
sys.path.insert(0,'.')
import rencontres_regle as rr, justice_regle as jr
rr.voyages=functools.lru_cache(1)(rr.voyages); jr._lire=functools.lru_cache(None)(jr._lire)
import dossier_interne as di
R=re.compile(r"\b(or|either|not|no|any of|at least one|none|neither|nor|unless|without|except)\b",re.I)
out=open(sys.argv[1],'w')
n=0
for l in open('registre/jugement-questions.jsonl'):
    q=json.loads(l)
    try: jour=dt.date.fromisoformat(q['jeu'])
    except Exception: continue
    try: B=di._briques(q['titre'],jour,q.get('resolue_le') or '')
    except Exception: continue
    for fam,meca,e,sil in B:
        if e is None: continue
        p=di._p(e); y=q.get('issue'); ll=None
        if y in (0,1) and p is not None:
            pp=min(max(p,0.01),0.99); ll=-math.log(pp if y==1 else 1-pp)
        out.write(json.dumps(dict(id=q['id'],source=q.get('source'),jeu=q['jeu'],titre=q['titre'],fam=fam,p=p,y=y,perte=ll,risque=bool(R.search(q['titre']))),ensure_ascii=False)+'\n'); out.flush()
    n+=1
print('questions',n)
