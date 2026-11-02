"""
infralib/testing/kubernetes -- Fake Kubernetes Client
=====================================================

This module contains a fake of the parts of the Kubernetes client module that
projects call while their programs run.
"""

from typing import Any, cast

import kubernetes


class _Annotations(dict[str, str]):
    """
    Annotations that hold a placeholder for any key that was not set, so that this
    fake does not need to know which annotations each project reads.
    """

    def __missing__(self, key: str) -> str:
        return f"fake-{key}"


def _object_meta(
    name: str, annotations: _Annotations
) -> kubernetes.client.V1ObjectMeta:
    """
    Builds object metadata without validation, which would copy the annotations
    into a plain dict and lose their placeholders.
    """
    return kubernetes.client.V1ObjectMeta.model_construct(
        name=name, annotations=annotations
    )


class FakeCoreV1Api:
    """
    Fake CoreV1Api. Every lookup succeeds and returns a placeholder object.
    """

    def __init__(self, backing_volume: str) -> None:
        self._backing_volume = backing_volume

    def list_node(
        self, label_selector: str | None = None
    ) -> kubernetes.client.V1NodeList:
        """
        Returns exactly one node.
        """
        node = kubernetes.client.V1Node(
            metadata=_object_meta(name="fake-node", annotations=_Annotations()),
            status=kubernetes.client.V1NodeStatus(
                addresses=[
                    kubernetes.client.V1NodeAddress(
                        type="InternalIP", address="192.0.2.1"
                    )
                ]
            ),
        )
        return kubernetes.client.V1NodeList(items=[node])

    def read_persistent_volume(self, name: str) -> kubernetes.client.V1PersistentVolume:
        """
        Returns a persistent volume whose namespace is "fake".
        """
        return kubernetes.client.V1PersistentVolume(
            metadata=_object_meta(
                name=name,
                annotations=_Annotations(
                    {
                        "backing-volume": self._backing_volume,
                        "namespace": "fake",
                        "user": "1000",
                        "group": "1000",
                        "mode": "0750",
                    }
                ),
            ),
            spec=kubernetes.client.V1PersistentVolumeSpec(
                access_modes=["ReadWriteOnce"],
                capacity={"storage": "1Gi"},
                local=kubernetes.client.V1LocalVolumeSource(path=f"/fake/{name}"),
                storage_class_name="fake",
                persistent_volume_reclaim_policy="Retain",
            ),
        )


class FakeKubernetesClient:
    """
    Fake of the kubernetes.client module, as used through
    ProviderFactory.kubernetes_client().
    """

    AppsV1Api: Any = None

    def __init__(self, backing_volume: str = "data0") -> None:
        self._core = FakeCoreV1Api(backing_volume)
        self.CoreV1Api = cast(Any, lambda: self._core)
