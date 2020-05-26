#!/usr/bin/env python
"""
This application is used to get the inventory of All Optics in the Fabric
It largely uses raw queries to the APIC API
"""
import acitoolkit.acitoolkit as ACI
from acitoolkit import Credentials, Session
from tabulate import tabulate
import logging
logging.basicConfig()


def interface_detail(apic, args, intf_ids):
    """
    Gather the Inventory of Optics in each Switch.  If the LLDP Neighbor is Defined Add as well.
    :param apic: Session instance logged in to the APIC
    :param args: Command line arguments
    :param intfs_ids: List of (node_id, intf)
    :return: None
    """
    data = []
    headers = []
    for list in intf_ids:
        node,switch_intf = list
        #print(node)
        #print(switch_intf)
        query_url_1 = ('/api/node/mo/topology/pod-1/node-%s/sys/phys-[%s]/phys.json'
                       '?query-target=children&target-subtree-class=ethpmFcot&subscription=yes' % (node, switch_intf))
        query_url_2 = ('/api/node/mo/topology/pod-1/node-%s/sys/lldp/inst/if-[%s].json'
                       '?query-target=children&target-subtree-class=lldpAdjEp' % (node, switch_intf))
        resp1 = apic.get(query_url_1)
        if not resp1.ok:
            print('Could not collect Optic data for switch %s Interface %s.' % node, switch_intf)
            print(resp1.text)
            return
        resp2 = apic.get(query_url_2)
        if not resp2.ok:
            print('Could not collect LLDP Neigbhor data for switch %s Interface %s.' % node, switch_intf)
            print(resp2.text)
            return
        for obj1 in resp1.json()['imdata']:
            obj_attr1 = obj1['ethpmFcot']['attributes']
            if obj_attr1['typeName'] == '':
                optic = '--'
            else:
                optic = obj_attr1['typeName']
            for obj2 in resp2.json()['imdata']:
                obj_attr2 = obj2['lldpAdjEp']['attributes']
                if obj_attr2['sysName'] == '':
                    neighbor = '--'
                else:
                    neighbor = obj_attr2['sysName']
                if obj_attr2['portIdV'] == '':
                    port = '--'
                else:
                    port = obj_attr2['portIdV']
                data.append((node, switch_intf, optic, neighbor, port))
    headers = ["Switch", "Interface", "Optic", "LLDP Neighbor", "Neighbor Interface"]
    if len(headers) and len(data):
        print(tabulate(data, headers=headers))
        print('\n')


def get_intf_ids(apic, args, node_ids):
    """
    Get the list of Physical Interface IDs from the APIC API.
    :param apic: Session instance logged in to the APIC
    :return: List of strings containing Node_ID and Interface ids
    """
    intfs = []
    for node_id in node_ids:
        if args.interface is not None:
            intx = node_id,str(args.interface)
            intfs.append(intx)
        else:
            query_url = ('/api/node/class/topology/pod-1/node-%s/l1PhysIf.json?'
                         'rsp-subtree=children&rsp-subtree-class=ethpmPhysIf' % (node_id))
                         
            resp = apic.get(query_url)
            if not resp.ok:
                print('Could not get Interface list from APIC.')
                return
            ints = resp.json()['imdata']
            for int in ints:
                intx = node_id,str(int['l1PhysIf']['attributes']['id'])
                #print intx
                intfs.append(intx)
    return intfs

def get_node_ids(apic, args):
    """
    Get the list of node ids from the APIC or use the CLI Argument to capture.
    If none, get all of the node ids
    :param apic: Session instance logged in to the APIC
    :param args: Command line arguments
    :return: List of strings containing node ids
    """
    if args.switch is not None:
        names = [args.switch]
    else:
        names = []
        query_url = ('/api/node/class/fabricNode.json?'
                     'query-target-filter=or(eq(fabricNode.role,"leaf"),'
                     'eq(fabricNode.role,"spine"))')
                     
        resp = apic.get(query_url)
        if not resp.ok:
            print('Could not get switch list from APIC.')
            return
        nodes = resp.json()['imdata']
        for node in nodes:
            #print(node['fabricNode']['attributes']['id'])
            names.append(str(node['fabricNode']['attributes']['id']))
    return names


def main():
    """
    Main common routine for show interface description
    :return: None
    """
    # Set up the command line options
    description = ('Simple application that logs in to the APIC'
                   'and displays the Interface Optics and Neighbors')
    creds = ACI.Credentials('apic', description)
    creds.add_argument('-s', '--switch',
                       type=str,
                       default=None,
                       help='Specify a particular switch id, e.g. "101"')
    creds.add_argument('-i', '--interface',
                       type=str,
                       default=None,
                       help='Specify a specific interface, e.g. "eth1/1"')
    args = creds.get()

    # Login to APIC
    apic = ACI.Session(args.url, args.login, args.password)
    resp = apic.login()
    if not resp.ok:
        print('%% Could not login to APIC')
        return

    # Show interface Optic & LLDP Neighbor
    #print('starting node_ids')
    node_ids = get_node_ids(apic, args)
    #print('starting intf_ids')
    intf_ids = get_intf_ids(apic, args, node_ids)
    #print('starting Section for Optics and Neighbors')
    details = interface_detail(apic, args, intf_ids)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
