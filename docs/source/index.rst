SoyutNet simulations
====================

This repo is a hobby open research project which aims to demonstrate
the capapbilities of PT net (Petri net) based formal methods to improve
producer/consumer pipelines by applying appropriate discrete event system (DES)
control policies in simulated real life scenarios.

The project is structured in a way to make the results easily reproducable.

This project's main focus is the technical documentation. The code is used to illustrate
the ideas and reproduce the results.

`Code repository 🔗 <https://github.com/dmrokan/soyutnet-simulations>`_

The simulations use `SoyutNet <https://soyutnet.readthedocs.io>`_ PT net simulator as backend.

Building
--------

.. code:: bash

    python3 -m venv venv
    source venv/bin/activate

    make docs

Simulations
-----------

PI controller
^^^^^^^^^^^^^

This simulation investigates that a proportional-integral (PI) controller
structure can be used to balance the work load of two TCP servers which accept
requests from a single source.

**Running:**

.. code:: bash

    git clone https://github.com/dmrokan/soyutnet-simulations
    sudo apt install graphviz python3-venv
    python3 -m venv venv
    source venv/bin/activate

    make build
    make build=pi_controller
    make run=pi_controller
    make results=pi_controller
    make graph=pi_controller

:doc:`Documentation </src.pi_controller>`

HTTP balancer
^^^^^^^^^^^^^

This simulation investigates that a proportional-integral (PI) controller
structure can be used to balance the work load of two HTTP servers which accepts
requests from a single source.

**Running:**

.. code:: bash

    git clone https://github.com/dmrokan/soyutnet-simulations
    sudo apt install graphviz python3-venv apache2-utils
    python3 -m venv venv
    source venv/bin/activate

    make build
    make build=http_balancer
    make run=http_balancer
    make results=http_balancer
    make graph=http_balancer

:doc:`Documentation </src.http_balancer>`

HTTP server
^^^^^^^^^^^

.. TODO: Write summary

This simulation investigates that a proportional-integral (PI) controller
structure can be used to balance the work load of two HTTP servers which accepts
requests from a single source.

**Running:**

.. code:: bash

    git clone https://github.com/dmrokan/soyutnet-simulations
    sudo apt install graphviz python3-venv apache2-utils
    python3 -m venv venv
    source venv/bin/activate

    make build
    make build=http_server
    make run=http_server
    make results=http_server
    make graph=http_server

:doc:`Documentation </src.http_server>`

Building
--------

.. code:: bash

    git clone https://github.com/dmrokan/soyutnet-simulations
    sudo apt install graphviz python3-venv
    python3 -m venv venv
    source venv/bin/activate

    make docs


`SoyutNet <https://github.com/dmrokan/soyutnet>`__
--------------------------------------------------

Modules
-------

.. toctree::
   :maxdepth: 1

   modules

License
-------

.. raw:: html

    <p style="text-align: unset;" xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/dmrokan/soyutnet-simulations">SoyutNet Simulations</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://github.com/dmrokan">Okan Demir</a> is licensed under <a href="https://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Creative Commons Attribution 4.0 International<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1" alt=""></a></p>

`License text <https://github.com/dmrokan/soyutnet-simulations/blob/main/CC-BY-license.md>`__

Credits
-------

`SoyutNet logo <https://soyutnet.readthedocs.io/en/latest/credits.html>`__
