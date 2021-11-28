# Introduction

Our solution for ELEC4123 Elective Topic project for Networking. 

Contains scripts to setup the snooping servers and execute the message reconstruction algorithm.

## Setup for different IP addresses

1. Turn on the Snoop-Me server with -http_post to enable message validation
2. Setup the snooper feeder servers on each of our VM instances.
   Do this by executing the script snooper_feederx.py on VM instance x.
3. On the third VM instance execute run_multi_kalman_solver.py with the arguments --use-feeders.

## Setup on same machine

1. Turn on the Snoop-Me server with -http_post and -multi_snooper_hosts to enable snoop requests from the same ip
2. Execute run_multi_kalman_solver.py without any additional arguments.
   This creates local snooper servers on the same machine.

## Running other versions of the solver

| Script                     | Description                                                                                                                                                                                                          |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| run_solver.py              | Single snooper solution                                                                                                                                                                                              |
| run_multi_solver.py        | Multi-snooper solution with snoopers running locally.<br />Requests are collated together.                                                                                                                           |
| run_hosted_multi_solver.py | Multi-snooper solution with a host server that collates Sr requests.<br />Run the script local_server_snoop.py to start the host server.<br />Pass in the arguments --use-feeders to connect to VM snooping feeders. |
| run_kalman_solver.py       | Single snooper solution with Kalman filter.                                                                                                                                                                          |
| run_multi_kalman_solver.py | Multi-snooper solution with Kalman filter.<br />Requests are done asychronously using multi-threading.<br />Pass in the arguments --use-feeders to connect to VM snooping feeders.                                   |
