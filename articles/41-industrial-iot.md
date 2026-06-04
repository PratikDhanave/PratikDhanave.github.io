---
title: "Industrial IoT: Real-Time Data From Manufacturing Plants to Cloud Analytics"
description: "Production-grade technical deep-dive on IndustrialIoT:Real-TimeDataFromManufacturingPlantstoCloudAnalytics"
keywords: ["41-industrial-iot"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
---

# Industrial IoT: Real-Time Data From Manufacturing Plants to Cloud Analytics

**Manufacturing plants produce data at machine speed.** A single assembly line has 50+ sensors: temperature, vibration, pressure, humidity. Each sends a reading every 100ms. That's 500 data points per second, per line. At Litmus, we built the backend to ingest this in real-time and surface anomalies before machines fail.

---

## The Challenge

**Sensor Data Characteristics:**
- **High velocity:** 500+ messages/second per plant
- **Low latency requirement:** Detect anomalies in < 5 seconds
- **Edge connectivity:** Plants often have poor/intermittent internet
- **Legacy protocols:** MQTT, OPC-UA (not REST)

### **Architecture**

```
Manufacturing Plant
  ├─ Sensor 1 (MQTT)
  ├─ Sensor 2 (MQTT)
  ├─ PLC Controller (OPC-UA) ← Siemens, ABB, Schneider
  └─ Local Buffer (queue anomalous readings)
           ↓
  Edge Gateway (Kubernetes on-premise)
           ↓
  Cloud (Python streaming pipelines)
           ↓
  Analytics + Anomaly Detection
```

---

## MQTT: The Sensor Protocol

MQTT is lightweight (< 100 bytes overhead). Perfect for sensors.

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    """Handle incoming sensor data."""
    payload = json.loads(msg.payload)
    # {'sensor_id': 'TEMP-01', 'temperature': 42.5, 'timestamp': 1686...}
    
    # Write to stream (Kafka, Pub/Sub)
    stream_producer.send({
        'sensor_id': payload['sensor_id'],
        'value': payload['temperature'],
        'timestamp': payload['timestamp'],
        'plant_id': userdata['plant_id'],
    })

client = mqtt.Client(client_id="edge-gateway-01")
client.user_data_set({'plant_id': 'plant-xyz'})
client.on_message = on_message
client.connect("plant-mqtt-broker.local", 1883, keepalive=60)
client.subscribe("sensors/+/data")  # Subscribe to all sensors
client.loop_forever()
```

---

## OPC-UA: The Industrial Standard

OPC-UA is a protocol for talking to PLCs (Programmable Logic Controllers) in factories.

```python
from opcua import Client

class OPCUAPoller:
    def __init__(self, endpoint: str):
        self.client = Client(endpoint)
        self.client.connect()
    
    def poll_registers(self, poll_interval_ms: int = 100):
        """Poll PLC registers every 100ms."""
        while True:
            # Read temperature from register
            temperature_node = self.client.get_node("ns=2;i=1001")
            temp_value = temperature_node.get_value()
            
            # Read pressure from register
            pressure_node = self.client.get_node("ns=2;i=1002")
            pressure_value = pressure_node.get_value()
            
            # Send to stream
            stream.send({
                'sensor_id': 'PLC-TEMP',
                'value': temp_value,
                'timestamp': datetime.now(),
            })
            
            time.sleep(poll_interval_ms / 1000)
    
    def disconnect(self):
        self.client.disconnect()
```

---

## Streaming Analytics: Anomaly Detection

Raw sensor data is noise. Transform it into insights.

```python
from apache_beam import Pipeline, Map, Filter
from apache_beam.options.pipeline_options import PipelineOptions

class SensorAnomalyDetector:
    def __init__(self):
        self.baseline_temp = 42.0  # Normal operating temperature
        self.threshold = 5.0  # Alert if > 5°C deviation
    
    def detect_anomaly(self, reading):
        """Flag readings outside normal range."""
        if abs(reading['value'] - self.baseline_temp) > self.threshold:
            return {
                'sensor_id': reading['sensor_id'],
                'value': reading['value'],
                'deviation': reading['value'] - self.baseline_temp,
                'status': 'ANOMALY',
                'timestamp': reading['timestamp'],
            }
        return None

# Dataflow pipeline
pipeline = Pipeline(options=PipelineOptions())

anomalies = (
    pipeline
    | 'Read from Pub/Sub' >> beam.io.gcp.pubsub.ReadFromPubSub(topic='sensor-data')
    | 'Parse JSON' >> Map(lambda x: json.loads(x))
    | 'Detect Anomalies' >> Map(detector.detect_anomaly)
    | 'Filter Nulls' >> Filter(lambda x: x is not None)
    | 'Write Alerts' >> beam.io.gcp.pubsub.WriteToPubSub(topic='anomalies')
)

pipeline.run()
```

---

## Edge-to-Cloud: Handling Disconnects

Plants have poor internet. Edge gateways buffer readings locally and sync when connection restored.

```python
import sqlite3
from datetime import datetime, timedelta

class EdgeBuffer:
    def __init__(self, db_path: str = "sensor_buffer.db"):
        self.db = sqlite3.connect(db_path)
        self._init_schema()
    
    def buffer_reading(self, reading: dict):
        """Write to local DB if cloud unreachable."""
        self.db.execute("""
            INSERT INTO buffered_readings
            (sensor_id, value, timestamp, synced)
            VALUES (?, ?, ?, 0)
        """, (reading['sensor_id'], reading['value'], reading['timestamp']))
        self.db.commit()
    
    def sync_to_cloud(self, cloud_endpoint: str):
        """Send buffered data once connection restored."""
        unsynced = self.db.execute("""
            SELECT id, sensor_id, value, timestamp FROM buffered_readings
            WHERE synced = 0
            ORDER BY timestamp ASC
        """).fetchall()
        
        for row_id, sensor_id, value, timestamp in unsynced:
            try:
                cloud_client.send({
                    'sensor_id': sensor_id,
                    'value': value,
                    'timestamp': timestamp,
                })
                self.db.execute("UPDATE buffered_readings SET synced = 1 WHERE id = ?", (row_id,))
                self.db.commit()
            except Exception as e:
                # Connection failed, retry later
                break

# Usage
buffer = EdgeBuffer()
try:
    cloud_client.send(reading)
except ConnectionError:
    buffer.buffer_reading(reading)
    # Retry on timer
    sync_thread = threading.Thread(target=buffer.sync_to_cloud)
    sync_thread.start()
```

---

**Tags:** #IoT #MQTT #OPC-UA #EdgeComputing #Streaming #Manufacturing

**Published:** June 2026  
**Author:** Pratik Dhanave  
**Related Projects:** Litmus Industrial IoT
