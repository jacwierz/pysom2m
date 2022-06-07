import base64
import json


class BasicContainer:
    
    def __init__(self, ty=None, ns=None, attr_list=[]):
        self.attr = dict()
        if ty:
            self.ty = ty
        else:
            raise ValueError("BasicContainer: containter type (ty) must be defined")
        if ns:
            self.ns = ns
        else:
            raise ValueError("BasicContainer: containter namespace (ns) must be defined")
        self.attr_list = attr_list
        self.attr_list_to_update = attr_list
        self.m2m_client_ref = None


    def resource_name(self, rn):
        if rn:
            self.attr['rn'] = rn


    def set_attr(self, name, value):
        if not name:
            return
        if name in self.attr_list:
            self.attr[name] = value


    def get_attr(self, name):
        return self.attr.get(name) 


    def mark_attributes_to_update(self, attr_list=None):
        if attr_list and isinstance(attr_list, (list, tuple)):
            self.attr_list_to_update = attr_list
        else:
            raise ValueError("BasicContainer.update(): attr_list must be instance of list or tuple")


    def get_content_type(self):
        return "application/json;ty={}".format(self.ty)


    def body_value_converter(self, attr, value):
         return value


    def get_body(self, create=False):

        b1 = dict()
        if create:
            for attr in self.attr:
                b1[attr] = self.body_value_converter(attr, self.attr[attr])
        else:
            for attr in self.attr_list_to_update:
                if attr in self.attr:
                    b1[attr] = self.body_value_converter(attr, self.attr[attr])
    
        b2 = dict()
        b2[self.ns] = b1
        return json.dumps(b2, indent=2)


    def __str__(self):
        al = []
        for key, val in self.attr.items():
            al.append("{}=>'{}'".format(key, str(val)))
        return ", ".join(al)


class AE(BasicContainer):

    
    def __init__(self, rr=False, api=None):
        if not api:
            raise ValueError("AE: App-ID (api) property must be set")
        super().__init__(ty=2, ns='m2m:ae', attr_list=['api', 'rr', 'poa'])
        self.set_attr('api', api)
        self.set_attr('rr', rr)
    
    def resource_name(self, rn):
        if rn:
            self.attr['rn'] = 'AE_' + rn


class Node(BasicContainer):
    '''
    nodeID: (ni) - mandatory
    hostedAELinks: (hael) - optional
    hostedServiceLinks: (hsl) - optional
    '''
    def __init__(self, node_id):
        super().__init__(ty=14, ns='m2m:nod', attr_list=['ni','hael', 'hsl'])
        if node_id:
            self.set_attr('ni', node_id)
        else:
            raise ValueError("Node: node_id must be set")
        

    def add_hosted_ae_link(self, hosted_ae_link_ri):
        '''
        This attribute allows to find the AEs hosted by the node that is represented by this <node> resource. 
        The attribute shall contain a list of resource identifiers of <AE> resources representing the ADN-AEs 
        residing on the node that is represented by the current <node> resource. In case the node that 
        is represented by this <node> resource does not contain an AE, this attribute shall not be present.
        '''
        if not self.get_attr('hael'):
            self.set_attr('hael', list())
        hosted_ae_links = self.get_attr('hael')
        if hosted_ae_link_ri in hosted_ae_links:
            return
        else:
            hosted_ae_links.append(hosted_ae_link_ri)

    def add_hosted_Service_Link(self, hosted_service_link_ri):
        '''
        This attribute allows to find <flexContainer> resources that have been created by an IPE to represent 
        services hosted on a NoDN, the NoDN being represented by this <node> resource. If the NoDN hosts a set 
        of services  represented by <flexContainer>s, then the attribute shall contain the list of resource 
        identifiers of these <flexContainer> resources. In case the node that is represented by this <node> 
        resource does not contain an service that is represented by a <flexContainer>, this attribute shall 
        not be present.
        '''
        if not self.get_attr('hsl'):
            self.set_attr('hsl', list())
        hosted_service_links = self.get_attr('hsl')
        if hosted_service_link_ri in hosted_service_links:
            return
        else:
            hosted_service_links.append(hosted_service_link_ri)


class MoDeviceInfo(BasicContainer):
    
    def __init__(self, ty=None, ns=None, attr_list=[]):
        super().__init__(ty=13, ns='m2m:dvi', attr_list=['mgd', 'dlb', 'man', 'dty', 'dvnm'])
        self.set_attr('mgd', 1007)

    def device_label(self, label):
        '''
        Unique device label assigned by the manufacturer. 
        The value of the attribute typically exposes the device’s serial number that is specific 
        to a manufacturer and possibly further restricted within the manufacturer by a deviceType or model. 
        '''
        self.set_attr('dlb', label)
    
    def manufacturer(self, man):
        '''
        The name/identifier of the device manufacturer.
        '''
        self.set_attr('man', man)
    
    def deviceType(self, dty):
        '''
        The type (e.g. cell phone, photo frame, smart meter) or product class (e.g. X-series) of the device.
        '''
        self.set_attr('dty', dty)

    def deviceName(self, dvnm):
        self.set_attr('dvnm', dvnm)


class SemanticDescriptor(BasicContainer):

    def __init__(self):
        super().__init__(ty=24, ns='m2m:smd', attr_list=['dcrp', 'dsp'])

    def body_value_converter(self, attr, value):
        if attr == 'dsp':
            bytes = value.encode('utf8')
            return base64.b64encode(bytes).decode('ascii')
        else:
            return  value


class FlexContainer(BasicContainer):

    def __init__(self, cnd=None, ns='m2m:fcnt', attr_list=[]):
        if not cnd:
            raise ValueError("FlexContainer container definition (cnd) proprety must be defined")
        attr_list.insert(0, 'cnd')
        super().__init__(ty=28, ns=ns, attr_list=attr_list)
        self.set_attr('cnd', cnd)
    

if __name__ == "__main__":

    containers = [] 

    ae = AE(api="com.orange.ipcam")
    ae.resource_name('IPCAM')
    ae.set_attr('poa', 'https://127.0.0.1:8090/callback')
    containers.append(ae)

    fc = FlexContainer(cnd='org.onem2m.common.device.deviceLight', attr_list=['pDANe'])
    fc.set_attr('pDANe', "W pokoju 404")
    containers.append(fc)


    sd1 = SemanticDescriptor()
    sd1.set_attr('dcrp', 'application/rdf+xml:1')
    sd1.set_attr('dsp', "ABCDEFGHIJKLMNOPRSTUWXYZ-abcdefghijklmnoprstuwxyz")
    containers.append(sd1)
    


    for cont in containers:
        print("-" * 80)
        print(cont)
        print("-" * 80)
        print(cont.get_content_type())
        print(cont.get_body(create=True))

        