# Webferea

This is a web counterpart to the GTK+ news aggregator [Liferea](https://lzone.de/liferea/ "Liferea"). Webferea syncs the sqlite-database of Liferea over ssh on a server which runs your Webferea instance. You can read selected feeds over the webinterface and flag their entites as *read* or *marked*. On the next sync, the flags are applied to your sqlite-database of Liferea and new entitites are uploaded to the web.

You can only access your feed list with a correct password, which you can set in the config. In the config you can list all feeds which unread items should be listed in Webferea.

The layout of the webinterface is optimized for the use on a smartphone.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes or on your server for production usage.

### Prerequisites

- [python 3.*](https://www.python.org)
- [Flask >=0.12.2](http://flask.pocoo.org)

### Installing

First of all, clone the files from the repository into a directory on your server and a directory on your desktop pc, who runs Liferea.

```
git clone https://github.com/CydNoxzed/webferea.git
```

### Server

Edit the configuration file *config_server.py* on your server, till it fits your needs.

If you want to use FCGI, you need to customize Webferea. [Here is a tutorial](http://flask.pocoo.org/docs/0.12/deploying/fastcgi/).

You can start webferea by creating a screen-session and start the *webferea.py* in it. You should proxy the traffic over a webserver to use SSL. Here a few example configurations for the webserver.

#### lighttpd
```
$HTTP["host"]=~"myserver.de" {
    proxy.server = ( "" => ((
        "host" => "127.0.0.1",
        "port" => "5665",
    )))
}
```

#### nginx
```
server {
    server_name myserver.de;
    proxy_set_header X-Forwarded-For $remote_addr;
    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_pass http://127.0.0.1:5665;
        proxy_buffering off;
        proxy_connect_timeout  36000s;
        proxy_read_timeout  36000s;
        proxy_send_timeout  36000s;
        send_timeout  36000s;
        client_max_body_size 0;
    }
}
```

### Client

Edit the *config_client.py* config file.

With the skript *webferea_backsync.py* you can download the database from the server and sync the flags back to your desktop liferea database.

If you want to, you can create a cronjob who starts this script and syncs the databases in the background.

After the sync you should restart Liferea, to see the proper sums of the unread items on every feed.


## Versioning

This project uses [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags).
For the changelog, see the [CHANGELOG.md](CHANGELOG.md) file for details.

## License

This project is licensed under the GPLv3 License - see the [LICENSE.md](LICENSE.md) file for details


## Known Bugs

- The links inside the entities are relative, thus they link to the server where webferea is hosted
- Text after embedded Youtube videos is not shown

## Planned Features

- Replace ssh database down/upload with http
- FCGI
