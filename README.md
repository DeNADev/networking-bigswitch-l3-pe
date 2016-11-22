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
        interface tenant project_example.openstack
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
Before enabling the plugin in neutron-server, You can execute bcf-sync-l3
command to check what the plugin will do.

    $ cd /path/to/networking_bigswitch_l3_pe
    # This is dry run mode. You can check what bcf-sync-l3 will do.
    $ sudo PYTHONPATH=.. ./bin/bcf-sync-l3
    No handlers could be found for logger "oslo_config.cfg"
    2016-11-22 17:38:38,388 - networking_bigswitch_l3_pe.lib.synchronizer - INFO - This is dry run mode.
    2016-11-22 17:38:38,388 - networking_bigswitch_l3_pe.lib.synchronizer - INFO - Start synchronization: events=None
    2016-11-22 17:38:38,596 - networking_bigswitch_l3_pe.lib.synchronizer - DEBUG - exclude_networks=[]
    2016-11-22 17:38:38,596 - networking_bigswitch_l3_pe.lib.synchronizer - INFO - Adding networks: [{'project_name': u'project_example.openstack', 'segment_name': u'net_example'}]
    2016-11-22 17:38:38,597 - networking_bigswitch_l3_pe.lib.synchronizer - INFO - Finished synchronization(dry run mode): synchronized resources: {'added': {'network': [{'project_name': u'project_example.openstack', 'segment_name': u'net_example'}]}}.
    # If there is no problem, You can run bcf-sync-l3 in execution mode.
    $ sudo PYTHONPATH=.. ./bin/bcf-sync-l3  -x
    No handlers could be found for logger "oslo_config.cfg"
    2016-11-22 17:38:42,529 - networking_bigswitch_l3_pe.lib.synchronizer - INFO - Start synchronization: events=None
    2016-11-22 17:38:42,724 - networking_bigswitch_l3_pe.lib.synchronizer - DEBUG - exclude_networks=[]
    2016-11-22 17:38:42,725 - networking_bigswitch_l3_pe.lib.synchronizer - INFO - Adding networks: [{'project_name': u'project_example.openstack', 'segment_name': u'net_example'}]
    2016-11-22 17:38:43,287 - networking_bigswitch_l3_pe.lib.synchronizer - INFO - Finished synchronization: synchronized resources: {'added': {'network': [{'project_name': u'project_example.openstack', 'segment_name': u'net_example'}]}}.

You can enable the plugin as the Neutron mechanism_drivers with bsn_ml2 plugin
in ```/etc/neutron/plugins/ml2/ml2_conf.ini```.

    [ml2]
    mechanism_drivers = bsn_ml2,networking_bigswitch_l3_pe

You can configure these parameters.

    [networking_bigswitch_l3_pe]
    api_url = https://<bcf_controller>:8443/api/v1
    sync_interval = 600
    exclude_physical_networks = physnet2

The plugin uses these parameters in restproxy section.

    [restproxy]
    server_auth = user:password
    neutron_id = neutron_name
