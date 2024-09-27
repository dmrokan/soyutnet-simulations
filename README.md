# SoyutNet simulations

This repo is a hobby open research project which aims to demonstrate
the capabilities of PT net (Petri net) based formal methods in improvement of
producer/consumer pipelines by implementing different discrete event system (DES)
control policies in simulated real life scenarios.

The project is structured in a way to make the results easily reproducable.

This project's main focus is the technical documentation. The code is used to illustrate
the ideas and reproduce the results.

[Documentation](https://soyutnet.readthedocs.io/projects/simulations)

[SoyutNet](https://github.com/dmrokan/soyutnet)

## Simulations

* [PI controller](https://github.com/dmrokan/soyutnet-simulations/tree/main/src/pi_controller)

## Running

A simulation can be run by

```bash
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate

make build
make build=pi_controller
make run=pi_controller
make results=pi_controller
make graph=pi_controller
```

## Building

```bash
git clone https://github.com/dmrokan/soyutnet-simulations
sudo apt install graphviz python3-venv
python3 -m venv venv
source venv/bin/activate

make docs
```

## License

SoyutNet simulations is licensed under

 <p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/dmrokan/soyutnet-simulations">SoyutNet Simulations</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://github.com/dmrokan">Okan Demir</a> is licensed under <a href="https://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Creative Commons Attribution 4.0 International<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1" alt=""></a></p>

[License text](https://github.com/dmrokan/soyutnet-simulations/blob/main/CC-BY-license.md)

### Exceptions

* Python code files under `src` folder
* Makefiles under `src` folder
* Makefile at project root

are licensed under

 <p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/dmrokan/soyutnet-simulations">SoyutNet Simulations Code</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://github.com/dmrokan">Okan Demir</a> is licensed under <a href="https://creativecommons.org/licenses/by-sa/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Creative Commons Attribution-ShareAlike 4.0 International<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1" alt=""></a></p>

[License text](https://github.com/dmrokan/soyutnet-simulations/blob/main/CC-BY-SA-license.md)
