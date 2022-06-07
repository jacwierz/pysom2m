import requests
import json
import uuid
import logging
from urllib.parse import urlparse
import socket

from .containers import AE, Node, BasicContainer

class Client:

    def genid(length=6):
        return uuid.uuid4().hex[0:length]

    def get_local_ip(cse_uri=None):

        netloc = urlparse(cse_uri)[1]
        (host, port) = netloc.split(':')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((host, int(port)))
        local_ip = "{}".format(s.getsockname()[0])
        s.close()
        return local_ip

    def __init__(self, cse_address, originator='admin:admin', cse_name='in-name', local_ip=None, local_port=8080):

        self.logger = logging.getLogger('onem2m.client')

        if cse_address:
            self.cse_address = cse_address
        else:
            raise ValueError("CSE address is not defined")

        self.originator = originator
        self.cse_name = cse_name

        # self.app_uri = None # do skasowania
        # Top level container resource name. In this implementation only AE and Node containers
        self.top_level_cnt_rn = set()
        self.app_ri = None
        # self.ri_ids_map = dict()

    def get_local_address(self):
        return self.interface_ip

    def create_ae(self, ae):
        if not isinstance(ae, AE):
            raise ValueError("Client.create_ae: ae is not instance of AE")

        headers = dict()
        headers['Content-Type'] = ae.get_content_type()
        headers['Accept'] = 'application/json'
        headers['X-M2M-Origin'] = self.originator

        if 'rn' in ae.attr: 
            self.delete_container(local_rn=ae.attr['rn'])  
            # self.app_uri = "{}/{}".format(cse_url, ae.attr['rn'])
            # self.delete_ae()

        cse_url = "{}/{}".format(self.cse_address, self.cse_name)
        resp = requests.post(cse_url, headers=headers, data=ae.get_body(create=True), timeout=10)
        self.print_http(resp)

        if resp.status_code == 201:
            obj = json.loads(resp.text)[ae.ns]
            rn = obj['rn']
            self.top_level_cnt_rn.add(rn)
            ae.attr['rn'] = rn
            # self.app_uri = "{}/{}".format(cse_url, ae.attr['rn'])
            # self.app_ri = obj['ri']
            ae.attr['ri'] = obj['ri']
        else:
            raise Exception("Server returns {} code, AE not created".format(resp.status_code))

    def delete_ae(self, ae):
        # headers = dict()
        # headers['X-M2M-Origin'] = self.originator
        # # resp = self.http.request('DELETE', self.app_uri, headers=headers)
        # resp = requests.delete(self.app_uri, headers=headers, timeout=10)
        # self.print_http(resp)
        pass

    def create_container(self, container=None, parent=None):

        parent_ri = None
        uri = None

        headers = dict()
        headers['Content-Type'] = container.get_content_type()
        headers['Accept'] = 'application/json'
        headers['X-M2M-Origin'] = self.originator

        if isinstance(parent, BasicContainer):
            parent_ri = parent.attr.get('ri')

        if isinstance(container, AE):
            if 'rn' in container.attr: 
                del_ae_uri = "{}/{}/{}".format(self.cse_address, self.cse_name, container.attr['rn'])
                resp = requests.delete(del_ae_uri, headers=headers, timeout=5)
                self.print_http(resp)

            uri = "{}/{}".format(self.cse_address, self.cse_name)

        elif isinstance(container, Node):
            if 'rn' in container.attr:
                del_ae_uri = "{}/{}/{}".format(self.cse_address, self.cse_name, container.attr['rn'])
                resp = requests.delete(del_ae_uri, headers=headers, timeout=5)
                self.print_http(resp) 
            uri = "{}/{}".format(self.cse_address, self.cse_name)

        elif isinstance(container, BasicContainer):
            if not parent_ri:
                raise ValueError("Client.create_container 'parent.attr.ri' not defined")
            uri = "{}/\x7e{}".format(self.cse_address, parent_ri)
        else:
            raise ValueError("Client.create_container 'container' is not instance of BasicContainer")

        

        resp = requests.post(uri, headers=headers, data=container.get_body(create=True), timeout=10)
        self.print_http(resp)

        if resp.status_code == 201:
            obj = json.loads(resp.text)[container.ns]
            container.attr['ri'] = obj['ri']
            container.attr['rn'] = obj['rn']
            container.m2m_client_ref = self
        else:
            raise Exception("Server returns {} code, container not created".format(resp.status_code))

        if container.ty == 2 or container.ty == 14:
            self.top_level_cnt_rn.add(container.attr['rn'])


    def update_container(self, container):

        if not isinstance(container, BasicContainer):
            raise ValueError("Client.update_container container is not instance of BasicContainer")

        headers = dict()
        headers['Content-Type'] = container.get_content_type()
        headers['Accept'] = 'application/json'
        headers['X-M2M-Origin'] = self.originator
        uri = "{}/\x7e{}".format(self.cse_address, container.attr['ri'])
        resp = requests.put(uri, headers=headers, data=container.get_body(create=False), timeout=10)
        self.print_http(resp)

        if resp.status_code != 200:
            raise Exception("Server returns {} code, container not updated".format(resp.status_code))


    def delete_container(self, ri=None, local_rn=None):
        headers = dict()
        headers['X-M2M-Origin'] = self.originator
        if ri:
            uri = "{}/\x7e{}".format(self.cse_address, ri)
        elif local_rn:
            uri = "{}/{}/{}".foramt(self.cse_address, self.cse_name, local_rn)
        else:
            raise ValueError("delete_container error; neither 'resource name (rn)' nor 'resource id (ri) not defined")

        resp = requests.delete(uri, headers=headers, timeout=5)
        self.print_http(resp)

    def close(self):
        headers = dict()
        headers['X-M2M-Origin'] = self.originator
        for cnt_rn in self.top_level_cnt_rn:
            uri = "{}/{}/{}".format(self.cse_address, self.cse_name, cnt_rn)
            resp = requests.delete(uri, headers=headers, timeout=5)
            self.print_http(resp)
             

    def print_http(self, response):

        req = response.request
        text = list()
        text.append('http trace:')
        text.append("< {} {}".format(req.method, req.url))
        for header in req.headers:
            text.append("< {}: {}".format(header, req.headers[header]))
        text.append('< ')
        if req.body:
            for body_line in req.body.split('\n'):
                text.append("< {}".format(body_line))

        text.append('')

        text.append("HTTP/1.1 {}".format(response.status_code))
        for header in response.headers:
            text.append("> {}: {}".format(header,response.headers[header]))

        text.append('> ')

        if response.text:
            for body_line in response.text.split('\n'):
                text.append("> {}".format(body_line))

        self.logger.info("\n".join(text))

    def __str__(self):
        return "cse_address={}, originator={}, cse-name={}, app_uri={}".format(
            self.cse_address, self.originator, self.cse_name, self.app_uri)
