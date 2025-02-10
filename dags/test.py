from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime
from kubernetes.client import models as k8s  # Kubernetes Python Client의 모델 가져오기

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 2, 3),
    'retries': 1,
    'retry_delay': 300,  # 재시도 간격(초)
}



# PVC 및 볼륨 설정
volume_config = k8s.V1Volume(
    name='my-pvc-volume',
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name='keypoint-test-pvc'  # PVC 이름
    )
)

volume_mounts = [
    k8s.V1VolumeMount(
        name='my-pvc-volume',
        mount_path='/app/data',     # 컨테이너 내부 경로
        sub_path='data'     # PVC 내부에서 data 폴더만 연결
    ),
    k8s.V1VolumeMount(
        name='my-pvc-volume',
        mount_path='/app/experiments',
        sub_path='experiments'
    ),
    k8s.V1VolumeMount(
        name='my-pvc-volume',
        mount_path='/app/models',
        sub_path='models'
    ),
    k8s.V1VolumeMount(
        name='my-pvc-volume',
        mount_path='/app/mlruns',
        sub_path='mlruns'
    )
]

# 1) shm 용도를 위한 emptyDir Volume 정의
volume_config_shm = k8s.V1Volume(
    name='dshm',
    empty_dir=k8s.V1EmptyDirVolumeSource(
        medium='Memory',      # RAM
        size_limit='8Gi'      # 8GB 예시
    )
)

volume_mount_shm = k8s.V1VolumeMount(
    name='dshm',
    mount_path='/dev/shm'
)




with DAG('test', default_args=default_args, schedule_interval=None) as dag:

    gpu_resources = k8s.V1ResourceRequirements(
        limits={'nvidia.com/gpu': '1'},
        requests={'nvidia.com/gpu': '1'}
    )
    
    # Task 1: 데이터 전처리
    preprocess = KubernetesPodOperator(
        task_id='preprocess',
        name='preprocess-pod',
        namespace='default',  # Kubernetes 네임스페이스
        image='ntw0403/autotrain:3.1',
        cmds=['python', 'make_dataset2.py'],
        arguments=[
            '-d', '{{ params.data_dir }}',
            '-ext', '{{ params.ext }}',
            '-n', '{{ params.n }}',
            '-sc', '{{ params.sc }}',
            '-c', '{{ params.c }}',
            '-tp', '{{ params.tp }}'
        ],
        params={
            'data_dir': 'data/front',
            'ext': 'png',
            'n': 24,
            'sc': 'body',
            'c': 'front',
            'tp': 0.7
        },
        volumes=[volume_config],
        volume_mounts=volume_mounts,
        kubernetes_conn_id='kubernetes_default',
        get_logs=True,
        is_delete_operator_pod=True,
        startup_timeout_seconds=3600,
        execution_timeout=None,
    )

    check_data = KubernetesPodOperator(
        task_id='check_data',
        name='check-data-pod',
        namespace='default',
        image='ntw0403/autotrain:3.1',
        
        # 핵심: sh -c로 설정
        cmds=["sh", "-c"],
        
        # 실행할 명령어들을 ;로 이어 하나의 문자열로 합쳐서 arguments에 전달
        arguments=[
            """
            echo "Current directory:";
            pwd;
            
            echo "Files in current directory:";
            ls -al;
            
            echo "Files in data:";
            ls -al data;
            
            echo "Sleeping for 15 seconds...";
            sleep 15
            """
        ],
        
        volumes=[volume_config],
        volume_mounts=volume_mounts,

        kubernetes_conn_id='kubernetes_default',
        get_logs=True,
        is_delete_operator_pod=True,
        startup_timeout_seconds=3600,
        execution_timeout=None,
    )



    # Task 2: 실험 설정
    make_experiments = KubernetesPodOperator(
        task_id='make_experiments',
        name='make-experiments-pod',
        namespace='default',
        image='ntw0403/autotrain:3.1',
        cmds=['python', 'make_experiments.py'],
        arguments=[
            '--num-keypoints', '{{ params.num_keypoints }}',
            '--flip-fairs', '{{ params.flip_fairs }}',
            '--data-format', '{{ params.data_format }}',
            '--data-root', '{{ params.data_root }}',
            '--begin-epoch', '{{ params.begin_epoch }}',
            '--end-epoch', '{{ params.end_epoch }}',
            '--config-file', '{{ params.config_file }}',
            '--output-file', '{{ params.output_file }}'
        ],
        params={
            'num_keypoints': 24,
            'flip_fairs': '[[1,4],[2,3],[5,7],[6,8],[9,10],[11,12],[13,14],[15,16],[17,19],[18,19],[21,23],[22,24]]',
            'data_format': 'png',
            'data_root': 'data/front',
            'begin_epoch': 50,
            'end_epoch': 300,
            'config_file': 'experiments/Auto/hrnet/w48_384x288_adam_lr1e-3.yaml',
            'output_file': 'experiments/Auto/hrnet/w48_384x288_adam_lr1e-3_auto_kube.yaml'
        },
        volumes=[volume_config],
        volume_mounts=volume_mounts,
        kubernetes_conn_id='kubernetes_default',
        get_logs=True,
        is_delete_operator_pod=True,
        startup_timeout_seconds=3600,
        execution_timeout=None,
    )

    # Task 3: 학습
    train = KubernetesPodOperator(
        task_id='train',
        name='train-pod',
        namespace='default',
        image='ntw0403/autotrain:3.1',
        cmds=['python', 'train/main/train.py'],
        arguments=[
            '--cfg', '{{ params.cfg }}',
            'MODEL.PRETRAINED', '{{ params.pretrained_model }}'
        ],
        params={
            'cfg': 'experiments/Auto/hrnet/w48_384x288_adam_lr1e-3_auto_kube.yaml',
            'pretrained_model': 'models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth',
            'run_name': "NTO_test"
        },
        
        
        
        container_resources=gpu_resources,
        node_selector={"gpu": "nvidia"},
        volumes=[volume_config, volume_config_shm],
        volume_mounts=volume_mounts + [volume_mount_shm],
        kubernetes_conn_id='kubernetes_default',
        get_logs=True,
        is_delete_operator_pod=True,
        startup_timeout_seconds=3600,
        execution_timeout=None,
    )

    # 태스크 순서 (원하는 대로 구성)
    preprocess >> check_data >> make_experiments >> train
