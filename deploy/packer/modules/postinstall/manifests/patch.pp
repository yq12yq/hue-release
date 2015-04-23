class postinstall::patch{
	#need to set some services in standby	
	file{'maintenance_script':
		ensure	=> file,
		path	=> "/tmp/put_in_maintenance.sh", 
		mode	=> '777',
		source	=> "puppet:///modules/postinstall/put_services_in_maintenance.sh"
	}

	exec{'put_maintenance':
		command	=> "bash -x /tmp/put_in_maintenance.sh",
		provider	=> 'shell',
		require	=>File['maintenance_script'],
		timeout	=> 0
	}
	#see bug BUG-34248 for this sed:
}
#include postinstall::patch
