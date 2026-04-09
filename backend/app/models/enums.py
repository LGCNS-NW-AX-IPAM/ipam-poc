from enum import Enum

class ReclaimStatus(str, Enum):
    READY = "Ready"
    IN_PROGRESS = "In-Progress"
    RELEASED = "Released"
    FAILED = "Failed"

class DetailStatus(str, Enum):
    READY = "Ready"
    IN_PROGRESS = "In-Progress"
    DHCP_REQUESTED = "DHCP_REQUESTED"
    DHCP_SUCCESS = "DHCP_SUCCESS"
    DHCP_FAILED = "DHCP_FAILED"
    DEVICE_REQUESTED = "DEVICE_REQUESTED"
    DEVICE_SUCCESS = "DEVICE_SUCCESS"
    DEVICE_FAILED = "DEVICE_FAILED"
