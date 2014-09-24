class install::ambari-server{

  include install::ambari-agent

  package {"ambari-server":
    ensure => installed,
    require => Exec["ambari-repo"]
  }

  exec {"ambari-server setup":
    command => 'ambari-server setup -j `source /etc/profile.d/java.sh; echo $JAVA_HOME` -s',
    require => [Package["ambari-server"]]
  }


  exec {"ambari-server start":
    command => "ambari-server start",
    require => [Exec["ambari-server setup"]]
  }


  file {"/tmp/install/check-ambari-hosts.sh":
    source => "puppet:///modules/install/check-ambari-hosts.sh"
  }

  file {"/tmp/install/check_hosts.py":
    source => "puppet:///modules/install/check_hosts.py"
  }

  exec {"wait for ambari register hosts":
    require => [Exec["ambari-server start"], Class["install::ambari-agent"],File["/tmp/install/check-ambari-hosts.sh"],File["/tmp/install/check_hosts.py"]],
    command => "/bin/bash /tmp/install/check-ambari-hosts.sh",
    timeout => 1000
  }

}
