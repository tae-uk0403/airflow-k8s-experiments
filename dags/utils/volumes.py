# common_config.py
from kubernetes.client import models as k8s

def get_pvc_volume():
    return k8s.V1Volume(
        name='my-pvc-volume',
        persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
            claim_name='keypoint-test-pvc'
        )
    )

def get_volume_mounts():
    return [
        k8s.V1VolumeMount(name='my-pvc-volume', mount_path='/app/data', sub_path='data'),
        k8s.V1VolumeMount(name='my-pvc-volume', mount_path='/app/experiments', sub_path='experiments'),
        k8s.V1VolumeMount(name='my-pvc-volume', mount_path='/app/models', sub_path='models'),
        k8s.V1VolumeMount(name='my-pvc-volume', mount_path='/app/mlruns', sub_path='mlruns')
    ]

def get_shm_volume_and_mount():
    shm_volume = k8s.V1Volume(
        name='dshm',
        empty_dir=k8s.V1EmptyDirVolumeSource(
            medium='Memory',
            size_limit='32Gi'
        )
    )
    shm_mount = k8s.V1VolumeMount(
        name='dshm',
        mount_path='/dev/shm'
    )
    return shm_volume, shm_mount

def get_gpu_resources():
    return k8s.V1ResourceRequirements(
        limits={'nvidia.com/gpu': '1'},
        requests={'nvidia.com/gpu': '1'}
    )






