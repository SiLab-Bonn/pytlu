import logging

import zmq


def init(socket_address="tcp://127.0.0.1:5500"):
    logging.info('Creating ZMQ context')
    context = zmq.Context()
    logging.info('Creating socket connection to server %s', socket_address)
    socket = context.socket(zmq.PUB)  # publisher socket
    socket.bind(socket_address)
    # send reset to indicate a new scan
    send_meta_data(socket, None, name='Reset')
    return socket


def send_meta_data(socket, conf, name):
    '''Sends the config via ZeroMQ to a specified socket. Is called at the beginning of a run and when the config changes. Conf can be any config dictionary.
    '''
    meta_data = dict(
        name=name,
        conf=conf
    )
    try:
        socket.send_json(meta_data, flags=zmq.NOBLOCK)
    except zmq.Again:
        pass


def send_data(socket, data, len_raw_data, scan_parameters={}, name='ReadoutData'):
    '''Sends the data of every read out (raw data and meta data) via ZeroMQ to a specified socket
    '''
    if not scan_parameters:
        scan_parameters = {}
    data_meta_data = dict(
        name=name,
        dtype=str(data[0].dtype),
        shape=data[0].shape,
        data_length=len_raw_data,  # data length
        timestamp_start=data[1],  # float
        timestamp_stop=data[2],  # float
        readout_error=data[3],  # int
        skipped_triggers=data[4],  # skipped trigger counter
        scan_parameters=scan_parameters  # dict
    )
    try:
        socket.send_json(data_meta_data, flags=zmq.SNDMORE | zmq.NOBLOCK)
        # PyZMQ supports sending numpy arrays without copying any data
        socket.send(data[0], flags=zmq.NOBLOCK)
    except zmq.Again:
        pass


def close(socket):
    if socket is not None:
        logging.info('Closing socket connection')
        socket.close()  # close here, do not wait for garbage collector
