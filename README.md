# SoyutNet simulations

This repo is a hobby open research project which aims to demonstrate
the capabilities of PT net (Petri net) based formal methods in improvement of
producer/consumer pipelines by implementing different discrete event system (DES)
control policies in simulated real life scenarios.

The project is structured in a way to make the results easily reproducable.

This project's main focus is the technical documentation. The code is used to illustrate
the ideas and reproduce the results.

## Running

```bash
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate

make build
make build=pi_controller
make run=pi_controller
make results=pi_controller
```

## Building

```bash
git clone https://github.com/dmrokan/soyutnet-simulations
sudo apt install graphviz python3-venv
python3 -m venv venv
source venv/bin/activate

make docs
```
