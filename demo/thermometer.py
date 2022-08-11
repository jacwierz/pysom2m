import argparse
import logging
import random
from re import A
import signal
import sys
import time
import yaml

from pysom2m import Client, AE, FlexContainer, Node, MoDeviceInfo
from yaml.loader import BaseLoader


loop = True

def __sig_hnd__(signal_number, __notused__):
        global loop
        logging.warning("sig_handler, signal number {} received".format(signal_number))
        loop = False

if __name__ == "__main__":

    logging.basicConfig(format='%(asctime)s [ %(levelname)s ] %(name)s - %(message)s',
                        level=logging.DEBUG, filename=None)
    
    parser = argparse.ArgumentParser(prog="thermometer")
    parser.add_argument("--cfg", help="Path to yaml file containing application configuration. It is mandatory",
        required=True)
    argv = parser.parse_args()

    try:
        with open(argv.cfg, 'r') as f:
            config = yaml.load(f, Loader=BaseLoader)
        cse_addr = config['onem2m_server']['address']
        cse_name = config['onem2m_server']['name']
        originator = config['onem2m_server']['originator']

    except Exception as e:
        print("problem occurs processing configuratuin file '{}'".format(e))
        sys.exit(2)

    logging.info("== Start application ==")
    signal.signal(signal.SIGINT, __sig_hnd__)
    signal.signal(signal.SIGTERM, __sig_hnd__)

    # cse_addr = 'http://192.168.9.120:8090'
    device_name = 'thermometer'
    # device_id = Client.genid()
    device_id = '5a142e'


    local_ip = Client.get_local_ip(cse_uri=cse_addr)
    logging.info("local_ip = {}".format(local_ip))
    client = Client(cse_addr, originator=originator)

    device_rn = "{}_{}".format(device_name, device_id)

    ae = AE(api='sdt.mocked.thermometer',rr=True)
    ae.resource_name(device_rn)
    ae.set_attr('poa', "http://{}:8090/callback".format(local_ip))
    client.create_container(ae)

    device = FlexContainer(cnd='org.onem2m.common.device.Thermometer',attr_list=['nl', 'flNLk'])
    device.resource_name("DEVICE_" + device_rn)
    # device.set_attr('nl', node.attr['ri'])
    client.create_container(device, parent=ae)

    node = Node("{}".format(device_id))
    node.resource_name('NODE_' + device_rn)
    node.add_hosted_ae_link(ae.attr['ri'])
    node.add_hosted_Service_Link(device.attr['ri'])
    client.create_container(node)

    mngt_dvi = MoDeviceInfo()
    mngt_dvi.resource_name('deviceInformation')
    mngt_dvi.device_label('S/N 20220001')
    mngt_dvi.manufacturer('com.github/jacwierz')
    mngt_dvi.deviceType('thermometer')
    mngt_dvi.deviceName('room 244')
    client.create_container(mngt_dvi, node)

    device.set_attr('nl', node.attr['ri'])
    device.mark_attributes_to_update(attr_list=['nl'])
    client.update_container(device)

    temp_value = 10.0

    # Datapoints
    # currentTemperature (curT0),  minValue (minVe),  maxValue (maxVe)
    # unit (unit): C or F or K
    temp = FlexContainer(cnd='org.onem2m.common.moduleclass.temperature', 
        attr_list=['curT0', 'unit', 'minVe', 'maxVe'])
    temp.resource_name('temperature')
    temp.set_attr('curT0', temp_value)
    temp.set_attr('unit', 'C')
    temp.set_attr('minVe', -40)
    temp.set_attr('maxVe', 50)
    client.create_container(temp, device)

    batery_level = 98.01

    # Datapoints
    # level (lvl) 0-100%, capacity (capay) mAh, lowBattery (lowBy) true/false,
    battery =  FlexContainer(cnd='org.onem2m.common.moduleclass.battery',
        attr_list=['lvl', 'capay', 'lowBy' ])
    battery.resource_name('battery')
    battery.set_attr('lvl', int(batery_level))
    battery.set_attr('capay', 2500)
    battery.set_attr('lowBy', False)
    client.create_container(battery, parent=device)

    t = 0
    while loop:
        time.sleep(1)
        t += 1 

        if t %30 == 0:
            rnd_tmp = 0.5 if random.randint(0,9) > 4 else -0.5
            temp_value += rnd_tmp
            if temp_value > 50:
                temp_value = 50
            if temp_value < -40:
                temp_value = -40
        
            temp.set_attr('curT0', temp_value)
            temp.mark_attributes_to_update(attr_list=['curT0'])
            client.update_container(temp)


        if t % 60 == 0:
            batery_level -= 0.1  

            if batery_level < 5:
                batery_level = 98.0
                battery.set_attr('lowBy', False)
            elif batery_level < 10:
                battery.set_attr('lowBy', True)
        
            battery.set_attr('lvl', int(batery_level))
            battery.mark_attributes_to_update(attr_list=['lvl', 'lowBy'])
            client.update_container(battery)       

    client.close()
    logging.info("== Aplication Exiting ==")


    