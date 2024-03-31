#!/usr/bin/env python

import hashlib
import subprocess
import yaml


examples = yaml.load(open('examples.yml'), yaml.SafeLoader)

print(examples)

changed = False

for script, save_md5 in examples.items():
    with open(script) as file:
        new_md5 = hashlib.md5(file.read().encode('utf-8')).hexdigest()
    if new_md5 == save_md5:
        continue
    changed = True
    examples[script] = new_md5
    subprocess.call('./{}'.format(script), shell=True)

if changed:
    open('examples.yml', 'w').write(yaml.dump(examples))
