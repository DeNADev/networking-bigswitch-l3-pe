networking-bigswitch-l3-pe
==========================

This is the OpenStack Neutron ML2 Driver for Big Cloud Fabric Physical Edition.

What the plugin does
--------------------
The plugin synchronizes networks and subnets in OpenStack with BCF. The plugin
periodically does the following:

 * The plugin checks if configurations related to networks and subnets in OpenStack
   exist in BCF. If configurations don't exist, the plugin adds them to BCF.
   * When adding a network, the plugin adds the following configurations.
   ```
    tenant project_example.openstack
      logical-router
        route 0.0.0.0/0 next-hop tenant system
        interface segment net_example
        interface tenant system
    tenant system
      logical-router
        interface tenant admin.openstack
   ```
   * When adding a subnet, the plugin adds the following configurations.
   ```
    tenant project_example.openstack
      logical-router
        interface segment net_example
          ip address 10.0.0.1/24
   ```
 * The plugin checks if networks and subnets related to BCF configurations exist
   in OpenStack. If networks and subnets don't exist, the plugin removes the
   configurations from BCF.

How to install
--------------
You can install the plugin by executing the following command.

    $ sudo python setup.py install

How to use
----------
You can enable the plugin as the Neutron mechanism_drivers with bsn_ml2 plugin
in ```/etc/neutron/plugins/ml2/ml2_conf.ini```.

    [ml2]
    mechanism_drivers = bsn_ml2,networking_bigswitch_l3_pe

You can configure these parameters.

    [networking_bigswitch_l3_pe]
    api_url = https://<bcf_controller>:8443/api/v1
    sync_interval = 600

The plugin uses these parameters in restproxy section.

    [restproxy]
    server_auth = admin:password
    neutron_id = neutron_name
