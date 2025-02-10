
import os
import yaml
from datetime import datetime
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

import os
import yaml
from utils.volumes import get_pvc_volume, get_volume_mounts, get_shm_volume_and_mount, get_gpu_resources



def create_experiment_dag(dag_id, config, schedule_interval=None):
    default_args = {
        'owner': 'airflow',
        'start_date': datetime(2025, 2, 3),
        'retries': 1,
        'retry_delay': 300,
    }

    dag = DAG(dag_id, default_args=default_args, schedule_interval=schedule_interval)

    # 공통 볼륨 및 마운트 정보 설정
    pvc_volume = get_pvc_volume()
    volume_mounts = get_volume_mounts()
    shm_volume, shm_mount = get_shm_volume_and_mount()
    gpu_resources = get_gpu_resources()

    # 태스크 1: 데이터 전처리
    preprocess = KubernetesPodOperator(
        task_id='preprocess',
        name='preprocess-pod',
        namespace='default',
        image='ntw0403/autotrain:3.1',
        cmds=['python', 'make_dataset2.py'],
        arguments=[
            '-d', config.get('data_dir'),
            '-ext', config.get('ext'),
            '-n', config.get('n'),
            '-sc', config.get('sc'),
            '-c', config.get('c'),
            '-tp', config.get('tp')
        ],
        volumes=[pvc_volume],
        volume_mounts=volume_mounts,
        kubernetes_conn_id='kubernetes_default',
        get_logs=True,
        is_delete_operator_pod=True,
        startup_timeout_seconds=3600,
        dag=dag,
    )

    # 태스크 2: 데이터 확인
    # check_data = KubernetesPodOperator(
    #     task_id='check_data',
    #     name='check-data-pod',
    #     namespace='default',
    #     image='ntw0403/autotrain:3.1',
    #     cmds=["sh", "-c"],
    #     arguments=[
    #         """
    #         echo "Current directory:";
    #         pwd;
    #         echo "Files in current directory:";
    #         ls -al;
    #         echo "Files in data:";
    #         ls -al data;
    #         echo "Sleeping for 15 seconds...";
    #         sleep 15
    #         """
    #     ],
    #     volumes=[pvc_volume],
    #     volume_mounts=volume_mounts,
    #     kubernetes_conn_id='kubernetes_default',
    #     get_logs=True,
    #     is_delete_operator_pod=True,
    #     startup_timeout_seconds=3600,
    #     dag=dag,
    # )

    # 태스크 3: 실험 설정
    make_experiments = KubernetesPodOperator(
        task_id='make_experiments',
        name='make-experiments-pod',
        namespace='default',
        image='ntw0403/autotrain:3.1',
        cmds=['python', 'make_experiments.py'],
        arguments=[
            '--num-keypoints', config.get('num_keypoints'),
            '--flip-fairs', config.get('flip_fairs'),
            '--data-format', config.get('data_format'),
            '--data-root', config.get('data_root'),
            '--begin-epoch', config.get('begin_epoch'),
            '--end-epoch', config.get('end_epoch'),
            '--config-file', config.get('config_file'),
            '--output-file', config.get('output_file')
        ],
        volumes=[pvc_volume],
        volume_mounts=volume_mounts,
        kubernetes_conn_id='kubernetes_default',
        get_logs=True,
        is_delete_operator_pod=True,
        startup_timeout_seconds=3600,
        dag=dag,
    )

    # 태스크 4: 학습
    train = KubernetesPodOperator(
        task_id='train',
        name='train-pod',
        namespace='default',
        image='ntw0403/autotrain:3.1',
        cmds=['python', 'train/main/train.py'],
        arguments=[
            '--cfg', config.get('output_file'),
            'MODEL.PRETRAINED', config.get('pretrained_model')
        ],
        container_resources=gpu_resources,
        node_selector={"gpu": "nvidia"},
        volumes=[pvc_volume, shm_volume],
        volume_mounts=volume_mounts + [shm_mount],
        kubernetes_conn_id='kubernetes_default',
        get_logs=True,
        is_delete_operator_pod=True,
        dag=dag,
    )

    # 태스크 의존성 설정
    preprocess >> make_experiments >> train

    return dag


# YAML 파일 경로 (Airflow가 읽을 수 있는 경로에 두거나 Airflow Variable로 경로를 전달)
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config/test_config.yaml')

with open(CONFIG_FILE, 'r') as f:
    config_data = yaml.safe_load(f)

    
for key, exp_config in config_data.get('experiments', {}).items():
    # config 파일 내의 'sc'와 'c' 값을 조합하여 DAG ID 생성
    sc = exp_config.get('sc')
    c = exp_config.get('c')
    dag_id = f"experiment_{sc}_{c}"
    globals()[dag_id] = create_experiment_dag(dag_id, exp_config)