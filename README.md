# Kubernetes & Airflow 기반 Keypoint Detection Pipeline

Airflow와 MLflow를 활용하여 Kubernetes 환경에서 Keypoint Detection 모델의 자동화 파이프라인 및 버전 관리를 수행하는 프로젝트입니다.
PVC 볼륨과 GPU 리소스를 연동하여 데이터셋 생성부터 실험 설정, 모델 학습까지 하나의 Airflow DAG에서 자동으로 실행할 수 있으며,
이를 통해 다수 사용자가 동시에 효율적으로 모델을 학습·관리하고, MLflow로 모델 및 실험 이력을 체계적으로 추적할 수 있도록 하였습니다
![Image](https://github.com/user-attachments/assets/1892e5a9-f939-4ce0-885c-e2554fd6e148)

## 프로젝트 개요

- **Airflow** : DAG(Directed Acyclic Graph)를 정의하여 데이터 전처리 → 실험 설정 → 모델 학습 과정을 자동화

- **Kubernetes** : Airflow KubernetesPodOperator를 통해 작업을 컨테이너 단위로 분리, PVC 볼륨 및 GPU 리소스를 효율적으로 사용

- **학습 관련 코드** : 데이터 전처리 → 실험 설정 → 모델 학습 코드
   - https://github.com/tae-uk0403/Auto-training-pipeline

- **전체 과정** : https://pinguengineer.tistory.com/12 

### 주요 서버 주소
- **Airflow** : [http://203.252.147.200:8105](http://203.252.147.200:8105)  
- **MLflow** : [http://203.252.147.200:8106](http://203.252.147.200:8106)

## 프로젝트 구조

### 1. common_config.py
- Kubernetes에서 PVC 볼륨, GPU 리소스, SHM 볼륨 등을 공통으로 설정하는 함수를 정의

- Airflow의 `KubernetesPodOperator` 설정 시 PVC 볼륨과 GPU 리소스를 할당

### 2. config/test_config.yaml
- 여러 실험(Experiment)을 YAML 형식으로 정의
- 여러 experiment를 생성하고, 생성한 yaml을 기반으로 DAG를 동적을 생성
- 여러 곳에서 parameter를 설정했던 기존의 문제점을 해결하기 위해 config.yaml파일 하나에서 parameter 설정 관리

### 3. run_dag.py
- Airflow에서 사용할 DAG(파이프라인)를 정의하는 파일
- config 디렉토리 내 yaml를 읽어 experiments 아래에 정의된 여러 실험을 순회하며 DAG를 생성
- 각 DAG는 아래 세 가지 태스크로 구성
  1. Preprocess (make_dataset2.py)
     - COCO 형식으로 데이터셋을 자동 변환합니다.
  2. Make Experiments (make_experiments.py)
     - 학습에 필요한 YAML 설정 파일을 업데이트합니다.
  3. Train (train/main/train.py)
     - 모델 훈련 스크립트를 실행 (GPU 사용)