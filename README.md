# SDR Monitoring via SNMP using GNU Radio

## Overview
This project implements an SDR-based monitoring system using GNU Radio.
Signal parameters are exported through an SNMP agent for remote monitoring.

## Architecture
GNU Radio → Python Shared State → SNMP Agent → External SNMP Client

## Requirements
- GNU Radio 3.10+
- Python 3.10+
- pysnmp

## Run Instructions
1. Start GNU Radio flowgraph
2. Run snmp_agent.py
3. Query via:
   snmpget -v2c -c public localhost:1161 1.3.6.1.4.1.x.x
