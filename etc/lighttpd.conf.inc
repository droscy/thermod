# Basic lighttpd configuration file for Thermod web interface.

server.modules += ( "mod_proxy", "mod_rewrite" )

# Change '<WEB-FILE-PATH>' with the path where you copied the web files.
alias.url += ( "/thermod" => "<WEB-FILE-PATH>" )

# Workaround to proxy and rewrite the requests to socket on lighttpd 1.4 as
# documented in the bug report http://redmine.lighttpd.net/issues/164#note-9.
$HTTP["url"] =~ "^/thermod/socket/" {
  proxy.server = ( "" => ( "" => ( "host" => "127.0.0.1", "port" => 4345 )))
}

# Change '127.0.0.1' with the IP address of the host where Thermod is running.
$SERVER["socket"] == ":4345" {
  url.rewrite-once = ( "^/thermod/socket/(.*)$" => "/$1" )
  proxy.server = ( "" => ( "" => ( "host" => "127.0.0.1", "port" => 4344 )))
}

