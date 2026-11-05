"""Analysis adapter: saved observations only, including DNS candidate checks."""
import json,sys
from pathlib import Path
import orglens.core as core
import orglens.names as names
from orglens.cli import main

source=Path(sys.argv[sys.argv.index('--replay')+1])
urls=set()
for line in (source/'envelopes.jsonl').read_text(encoding='utf8').splitlines():
    for snapshot in json.loads(line)['source_snapshots']:
        urls.add(snapshot['source_url'])
        urls.add(snapshot.get('requested_url',snapshot['source_url']))
names.resolves=lambda url:url in urls
output=Path(sys.argv[sys.argv.index('--output')+1])
try:main()
finally:
    output.mkdir(parents=True,exist_ok=True)
    (output/'experiment-adapter.json').write_text(json.dumps({'mode':'saved-source policy comparison',
        'source_module':core.__file__,'dns':'limited to exact saved observation URLs; no DNS or HTTP network',
        'limitations':'Replay compares policy on available observations, not current coverage or official recall.'},indent=2),encoding='utf8')
