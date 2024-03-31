#!/usr/bin/env python

import hashlib
import subprocess
import yaml


INDEX_TEMPLATE = '''
Examples
========

.. toctree::
   :maxdepth: 3

   {}
'''


IMAGE_TEMPLATE = '''
.. _{0[name]}_example:

{0[title]}
{0[title_len]}

{0[description]}

Source Code
-----------

.. literalinclude:: {0[script]}

Generated Image
---------------

Below is the generated image from the code above. If you're having issues with the image below, try the :download:`direct link to image <{0[name]}.png>`.

.. container:: example-image

    .. image:: {0[name]}.png
        :target: ../_downloads/{0[name]}.png

'''


index = []
new_yaml = []

for info in yaml.load(open('examples.yml'), yaml.SafeLoader):
    new_info = info
    new_yaml.append(new_info)

    index.append(info['name'])
    info['title_len'] = ('=' * (len(info['title'])))

    # Generate the rst for this example
    open('{}.rst'.format(info['name']), 'w').write(
        IMAGE_TEMPLATE.format(info).strip()
    )


    print(info['run'])

    # If the hash of the example hasn't changed, don't run again
    with open(info['script']) as file:
        filemd5 = hashlib.md5(file.read().encode('utf-8')).hexdigest()

    if filemd5 != info.get('md5'):
        info['md5'] = filemd5

        subprocess.call(info['run'], shell=True)

        if 'execute_after' in info:
            print('Running {}'.format(info['execute_after']))
            subprocess.call(info['execute_after'], shell=True)
    del info['title_len']

open('index.rst', 'w').write(INDEX_TEMPLATE.format('\n   '.join(index)))

out = yaml.dump(new_yaml, default_flow_style=False)
open('examples.yml', 'w').write(out)

