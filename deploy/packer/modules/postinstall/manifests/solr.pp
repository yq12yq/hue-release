class postinstall::solr{

  exec {"download solr":
    command => "wget -O /opt/solr.tar.gz http://mirror.reverse.net/pub/apache/lucene/solr/4.7.2/solr-4.7.2.tgz && tar xvf solr.tar.gz && rm solr.tar.gz",
    cwd => "/opt",
    timeout => 0
  }
  
  
}
