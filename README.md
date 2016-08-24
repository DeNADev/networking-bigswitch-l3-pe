networking-bigswitch-l3-pe
==========================

This is the OpenStack Neutron ML2 Driver for Big Cloud Fabric Physical Edition.

What the plugin does
--------------------
The plugin syncs logical routers with BCF Physical Edition. Specifically, the plugin does the following:

 * When a network is created in OpenStack, the plugin creates tenant interfaces and
   a segment interface and adds a static route to the system tenant.
   When the network is deleted, the plugin deletes them.
 * When a subnet is created in OpenStack, the plugin assigns the gateway ip address
   to the segment interface.
   When the subnet is deleted, the plugin remove the address from the interface.

How to install
--------------
You can install the plugin by executing the following command.

    $ sudo python setup.py install

How to use
----------
You can enable the plugin as the Neutron mechanism_drivers with bsn_ml2 plugin in ```/etc/neutron/plugins/ml2/ml2_conf.ini```.

    [ml2]
    mechanism_drivers = bsn_ml2,networking_bigswitch_l3_pe

The BCF API URL should be configured as follows.

    [networking_bigswitch_l3_pe]
    api_url  = https://<bcf_controller>:8443/api/v1

The plugin uses these parameters in restproxy section.

    [restproxy]
    server_auth = admin:password
    neutron_id = neutron_name
