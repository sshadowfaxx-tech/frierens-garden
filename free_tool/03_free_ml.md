# 🆓 FREE ML Infrastructure Alternatives Guide

> Replace expensive SageMaker and hosted ML services with $0 self-hosted solutions

---

## Table of Contents

1. [ML Training](#1-ml-training)
2. [Model Serving](#2-model-serving)
3. [Feature Store](#3-feature-store)
4. [Model Registry](#4-model-registry)
5. [Inference Optimization](#5-inference-optimization)
6. [Alternative Compute](#6-alternative-compute)
7. [Consumer Hardware Setup Guide](#7-consumer-hardware-setup-guide-rtx-4090)

---

## 1. ML Training

### 1.1 Local GPU Training

**Cost: $0 (after hardware investment)**

#### Pros:
- No usage fees
- Complete control over environment
- No data privacy concerns
- No session timeouts

#### Recommended Hardware (Consumer GPUs):
| GPU | VRAM | Best For | Price Range |
|-----|------|----------|-------------|
| RTX 4090 | 24GB | Small-medium models, fine-tuning | ~$1,600 |
| RTX 3090 | 24GB | Budget alternative | ~$800-1,000 |
| RTX 4080 | 16GB | Entry-level training | ~$1,200 |
| RTX 6000 Ada | 48GB | Professional workloads | ~$6,800 |

#### Quick Setup:
```bash
# Ubuntu setup for RTX 4090
# 1. Install NVIDIA drivers (CUDA 12.0+)
ubuntu-drivers devices
sudo ubuntu-drivers autoinstall

# 2. Install CUDA toolkit
wget https://developer.download.nvidia.com/compute/cuda/12.4.0/local_installers/cuda_12.4.0_550.54.14_linux.run
sudo sh cuda_12.4.0_550.54.14_linux.run

# 3. Install cuDNN
sudo apt install nvidia-cudnn

# 4. Setup Python environment
conda create -n ml python=3.10
conda activate ml

# 5. Install PyTorch with CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 6. Install TensorFlow
pip install tensorflow

# 7. Verify installation
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
python -c "import tensorflow as tf; print(f'TF: {tf.__version__}, GPUs: {tf.config.list_physical_devices(\"GPU\")}')"
```

---

### 1.2 Google Colab (Free Tier)

**Cost: $0**

#### Limits (Free Tier):
- **GPU:** T4 (12GB VRAM) - ~12 hours max session
- **RAM:** 12.7GB system RAM
- **Storage:** ~78GB (including OS)
- **Idle timeout:** 90 minutes
- **Max session:** 12 hours

#### Pro Tips:
```python
# Check GPU allocation
!nvidia-smi

# Mount Google Drive for persistent storage
from google.colab import drive
drive.mount('/content/drive')

# Enable high-RAM (if available)
# Runtime → Change runtime type → High-RAM

# Use mixed precision training for faster compute
from tensorflow.keras import mixed_precision
policy = mixed_precision.Policy('mixed_float16')
mixed_precision.set_global_policy(policy)
```

#### Avoiding Disconnects:
```python
# Keep Colab alive (run in console)
# Ctrl+Shift+I → Console → paste:
function KeepClicking(){
  console.log("Clicking");
  document.querySelector("colab-toolbar-button#connect").click()
}
setInterval(KeepClicking, 60000)
```

---

### 1.3 Kaggle Notebooks

**Cost: $0**

#### Limits:
- **GPU:** P100 or T4 (30 GPU hours/week)
- **TPU:** 20 TPU hours/week
- **Session duration:** 9 hours max
- **Storage:** 20GB persistent
- **Background execution:** Available

#### Setup:
```python
# Enable GPU/TPU
# Settings → Accelerator → GPU/TPU

# Install packages
!pip install -q transformers datasets accelerate

# Import and use
import torch
from transformers import AutoModel, AutoTokenizer

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Kaggle datasets are pre-downloaded
import os
print(os.listdir('/kaggle/input/'))
```

#### Key Features:
- Direct integration with Kaggle datasets
- Public datasets library access
- Competition submissions
- Version control for notebooks

---

### 1.4 AWS SageMaker Studio Lab

**Cost: $0 (no credit card required)**

#### Limits:
- **GPU:** 4 hours per session
- **Daily limit:** 4 hours GPU per 24 hours
- **CPU:** 8 hours per session
- **Storage:** 15GB persistent

#### Setup:
1. Request access at: https://studiolab.sagemaker.aws/
2. Wait for approval (usually 1-3 days)
3. Launch JupyterLab environment
4. GitHub integration built-in

---

## 2. Model Serving

### 2.1 TensorFlow Serving

**Cost: $0 (open source)**

#### Docker Deployment:
```bash
# Pull TF Serving image
docker pull tensorflow/serving:latest-gpu

# Prepare model directory structure
# /models/my_model/1/saved_model.pb

# Run TF Serving
docker run -p 8501:8501 \
  --mount type=bind,source=/path/to/my_model/,target=/models/my_model \
  -e MODEL_NAME=my_model \
  -t tensorflow/serving:latest-gpu

# REST API endpoint: http://localhost:8501/v1/models/my_model:predict
```

#### Model Configuration (models.config):
```protobuf
model_config_list {
  config {
    name: 'my_model'
    base_path: '/models/my_model/'
    model_platform: 'tensorflow'
    model_version_policy {
      specific {
        versions: 1
        versions: 2
      }
    }
  }
}
```

#### Client Request:
```python
import requests
import json

data = json.dumps({
    "signature_name": "serving_default",
    "instances": [[1.0, 2.0, 3.0]]
})

response = requests.post(
    'http://localhost:8501/v1/models/my_model:predict',
    data=data,
    headers={"content-type": "application/json"}
)
print(response.json())
```

---

### 2.2 TorchServe

**Cost: $0 (open source)**

#### Installation & Setup:
```bash
# Install TorchServe
pip install torchserve torch-model-archiver

# Create .mar file (model archive)
torch-model-archiver \
  --model-name my_model \
  --version 1.0 \
  --model-file model.py \
  --serialized-file model.pth \
  --handler custom_handler.py \
  --export-path model-store

# Start TorchServe
torchserve --start \
  --model-store model-store \
  --models my_model=my_model.mar
```

#### Custom Handler Example:
```python
# custom_handler.py
from ts.torch_handler.base_handler import BaseHandler
import torch
import json

class ModelHandler(BaseHandler):
    def preprocess(self, data):
        return torch.tensor(json.loads(data[0]["body"]))
    
    def inference(self, data, context):
        return self.model(data).tolist()
    
    def postprocess(self, inference_output):
        return [inference_output]
```

#### Management APIs:
```bash
# List models
curl http://localhost:8081/models

# Scale workers
curl -X PUT "http://localhost:8081/models/my_model?min_worker=2&max_worker=4"

# Describe model
curl http://localhost:8081/models/my_model/1.0
```

---

### 2.3 MLflow (Self-Hosted)

**Cost: $0 (open source)**

#### Setup MLflow Tracking Server:
```bash
# Install
pip install mlflow

# Start tracking server
mlflow server \
  --backend-store-uri postgresql://user:pass@localhost/mlflow \
  --default-artifact-root s3://my-bucket/mlflow \
  --host 0.0.0.0 \
  --port 5000

# Or use local file storage (dev only)
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlruns \
  --host 0.0.0.0
```

#### Model Serving with MLflow:
```python
import mlflow

# Log model
with mlflow.start_run():
    mlflow.sklearn.log_model(model, "model", registered_model_name="my_model")

# Serve model
# mlflow models serve -m models:my_model/1 -p 1234
```

#### Docker Deployment:
```bash
# Build serving image
mlflow models build-docker -m models:my_model/1 -n my-mlflow-model

# Run container
docker run -p 5001:8080 my-mlflow-model
```

---

### 2.4 BentoML

**Cost: $0 (open source)**

#### Service Definition:
```python
# service.py
import bentoml
from bentoml.io import NumpyNdarray, JSON

# Load model from BentoML store
model_ref = bentoml.sklearn.get("sklearn_model:latest")
model_runner = model_ref.to_runner()

# Create service
svc = bentoml.Service("predictor", runners=[model_runner])

@svc.api(input=NumpyNdarray(), output=JSON())
def predict(input_data):
    result = model_runner.predict.run(input_data)
    return {"predictions": result.tolist()}
```

#### Register & Serve:
```bash
# Save model to BentoML store
python -c "
import bentoml
from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier()
bentoml.sklearn.save_model('sklearn_model', model)
"

# Run development server
bentoml serve service.py:svc --reload

# Build production Bento
bentoml build

# Build Docker image
bentoml containerize predictor:latest

# Run production container
docker run -p 3000:3000 predictor:latest
```

---

## 3. Feature Store

### 3.1 Feast (Open Source)

**Cost: $0 (open source)**

#### Installation:
```bash
pip install feast

# Initialize project
feast init my_feature_repo
cd my_feature_repo/feature_repo
```

#### Feature Definition (features.py):
```python
from feast import Entity, Feature, FeatureView, ValueType
from feast.types import Float32, Int64, String
from datetime import timedelta

# Define entity
user = Entity(
    name="user_id",
    value_type=ValueType.INT64,
    description="User ID"
)

# Define feature view
user_features = FeatureView(
    name="user_features",
    entities=["user_id"],
    ttl=timedelta(days=1),
    schema=[
        Field(name="age", dtype=Int64),
        Field(name="income", dtype=Float32),
        Field(name="city", dtype=String),
    ],
    online=True,
    source=user_data_source,
)
```

#### Configuration (feature_store.yaml):
```yaml
project: my_project
registry: data/registry.db
provider: local
online_store:
    type: redis
    connection_string: localhost:6379
offline_store:
    type: file
```

#### Usage:
```python
from feast import FeatureStore

store = FeatureStore(repo_path=".")

# Materialize features to online store
store.materialize_incremental(end_date=datetime.now())

# Retrieve online features
features = store.get_online_features(
    features=[
        "user_features:age",
        "user_features:income",
    ],
    entity_rows=[{"user_id": 1}],
).to_dict()
```

---

### 3.2 Custom Redis/PostgreSQL Solution

**Cost: $0 (self-hosted)**

#### Redis Feature Store:
```python
import redis
import json
import pickle
from datetime import datetime, timedelta

class RedisFeatureStore:
    def __init__(self, host='localhost', port=6379, db=0):
        self.r = redis.Redis(host=host, port=port, db=db)
    
    def set_features(self, entity_id, features, ttl=86400):
        """Store features with TTL"""
        key = f"features:{entity_id}"
        self.r.setex(key, ttl, pickle.dumps(features))
    
    def get_features(self, entity_id):
        """Retrieve features"""
        key = f"features:{entity_id}"
        data = self.r.get(key)
        return pickle.loads(data) if data else None
    
    def get_batch_features(self, entity_ids):
        """Batch retrieve"""
        keys = [f"features:{eid}" for eid in entity_ids]
        data = self.r.mget(keys)
        return [pickle.loads(d) if d else None for d in data]

# Usage
store = RedisFeatureStore()
store.set_features("user_123", {"age": 30, "income": 50000})
features = store.get_features("user_123")
```

#### PostgreSQL Feature Store:
```python
import psycopg2
import pandas as pd
from sqlalchemy import create_engine

class PostgresFeatureStore:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)
    
    def create_feature_table(self, table_name, schema):
        """Create feature table"""
        columns = ", ".join([f"{col} {dtype}" for col, dtype in schema.items()])
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} (entity_id TEXT PRIMARY KEY, {columns}, created_at TIMESTAMP DEFAULT NOW())"
        with self.engine.connect() as conn:
            conn.execute(sql)
    
    def insert_features(self, table_name, df):
        """Insert/update features"""
        df.to_sql(table_name, self.engine, if_exists='append', index=False)
    
    def get_features(self, table_name, entity_ids):
        """Retrieve features"""
        ids = ", ".join([f"'{eid}'" for eid in entity_ids])
        sql = f"SELECT * FROM {table_name} WHERE entity_id IN ({ids})"
        return pd.read_sql(sql, self.engine)

# Usage
store = PostgresFeatureStore("postgresql://user:pass@localhost/db")
store.create_feature_table("user_features", {"age": "INTEGER", "income": "FLOAT"})
```

---

## 4. Model Registry

### 4.1 MLflow Model Registry

**Cost: $0 (open source)**

```python
import mlflow
import mlflow.sklearn

# Set tracking URI
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("my_experiment")

with mlflow.start_run():
    # Log parameters and metrics
    mlflow.log_param("n_estimators", 100)
    mlflow.log_metric("accuracy", 0.95)
    
    # Log and register model
    mlflow.sklearn.log_model(
        sk_model=model,
        artifact_path="model",
        registered_model_name="my_classifier"
    )

# Transition model stages
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="my_classifier",
    version=1,
    stage="Production"
)

# Load registered model
model = mlflow.sklearn.load_model("models:/my_classifier/Production")
```

---

### 4.2 DVC (Data Version Control)

**Cost: $0 (open source)**

```bash
# Install
pip install dvc

# Initialize
git init
dvc init
git commit -m "Initialize DVC"

# Track large files/models
dvc add model.pkl
git add model.pkl.dvc .gitignore
git commit -m "Add model"

# Set remote storage
dvc remote add -d myremote s3://mybucket/dvc
dvc push

# Pull models
dvc pull

# Version models with Git tags
git tag -a v1.0 -m "Model version 1.0"
git push origin v1.0
```

#### DVC Pipeline:
```yaml
# dvc.yaml
stages:
  prepare:
    cmd: python prepare.py
    deps:
      - data/raw.csv
    outs:
      - data/prepared.csv
  
  train:
    cmd: python train.py
    deps:
      - data/prepared.csv
      - train.py
    outs:
      - model.pkl
    metrics:
      - metrics.json:
          cache: false
```

---

### 4.3 Git LFS (Large File Storage)

**Cost: $0 (self-hosted or free tier)**

```bash
# Install Git LFS
git lfs install

# Track model files
git lfs track "*.pkl"
git lfs track "*.h5"
git lfs track "models/**"

# Commit tracking configuration
git add .gitattributes
git commit -m "Track models with LFS"

# Push to remote
git add model.pkl
git commit -m "Add trained model"
git push

# Self-hosted LFS server (optional)
# Use GitLab, Gitea, or https://github.com/lfs-server/lfs-server
```

---

## 5. Inference Optimization

### 5.1 ONNX Runtime

**Cost: $0 (open source)**

#### Export to ONNX:
```python
# PyTorch to ONNX
import torch

model.eval()
dummy_input = torch.randn(1, 3, 224, 224)

torch.onnx.export(
    model,
    dummy_input,
    "model.onnx",
    export_params=True,
    opset_version=14,
    do_constant_folding=True,
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
)

# TensorFlow to ONNX
# pip install tf2onnx
# python -m tf2onnx.convert --saved-model tf_model --output model.onnx
```

#### Optimize with ONNX Runtime:
```python
import onnxruntime as ort
import numpy as np

# Session options for optimization
sess_options = ort.SessionOptions()
sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
sess_options.intra_op_num_threads = 4

# Use GPU execution provider
providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
session = ort.InferenceSession("model.onnx", sess_options, providers=providers)

# Run inference
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name
input_data = np.random.randn(1, 3, 224, 224).astype(np.float32)
result = session.run([output_name], {input_name: input_data})
```

#### Quantization:
```python
from onnxruntime.quantization import quantize_dynamic, QuantType

# Dynamic quantization (simplest)
quantize_dynamic(
    model_input="model.onnx",
    model_output="model_quantized.onnx",
    weight_type=QuantType.QInt8
)

# Static quantization (better performance)
from onnxruntime.quantization import quantize_static, CalibrationDataReader, QuantType

class DataReader(CalibrationDataReader):
    def __init__(self):
        self.data = [...]  # Your calibration data
        self.iter = iter(self.data)
    
    def get_next(self):
        return next(self.iter, None)

quantize_static(
    model_input="model.onnx",
    model_output="model_static_quant.onnx",
    calibration_data_reader=DataReader(),
    quant_format=QuantType.QInt8
)
```

---

### 5.2 TensorRT

**Cost: $0 (free, requires NVIDIA GPU)**

#### Convert ONNX to TensorRT:
```bash
# Using trtexec (included with TensorRT)
trtexec --onnx=model.onnx \
  --saveEngine=model.trt \
  --fp16 \
  --workspace=4096

# INT8 quantization
trtexec --onnx=model.onnx \
  --saveEngine=model_int8.trt \
  --int8 \
  --calibInt8=calibration.cache
```

#### Python API:
```python
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
import numpy as np

class TensorRTInference:
    def __init__(self, engine_path):
        self.logger = trt.Logger(trt.Logger.WARNING)
        
        # Load engine
        with open(engine_path, 'rb') as f:
            runtime = trt.Runtime(self.logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        
        self.context = self.engine.create_execution_context()
        
        # Allocate buffers
        self.allocate_buffers()
    
    def allocate_buffers(self):
        self.inputs = []
        self.outputs = []
        self.bindings = []
        self.stream = cuda.Stream()
        
        for binding in self.engine:
            size = trt.volume(self.engine.get_binding_shape(binding))
            dtype = trt.nptype(self.engine.get_binding_dtype(binding))
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            self.bindings.append(int(device_mem))
            
            if self.engine.binding_is_input(binding):
                self.inputs.append({'host': host_mem, 'device': device_mem})
            else:
                self.outputs.append({'host': host_mem, 'device': device_mem})
    
    def infer(self, input_data):
        # Copy input to device
        np.copyto(self.inputs[0]['host'], input_data.ravel())
        cuda.memcpy_htod_async(self.inputs[0]['device'], self.inputs[0]['host'], self.stream)
        
        # Run inference
        self.context.execute_async_v2(bindings=self.bindings, stream_handle=self.stream.handle)
        
        # Copy output to host
        cuda.memcpy_dtoh_async(self.outputs[0]['host'], self.outputs[0]['device'], self.stream)
        self.stream.synchronize()
        
        return self.outputs[0]['host']

# Usage
model = TensorRTInference("model.trt")
output = model.infer(np.random.randn(1, 3, 224, 224).astype(np.float32))
```

---

### 5.3 Quantization Techniques

#### PyTorch Quantization:
```python
import torch
import torch.quantization

# Post-training static quantization
model.eval()
model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
torch.quantization.prepare(model, inplace=True)

# Calibrate with representative data
with torch.no_grad():
    for data, _ in calibration_loader:
        model(data)

torch.quantization.convert(model, inplace=True)

# Save quantized model
torch.jit.save(torch.jit.script(model), "model_quantized.pt")
```

#### TensorFlow Quantization:
```python
import tensorflow as tf

# Post-training quantization
converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
converter.optimizations = [tf.lite.Optimize.DEFAULT]

# Full integer quantization (requires representative dataset)
def representative_dataset():
    for _ in range(100):
        data = np.random.rand(1, 224, 224, 3).astype(np.float32)
        yield [data]

converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

tflite_model = converter.convert()
with open('model_quantized.tflite', 'wb') as f:
    f.write(tflite_model)
```

---

## 6. Alternative Compute

### 6.1 RunPod

**Cost: ~$0.34-$0.69/hr for RTX 4090, per-second billing**

#### Pricing (2025):
| GPU | Community Cloud | Secure Cloud |
|-----|-----------------|--------------|
| RTX 4090 | $0.34/hr | $0.69/hr |
| RTX 5090 | $0.69/hr | - |
| A100 80GB | $1.19/hr | $1.64/hr |
| H100 | $1.99/hr | $2.39/hr |
| H200 | $3.59/hr | - |
| B200 | $5.98/hr | - |

#### Setup:
```bash
# Use Serverless for auto-scaling inference
# Use Pods for persistent training environments

# Connect via SSH
ssh root@<pod-ip> -p <port>

# Pre-configured templates available:
# - PyTorch
# - TensorFlow
# - JAX
# - Stable Diffusion
# - LLaMA/LLM training
```

#### Serverless Deployment:
```python
# deploy.py for RunPod serverless
import runpod

def handler(job):
    job_input = job['input']
    # Your inference code here
    result = model.predict(job_input)
    return result

runpod.serverless.start({'handler': handler})
```

---

### 6.2 Vast.ai

**Cost: 50-70% cheaper than hyperscalers, marketplace pricing**

#### Pricing (Approximate):
| GPU | Price Range |
|-----|-------------|
| RTX 4090 | $0.20-$0.35/hr |
| RTX 3090 | $0.15-$0.25/hr |
| A100 40GB | $0.50-$0.70/hr |
| A100 80GB | $0.60-$0.80/hr |
| H100 | $1.77-$2.50/hr |

#### Features:
- Marketplace model (peer-to-peer rentals)
- Spot instances available
- SSH access
- JupyterLab support
- Template marketplace

#### CLI Usage:
```bash
# Install Vast CLI
pip install vastai

# Search for instances
vastai search offers 'gpu_name=RTX_4090'

# Create instance
vastai create instance <offer-id> --image pytorch/pytorch --disk 30

# Connect
ssh -p <port> root@<host>
```

---

### 6.3 Other Budget Options

| Provider | Best For | Pricing |
|----------|----------|---------|
| **Thunder Compute** | A100 at ~$0.66/hr | Budget training |
| **DataCrunch** | V100 at ~$0.39/hr | Mid-sized models |
| **Lambda Labs** | A100 at $1.29/hr | Research workloads |
| **Paperspace** | Free tier M4000 | Beginners |
| **AWS Spot** | 60-90% discount | Fault-tolerant jobs |
| **GCP Preemptible** | Similar to AWS Spot | Batch processing |

---

## 7. Consumer Hardware Setup Guide (RTX 4090)

### 7.1 Hardware Requirements

| Component | Recommendation | Budget Alternative |
|-----------|---------------|-------------------|
| GPU | RTX 4090 24GB | RTX 3090 24GB |
| CPU | AMD Ryzen 9 7950X | Intel i7-13700K |
| RAM | 64GB DDR5 | 32GB DDR4 |
| Storage | 2TB NVMe SSD (PCIe 4.0) | 1TB NVMe SSD |
| PSU | 1000W 80+ Gold | 850W 80+ Gold |
| Cooling | Custom loop or high-end air | Premium air cooler |

### 7.2 Complete Ubuntu Setup Script

```bash
#!/bin/bash
# setup_rtx4090.sh - Complete ML environment setup for RTX 4090

set -e

echo "=== RTX 4090 ML Environment Setup ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y build-essential git wget curl vim htop nvtop \
    software-properties-common apt-transport-https ca-certificates \
    gnupg lsb-release

# Install NVIDIA driver (latest)
ubuntu-drivers devices
sudo ubuntu-drivers autoinstall

# Reboot required here
# sudo reboot

# Install CUDA 12.4
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.4.0/local_installers/cuda-repo-ubuntu2204-12-4-local_12.4.0-550.54.14-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2204-12-4-local_12.4.0-550.54.14-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2204-12-4-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda-toolkit-12-4

# Set environment variables
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Install cuDNN
# Download from https://developer.nvidia.com/cudnn (requires login)
# sudo dpkg -i cudnn-local-repo-*.deb
# sudo apt update
# sudo apt install libcudnn8 libcudnn8-dev

# Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
rm Miniconda3-latest-Linux-x86_64.sh
echo 'export PATH="$HOME/miniconda/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Create ML environment
conda create -n ml python=3.10 -y
conda activate ml

# Install PyTorch (CUDA 12.1)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install TensorFlow
pip install tensorflow

# Install ML tools
pip install transformers datasets accelerate bitsandbytes peft \
    mlflow onnxruntime-gpu tensorrt jupyterlab wandb \
    numpy pandas scikit-learn matplotlib seaborn plotly \
    fastapi uvicorn bentoml

# Install Docker
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER

# Install NVIDIA Docker
# Add the package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-docker2
sudo systemctl restart docker

# Verify installations
echo "=== Verification ==="
nvidia-smi
nvcc --version
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"
python -c "import tensorflow as tf; print(f'TensorFlow: {tf.__version__}'); print(f'GPUs: {tf.config.list_physical_devices(\"GPU\")}')"

echo "=== Setup Complete! ==="
echo "Reboot recommended: sudo reboot"
```

### 7.3 Multi-GPU Setup (RTX 4090)

⚠️ **Important:** RTX 4090s have NVLink disabled. Use the following workaround:

```bash
# Add to ~/.bashrc for multi-GPU training
export NCCL_P2P_DISABLE=1
export CUDA_VISIBLE_DEVICES=0,1,2,3

# For PyTorch DDP
# Slower but functional
torchrun --nproc_per_node=4 train.py
```

### 7.4 Optimization Tips for RTX 4090

```python
# Enable TF32 for faster training (Ampere/Ada GPUs)
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

# Enable cudnn benchmarking
torch.backends.cudnn.benchmark = True

# Mixed precision training
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()
for data, target in dataloader:
    optimizer.zero_grad()
    
    with autocast():
        output = model(data)
        loss = criterion(output, target)
    
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()

# Memory optimization with gradient checkpointing
model.gradient_checkpointing_enable()

# Use Flash Attention 2 (if supported)
pip install flash-attn --no-build-isolation
```

### 7.5 Model Size Limits (RTX 4090 - 24GB)

| Precision | Max Model Size | Example Models |
|-----------|---------------|----------------|
| FP32 | ~6B params | GPT-2 XL, T5-large |
| FP16/BF16 | ~12B params | LLaMA-7B (with offloading) |
| INT8 | ~16B params | LLaMA-13B ( quantized) |
| INT4 | ~24B params | LLaMA-30B (4-bit) |

### 7.6 Cost Comparison: Local vs Cloud

| Scenario | Local (RTX 4090) | Cloud (RunPod RTX 4090) |
|----------|-----------------|------------------------|
| Initial Cost | $1,600 (one-time) | $0 |
| 8 hrs/day, 5 days/week | $0 | ~$550/month |
| Break-even point | 3 months | - |
| 2-year total | $1,600 | ~$13,200 |
| Performance | 100% | ~90-95% |

**ROI Analysis:** After ~3 months of regular use, local hardware pays for itself.

---

## Summary: Free ML Stack Recommendations

| Function | Recommended Tool | Alternative |
|----------|-----------------|-------------|
| Training | Local GPU / Kaggle | Colab Free |
| Serving | BentoML | TorchServe/TF Serving |
| Feature Store | Feast + Redis | Custom PostgreSQL |
| Model Registry | MLflow | DVC |
| Optimization | ONNX Runtime + TensorRT | Quantization |
| Cheap Compute | Vast.ai | RunPod Community |

---

## References & Resources

- [Feast Documentation](https://docs.feast.dev/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [BentoML Documentation](https://docs.bentoml.com/)
- [ONNX Runtime Docs](https://onnxruntime.ai/docs/)
- [TensorRT Documentation](https://docs.nvidia.com/deeplearning/tensorrt/)
- [RunPod Documentation](https://docs.runpod.io/)
- [Vast.ai Documentation](https://vast.ai/docs/)

---

*Last Updated: March 2025*
*Contributing: PRs welcome for updates and corrections*
