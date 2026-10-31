from config import default_config
from schroedinger.states import get_wave_packet as _get_wave_packet

def get_wave_packet(config=default_config):
    return _get_wave_packet(config)
